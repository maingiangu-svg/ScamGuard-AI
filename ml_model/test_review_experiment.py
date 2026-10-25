"""Experimental training must never consume the reserved external test."""
import unittest
import numpy as np

from run_review_experiment import experimental_training_rows, metric_summary, choose_human_sample


class ReviewExperimentTests(unittest.TestCase):
    def test_ai_training_requires_opt_in_and_rejects_external_test_even_with_opt_in(self):
        row = {"case_id": "T1", "source_split": "provider_train", "raw_text": "hello",
               "ai_proposed_label": 0, "label_provenance": "ai_semantic_review"}
        with self.assertRaisesRegex(ValueError, "opt-in"):
            experimental_training_rows([row], False)
        self.assertEqual(experimental_training_rows([row], True)[0]["candidate_label"], 0)
        bad = dict(row, source_split="provider_test")
        with self.assertRaisesRegex(ValueError, "reserved"):
            experimental_training_rows([bad], True)
        for extra in [{"partition": "test"}, {"partition": "validation"}, {"do_not_train": True}]:
            with self.assertRaisesRegex(ValueError, "reserved"):
                experimental_training_rows([dict(row, **extra)], True)
        unresolved = dict(row, ai_proposed_label=None)
        self.assertEqual(experimental_training_rows([unresolved], True), [])

    def test_human_sample_covers_both_classes_and_does_not_expose_proposed_labels(self):
        rows = [{"case_id": f"V{i}", "raw_text": str(i), "resolved_review_label": i % 2,
                 "similarity_group": f"G{i}", "ai_category": f"C{i % 3}"} for i in range(40)]
        sample = choose_human_sample(rows, 6)
        self.assertEqual(len(sample), 12)
        ids = {r["case_id"] for r in sample}
        self.assertEqual({r["resolved_review_label"] for r in rows if r["case_id"] in ids}, {0, 1})
        self.assertTrue(all(r["human_label"] is None and "resolved_review_label" not in r
                            and "ai_category" not in r for r in sample))

    def test_false_alarms_and_missed_attacks_are_reported_separately(self):
        result = metric_summary(np.array([0, 0, 1, 1]), np.array([.1, .8, .2, .9]))
        self.assertEqual(result["confusion"], {"tn": 1, "fp": 1, "fn": 1, "tp": 1})
        self.assertEqual(result["recall"], .5)
        self.assertEqual(result["policy"]["missed_low_risk"], 1)
        self.assertEqual(result["policy"]["benign_high_risk"], 1)


if __name__ == "__main__":
    unittest.main()
