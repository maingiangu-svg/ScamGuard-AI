"""Offline similarity audit of reviewed Vietnamese holdout candidates; no training."""
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from preprocess import DATA_DIR, extract_urls

REVIEW = DATA_DIR / "prepared/review_2026-10-25"
THRESHOLD = .90


def audit_url_text(text):
    """Remove punctuation wrapping explicit dataset URLs, without fetching them."""
    return re.sub(r"https?://[^\s<>]+", lambda m: m.group().rstrip("]}).,;:!?\"'"), text, flags=re.I)


def audit_hostnames(text):
    _, urls = extract_urls(audit_url_text(text))
    return {urlsplit(u).hostname for u in urls}


def template_signature(text):
    text = unicodedata.normalize("NFC", text).casefold()
    text, _ = extract_urls(audit_url_text(text))
    text = re.sub(r"\[(?:number|money|time|date|name|point|phone)\]", " <slot> ", text)
    text = re.sub(r"\d+(?:[.,:/-]\d+)*", " <slot> ", text)
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    text = text.replace("đ", "d")
    return " ".join(re.findall(r"<url>|<slot>|[^\W_]+", text))


def similarity_edges(queries, references, threshold=THRESHOLD):
    """All char-ngram cosine matches above threshold; scores are not probabilities."""
    if not queries or not references:
        return
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                 max_features=60000, dtype=np.float32)
    matrix = vectorizer.fit_transform(references + queries)
    ref = matrix[:len(references)]
    query = matrix[len(references):]
    # ponytail: sparse batches bound memory for this ~90k-reference offline audit.
    for start in range(0, len(queries), 24):
        scores = (query[start:start + 24] @ ref.T).tocoo()
        for i, j, score in zip(scores.row, scores.col, scores.data):
            if score >= threshold:
                yield start + int(i), int(j), min(1.0, float(score))


def audit_partitions(rows, edges, reference_overlap):
    if len({r["case_id"] for r in rows}) != len(rows):
        raise ValueError("Repeated case ID")
    if any(r["resolved_review_label"] is not None and
           (type(r["resolved_review_label"]) is not int or r["resolved_review_label"] not in (0, 1))
           for r in rows):
        raise ValueError("Review labels must be explicit integers 0/1 or null")
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for left, right in edges:
        parent[find(left)] = find(right)
    members = defaultdict(list)
    for i in range(len(rows)):
        members[find(i)].append(i)
    result = [None] * len(rows)
    for indices in members.values():
        cases = sorted(rows[i]["case_id"] for i in indices)
        group_id = "VI-G-" + hashlib.sha256("|".join(cases).encode()).hexdigest()[:12]
        labels = {rows[i]["resolved_review_label"] for i in indices} - {None}
        overlap = any(i in reference_overlap for i in indices)
        unresolved = any(rows[i]["resolved_review_label"] is None for i in indices)
        conflict = len(labels) > 1
        for i in indices:
            disposition = ("quarantine_unresolved_label" if rows[i]["resolved_review_label"] is None else
                           "blocked_group_label_conflict" if conflict else
                           "blocked_unresolved_group" if unresolved else
                           "blocked_reference_overlap" if overlap else
                           "reserved_holdout_pending_validation")
            result[i] = dict(rows[i], similarity_group=group_id, group_size=len(indices),
                             group_label_conflict=conflict, group_contains_unresolved=unresolved,
                             direct_reference_overlap=i in reference_overlap,
                             group_reference_overlap=overlap, holdout_disposition=disposition,
                             intended_role="external_holdout_only", do_not_train=True,
                             eligible_for_verified_evaluation=False)
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rows(directory, stem, rows):
    (directory / f"{stem}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    if rows:
        with (directory / f"{stem}.csv").open("w", encoding="utf-8-sig", newline="") as f:
            columns = list(dict.fromkeys(key for row in rows for key in row))
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                              for k, v in row.items()} for row in rows)
    else:
        (directory / f"{stem}.csv").write_text("", encoding="utf-8-sig")


def main():
    sources = [(DATA_DIR / "smishing_combined.csv", "legacy_sms", "message"),
               (DATA_DIR / "prepared/spam_restored_full.csv", "uci_restored", "raw_text"),
               (DATA_DIR / "reference/vietnamese_sms_dataset/train.csv", "provider_train", "message")]
    protected = list(REVIEW.glob("*.*")) + [p for p, _, _ in sources]
    protected += list((DATA_DIR.parent / "models").glob("*"))
    protected += list(DATA_DIR.glob("*.csv"))
    protected = sorted({p for p in protected if p.is_file()})
    hashes = {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in protected}
    rows = [json.loads(s) for s in (REVIEW / "vi_ai_review.jsonl").read_text(encoding="utf-8").splitlines()]
    signatures = [template_signature(r["raw_text"]) for r in rows]
    ref_by_template, ref_hosts = defaultdict(list), defaultdict(list)
    source_counts = {}
    for path, source, column in sources:
        with path.open(encoding="utf-8-sig", newline="") as f:
            records = list(csv.DictReader(f))
        source_counts[source] = len(records)
        for n, row in enumerate(records, 1):
            record = {"source": source, "record": n, "raw_text": row[column]}
            signature = template_signature(row[column])
            if signature:
                ref_by_template[signature].append(record)
            for host in audit_hostnames(row[column]):
                ref_hosts[host].append(record)
    print(json.dumps({"loaded_review": len(rows), "reference_rows": source_counts,
                      "reference_templates": len(ref_by_template)}), flush=True)
    edges, overlap_rows = [], []
    seen, reference_overlap = {}, set()
    for i, (row, signature) in enumerate(zip(rows, signatures)):
        hosts = set(row.get("extracted_hostnames", [])) | audit_hostnames(row["raw_text"])
        for key in ["template:" + signature] + ["host:" + h for h in sorted(hosts) if h]:
            if key in seen:
                edges.append({"left_id": rows[seen[key]]["case_id"], "right_id": row["case_id"],
                              "left_index": seen[key], "right_index": i,
                              "method": key.split(":", 1)[0], "cosine": None})
            else:
                seen[key] = i

        def record_match(method, records, score=None):
            reference_overlap.add(i)
            overlap_rows.append({"case_id": row["case_id"], "method": method, "cosine": score,
                                 "raw_text": row["raw_text"], "reference_example": records[0]["raw_text"],
                                 "reference_count": len(records),
                                 "reference_records": [f"{r['source']}:{r['record']}" for r in records]})

        if signature in ref_by_template:
            record_match("exact_masked_template", ref_by_template[signature])
        for host in sorted(hosts):
            if host in ref_hosts:
                record_match("shared_hostname:" + host, ref_hosts[host])
    # Approximate matches require enough visible words; do not compare gibberish/codes as prose.
    long_ids = [i for i, s in enumerate(signatures) if len(s) >= 40 and
                len(re.findall(r"\b[a-z]{2,}\b", s.replace("<slot>", "").replace("<url>", ""))) >= 6]
    long_texts = [signatures[i] for i in long_ids]
    for a, b, score in similarity_edges(long_texts, long_texts):
        i, j = long_ids[a], long_ids[b]
        if i < j and signatures[i] != signatures[j]:
            edges.append({"left_id": rows[i]["case_id"], "right_id": rows[j]["case_id"],
                          "left_index": i, "right_index": j, "method": "char_ngram_cosine", "cosine": score})
    reference_templates = list(ref_by_template)
    for a, b, score in similarity_edges(long_texts, reference_templates):
        i = long_ids[a]
        if signatures[i] == reference_templates[b]:
            continue
        records = ref_by_template[reference_templates[b]]
        reference_overlap.add(i)
        overlap_rows.append({"case_id": rows[i]["case_id"], "method": "char_ngram_cosine", "cosine": score,
                             "raw_text": rows[i]["raw_text"], "reference_example": records[0]["raw_text"],
                             "reference_count": len(records),
                             "reference_records": [f"{r['source']}:{r['record']}" for r in records]})
    output = audit_partitions(rows, [(e["left_index"], e["right_index"]) for e in edges], reference_overlap)
    assert hashes == {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in protected}, "Protected input changed"
    directory = REVIEW / "holdout_audit"
    directory.mkdir(exist_ok=True)
    write_rows(directory, "all_519_group_manifest", output)
    write_rows(directory, "quarantine_63_unresolved", [r for r in output if r["resolved_review_label"] is None])
    write_rows(directory, "annotated_456_candidates", [r for r in output if r["resolved_review_label"] is not None])
    reserved = [r for r in output if r["holdout_disposition"] == "reserved_holdout_pending_validation"]
    write_rows(directory, "reserved_holdout_candidates", reserved)
    write_rows(directory, "within_review_similarity_edges", edges)
    write_rows(directory, "reference_overlap_evidence", overlap_rows)
    grouped = defaultdict(list)
    for row in output:
        grouped[row["similarity_group"]].append(row)
    groups = [{"group_id": key, "size": len(value), "case_ids": [r["case_id"] for r in value],
               "labels": sorted({r["resolved_review_label"] for r in value} - {None}),
               "contains_unresolved": value[0]["group_contains_unresolved"],
               "label_conflict": value[0]["group_label_conflict"],
               "reference_overlap": value[0]["group_reference_overlap"]} for key, value in grouped.items()]
    write_rows(directory, "similarity_groups", groups)
    report = {"date": "2026-10-25", "review_rows": len(output),
              "quarantine_unresolved": sum(r["resolved_review_label"] is None for r in output),
              "annotated_candidates": sum(r["resolved_review_label"] is not None for r in output),
              "reference_rows": source_counts, "similarity_threshold": THRESHOLD,
              "group_count": len(groups), "multi_message_groups": sum(g["size"] > 1 for g in groups),
              "group_label_conflicts": sum(g["label_conflict"] for g in groups),
              "direct_reference_overlap_rows": len(reference_overlap),
              "dispositions": dict(Counter(r["holdout_disposition"] for r in output)),
              "reserved_label_counts": dict(Counter(str(r["resolved_review_label"]) for r in reserved)),
              "protected_file_sha256": hashes, "audit_code_sha256": sha(Path(__file__)),
              "training_performed": False, "verified_evaluation_performed": False,
              "limitations": ["Similarity is a conservative lexical/template screen, not proof of the same campaign.",
                              "No guarantee of detecting semantic paraphrases or unseen data sources.",
                              "AI/user labels retain their provenance; no expert verification is inferred.",
                              "The audited provider test stays reserved; no rows are assigned to training.",
                              "Reported conflicts are group review flags, not automatic label corrections.",
                              "Audit TF-IDF uses combined unlabeled text only to find overlap; no classifier is fitted."]}
    (directory / "audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (directory / "KET_QUA_TACH_VA_NHOM.md").write_text(
        "# Kết quả tách và kiểm tra tin tương tự — 25/10/2026\n\n"
        f"Đã tách {report['quarantine_unresolved']} mẫu chưa rõ vào `quarantine_63_unresolved.csv/jsonl`. "
        f"{report['annotated_candidates']} mẫu đã có nhãn đề xuất nằm trong `annotated_456_candidates.csv/jsonl`; "
        "đây chưa phải dữ liệu được chuyên gia kiểm định. Không thay nhãn nguồn hoặc huấn luyện model.\n\n"
        f"Kiểm tra với {sum(source_counts.values()):,} bản ghi từ SMS cũ, UCI khôi phục và tập train nhà cung cấp. "
        f"Phát hiện {len(reference_overlap)} mẫu có trùng mẫu câu, gần giống hoặc chung hostname với nguồn đối chiếu. "
        f"519 mẫu được gom thành {len(groups)} nhóm, trong đó {report['multi_message_groups']} nhóm có nhiều tin, "
        f"{report['group_label_conflicts']} nhóm chứa cả nhãn 0 và 1. Khác nhãn trong nhóm là cờ cần kiểm tra, không tự sửa.\n\n"
        "## Các trạng thái\n\n" + "\n".join(f"- `{k}`: {v} mẫu." for k, v in report['dispositions'].items()) +
        "\n\nMọi thành viên trong nhóm phải cùng một phía nếu chia dữ liệu sau này. Một mẫu trùng nguồn đối chiếu "
        "sẽ chặn cả nhóm khỏi danh sách holdout mới. Nhóm có mẫu chưa rõ hoặc nhãn trái nhau cũng chưa được chọn. "
        "Những tin không có nhãn vẫn giữ null; không được chuyển thành 0.\n\n"
        f"Còn {len(reserved)} mẫu trong `reserved_holdout_candidates.csv/jsonl` sau sàng lọc; nhãn: "
        f"{report['reserved_label_counts']}. Đây là ứng viên cần kiểm định, không phải bộ chuẩn đo độ chính xác. "
        "Các cờ `do_not_train=true` và `eligible_for_verified_evaluation=false` được giữ nguyên.\n\n"
        "## Cách dò và giới hạn\n\n"
        "Chuẩn hóa để so sánh: bỏ khác biệt hoa/thường, dấu tiếng Việt, dấu câu; che URL, số và placeholder "
        "đã ẩn. Nối các tin cùng mẫu câu hoặc hostname, rồi nối cặp có cosine ký tự 3–5 gram từ 0,90 trở lên. "
        "Chỉ dò gần đúng khi còn ít nhất 6 từ và 40 ký tự. Ngưỡng là lựa chọn sàng lọc thận trọng, chưa được "
        "hiệu chuẩn bằng nhãn cặp giống/khác. Có thể gom quá rộng hoặc bỏ sót diễn đạt lại. TF-IDF chỉ phục vụ "
        "kiểm tra trùng lặp, không huấn luyện bộ phân loại.\n\n"
        "`reference_overlap_evidence.csv/jsonl` chứa cặp đối chiếu và điểm tương đồng; "
        "`within_review_similarity_edges.csv/jsonl` và `similarity_groups.csv/jsonl` giải thích cách gom; "
        "`all_519_group_manifest.csv/jsonl` là danh sách trạng thái từng mẫu. Các mã reference dạng "
        "nguồn:số_bản_ghi tính từ 1, không tính dòng tiêu đề. Toàn bộ nguồn và model được kiểm tra SHA-256 trước/sau.\n",
        encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["review_rows", "group_count", "group_label_conflicts", "dispositions"]}), flush=True)


if __name__ == "__main__":
    main()
