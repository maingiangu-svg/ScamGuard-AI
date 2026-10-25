"""Grouped supervised research: prepare, select on validation, then test once."""
import argparse
import csv
import json
import pickle
import unicodedata
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from audit_vi_holdout import REVIEW, audit_hostnames, audit_url_text, template_signature, similarity_edges, write_rows, sha
from run_review_experiment import read_jsonl, write_json, reviewed_training_data, metric_summary
from preprocess import DATA_DIR, extract_urls, normalize_text
from modeling import url_scores, meta_features
from predict import load_bundle

ROOT = REVIEW / "round2"
SOURCE = DATA_DIR / "reference/vietnamese_sms_dataset/train.csv"


def partition_eligibility(rows):
    priorities = {"test": 3, "validation": 2, "train": 1}
    groups = defaultdict(list)
    for row in rows:
        groups[row["group"]].append(row)
    result = []
    for members in groups.values():
        role = "train" if any(r["previous_train"] for r in members) else max(
            (r["partition"] for r in members), key=priorities.get)
        for row in members:
            result.append(dict(row, effective_group_partition=role,
                               split_eligible=row["partition"] == role,
                               split_reason="isolated" if row["partition"] == role else "cross_partition_group_blocked"))
    return result


def choose_threshold(y, scores):
    candidates = []
    for value in range(5, 96):
        threshold = value / 100
        pred = scores >= threshold
        tp = int(((y == 1) & pred).sum())
        fp = int(((y == 0) & pred).sum())
        fn = int(((y == 1) & ~pred).sum())
        negatives = int((y == 0).sum())
        fpr = fp / negatives if negatives else 1.0
        if fpr <= .10:
            candidates.append({"threshold": threshold, "f2": 5 * tp / (5 * tp + 4 * fn + fp) if tp else 0.0,
                               "recall": tp / (tp + fn) if tp + fn else 0.0,
                               "precision": tp / (tp + fp) if tp + fp else 0.0,
                               "false_positive_rate": fpr})
    if not candidates:
        raise ValueError("No validation threshold meets false-positive constraint")
    return max(candidates, key=lambda r: (r["f2"], r["recall"], r["precision"], r["threshold"]))


def training_model(kind):
    word = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, sublinear_tf=True, dtype=np.float32)
    features = FeatureUnion([("word", word)])
    if kind == "word_char":
        features.transformer_list.append(("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                                                  max_features=16000, sublinear_tf=True, dtype=np.float32)))
    elif kind != "word":
        raise ValueError("Unknown predeclared model variant")
    return Pipeline([("features", features), ("classifier", LogisticRegression(
        C=1.0, class_weight="balanced", max_iter=1000, random_state=42))])


def text_input(text):
    text = unicodedata.normalize("NFC", audit_url_text(text)).casefold()
    return re.sub(r"\s+", " ", re.sub(r"\d{4,}", "<number>", text)).strip()


def read_notes(role):
    path = ROOT / f"{role}_review_candidates.jsonl"
    notes = json.loads((ROOT / f"{role}_review_notes.json").read_text(encoding="utf-8"))
    if sha(path) != notes["input_sha256"]:
        raise ValueError(f"{role} candidate checksum changed")
    rows = read_jsonl(path)
    assignments = {}
    available = {r["source_record"] for r in rows}
    for group in notes["groups"]:
        for number in map(int, group["ids"].split(",")):
            if number not in available or number in assignments:
                raise ValueError(f"Unexpected/repeated {role} annotation ID: {number}")
            assignments[number] = group
    if assignments.keys() != available:
        raise ValueError(f"Missing {role} annotations: {available-assignments.keys()}")
    result = []
    for row in rows:
        group = assignments[row["source_record"]]
        if group["label"] is not None and (type(group["label"]) is not int or group["label"] not in (0, 1)):
            raise ValueError("Unknown review label")
        result.append(dict(row, resolved_label=group["label"], category=group["category"], rationale_vi=group["reason"],
                           label_provenance="ai_semantic_review", gold_smishing_label=None, expert_verified=False))
    return result


def check_snapshot():
    hashes = json.loads((ROOT / "source_snapshot.json").read_text(encoding="utf-8"))
    for path, checksum in hashes.items():
        if sha(DATA_DIR.parent / path) != checksum:
            raise ValueError(f"Protected source/model changed: {path}")


def prepare():
    if (ROOT / "selection_frozen.json").exists():
        raise ValueError("Selection already frozen; do not repartition after model selection")
    protected = list(DATA_DIR.glob("*.csv")) + [p for p in (DATA_DIR / "reference").rglob("*") if p.is_file()]
    protected += [p for p in (DATA_DIR.parent / "models").rglob("*") if p.is_file()]
    protected += [p for p in REVIEW.rglob("*") if p.is_file() and ROOT not in p.parents]
    write_json(ROOT / "source_snapshot.json", {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in sorted(set(protected))})
    train = read_notes("train")
    validation = read_notes("validation")
    test = read_jsonl(ROOT / "test_review_candidates.jsonl")
    previous, legacy = reviewed_training_data()
    previous = [dict(r, partition="train", resolved_label=r["ai_proposed_label"],
                     category=r["ai_category"]) for r in previous]
    selected = previous + train + validation + test
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    source_hash = sha(SOURCE)
    for row in selected:
        n = row["source_record"]
        if row["raw_text"] != raw[n - 1]["message"] or row["source_sha256"] != source_hash:
            raise ValueError("Source identity mismatch")
    # Full-source grouping catches siblings not selected in the annotation sample.
    parents = list(range(len(raw)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    signatures = [template_signature(r["message"]) for r in raw]
    seen = {}
    for i, row in enumerate(raw):
        for key in ["text:" + signatures[i]] + ["host:" + h for h in sorted(audit_hostnames(row["message"]))]:
            if key in seen:
                parents[find(i)] = find(seen[key])
            else:
                seen[key] = i
    for i, j, score in similarity_edges(signatures, signatures, .80):
        if i < j:
            parents[find(i)] = find(j)
    members = defaultdict(list)
    for i in range(len(raw)):
        members[find(i)].append(i)
    group_ids = {i: f"R2-G-{min(indices)+1:04}" for indices in members.values() for i in indices}
    anchors = {r["case_id"] for r in previous}
    selected = [dict(r, group=group_ids[r["source_record"] - 1], previous_train=r["case_id"] in anchors) for r in selected]
    isolated = partition_eligibility(selected)
    # A final check against ALL legacy SMS also protects the baseline comparison.
    references, legacy_hosts = {}, set()
    for path, column in [(DATA_DIR / "smishing_combined.csv", "message"),
                         (DATA_DIR / "prepared/spam_restored_full.csv", "raw_text")]:
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                signature = template_signature(row[column])
                if signature:
                    references[signature] = True
                legacy_hosts.update(audit_hostnames(row[column]))
    eval_rows = [r for r in isolated if r["partition"] != "train"]
    blocked = {r["group"] for r in eval_rows if audit_hostnames(r["raw_text"]) & legacy_hosts}
    evidence = []
    keys = list(references)
    for i, j, score in similarity_edges([template_signature(r["raw_text"]) for r in eval_rows], keys, .80):
        blocked.add(eval_rows[i]["group"])
        evidence.append({"case_id": eval_rows[i]["case_id"], "cosine": score, "reference_template": keys[j]})
    for row in isolated:
        if row["partition"] != "train" and row["group"] in blocked:
            row["split_eligible"] = False
            row["split_reason"] = "legacy_source_overlap"
        row["do_not_train"] = row["partition"] != "train"
        row["eligible_for_verified_evaluation"] = False
    active_groups = defaultdict(set)
    for row in isolated:
        if row["split_eligible"]:
            active_groups[row["group"]].add(row["partition"])
    assert all(len(v) == 1 for v in active_groups.values())
    write_rows(ROOT, "corrected_split_manifest", isolated)
    write_rows(ROOT, "legacy_overlap_evidence", evidence)
    for role in ("train", "validation"):
        write_rows(ROOT, f"reviewed_{role}", [r for r in isolated if r["partition"] == role])
    write_rows(ROOT, "quarantine_reviewed", [r for r in isolated if r["partition"] != "test" and
                                              (r["resolved_label"] is None or not r["split_eligible"])])
    blind = [{"case_id": r["case_id"], "raw_text": r["raw_text"], "human_label": None,
              "human_reviewer": None, "evidence": None, "expert_verified": False} for r in test]
    if not (ROOT / "test_human_annotation.jsonl").exists():
        write_rows(ROOT, "test_human_annotation", blind)
    report = {"requested": dict(Counter(r["partition"] for r in isolated)),
              "split_eligible": dict(Counter(r["partition"] for r in isolated if r["split_eligible"])),
              "annotated_train_labels": dict(Counter(str(r["resolved_label"]) for r in isolated if r["partition"] == "train")),
              "validation_labels": dict(Counter(str(r["resolved_label"]) for r in isolated if r["partition"] == "validation")),
              "group_count_full_provider": len(members), "source_sha256": source_hash,
              "test_candidate_sha256": sha(ROOT / "test_review_candidates.jsonl"),
              "grouping_code_sha256": sha(Path(__file__).parent / "audit_vi_holdout.py"),
              "wrapped_url_bug_fixed": True, "split_group_disjoint": True,
              "no_test_rows_reassigned_to_training": True}
    write_json(ROOT / "prepare_report.json", report)
    check_snapshot()
    print(json.dumps(report), flush=True)


def baseline_scores(bundle, rows):
    normalized, links = [], []
    for row in rows:
        masked, urls = extract_urls(row["raw_text"])
        normalized.append(normalize_text(masked))
        links.append(urls)
    text = bundle["text_model"].predict_proba(normalized)[:, 1]
    url = url_scores(bundle["url_model"], links)
    full = text.copy()
    paired = np.array([bool(u) for u in links])
    if paired.any():
        full[paired] = bundle["meta_model"].predict_proba(meta_features(text[paired], url[paired]))[:, 1]
    return {"deployed_text": text, "deployed_full": full}


def select():
    if (ROOT / "selection_frozen.json").exists():
        raise ValueError("Model selection is already frozen; refusing to tune again")
    check_snapshot()
    train = [r for r in read_jsonl(ROOT / "reviewed_train.jsonl") if r["split_eligible"] and r["resolved_label"] is not None]
    _, legacy = reviewed_training_data()
    train += [dict(r, resolved_label=r["proposed_label"], partition="train", group=f"OLD-{r['source_record']}",
                   source_split="legacy_review", label_provenance="ai_semantic_review")
              for r in legacy if r["proposed_label"] is not None]
    # Exact input conflicts are removed; near-related examples stay in the same partition.
    labels = defaultdict(set)
    for row in train:
        labels[text_input(row["raw_text"])].add(row["resolved_label"])
    kept, seen = [], set()
    for row in train:
        key = text_input(row["raw_text"])
        if len(labels[key]) == 1 and key not in seen:
            kept.append(row)
            seen.add(key)
    train = kept
    val = [r for r in read_jsonl(ROOT / "reviewed_validation.jsonl") if r["split_eligible"] and r["resolved_label"] is not None]
    x, y = [text_input(r["raw_text"]) for r in train], np.array([r["resolved_label"] for r in train])
    vx, vy = [text_input(r["raw_text"]) for r in val], np.array([r["resolved_label"] for r in val])
    if set(y) != {0, 1} or set(vy) != {0, 1}:
        raise ValueError("Both classes required in train and validation")
    write_rows(ROOT, "fitted_training_manifest", train)
    write_rows(ROOT, "validation_used", val)
    trials, models, probabilities = {}, {}, {}
    for kind in ("word", "word_char"):
        model = training_model(kind).fit(x, y)
        scores = model.predict_proba(vx)[:, 1]
        trials[kind] = choose_threshold(vy, scores)
        trials[kind]["metrics_at_50"] = metric_summary(vy, scores)
        models[kind], probabilities[kind] = model, scores
    chosen = max(trials, key=lambda k: (trials[k]["f2"], trials[k]["recall"], trials[k]["precision"], k == "word"))
    with (ROOT / "selected_research_model.pkl").open("wb") as f:
        pickle.dump(models[chosen], f, protocol=pickle.HIGHEST_PROTOCOL)
    baseline = baseline_scores(load_bundle(), val)
    baseline_thresholds = {name: choose_threshold(vy, scores) for name, scores in baseline.items()}
    write_rows(ROOT, "validation_predictions", [dict(r, word_score=float(probabilities["word"][i]),
               word_char_score=float(probabilities["word_char"][i]),
               **{k + "_score": float(v[i]) for k, v in baseline.items()}) for i, r in enumerate(val)])
    frozen = {"selected_model": chosen, "selected_threshold": trials[chosen]["threshold"],
              "validation_trials": trials, "baseline_thresholds": baseline_thresholds,
              "training_rows": len(train), "training_labels": dict(Counter(str(v) for v in y)),
              "validation_rows": len(val), "validation_labels": dict(Counter(str(v) for v in vy)),
              "model_sha256": sha(ROOT / "selected_research_model.pkl"),
              "test_candidate_sha256": sha(ROOT / "test_review_candidates.jsonl"),
              "split_manifest_sha256": sha(ROOT / "corrected_split_manifest.jsonl"),
              "source_snapshot_sha256": sha(ROOT / "source_snapshot.json"),
              "experiment_code_sha256": sha(Path(__file__)),
              "test_labels_used_for_selection": False, "expert_verified": False}
    write_json(ROOT / "selection_frozen.json", frozen)
    check_snapshot()
    print(json.dumps(frozen), flush=True)


def at_threshold(y, scores, threshold):
    pred = scores >= threshold
    return {"threshold": threshold, "tn": int(((y == 0) & ~pred).sum()), "fp": int(((y == 0) & pred).sum()),
            "fn": int(((y == 1) & ~pred).sum()), "tp": int(((y == 1) & pred).sum())}


def test_once():
    if (ROOT / "final_report.json").exists():
        raise ValueError("This test has already been evaluated; do not tune or rerun it")
    frozen = json.loads((ROOT / "selection_frozen.json").read_text(encoding="utf-8"))
    for name, key in [("selected_research_model.pkl", "model_sha256"), ("test_review_candidates.jsonl", "test_candidate_sha256"),
                      ("corrected_split_manifest.jsonl", "split_manifest_sha256"), ("source_snapshot.json", "source_snapshot_sha256")]:
        if sha(ROOT / name) != frozen[key]:
            raise ValueError("Frozen selection/input changed")
    if sha(Path(__file__)) != frozen["experiment_code_sha256"]:
        raise ValueError("Experiment code changed after selection")
    check_snapshot()
    annotations = {r["case_id"]: r for r in read_notes("test")}
    manifest = read_jsonl(ROOT / "corrected_split_manifest.jsonl")
    annotated = [dict(r, **{k: annotations[r["case_id"]][k] for k in
                 ("resolved_label", "category", "rationale_vi", "label_provenance", "gold_smishing_label")})
                 for r in manifest if r["partition"] == "test"]
    write_rows(ROOT, "test_reviewed_all", annotated)
    rows = [r for r in annotated if r["split_eligible"] and r["resolved_label"] is not None]
    if {r["resolved_label"] for r in rows} != {0, 1}:
        raise ValueError("Final evaluation requires both classes")
    write_rows(ROOT, "frozen_test_used", rows)
    y = np.array([r["resolved_label"] for r in rows])
    with (ROOT / "selected_research_model.pkl").open("rb") as f:
        model = pickle.load(f)
    candidate = model.predict_proba([text_input(r["raw_text"]) for r in rows])[:, 1]
    scores = baseline_scores(load_bundle(), rows)
    scores["selected_candidate"] = candidate
    thresholds = {name: v["threshold"] for name, v in frozen["baseline_thresholds"].items()}
    thresholds["selected_candidate"] = frozen["selected_threshold"]
    metrics = {name: {"fixed_50": metric_summary(y, value),
                      "validation_selected_policy": at_threshold(y, value, thresholds[name])} for name, value in scores.items()}
    predictions = [dict(r, **{name + "_score": float(value[i]) for name, value in scores.items()},
                        candidate_error=bool((candidate[i] >= thresholds["selected_candidate"]) != y[i])) for i, r in enumerate(rows)]
    write_rows(ROOT, "test_predictions", predictions)
    write_rows(ROOT, "test_error_cases", [r for r in predictions if r["candidate_error"]])
    report = {"date": "2026-10-25", "steps": {"expanded_semantic_review": "complete",
              "independent_human_test_verification": "pending_independent_labels; blind file prepared",
              "grouped_train_validation_test": "complete", "validation_selection_and_one_test_run": "complete"},
              "selection": frozen, "test_requested": len(annotated), "test_used": len(rows),
              "test_labels": dict(Counter(str(v) for v in y)), "test_unresolved": sum(r["resolved_label"] is None for r in annotated),
              "test_blocked_by_group_or_legacy": sum(not r["split_eligible"] for r in annotated),
              "metrics_against_ai_review_only": metrics, "expert_verified_test_labels": 0,
              "test_evaluations": 1, "deployed_model_replaced": False,
              "test_annotation_sha256": sha(ROOT / "test_review_notes.json"),
              "limits": ["AI annotations are not expert-verified; same annotator causes correlated errors.",
                         "One provider and many repeated linguistic patterns; campaign independence not proven.",
                         "Sampling is stratified on upstream spam/scam labels; class proportions are not real traffic prevalence.",
                         "URL endings/wording may be source artifacts. No causal claim that labels alone explain improvement.",
                         "Small test; do not deploy or claim real-world accuracy from these results."]}
    check_snapshot()
    write_json(ROOT / "final_report.json", report)
    print(json.dumps({k: report[k] for k in ("steps", "test_used", "test_labels", "metrics_against_ai_review_only")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "select", "test"))
    parser.add_argument("--allow-ai-labels", action="store_true")
    args = parser.parse_args()
    if not args.allow_ai_labels:
        parser.error("Explicit --allow-ai-labels is required for this isolated AI-label experiment")
    {"prepare": prepare, "select": select, "test": test_once}[args.phase]()
