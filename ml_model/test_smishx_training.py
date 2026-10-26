"""SmishX labels must not override project scope or protected partitions."""
import json
from pathlib import Path
import tempfile
import unittest

from smishx_training import screen_source, merge_exact_rows, group_status, export_rows


class SmishxTrainingTests(unittest.TestCase):
    def test_language_and_scope_exclusions_preserve_human_source_label(self):
        notes = {"other_or_mixed_language_ids": [2], "language_unresolved_fragment_ids": [3],
                 "scope_unresolved_or_conflicting_ids": [4]}
        source = {"SMS": "Source text", "label": "smishing", "if_URL": "0", "if_phone": "0", "if_email": "0"}
        self.assertEqual(screen_source(source, 1, notes)["label"], 1)
        for number in (2, 3, 4):
            row = screen_source(source, number, notes)
            self.assertIsNone(row["label"])
            self.assertEqual(row["original_label"], "smishing")
            self.assertTrue(row["human_verified_by_source"])
            self.assertFalse(row["expert_verified"])
            self.assertTrue(row["issue"])

    def test_duplicate_disagreement_is_quarantined_not_promoted(self):
        old = {"case_id": "old", "label": 0, "source": "old", "human_verified_by_source": False}
        human = {"case_id": "human", "label": 1, "source": "smishx", "human_verified_by_source": True}
        self.assertIsNone(merge_exact_rows([old, human]))
        agreeing = dict(old, label=1)
        merged = merge_exact_rows([agreeing, human])
        self.assertEqual(merged["case_id"], "human")
        self.assertEqual(set(merged["merged_case_ids"]), {"old", "human"})

    def test_protected_bridge_wins_and_previously_fitted_groups_are_train_only(self):
        human = {"anchor": "smishx", "blocked_domain": False}
        fitted = {"anchor": "previous_train", "blocked_domain": False}
        holdout = {"anchor": "protected", "blocked_domain": False}
        self.assertEqual(group_status([human]), "novel")
        self.assertEqual(group_status([human, fitted]), "train")
        self.assertEqual(group_status([human, fitted, holdout]), "blocked")
        self.assertEqual(group_status([dict(human, blocked_domain=True)]), "blocked")

    def test_unicode_line_separators_roundtrip_with_existing_jsonl_loader(self):
        row = {"raw_text": "Hello\u2028there\u0085friend\u2029!", "label": 0}
        test_root = Path(__file__).resolve().parent / "data/prepared"
        test_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(test_root.resolve()))
            export_rows(Path(directory), "sample", [row])
            lines = (Path(directory) / "sample.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), row)


if __name__ == "__main__":
    unittest.main()
