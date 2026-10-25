"""Opt-in supervised experiment on AI-reviewed labels, separate from deployed models."""
import argparse
import csv
import hashlib
import json
import pickle
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from audit_vi_holdout import REVIEW, audit_partitions, similarity_edges, template_signature, write_rows, sha
from modeling import text_model, url_scores, meta_features, pipeline_fingerprint
from predict import load_bundle
from preprocess import DATA_DIR, clean_messages, extract_urls, normalize_text
from train_meta_fusion import compute_metrics

EXPERIMENT = REVIEW / "experiment"


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def experimental_training_rows(rows, allow_ai):
    if not allow_ai:
        raise ValueError("AI-reviewed training requires explicit experimental opt-in")
    result = []
    for row in rows:
        if (row["source_split"] not in {"provider_train", "legacy_review"}
                or row.get("partition") in {"validation", "test"} or row.get("do_not_train") is True):
            raise ValueError("Cannot train on reserved external test records")
        label = row["ai_proposed_label"]
        if label is None:
            continue
        if type(label) is not int or label not in (0, 1):
            raise ValueError("Invalid explicit review label")
        result.append(dict(row, candidate_label=label,
                           candidate_label_provenance="ai_semantic_review",
                           experiment_use="explicit_opt_in_ai_label_training_only",
                           expert_verified=False, eligible_for_automatic_training=False))
    return result


def choose_human_sample(rows, per_class=15):
    selected = []
    for label in (1, 0):
        pool = sorted((r for r in rows if r["resolved_review_label"] == label),
                      key=lambda r: (r["ai_category"], r["case_id"]))
        categories, groups, chosen = set(), set(), []
        for diverse in (True, False):
            for row in pool:
                if len(chosen) >= per_class:
                    break
                if row["similarity_group"] in groups or (diverse and row["ai_category"] in categories):
                    continue
                groups.add(row["similarity_group"])
                categories.add(row["ai_category"])
                chosen.append(row)
        selected += chosen
    return [{"case_id": r["case_id"], "raw_text": r["raw_text"], "human_label": None,
             "human_reviewer": None, "evidence": None, "expert_verified": False}
            for r in sorted(selected, key=lambda r: r["case_id"])]


def metric_summary(y, scores):
    result = compute_metrics(y, scores)
    tn, fp, fn, tp = confusion_matrix(y, scores >= .5, labels=[0, 1]).ravel()
    result["confusion"] = {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
    rounded = np.rint(scores * 100)
    result["policy"] = {"missed_low_risk": int(((y == 1) & (rounded < 30)).sum()),
                        "benign_review_or_high": int(((y == 0) & (rounded >= 30)).sum()),
                        "benign_high_risk": int(((y == 0) & (rounded >= 80)).sum()),
                        "scam_high_risk": int(((y == 1) & (rounded >= 80)).sum())}
    return result


def reviewed_training_data():
    sample_path = EXPERIMENT / "vi_train_manual_review_candidates.jsonl"
    notes = json.loads((EXPERIMENT / "vi_train_manual_review_notes.json").read_text(encoding="utf-8"))
    if sha(sample_path) != notes["input_sha256"]:
        raise ValueError("Training review sample changed; manual re-review required")
    sample = read_jsonl(sample_path)
    by_id = {r["source_record"]: r for r in sample}
    assignments = {}
    for group in notes["groups"]:
        for number in map(int, group["ids"].split(",")):
            if number not in by_id or number in assignments:
                raise ValueError(f"Missing or repeated reviewed training ID: {number}")
            assignments[number] = group
    if assignments.keys() != by_id.keys() or len(sample) != 120:
        raise ValueError("Training sample review is incomplete")
    reviewed = []
    source = DATA_DIR / "reference/vietnamese_sms_dataset/train.csv"
    with source.open(encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))
    for row in sample:
        source_row = source_rows[row["source_record"] - 1]
        if (row["source_sha256"] != sha(source) or source_row["message"] != row["raw_text"]
                or source_row["label"] != row["original_source_label"]):
            raise ValueError("Provider training provenance mismatch")
        group = assignments[row["source_record"]]
        reviewed.append(dict(row, ai_proposed_label=group["label"], ai_category=group["category"],
                             rationale_vi=group["reason"], label_provenance="ai_semantic_review",
                             ai_reviewer="Codex (AI)", gold_smishing_label=None,
                             eligible_for_automatic_training=False))
    legacy = read_jsonl(REVIEW / "sms_200_ai_review.jsonl")
    legacy = [dict(r, case_id=f"OLD-{r['source_record']}", source_split="legacy_review",
                   ai_proposed_label=r["proposed_label"]) for r in legacy]
    return reviewed, legacy


def human_review_progress(sample, evaluation):
    decisions = json.loads((EXPERIMENT / "human_verification.json").read_text(encoding="utf-8"))
    sample_by_id = {r["case_id"]: r for r in sample}
    known = []
    for decision in decisions["decisions"]:
        if decision["case_id"] in sample_by_id:
            known.append(dict(sample_by_id[decision["case_id"]], human_label=decision["label"],
                              human_reviewer="project_user", evidence=decision["user_answer"], expert_verified=False))
    write_rows(EXPERIMENT, "human_validation_confirmed", known)
    evaluation_ids = {r["case_id"] for r in evaluation}
    status = {"sample_size": len(sample), "user_confirmed_cases": len(known),
              "user_confirmed_in_frozen_evaluation": sum(r["case_id"] in evaluation_ids for r in known),
              "pending_asked_case_ids": decisions["pending_case_ids"], "expert_verified_cases": 0,
              "verified_accuracy_available": False,
              "note": "Individual user labels do not establish sender identity or independent expert ground truth."}
    write_json(EXPERIMENT / "human_validation_progress.json", status)
    return status


def screen_evaluation(rows):
    """Freeze a more conservative .80 lexical screen before fitting or predicting."""
    references = defaultdict(list)
    for path, source, column in [
        (DATA_DIR / "smishing_combined.csv", "legacy_sms", "message"),
        (DATA_DIR / "prepared/spam_restored_full.csv", "uci_restored", "raw_text"),
        (DATA_DIR / "reference/vietnamese_sms_dataset/train.csv", "provider_train", "message"),
    ]:
        with path.open(encoding="utf-8-sig", newline="") as f:
            for n, row in enumerate(csv.DictReader(f), 1):
                signature = template_signature(row[column])
                if signature:
                    references[signature].append(f"{source}:{n}")
    signatures = [template_signature(r["raw_text"]) for r in rows]
    keys = list(references)
    edges, overlap, evidence = [], set(), []
    seen = {}
    for i, row in enumerate(rows):
        if row["similarity_group"] in seen:
            edges.append((seen[row["similarity_group"]], i))
        else:
            seen[row["similarity_group"]] = i
    for i, j, score in similarity_edges(signatures, signatures, .80):
        if i < j:
            edges.append((i, j))
    for i, j, score in similarity_edges(signatures, keys, .80):
        overlap.add(i)
        evidence.append({"case_id": rows[i]["case_id"], "cosine": score,
                         "reference_records": references[keys[j]], "reference_template": keys[j]})
    prepared = [dict(r, previous_similarity_group=r["similarity_group"]) for r in rows]
    manifest = audit_partitions(prepared, edges, overlap)
    return manifest, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-ai-labels", action="store_true",
                        help="Explicitly permit AI labels for this isolated research experiment only")
    args = parser.parse_args()
    if not args.allow_ai_labels:
        parser.error("Use --allow-ai-labels only for an explicitly authorized exploratory training run")
    protected = [p for p in REVIEW.rglob("*") if p.is_file() and EXPERIMENT not in p.parents]
    protected += list(DATA_DIR.glob("*.csv"))
    protected += [p for p in (DATA_DIR / "reference").rglob("*") if p.is_file()]
    protected += [p for p in (DATA_DIR.parent / "models").rglob("*") if p.is_file()]
    protected += list(EXPERIMENT.glob("*manual_review*"))
    protected = sorted(set(protected))
    input_hashes = {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in protected}
    reviewed, legacy = reviewed_training_data()
    training = experimental_training_rows(reviewed + legacy, args.allow_ai_labels)
    write_rows(EXPERIMENT, "vi_train_ai_review", reviewed)
    write_rows(EXPERIMENT, "vi_train_unresolved", [r for r in reviewed if r["ai_proposed_label"] is None])
    prior_eval = read_jsonl(REVIEW / "holdout_audit/reserved_holdout_candidates.jsonl")
    sample = choose_human_sample(prior_eval)
    sample_path = EXPERIMENT / "human_validation_sample.jsonl"
    if not sample_path.exists():
        write_rows(EXPERIMENT, "human_validation_sample", sample)
    else:
        saved = read_jsonl(sample_path)
        if [(r["case_id"], r["raw_text"]) for r in saved] != [(r["case_id"], r["raw_text"]) for r in sample]:
            raise ValueError("Existing human review sample differs; refusing to overwrite")
    print(json.dumps({"training_candidates": len(training), "vi_reviewed": len(reviewed),
                      "vi_proposed_labels": dict(Counter(str(r["ai_proposed_label"]) for r in reviewed)),
                      "human_validation_sample": len(sample), "screening_threshold": .80}), flush=True)
    manifest, evidence = screen_evaluation(prior_eval)
    write_rows(EXPERIMENT, "strict_evaluation_screen", manifest)
    write_rows(EXPERIMENT, "strict_overlap_evidence", evidence)
    evaluation = [r for r in manifest if r["holdout_disposition"] == "reserved_holdout_pending_validation"]
    if not evaluation or len({r["resolved_review_label"] for r in evaluation}) != 2:
        raise ValueError("Conservative evaluation split requires both classes")
    write_rows(EXPERIMENT, "frozen_exploratory_evaluation", evaluation)
    dedup_keys = []
    for row in training:
        masked, urls = extract_urls(row["raw_text"])
        normalized = normalize_text(masked)
        dedup_keys.append(normalized + "|" + json.dumps(urls, ensure_ascii=False))
    clean, training_audit = clean_messages(pd.DataFrame({"raw_text": [r["raw_text"] for r in training],
                                                       "label": [r["candidate_label"] for r in training]}))
    fit_keys, consumed = set(clean.dedup_key), set()
    training_manifest = []
    for row, key in zip(training, dedup_keys):
        use = key in fit_keys and key not in consumed
        consumed.add(key)
        training_manifest.append(dict(row, used_in_fit=use))
    assert sum(r["used_in_fit"] for r in training_manifest) == len(clean)
    assert not {r["raw_text"] for r in training_manifest} & {r["raw_text"] for r in evaluation}
    write_rows(EXPERIMENT, "experimental_training_manifest", training_manifest)
    print(json.dumps({"frozen_evaluation_rows": len(evaluation),
                      "evaluation_labels": dict(Counter(str(r["resolved_review_label"]) for r in evaluation)),
                      "fitting_rows": len(clean)}), flush=True)
    # Same estimator and fixed settings as the deployed text model: no holdout tuning.
    candidate = text_model().fit(clean.normalized_text.to_numpy(), clean.label.to_numpy())
    deployed = load_bundle()
    eval_texts, links = [], []
    for row in evaluation:
        masked, urls = extract_urls(row["raw_text"])
        eval_texts.append(normalize_text(masked))
        links.append(urls)
    y = np.asarray([r["resolved_review_label"] for r in evaluation])
    current_text = deployed["text_model"].predict_proba(eval_texts)[:, 1]
    current_url = url_scores(deployed["url_model"], links)
    current_full = current_text.copy()
    paired = np.asarray([bool(u) for u in links])
    if paired.any():
        current_full[paired] = deployed["meta_model"].predict_proba(
            meta_features(current_text[paired], current_url[paired]))[:, 1]
    candidate_text = candidate.predict_proba(eval_texts)[:, 1]
    metrics = {"deployed_text_only": metric_summary(y, current_text),
               "candidate_text_only": metric_summary(y, candidate_text),
               "deployed_full_pipeline_context": metric_summary(y, current_full)}
    predictions = []
    for row, old, new, full in zip(evaluation, current_text, candidate_text, current_full):
        predictions.append(dict(row, deployed_text_score=float(old), candidate_text_score=float(new),
                                deployed_full_score=float(full),
                                candidate_error_at_50=bool((new >= .5) != row["resolved_review_label"]),
                                baseline_error_at_50=bool((old >= .5) != row["resolved_review_label"])))
    write_rows(EXPERIMENT, "comparison_predictions", predictions)
    write_rows(EXPERIMENT, "candidate_error_cases", [r for r in predictions if r["candidate_error_at_50"]])
    metadata = {"purpose": "Isolated exploratory supervised text experiment; not an API model bundle",
                "ai_labels_opt_in": True, "expert_verified": False,
                "pipeline_fingerprint": pipeline_fingerprint(), "algorithm": "existing text_model; fixed C=1",
                "training_manifest_sha256": sha(EXPERIMENT / "experimental_training_manifest.jsonl"),
                "frozen_evaluation_sha256": sha(EXPERIMENT / "frozen_exploratory_evaluation.jsonl")}
    with (EXPERIMENT / "experimental_text_model.pkl").open("wb") as f:
        pickle.dump({"metadata": metadata, "text_model": candidate}, f, protocol=pickle.HIGHEST_PROTOCOL)
    progress = human_review_progress(sample, evaluation)
    report = {"date": "2026-10-25", "training_performed": True, "deployed_model_replaced": False,
              "verified_evaluation_performed": False, "human_validation_sample_size": len(sample),
              "human_validation_status": "pending_user_or_independent_annotation",
              "human_validation_progress": progress, "model_metadata": metadata,
              "experimental_model_sha256": sha(EXPERIMENT / "experimental_text_model.pkl"),
              "vi_training_review_counts": dict(Counter(str(r["ai_proposed_label"]) for r in reviewed)),
              "legacy_review_counts": dict(Counter(str(r["ai_proposed_label"]) for r in legacy)),
              "training_audit": training_audit, "training_sources": dict(Counter(r["source_split"] for r in training_manifest if r["used_in_fit"])),
              "frozen_evaluation_samples": len(evaluation), "evaluation_label_counts": dict(Counter(str(v) for v in y)),
              "stricter_screen_threshold": .80, "screen_dispositions": dict(Counter(r["holdout_disposition"] for r in manifest)),
              "metrics_against_ai_proposals_only": metrics,
              "baseline_bundle_sha256": sha(DATA_DIR.parent / "models/model_bundle.pkl"),
              "input_sha256": input_hashes, "experiment_code_sha256": sha(Path(__file__)),
              "promotion_decision": "Do not deploy based on AI-label comparison; human validation and broader evaluation are still required.",
              "limitations": ["No expert-verified test labels. Reported metrics measure agreement with AI proposals, not verified real-world accuracy.",
                              "Small, imbalanced evaluation set; lexical screening does not establish semantic or campaign independence.",
                              "Training and evaluation annotations come from the same AI reviewer, creating correlated annotation bias.",
                              "Only the text estimator is retrained; existing fusion is reported separately as context, not as an equivalent architecture.",
                              "The human sample is selected for class/category coverage and is not a prevalence estimate.",
                              "No tuning or repeated model selection on the frozen evaluation set was performed."]}
    assert input_hashes == {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in protected}, "Original data/model changed"
    write_json(EXPERIMENT / "experiment_report.json", report)
    lines = ["# Thử nghiệm huấn luyện và so sánh — 25/10/2026", "",
             "Đã huấn luyện một model văn bản thử nghiệm riêng. Model đang dùng trong ứng dụng được giữ nguyên.", "",
             "**Kết quả bên dưới so với nhãn AI đề xuất, chưa phải độ chính xác được con người/chuyên gia kiểm định.**", "",
             f"Đọc thêm 120 tin từ tập train tiếng Việt: {report['vi_training_review_counts']}. "
             f"Kết hợp các nhãn AI rõ của mẫu 200 tin cũ; sau lọc trùng/xung đột còn {len(clean)} tin huấn luyện.", "",
             f"Lọc lại 379 ứng viên kiểm thử bằng ngưỡng tương đồng 0,80 với toàn bộ nguồn train/legacy, trước khi fit hoặc dự đoán. "
             f"Còn {len(evaluation)} mẫu với nhãn {report['evaluation_label_counts']}. Không đưa mẫu external test nào vào train.", "",
             "| Model | Báo nhầm FP | Bỏ sót FN | Bắt đúng TP | F1 so với nhãn AI |", "|---|---:|---:|---:|---:|"]
    for name, value in metrics.items():
        c = value["confusion"]
        lines.append(f"| {name} | {c['fp']} | {c['fn']} | {c['tp']} | {value['f1']:.3f} |")
    new_policy = metrics["candidate_text_only"]["policy"]
    old_policy = metrics["deployed_text_only"]["policy"]
    lines += ["", "So sánh chính là hai model text-only cùng thuật toán và tham số, khác dữ liệu huấn luyện. "
              "Dòng full pipeline là bối cảnh vận hành, có thêm URL/fusion nên không phải cùng cấu hình với model thử.", "",
              f"**Theo chính sách ứng dụng (30 điểm cần xem xét, 80 điểm cảnh báo cao), model thử đưa "
              f"{new_policy['benign_review_or_high']} tin nhãn 0 vào diện xem xét/cảnh báo, so với "
              f"{old_policy['benign_review_or_high']} của model văn bản cũ. Có "
              f"{new_policy['scam_high_risk']} ca nhãn 1 đạt cảnh báo cao. Vì vậy giảm lỗi ở ngưỡng 50% chưa chứng minh "
              "model phù hợp để thay vào ứng dụng. Không điều chỉnh ngưỡng sau khi xem kết quả tập này.**", "",
              f"Chuẩn bị {len(sample)} mẫu kiểm định có phủ nhóm nội dung/lớp trong `human_validation_sample.csv/jsonl`, "
              "không hiển thị nhãn AI. Những câu bạn đã trả lời được lưu riêng trong `human_verification.json`; "
              "không suy rộng câu trả lời sang mẫu tương tự và không ghi thành chuyên gia kiểm định.", "",
              f"Hiện ghi nhận {progress['user_confirmed_cases']} mẫu trong bộ nhỏ đã được bạn xác nhận; "
              f"{progress['user_confirmed_in_frozen_evaluation']} mẫu nằm trong tập so sánh sau lọc chặt. "
              f"Các câu đã hỏi còn chờ trả lời: {progress['pending_asked_case_ids']}. "
              "Chưa tính chỉ số độ chính xác được con người kiểm định.", "",
              "`vi_train_ai_review.csv/jsonl`: 120 tin mới đọc, nhãn nguồn, nhãn AI và lý do. "
              "`vi_train_unresolved.csv/jsonl`: các tin loại khỏi lần fit này. "
              "`experimental_training_manifest.csv/jsonl`: truy vết từng mẫu có/không dùng trong fit. "
              "`strict_evaluation_screen.csv/jsonl` và `strict_overlap_evidence.csv/jsonl`: quyết định lọc cùng bằng chứng. "
              "`comparison_predictions.csv/jsonl`: dự đoán từng tin; `candidate_error_cases.csv/jsonl`: các lỗi theo nhãn AI.", "",
              "`experimental_text_model.pkl` chỉ là model nghiên cứu riêng, không phải bundle đủ thành phần cho ứng dụng. "
              "Các nhãn AI chỉ được dùng sau opt-in thử nghiệm; cờ nguồn chặn tự động huấn luyện/đánh giá được giữ nguyên trong dữ liệu gốc.", "",
              "Bước cần người thật: hoàn tất xác minh tập nhỏ và xử lý bất đồng nhãn, rồi đánh giá trên dữ liệu đủ đa dạng, "
              "đặc biệt thêm ca lừa đảo. Chưa thay model ứng dụng hoặc công bố cải thiện chính thức từ thử nghiệm này."]
    (EXPERIMENT / "KET_QUA_THU_NGHIEM.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"training_rows": len(clean), "evaluation_rows": len(evaluation),
                      "metrics_against_ai_proposals_only": metrics}), flush=True)


if __name__ == "__main__":
    main()
