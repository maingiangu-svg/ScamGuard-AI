"""Fit isolated supervised candidates, select on validation, freeze, then test once."""
import argparse
import json
import pickle
from collections import Counter
from pathlib import Path

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold

from external_training import OUT, ROUND2, prepare, check_snapshot, url_input
from audit_vi_holdout import audit_url_text, write_rows, sha
from modeling import url_model, url_scores, meta_features
from preprocess import extract_urls
from round2_experiment import training_model, text_input, choose_threshold, at_threshold
from run_review_experiment import read_jsonl, write_json, metric_summary

CODE_FILES = ("external_training.py", "external_experiment.py", "round2_experiment.py", "audit_vi_holdout.py",
              "modeling.py", "preprocess.py", "run_review_experiment.py")


def require_training_partition(rows):
    if not rows or any(r["partition"] != "train" or r["do_not_train"] or
                       type(r["label"]) is not int or r["label"] not in (0, 1) for r in rows):
        raise ValueError("Only resolved, explicitly eligible training records can be fitted")


def sms_links(rows):
    return [[url_input(u) for u in extract_urls(audit_url_text(r["raw_text"]))[1]] for r in rows]


def sms_scores(bundle, rows):
    text = bundle["text_model"].predict_proba([text_input(r["raw_text"]) for r in rows])[:, 1]
    if bundle["sms_mode"] == "text":
        return text
    links = url_scores(bundle["url_model"], sms_links(rows))
    return bundle["meta_model"].predict_proba(meta_features(text, links))[:, 1]


def policy_metrics(y, scores, threshold):
    result = at_threshold(y, scores, threshold)
    tp, fp, fn, tn = (result[k] for k in ("tp", "fp", "fn", "tn"))
    result.update(precision=tp / (tp + fp) if tp + fp else 0.0,
                  recall=tp / (tp + fn) if tp + fn else 0.0,
                  f1=2 * tp / (2 * tp + fp + fn) if tp else 0.0,
                  f2=5 * tp / (5 * tp + fp + 4 * fn) if tp else 0.0,
                  false_positive_rate=fp / (fp + tn) if fp + tn else None,
                  n=len(y), positives=int((y == 1).sum()))
    return result


def verify_frozen():
    frozen = json.loads((OUT / "selection_frozen.json").read_text(encoding="utf-8"))
    for name, expected in frozen["files_sha256"].items():
        if sha(OUT / name) != expected:
            raise ValueError(f"Frozen experiment input/artifact changed: {name}")
    for name, expected in frozen["code_sha256"].items():
        if sha(Path(__file__).parent / name) != expected:
            raise ValueError(f"Frozen experiment code changed: {name}")
    check_snapshot()
    return frozen


def select():
    if (OUT / "selection_frozen.json").exists() or (OUT / "final_report.json").exists():
        raise ValueError("Selection already frozen; start a separate experiment for new choices")
    check_snapshot()
    train, val = (read_jsonl(OUT / f"sms_{role}.jsonl") for role in ("train", "validation"))
    url_train, url_val = (read_jsonl(OUT / f"url_{role}.jsonl") for role in ("train", "validation"))
    require_training_partition(train)
    require_training_partition(url_train)
    protocol = {"sms_candidates": ["word", "word_char"], "sms_vi_sample_weight": 3.0,
                "selection": "maximum validation F2 subject to FPR <= 0.10; tie prefer text over fusion",
                "fusion": "3-fold grouped out-of-fold text scores + URL head trained outside all SMS domains; real SMS links only",
                "url_model": "existing fixed lexical HistGradientBoosting; no metadata, HTTP/HTTPS collapsed",
                "url_target": "feed-reported abuse/phishing vs benign, not exclusively credential phishing",
                "test_labels_used_for_selection": False, "production_compatible": False}
    write_json(OUT / "training_protocol.json", protocol)
    x, vx = ([text_input(r["raw_text"]) for r in rows] for rows in (train, val))
    y, vy = (np.array([r["label"] for r in rows]) for rows in (train, val))
    weights = np.array([3.0 if r["language"] == "vi" else 1.0 for r in train])
    models, val_scores, trials = {}, {}, {}
    for kind in protocol["sms_candidates"]:
        model = training_model(kind)
        model.fit(x, y, classifier__sample_weight=weights)
        probabilities = model.predict_proba(vx)[:, 1]
        models[kind], val_scores[kind] = model, probabilities
        trials[kind] = choose_threshold(vy, probabilities)
        print(json.dumps({"text_candidate": kind, "validation": trials[kind]}), flush=True)
    chosen = max(trials, key=lambda k: (trials[k]["f2"], trials[k]["recall"], trials[k]["precision"], k == "word"))
    url_head = url_model()
    url_head.fit([r["url"] for r in url_train], np.array([r["label"] for r in url_train]))
    url_val_scores = url_head.predict_proba([r["url"] for r in url_val])[:, 1]
    url_trial = choose_threshold(np.array([r["label"] for r in url_val]), url_val_scores)
    print(json.dumps({"url_validation": url_trial}), flush=True)
    # The URL head never saw any SMS domains. Only the text head needs OOF scores here.
    oof = np.empty(len(train), dtype=float)
    groups = [r["group"] for r in train]
    for fit, held in StratifiedGroupKFold(3, shuffle=True, random_state=42).split(x, y, groups):
        fold_model = training_model(chosen)
        fold_model.fit([x[i] for i in fit], y[fit], classifier__sample_weight=weights[fit])
        oof[held] = fold_model.predict_proba([x[i] for i in held])[:, 1]
    url_fit_scores = url_scores(url_head, sms_links(train))
    meta = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    meta.fit(meta_features(oof, url_fit_scores), y, sample_weight=weights)
    url_sms_val = url_scores(url_head, sms_links(val))
    fusion_scores = meta.predict_proba(meta_features(val_scores[chosen], url_sms_val))[:, 1]
    trials["fusion"] = choose_threshold(vy, fusion_scores)
    mode = "fusion" if trials["fusion"]["f2"] > trials[chosen]["f2"] else "text"
    sms_trial = trials["fusion" if mode == "fusion" else chosen]
    bundle = {"artifact_type": "isolated_supervised_research", "production_compatible": False,
              "sklearn_version": sklearn.__version__, "text_model": models[chosen], "url_model": url_head,
              "meta_model": meta, "sms_mode": mode, "text_variant": chosen,
              "sms_threshold": sms_trial["threshold"], "url_threshold": url_trial["threshold"],
              "protocol": protocol, "preprocessing": "round2.text_input + external_training.url_input"}
    with (OUT / "research_bundle.pkl").open("wb") as f:
        pickle.dump(bundle, f)
    write_rows(OUT, "sms_validation_predictions", [dict(r, text_score=float(val_scores[chosen][i]),
               fusion_score=float(fusion_scores[i])) for i, r in enumerate(val)])
    write_rows(OUT, "url_validation_predictions", [dict(r, score=float(url_val_scores[i])) for i, r in enumerate(url_val)])
    pin_names = [p.name for p in OUT.glob("*.jsonl")] + ["research_bundle.pkl", "training_protocol.json",
                  "preparation_report.json", "sms_semantic_review_notes.json", "protected_snapshot.json"]
    frozen = {"selected_text": chosen, "selected_sms_mode": mode, "sms_validation_trials": trials,
              "selected_sms_policy": sms_trial, "selected_url_policy": url_trial,
              "files_sha256": {name: sha(OUT / name) for name in sorted(set(pin_names))},
              "code_sha256": {name: sha(Path(__file__).parent / name) for name in CODE_FILES},
              "test_labels_used_for_selection": False, "sklearn_version": sklearn.__version__,
              "deployed_model_replaced": False, "expert_verified_sms_training": 0}
    check_snapshot()
    write_json(OUT / "selection_frozen.json", frozen)
    print(json.dumps({k: v for k, v in frozen.items() if not k.endswith("sha256")}), flush=True)


def evaluate_set(name, rows, scores, threshold):
    y = np.array([r["label"] for r in rows])
    predictions = [dict(r, score=float(scores[i]), predicted_label=int(scores[i] >= threshold),
                        error=bool((scores[i] >= threshold) != y[i])) for i, r in enumerate(rows)]
    write_rows(OUT, name + "_predictions", predictions)
    write_rows(OUT, name + "_errors", [r for r in predictions if r["error"]])
    metrics = {"selected_policy": policy_metrics(y, scores, threshold), "fixed_50": metric_summary(y, scores)}
    for column in ("language", "source", "tier"):
        if rows and column in rows[0]:
            metrics["by_" + column] = {}
            for value in sorted({r[column] for r in rows}):
                indices = [i for i, r in enumerate(rows) if r[column] == value]
                metrics["by_" + column][value] = policy_metrics(y[indices], scores[indices], threshold)
    return metrics


def test_once():
    if (OUT / "final_report.json").exists() or (OUT / "test_started.json").exists():
        raise ValueError("Held-out evaluation already started; never tune or repeat it in this experiment")
    frozen = verify_frozen()
    with (OUT / "research_bundle.pkl").open("rb") as f:
        bundle = pickle.load(f)
    write_json(OUT / "test_started.json", {"selection_sha256": sha(OUT / "selection_frozen.json"), "runs": 1})
    metrics = {}
    rows = read_jsonl(OUT / "sms_test.jsonl")
    metrics["sms_source_and_ai_labels"] = evaluate_set("sms_test", rows, sms_scores(bundle, rows), bundle["sms_threshold"])
    for name in ("url_test", "url_human_strict_test"):
        rows = read_jsonl(OUT / (name + ".jsonl"))
        scores = bundle["url_model"].predict_proba([r["url"] for r in rows])[:, 1]
        metrics[name] = evaluate_set(name, rows, scores, bundle["url_threshold"])
    # A repeatedly inspected historical Vietnamese set is a diagnostic, never a fresh benchmark.
    historic = [dict(r, label=r["resolved_label"]) for r in read_jsonl(ROUND2 / "frozen_test_used.jsonl")]
    metrics["historical_vi_diagnostic_only"] = evaluate_set("historical_vi_diagnostic", historic,
                                                         sms_scores(bundle, historic), bundle["sms_threshold"])
    report = {"date": "2026-10-25", "status": "completed_isolated_supervised_training_and_one_frozen_test_run",
              "preparation": json.loads((OUT / "preparation_report.json").read_text(encoding="utf-8")),
              "selection": {k: frozen[k] for k in ("selected_text", "selected_sms_mode", "selected_sms_policy", "selected_url_policy")},
              "metrics": metrics, "test_evaluations": 1, "deployed_model_replaced": False,
              "artifact": "research_bundle.pkl", "production_compatible": False,
              "limits": ["SMS labels are source labels or AI reviews, not independent expert verification.",
                         "PhishVN training positives include broad feed-reported abuse, not exclusively credential phishing.",
                         "Human URL evaluation uses 81 evidence-supported cases from the authors' published audit; expert qualifications not established.",
                         "All 200 human-audit domains were reserved; the other 119 are not automatically relabeled or fitted.",
                         "Small, nonrepresentative class-stratified holdouts do not establish real-traffic accuracy or prevalence.",
                         "Historical Vietnamese scores are a reused diagnostic; no new independent Vietnamese human benchmark exists.",
                         "No deployed-model comparison: old training sources may overlap these newly acquired datasets.",
                         "MIMICS-3500 not used: no official public data file with verified provenance/license found."]}
    verify_frozen()
    write_json(OUT / "final_report.json", report)
    print(json.dumps({k: v["selected_policy"] for k, v in metrics.items()}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "select", "test", "predict"))
    parser.add_argument("--allow-ai-labels", action="store_true")
    parser.add_argument("--text")
    args = parser.parse_args()
    if not args.allow_ai_labels:
        parser.error("Use --allow-ai-labels to acknowledge the isolated experiment's label quality")
    if args.phase == "predict":
        if not args.text:
            parser.error("--text is required for predict")
        verify_frozen()
        with (OUT / "research_bundle.pkl").open("rb") as f:
            candidate = pickle.load(f)
        score = float(sms_scores(candidate, [{"raw_text": args.text}])[0])
        print(json.dumps({"score": score, "label": int(score >= candidate["sms_threshold"]),
                          "threshold": candidate["sms_threshold"], "research_only": True}))
    else:
        {"prepare": prepare, "select": select, "test": test_once}[args.phase]()
