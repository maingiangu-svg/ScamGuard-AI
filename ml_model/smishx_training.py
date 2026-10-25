"""Isolated SmishX SMS expansion; preserve published labels and old holdouts."""
import argparse
import csv
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import sklearn

from audit_vi_holdout import REVIEW, audit_hostnames, template_signature, similarity_edges, write_rows, sha
from external_training import OUT as PREVIOUS, REF, ROUND2, RegisteredDomains, grouped_split
from external_experiment import verify_frozen as verify_previous, require_training_partition, policy_metrics, CODE_FILES
from preprocess import DATA_DIR
from round2_experiment import training_model, text_input, choose_threshold
from run_review_experiment import read_jsonl, write_json

OUT = DATA_DIR / "prepared/smishx_training_2026-10-25"
SOURCE = DATA_DIR / "reference/english_sms_2026-10-25/smishx/data/dataset.csv"
SOURCE_SHA = "8d65e373b17477c34e8f1c619e6f59d249e8fca21276cabdd03a55d11a469285"
COMMIT = "116a8c827741e0572563f678d25ed04306b1e3ff"


def export_rows(directory, stem, rows):
    write_rows(directory, stem, rows)
    # Escape Unicode separators because the frozen older loader uses splitlines().
    (directory / (stem + ".jsonl")).write_text(
        "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows), encoding="utf-8")


def screen_source(row, number, notes):
    original = row["label"]
    if original not in {"smishing", "spam", "legitimate"}:
        raise ValueError("Unknown published SmishX label")
    issue = ""
    if number in notes["other_or_mixed_language_ids"]:
        issue = "other_or_mixed_language"
    elif number in notes["language_unresolved_fragment_ids"]:
        issue = "language_unresolved_fragment"
    elif number in notes["scope_unresolved_or_conflicting_ids"]:
        issue = "project_scope_unresolved_or_conflicting"
    return {"case_id": f"SMISHX-{number:04d}", "raw_text": row["SMS"], "original_label": original,
            "label": None if issue else int(original == "smishing"), "issue": issue,
            "source": "smishx", "source_record": number, "source_sha256": SOURCE_SHA,
            "source_commit": COMMIT, "label_provenance": "published_two_researcher_manual_relabeling_with_disagreement_resolution",
            "human_verified_by_source": True, "human_verified_by_project": False, "expert_verified": False,
            "language": "en" if not issue.startswith(("other_", "language_")) else "unresolved_or_other",
            "language_review_provenance": "AI_content_screen_not_source_human_language_annotation",
            "original_if_URL": row["if_URL"], "original_if_phone": row["if_phone"], "original_if_email": row["if_email"],
            "anchor": "smishx", "partition": "unassigned", "do_not_train": True}


def merge_exact_rows(rows):
    if len({r["label"] for r in rows}) != 1 or rows[0]["label"] is None:
        return None
    preferred = next((r for r in rows if r.get("human_verified_by_source")), rows[0])
    return dict(preferred, merged_case_ids=[r["case_id"] for r in rows],
                merged_label_provenance=[{"case_id": r["case_id"], "source": r["source"],
                                          "label": r["label"]} for r in rows])


def group_status(members):
    if any(r["anchor"] == "protected" or r.get("blocked_domain") for r in members):
        return "blocked"
    return "train" if any(r["anchor"] == "previous_train" for r in members) else "novel"


def check_snapshot():
    verify_previous()
    for name, expected in json.loads((OUT / "protected_snapshot.json").read_text(encoding="utf-8")).items():
        if sha(DATA_DIR.parent / name) != expected:
            raise ValueError(f"Protected source or earlier experiment changed: {name}")


def prepare():
    if (OUT / "selection_frozen.json").exists():
        raise ValueError("Selection is already frozen")
    verify_previous()
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError("Published SmishX file changed")
    notes_path = OUT / "source_scope_review_notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    if notes["source_sha256"] != SOURCE_SHA:
        raise ValueError("Scope review does not match published source")
    protected = [p for base in (PREVIOUS, SOURCE.parents[1], DATA_DIR / "prepared/english_sms_2026-10-25")
                 for p in base.rglob("*") if p.is_file()] + [notes_path]
    write_json(OUT / "protected_snapshot.json", {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in sorted(set(protected))})
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    if len(raw) != 1200:
        raise ValueError("Unexpected source size")
    human = [screen_source(r, i, notes) for i, r in enumerate(raw, 1)]
    export_rows(OUT, "smishx_source_screened", human)
    export_rows(OUT, "smishx_english_scope_eligible", [r for r in human if r["label"] is not None])
    base = [dict(r, anchor="previous_train", previous_group=r["group"]) for r in read_jsonl(PREVIOUS / "sms_train.jsonl")]
    old_val = read_jsonl(PREVIOUS / "sms_validation.jsonl")
    old_test = read_jsonl(PREVIOUS / "sms_test.jsonl")
    reserved = [dict(r, anchor="protected", previous_group=r["group"]) for r in old_val + old_test]
    for path in (ROUND2 / "reviewed_validation.jsonl", ROUND2 / "test_reviewed_all.jsonl",
                 REVIEW / "vi_external_test_disjoint_candidates.jsonl"):
        reserved.extend(dict(r, anchor="protected") for r in read_jsonl(path))
    all_rows = base + human + reserved
    domains = RegisteredDomains((REF / "public_suffix_list.dat").read_text(encoding="utf-8"))
    audited_domains = {domains(h) for r in read_jsonl(PREVIOUS / "url_human_audit_all_200.jsonl")
                       for h in audit_hostnames(r["url"])}
    parent = list(range(len(all_rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen, signatures = {}, []
    for i, row in enumerate(all_rows):
        roots = {domains(h) for h in audit_hostnames(row["raw_text"])}
        row["registrable_domains"] = sorted(roots)
        row["blocked_domain"] = bool(roots & audited_domains)
        signature = template_signature(row["raw_text"])
        signatures.append(signature)
        keys = ["model:" + text_input(row["raw_text"]), "template:" + signature] + ["domain:" + h for h in sorted(roots)]
        if row.get("previous_group"):
            keys.append("previous_group:" + row["previous_group"])
        for key in keys:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    print(json.dumps({"grouping_records": len(all_rows), "screened_human_eligible": sum(r["label"] is not None for r in human)}), flush=True)
    for i, j, score in similarity_edges(signatures, signatures, .80):
        if i < j:
            parent[find(i)] = find(j)
    members = defaultdict(list)
    for i, row in enumerate(all_rows):
        row["group"] = f"SX-G-{find(i)}"
        members[row["group"]].append(row)
    status = {key: group_status(rows) for key, rows in members.items()}
    quarantine, train, novel = [], [], []
    candidates = defaultdict(list)
    for row in base + human:
        if row["label"] is None:
            quarantine.append(row)
        elif status[row["group"]] == "blocked":
            quarantine.append(dict(row, issue="protected_holdout_or_audit_domain_group"))
        else:
            candidates[text_input(row["raw_text"])].append(row)
    for values in candidates.values():
        merged = merge_exact_rows(values)
        if merged is None:
            quarantine.extend(dict(r, issue="conflicting_model_normalized_labels") for r in values)
        elif status[merged["group"]] == "train":
            train.append(merged)
        else:
            novel.append(merged)
    pool_i, test_i = grouped_split(novel)
    inner = [novel[i] for i in pool_i]
    new_fit, new_val = grouped_split(inner)
    train.extend(inner[i] for i in new_fit)
    validation = [dict(r, evaluation_origin="reused_old_validation") for r in reserved[:len(old_val)]]
    validation.extend(dict(inner[i], evaluation_origin="new_source_human_validation") for i in new_val)
    test = [dict(novel[i], evaluation_origin="new_source_human_test_disjoint_from_previous_fit_and_holdouts") for i in test_i]
    splits = {"train": train, "validation": validation, "test": test}
    for role, rows in splits.items():
        for row in rows:
            row["partition"], row["do_not_train"] = role, role != "train"
        export_rows(OUT, role, rows)
    export_rows(OUT, "quarantine", quarantine)
    export_rows(OUT, "historical_sms_diagnostic", [dict(r, label=r["label"], partition="historical_test", do_not_train=True) for r in old_test])
    export_rows(OUT, "historical_vi_diagnostic", [dict(r, label=r["resolved_label"], partition="historical_test", do_not_train=True)
                                                 for r in read_jsonl(ROUND2 / "frozen_test_used.jsonl")])
    for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if {r["group"] for r in splits[a]} & {r["group"] for r in splits[b]}:
            raise ValueError("New experiment groups cross partitions")
    protocol = {"candidates": ["word", "word_char"], "sample_weight_vi": 3.0, "sample_weight_published_human_en": 2.0,
                "selection": "pooled validation F2 with FPR <= 0.10; existing fixed threshold grid; no test tuning",
                "scope": "SMS text only; URL head unchanged; IMC and MIMICS not fitted",
                "baseline": "previous frozen external experiment text model and SMS threshold",
                "test": "new human source groups outside previous fitted SMS and historical holdout groups",
                "historical_tests": "reused diagnostics only, never new independent results",
                "production_compatible": False}
    write_json(OUT / "training_protocol.json", protocol)
    report = {"source_rows": len(human), "source_eligible": sum(r["label"] is not None for r in human),
              "source_screening_issues": dict(Counter(r["issue"] for r in human if r["issue"])),
              "source_eligible_labels": dict(Counter(str(r["label"]) for r in human if r["label"] is not None)),
              "novel_human_pool_before_split": len(novel), "quarantine_issues": dict(Counter(r["issue"] for r in quarantine)),
              "splits": {role: {"rows": len(rows), "labels": dict(Counter(str(r["label"]) for r in rows)),
                         "by_language_label": dict(Counter(f'{r["language"]}:{r["label"]}' for r in rows)),
                         "published_human_rows": sum(r.get("human_verified_by_source", False) for r in rows)} for role, rows in splits.items()},
              "legacy_rows_removed_to_protect_new_bridges": sum(r["anchor"] == "previous_train" for r in quarantine),
              "previous_experiments_modified": False, "expert_verified_by_project": False,
              "minimum_test_class_count": min(Counter(r["label"] for r in test).values())}
    write_json(OUT / "preparation_report.json", report)
    check_snapshot()
    print(json.dumps(report), flush=True)


def select():
    if (OUT / "selection_frozen.json").exists():
        raise ValueError("Selection is already frozen")
    check_snapshot()
    train, val = (read_jsonl(OUT / (role + ".jsonl")) for role in ("train", "validation"))
    require_training_partition(train)
    protocol = json.loads((OUT / "training_protocol.json").read_text(encoding="utf-8"))
    x, vx = ([text_input(r["raw_text"]) for r in rows] for rows in (train, val))
    y, vy = (np.array([r["label"] for r in rows]) for rows in (train, val))
    weights = np.array([3.0 if r["language"] == "vi" else 2.0 if r.get("human_verified_by_source") else 1.0 for r in train])
    models, trials, scores = {}, {}, {}
    for kind in protocol["candidates"]:
        model = training_model(kind)
        model.fit(x, y, classifier__sample_weight=weights)
        scores[kind] = model.predict_proba(vx)[:, 1]
        trials[kind], models[kind] = choose_threshold(vy, scores[kind]), model
        print(json.dumps({"candidate": kind, "validation": trials[kind]}), flush=True)
    chosen = max(trials, key=lambda key: (trials[key]["f2"], trials[key]["recall"], trials[key]["precision"], key == "word"))
    bundle = {"text_model": models[chosen], "threshold": trials[chosen]["threshold"], "variant": chosen,
              "production_compatible": False, "artifact_type": "smishx_sms_research", "sklearn_version": sklearn.__version__}
    with (OUT / "research_model.pkl").open("wb") as f:
        pickle.dump(bundle, f)
    export_rows(OUT, "validation_predictions", [dict(r, score=float(scores[chosen][i])) for i, r in enumerate(val)])
    files = list(OUT.glob("*.jsonl")) + [OUT / name for name in ("source_scope_review_notes.json", "training_protocol.json", "protected_snapshot.json", "preparation_report.json", "research_model.pkl")]
    frozen = {"selected": chosen, "threshold": bundle["threshold"], "validation_trials": trials,
              "files_sha256": {p.name: sha(p) for p in files},
              "code_sha256": {name: sha(Path(__file__).parent / name) for name in (*CODE_FILES, "smishx_training.py")},
              "test_used_for_selection": False, "previous_selection_sha256": sha(PREVIOUS / "selection_frozen.json")}
    check_snapshot()
    write_json(OUT / "selection_frozen.json", frozen)


def verify_frozen():
    check_snapshot()
    frozen = json.loads((OUT / "selection_frozen.json").read_text(encoding="utf-8"))
    for name, expected in frozen["files_sha256"].items():
        if sha(OUT / name) != expected:
            raise ValueError(f"Frozen new experiment file changed: {name}")
    for name, expected in frozen["code_sha256"].items():
        if sha(Path(__file__).parent / name) != expected:
            raise ValueError(f"Frozen experiment code changed: {name}")
    return frozen


def test_once():
    if (OUT / "test_started.json").exists():
        raise ValueError("Test already started; do not rerun or tune against it")
    frozen = verify_frozen()
    with (OUT / "research_model.pkl").open("rb") as f:
        candidate = pickle.load(f)
    with (PREVIOUS / "research_bundle.pkl").open("rb") as f:
        baseline = pickle.load(f)
    if baseline["sms_mode"] != "text":
        raise ValueError("This before/after comparison requires a text-only baseline")
    write_json(OUT / "test_started.json", {"evaluations": 1, "selection_sha256": sha(OUT / "selection_frozen.json")})
    result = {}
    for name in ("test", "historical_sms_diagnostic", "historical_vi_diagnostic"):
        rows = read_jsonl(OUT / (name + ".jsonl"))
        x, y = [text_input(r["raw_text"]) for r in rows], np.array([r["label"] for r in rows])
        new = candidate["text_model"].predict_proba(x)[:, 1]
        old = baseline["text_model"].predict_proba(x)[:, 1]
        metrics = {"candidate": policy_metrics(y, new, candidate["threshold"]),
                   "previous_research_model": policy_metrics(y, old, baseline["sms_threshold"])}
        if all("language" in r for r in rows):
            metrics["by_language"] = {}
            for language in sorted({r["language"] for r in rows}):
                indices = [i for i, r in enumerate(rows) if r["language"] == language]
                metrics["by_language"][language] = {"candidate": policy_metrics(y[indices], new[indices], candidate["threshold"]),
                    "previous_research_model": policy_metrics(y[indices], old[indices], baseline["sms_threshold"])}
        result[name] = metrics
        predictions = [dict(r, candidate_score=float(new[i]), baseline_score=float(old[i]),
                       candidate_label=int(new[i] >= candidate["threshold"]), baseline_label=int(old[i] >= baseline["sms_threshold"]),
                       candidate_error=bool((new[i] >= candidate["threshold"]) != y[i])) for i, r in enumerate(rows)]
        export_rows(OUT, name + "_predictions", predictions)
        export_rows(OUT, name + "_errors", [r for r in predictions if r["candidate_error"]])
    report = {"status": "completed_isolated_sms_training", "date": "2026-10-25", "selection": {k: frozen[k] for k in ("selected", "threshold", "validation_trials")},
              "preparation": json.loads((OUT / "preparation_report.json").read_text(encoding="utf-8")), "metrics": result,
              "test_evaluations": 1, "deployed_model_replaced": False, "url_model_retrained": False,
              "IMC25_fitted_rows": 0, "MIMICS_3500_fitted_rows": 0,
              "limits": ["SmishX source human labels are not this project's independent expert adjudication.",
                         "Language/scope exclusions are AI screening, not new human verification.",
                         "Test contains only previously unseen SmishX groups for this research baseline, not an independent collection or a test of the deployed model.",
                         "Old SMS/Vietnamese test results are reused diagnostics, not new independent evidence.",
                         "Grouping excludes similarities >=0.80 and shared registered domains; complete campaign independence is not established.",
                         "Nonrepresentative public data and small class/group counts do not establish deployment readiness."]}
    verify_frozen()
    write_json(OUT / "final_report.json", report)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "select", "test", "predict"))
    parser.add_argument("--allow-mixed-labels", action="store_true")
    parser.add_argument("--text")
    args = parser.parse_args()
    if not args.allow_mixed_labels:
        parser.error("--allow-mixed-labels acknowledges source-human plus historical AI/source labels")
    if args.phase == "predict":
        if not args.text:
            parser.error("--text is required")
        verify_frozen()
        with (OUT / "research_model.pkl").open("rb") as f:
            model = pickle.load(f)
        score = float(model["text_model"].predict_proba([text_input(args.text)])[0, 1])
        print(json.dumps({"score": score, "label": int(score >= model["threshold"]), "threshold": model["threshold"], "research_only": True}))
    else:
        {"prepare": prepare, "select": select, "test": test_once}[args.phase]()
