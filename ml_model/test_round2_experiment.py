"""The new validation/test must stay separate from training and model selection."""
import unittest
import numpy as np

from round2_experiment import partition_eligibility, choose_threshold, training_model
from audit_vi_holdout import audit_hostnames


class RoundTwoTests(unittest.TestCase):
    def test_cross_partition_group_never_moves_seen_training_into_test(self):
        rows = [{"case_id": "A", "partition": "train", "group": "g", "previous_train": False},
                {"case_id": "B", "partition": "validation", "group": "g", "previous_train": False},
                {"case_id": "C", "partition": "test", "group": "g", "previous_train": False}]
        answer = partition_eligibility(rows)
        self.assertEqual([r["split_eligible"] for r in answer], [False, False, True])
        rows[0]["previous_train"] = True
        answer = partition_eligibility(rows)
        self.assertEqual([r["split_eligible"] for r in answer], [True, False, False])

    def test_bracketed_domain_overlap_is_visible_before_splitting(self):
        self.assertTrue(audit_hostnames("Xem [http://a.example.com]") &
                        audit_hostnames("Tra cuu http://a.example.com"))

    def test_threshold_obeys_validation_false_alarm_limit(self):
        y = np.array([0] * 10 + [1] * 3)
        scores = np.array([.1] * 9 + [.6, .5, .7, .9])
        result = choose_threshold(y, scores)
        self.assertLessEqual(result["false_positive_rate"], .1)
        self.assertGreater(result["recall"], 0)
        self.assertIn("threshold", result)

    def test_candidate_features_keep_real_url_information_and_vietnamese(self):
        model = training_model("word_char")
        x = ["Thông báo hợp lệ https://safe.example.vn"] * 6 + ["Đăng nhập giả https://evil.fake.top"] * 6
        model.fit(x, [0] * 6 + [1] * 6)
        self.assertLess(model.predict_proba([x[0]])[0, 1], model.predict_proba([x[-1]])[0, 1])
        names = model.named_steps["features"].get_feature_names_out()
        self.assertTrue(any("fake" in n for n in names))


if __name__ == "__main__":
    unittest.main()
