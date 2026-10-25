"""Holdout preparation must preserve uncertainty and isolate connected templates."""
import unittest
import csv
import json
import tempfile
from pathlib import Path

from audit_vi_holdout import audit_partitions, similarity_edges, template_signature, write_rows, audit_hostnames


def sample(case, label):
    return {"case_id": case, "raw_text": "original", "resolved_review_label": label,
            "original_source_label": "1", "expert_verified": False,
            "gold_smishing_label": None, "do_not_train": True}


class HoldoutAuditTests(unittest.TestCase):
    def test_bracket_wrapped_urls_share_template_and_host_with_unwrapped_urls(self):
        left = "Cap nhat dia chi: [http://ghtk.capnhat-diachi.top]"
        right = "Cap nhat dia chi: http://ghtk.capnhat-diachi.top"
        self.assertEqual(template_signature(left), template_signature(right))
        self.assertEqual(audit_hostnames(left), {"ghtk.capnhat-diachi.top"})
        self.assertEqual(audit_hostnames("Xem [https://example.com/a?x=1]."), {"example.com"})

    def test_export_preserves_provenance_columns_from_different_sources(self):
        rows = [{"case_id": "A", "provider_record": 1},
                {"case_id": "B", "human_evidence": "confirmed", "expert_verified": False}]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / "data") as folder:
            root = Path(folder)
            write_rows(root, "mixed", rows)
            with (root / "mixed.csv").open(encoding="utf-8-sig", newline="") as f:
                saved = list(csv.DictReader(f))
            self.assertEqual(saved[1]["human_evidence"], "confirmed")
            self.assertEqual(saved[0]["provider_record"], "1")
            self.assertEqual([json.loads(s) for s in (root / "mixed.jsonl").read_text(encoding="utf-8").splitlines()], rows)

    def test_template_changes_do_not_hide_similar_messages(self):
        left = "Mã OTP là 123456, ngày 21/10/2026. Xem https://a.example.com/path"
        right = "Ma OTP la [NUMBER], ngay [DATE]. Xem https://b.example.com/other"
        self.assertEqual(template_signature(left), template_signature(right))
        self.assertNotEqual(template_signature("Không cung cấp mã cho người khác"),
                            template_signature("Cung cấp mã cho người khác"))

    def test_near_matching_detects_small_edits_without_matching_unrelated_text(self):
        text = "Quy khach da dang ky thanh cong dich vu thong bao cuoc goi nho cua nha mang"
        hits = list(similarity_edges([text], [text.replace("thanh cong", "thanh congg"),
                                              "Hen gap nhau o cong vien vao toi thu bay"], .90))
        self.assertEqual([(i, j) for i, j, _ in hits], [(0, 0)])
        self.assertGreaterEqual(hits[0][2], .90)

    def test_group_overlap_and_label_conflicts_propagate_without_changing_labels(self):
        rows = [sample("A", 0), sample("B", 0), sample("C", 0),
                sample("D", None), sample("E", 1), sample("F", 0)]
        edges = [(0, 1), (1, 2), (3, 4)]
        output = audit_partitions(rows, edges, {0})
        self.assertEqual({r["holdout_disposition"] for r in output[:3]}, {"blocked_reference_overlap"})
        self.assertEqual(output[3]["holdout_disposition"], "quarantine_unresolved_label")
        self.assertEqual(output[4]["holdout_disposition"], "blocked_unresolved_group")
        self.assertEqual(output[5]["holdout_disposition"], "reserved_holdout_pending_validation")
        self.assertEqual(rows[3]["resolved_review_label"], None)
        self.assertEqual(output[3]["original_source_label"], "1")
        self.assertEqual(output[0]["similarity_group"], output[2]["similarity_group"])
        self.assertNotEqual(output[0]["similarity_group"], output[5]["similarity_group"])
        mixed = audit_partitions([sample("G", 0), sample("H", 1)], [(0, 1)], set())
        self.assertTrue(all(r["holdout_disposition"] == "blocked_group_label_conflict" for r in mixed))
        self.assertEqual([r["resolved_review_label"] for r in mixed], [0, 1])
        self.assertTrue(all(r["do_not_train"] and not r["eligible_for_verified_evaluation"] for r in mixed))

    def test_invalid_labels_are_rejected_instead_of_defaulted_to_zero(self):
        with self.assertRaises(ValueError):
            audit_partitions([sample("bad", "")], [], set())
        with self.assertRaises(ValueError):
            audit_partitions([sample("repeat", 0), sample("repeat", 1)], [], set())


if __name__ == "__main__":
    unittest.main()
