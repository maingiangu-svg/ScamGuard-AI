"""Traceable external-data experiment. Source labels are never expert labels."""
import csv
import hashlib
import io
import ipaddress
import json
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zipfile import ZipFile

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from audit_vi_holdout import REVIEW, audit_hostnames, audit_url_text, template_signature, similarity_edges, write_rows, sha
from data_quality import repair_url
from preprocess import DATA_DIR
from round2_experiment import text_input
from run_review_experiment import read_jsonl, write_json

REF = DATA_DIR / "reference/external_2026-10-25"
OUT = DATA_DIR / "prepared/external_training_2026-10-25"
ROUND2 = REVIEW / "round2"
PINS = {"Dataset_5971.zip": "9bbf3188fdad81495d8e82825648b9b63b53fc86841a3d26c02629990b233cc3",
        "PhishVN_v3.1.0_open.zip": "308351e9d0c0fca13a81f2f63524a7dee08ccba6c775848d125b3da5525d0ab5",
        "public_suffix_list.dat": "0232f4df0831911356e8ee1f4d5c3b6b12c0ed3f6bd66b0f81c8ab5d3d49e9ca"}
AUDIT_COMMIT = "2e2974144ee2e77170ddf06e1ec615d8586854a0"


def url_input(value):
    """Remove the collection's HTTP/HTTPS shortcut while retaining lexical cues."""
    fixed, _ = repair_url(value)
    if not fixed:
        raise ValueError("Invalid URL model input")
    parts = urlsplit(fixed)
    return urlunsplit(("http", parts.netloc, parts.path, parts.query, ""))


class RegisteredDomains:
    """Offline Public Suffix List rules, including wildcard and exception rules."""
    def __init__(self, content):
        self.exact, self.wild, self.exceptions = set(), set(), set()
        for line in content.splitlines():
            rule = line.split("//", 1)[0].strip()
            if not rule:
                continue
            target = self.exceptions if rule.startswith("!") else self.wild if rule.startswith("*.") else self.exact
            rule = rule.removeprefix("!").removeprefix("*.")
            target.add(rule.encode("idna").decode("ascii").lower())

    @lru_cache(maxsize=100000)
    def __call__(self, host):
        host = host.rstrip(".").encode("idna").decode("ascii").lower()
        try:
            ipaddress.ip_address(host)
            return host
        except ValueError:
            pass
        parts, length = host.split("."), 1
        for i in range(len(parts)):
            suffix = ".".join(parts[i:])
            if suffix in self.exceptions:
                length = len(parts) - i - 1
                break
            if suffix in self.exact:
                length = max(length, len(parts) - i)
            if i > 0 and suffix in self.wild:
                length = max(length, len(parts) - i + 1)
        return ".".join(parts[-(length + 1):])


def sms_project_label(original, review):
    original = original.strip().lower()
    if original not in {"ham", "spam", "smishing"}:
        raise ValueError("Unknown SMS source label")
    if review is not None:
        value = review["label"]
        if value is not None and (type(value) is not int or value not in (0, 1)):
            raise ValueError("Invalid reviewed label")
        return value
    return 0 if original in {"ham", "spam"} else None


def url_primary_eligible(row):
    return ((row["label"] == "phishing" and row["tier"] == "gold") or
            (row["label"] == "benign" and row["tier"] in {"gold", "silver"}))


def merge_human_audit(a, b, arbitration):
    second = {r["vid"]: r for r in b}
    decisions = {r["vid"]: r for r in arbitration}
    first_ids = {r["vid"] for r in a}
    if len(first_ids) != len(a) or len(second) != len(b) or first_ids != set(second):
        raise ValueError("Audit IDs must match uniquely")
    if len(decisions) != len(arbitration) or not set(decisions) <= first_ids:
        raise ValueError("Arbitration IDs must be unique and belong to the audit")
    output = []
    for row in a:
        other = second[row["vid"]]
        if row["url"] != other["url"]:
            raise ValueError("Audit source URL mismatch")
        if row["vid"] in decisions:
            decision = decisions[row["vid"]]
            if decision["url"] != row["url"]:
                raise ValueError("Arbitration URL mismatch")
            verdict, evidence = decision["final_verdict"], decision["final_evidence"]
            rationale = decision.get("rationale", "")
            provenance = "published_independent_human_arbitration"
        else:
            if row["verdict"] != other["verdict"]:
                raise ValueError("Audit disagreement lacks arbitration")
            verdict, evidence = row["verdict"], row["evidence"] + ";" + other["evidence"]
            rationale, provenance = "Independent annotators agree", "published_two_annotator_consensus"
        if verdict not in {"phishing", "scam", "legitimate", "unsure"}:
            raise ValueError("Unknown human verdict")
        supported = bool({"archive", "capture", "urlscan", "registry"} & set(evidence.split(";")))
        label = {"phishing": 1, "legitimate": 0}.get(verdict)
        output.append({"case_id": "PHISHVN-AUDIT-" + row["vid"], "url_original": row["url"],
                       "human_verdict": verdict, "label": label, "evidence": evidence, "rationale": rationale,
                       "label_provenance": provenance, "human_verified": True, "expert_verified": False,
                       "strict_human_test_eligible": supported and label is not None,
                       "source_commit": AUDIT_COMMIT})
    return output


def csv_file(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def archive_csv(archive, name):
    with ZipFile(archive) as z:
        return list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))))


def verify_sources():
    for name, expected in PINS.items():
        if sha(REF / name) != expected:
            raise ValueError(f"Source checksum mismatch: {name}")
    tree = json.loads((REF / "phishvn_tree.json").read_text(encoding="utf-8"))
    if tree["sha"] != AUDIT_COMMIT:
        raise ValueError("Audit repository revision changed")
    for name in ("annotator_A.csv", "annotator_B.csv", "adjudicated.csv", "CODEBOOK.md"):
        path = "docs/verify/" + name
        content = (REF / "phishvn_audit" / path).read_bytes()
        expected = next(r["sha"] for r in tree["tree"] if r["path"] == path)
        if hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest() != expected:
            raise ValueError("Published human audit checksum mismatch")
    with ZipFile(REF / "PhishVN_v3.1.0_open.zip") as z:
        for line in z.read("MANIFEST.txt").decode("utf-8").splitlines():
            fields = line.split()
            if fields and re.fullmatch(r"[0-9a-f]{64}", fields[0]):
                if hashlib.sha256(z.read(fields[1])).hexdigest() != fields[0]:
                    raise ValueError("PhishVN internal MANIFEST mismatch")


def semantic_sms_notes():
    notes = json.loads((OUT / "sms_semantic_review_notes.json").read_text(encoding="utf-8"))
    sample = {}
    for name, expected in notes["input_sha256"].items():
        if sha(OUT / name) != expected:
            raise ValueError("SMS semantic sample changed")
        for row in read_jsonl(OUT / name):
            if row["source_record"] in sample:
                raise ValueError("Repeated semantic sample ID")
            sample[row["source_record"]] = row
    result = {}
    for group in notes["groups"]:
        for record in map(int, group["ids"].split(",")):
            if record in result or record not in sample:
                raise ValueError("Unexpected/repeated semantic annotation")
            result[record] = group
    if set(sample) != set(result):
        raise ValueError("Incomplete SMS semantic review")
    return result


def check_snapshot():
    for name, expected in json.loads((OUT / "protected_snapshot.json").read_text(encoding="utf-8")).items():
        if sha(DATA_DIR.parent / name) != expected:
            raise ValueError(f"Protected source/model changed: {name}")


def grouped_split(rows):
    y = np.array([r["label"] for r in rows])
    groups = np.array([r["group"] for r in rows])
    for train, test in StratifiedGroupKFold(5, shuffle=True, random_state=42).split(y, y, groups):
        if len(set(y[train])) == len(set(y[test])) == 2:
            return train, test
    raise ValueError("Cannot split groups with both classes")


def prepare():
    if (OUT / "selection_frozen.json").exists():
        raise ValueError("Experiment already frozen")
    verify_sources()
    protected = [p for p in REVIEW.rglob("*") if p.is_file()]
    protected += [p for p in (DATA_DIR.parent / "models").rglob("*") if p.is_file()]
    protected += list(DATA_DIR.glob("*.csv")) + [p for p in REF.rglob("*") if p.is_file()]
    write_json(OUT / "protected_snapshot.json", {str(p.relative_to(DATA_DIR.parent)): sha(p) for p in sorted(set(protected))})
    domain = RegisteredDomains((REF / "public_suffix_list.dat").read_text(encoding="utf-8"))
    base = REF / "phishvn_audit/docs/verify"
    audit = merge_human_audit(csv_file(base / "annotator_A.csv"), csv_file(base / "annotator_B.csv"), csv_file(base / "adjudicated.csv"))
    audit_domains = set()
    for row in audit:
        url, reason = repair_url(row["url_original"])
        if not url:
            raise ValueError("Invalid URL in human audit")
        row.update(url=url_input(url), group=domain(urlsplit(url).hostname), partition="human_test", do_not_train=True)
        audit_domains.add(row["group"])
    write_rows(OUT, "url_human_audit_all_200", audit)
    write_rows(OUT, "url_human_strict_test", [r for r in audit if r["strict_human_test_eligible"]])
    notes = semantic_sms_notes()
    sms, quarantine = [], []
    for n, row in enumerate(archive_csv(REF / "Dataset_5971.zip", "Dataset_5971.csv"), 1):
        review = notes.get(n)
        label = sms_project_label(row["LABEL"], review)
        record = {"case_id": f"M5971-{n:04}", "raw_text": row["TEXT"], "label": label,
                  "original_label": row["LABEL"], "label_provenance": "ai_semantic_review" if review else "upstream_ham_or_non_smishing_spam",
                  "rationale_vi": review["reason"] if review else "Original source class ham/spam; not independently verified for project scope.",
                  "source": "mishra_soni_5971", "source_record": n, "source_sha256": PINS["Dataset_5971.zip"],
                  "expert_verified": False, "human_verified": False, "language": "en", "license": "CC BY 4.0"}
        if label is None:
            record["issue"] = "unresolved_semantic_review" if review else "source_smishing_not_scope_reviewed"
            quarantine.append(record)
        else:
            sms.append(record)
    project = read_jsonl(ROUND2 / "latest_train_review_with_user_decisions.jsonl")
    for r in project:
        if r["split_eligible"] and r["resolved_label"] is not None:
            sms.append({"case_id": r["case_id"], "raw_text": r["raw_text"], "label": r["resolved_label"],
                        "original_label": r["original_source_label"], "label_provenance": r["label_provenance"],
                        "source": "project_reviewed_vi", "source_record": r["source_record"], "source_sha256": r["source_sha256"],
                        "expert_verified": False, "human_verified": False, "language": "vi", "license": "CC BY 4.0"})
    for r in read_jsonl(REVIEW / "sms_200_ai_review.jsonl"):
        if r["proposed_label"] is not None:
            sms.append({"case_id": f"OLD-{r['source_record']}", "raw_text": r["raw_text"], "label": r["proposed_label"],
                        "original_label": r["original_label"], "label_provenance": "ai_semantic_review",
                        "source": "project_legacy_review", "expert_verified": False, "human_verified": False, "language": "en"})
    # Never move historical held-out Vietnamese messages into training through a new source.
    reserved = read_jsonl(ROUND2 / "reviewed_validation.jsonl") + read_jsonl(ROUND2 / "test_reviewed_all.jsonl")
    reserved += read_jsonl(REVIEW / "vi_external_test_disjoint_candidates.jsonl")
    by_text = defaultdict(list)
    for r in sms:
        by_text[text_input(r["raw_text"])].append(r)
    unique = []
    for key, values in by_text.items():
        if not key or len({r["label"] for r in values}) > 1:
            quarantine.extend(dict(r, issue="empty_or_conflicting_review_labels") for r in values)
            continue
        keep = next((r for r in values if r["source"] == "project_reviewed_vi"), values[0])
        keep["merged_case_ids"] = [r["case_id"] for r in values]
        unique.append(keep)
    all_sms = unique + [dict(r, source="historical_reserved", label=None) for r in reserved]
    parent = list(range(len(all_sms)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    signatures = [template_signature(r["raw_text"]) for r in all_sms]
    sms_domains = set()
    for i, row in enumerate(all_sms):
        roots = {domain(h) for h in audit_hostnames(row["raw_text"])}
        sms_domains.update(roots)
        row["registrable_domains"] = sorted(roots)
        for key in ["text:" + signatures[i]] + ["domain:" + h for h in sorted(roots)]:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    print(json.dumps({"sms_candidates_before_grouping": len(unique), "reserved_contexts": len(reserved)}), flush=True)
    for i, j, score in similarity_edges(signatures, signatures, .80):
        if i < j:
            parent[find(i)] = find(j)
    blocked = {find(i) for i in range(len(unique), len(all_sms))}
    accepted = []
    for i, row in enumerate(unique):
        row["group"] = "SMS-G-" + str(find(i))
        if find(i) in blocked or set(row["registrable_domains"]) & audit_domains:
            quarantine.append(dict(row, issue="historical_sms_or_human_url_holdout_overlap"))
        else:
            accepted.append(row)
    pool, test = grouped_split(accepted)
    inner_rows = [accepted[i] for i in pool]
    train_i, val_i = grouped_split(inner_rows)
    splits = {"train": [inner_rows[i] for i in train_i], "validation": [inner_rows[i] for i in val_i],
              "test": [accepted[i] for i in test]}
    for role, values in splits.items():
        for r in values:
            r["partition"], r["do_not_train"] = role, role != "train"
        write_rows(OUT, "sms_" + role, values)
    write_rows(OUT, "sms_quarantine", quarantine)
    urls, url_quarantine = [], []
    for n, r in enumerate(archive_csv(REF / "PhishVN_v3.1.0_open.zip", "data/dataset_url.csv"), 1):
        url, action = repair_url(r["url"])
        if url:
            url = url_input(url)
        group = domain(urlsplit(url).hostname) if url else None
        row = {"case_id": "PHISHVN-" + r["id"], "url": url, "original_url": r["url"], "label": 1 if r["label"] == "phishing" else 0,
               "original_label": r["label"], "tier": r["tier"], "source": r["source"], "source_record": n,
               "source_sha256": PINS["PhishVN_v3.1.0_open.zip"], "provider_split": r["split"], "group": group,
               "label_provenance": "upstream_source_status_and_registry_not_expert_verified",
               "target_scope": "source_reported_abuse_or_phishing_vs_benign", "expert_verified": False, "human_verified": False,
               "collected_at": r["collected_at"], "license": "CC BY 4.0", "url_repair": action}
        if r["label"] not in {"phishing", "benign"} or r["split"] not in {"train", "val", "test"}:
            raise ValueError("Unknown PhishVN label/split")
        issue = ("invalid_url" if not url else "lower_confidence_positive_or_bronze" if not url_primary_eligible(r) else
                 "human_audit_holdout_domain" if group in audit_domains else "sms_domain_exclusion" if group in sms_domains else "")
        if issue:
            url_quarantine.append(dict(row, issue=issue))
        else:
            urls.append(row)
    labels = defaultdict(set)
    roles = defaultdict(set)
    for r in urls:
        labels[r["url"].rstrip("/")].add(r["label"])
        roles[r["group"]].add(r["provider_split"])
    filtered, seen = [], set()
    for r in urls:
        key = r["url"].rstrip("/")
        issue = "conflicting_url_labels" if len(labels[key]) > 1 else "provider_group_cross_split" if len(roles[r["group"]]) > 1 else "duplicate_url" if key in seen else ""
        if issue:
            url_quarantine.append(dict(r, issue=issue))
        else:
            filtered.append(r)
            seen.add(key)
    native_train = [r for r in filtered if r["provider_split"] == "train"]
    fit_i, val_i = grouped_split(native_train)
    url_splits = {"train": [native_train[i] for i in fit_i],
                  "validation": [native_train[i] for i in val_i] + [r for r in filtered if r["provider_split"] == "val"],
                  "test": [r for r in filtered if r["provider_split"] == "test"]}
    for role, values in url_splits.items():
        for row in values:
            row["partition"], row["do_not_train"] = role, role != "train"
        write_rows(OUT, "url_" + role, values)
    write_rows(OUT, "url_quarantine", url_quarantine)
    for family in [splits, url_splits]:
        for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
            assert not {r["group"] for r in family[a]} & {r["group"] for r in family[b]}
    manifest = {"date": "2026-10-25", "sources": {"sms": {"doi": "10.17632/f45bkkt8pr.1", "sha256": PINS["Dataset_5971.zip"]},
                "url": {"doi": "10.17632/b97hxbxtpd.4", "sha256": PINS["PhishVN_v3.1.0_open.zip"]},
                "MIMICS-3500": {"used": False, "records": 0, "status": "no_verified_public_dataset_file_found",
                                "paper_repository": "https://hdl.handle.net/10612/27150", "paper_embargo_until": "2028-12-31"}},
                "sms_splits": {k: dict(Counter(str(r["label"]) for r in v)) for k, v in splits.items()},
                "url_splits": {k: dict(Counter(str(r["label"]) for r in v)) for k, v in url_splits.items()},
                "sms_semantic_reviewed": len(notes), "sms_quarantine_issues": dict(Counter(r["issue"] for r in quarantine)),
                "url_quarantine_issues": dict(Counter(r["issue"] for r in url_quarantine)),
                "human_url_strict_test": sum(r["strict_human_test_eligible"] for r in audit), "audit_reserved_all": len(audit),
                "confidence_policy": "Positive URLs: gold only; benign URLs: gold/silver. Bronze/pending positives quarantined. No scenario tokens used as labels/features.",
                "url_features": "Recomputed lexical URL features only; force http scheme to remove HTTPS collection shortcut; no label/source/tier/status/scenario/split/is_https inputs.",
                "human_audit_commit": AUDIT_COMMIT, "public_suffix_sha256": PINS["public_suffix_list.dat"]}
    write_json(OUT / "preparation_report.json", manifest)
    check_snapshot()
    print(json.dumps(manifest), flush=True)
