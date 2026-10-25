"""External sources must keep their label scope and independent holdouts."""
import unittest

from external_training import RegisteredDomains, sms_project_label, url_primary_eligible, merge_human_audit, url_input
from external_experiment import require_training_partition


class ExternalTrainingTests(unittest.TestCase):
    def test_url_transport_is_removed_without_removing_impersonation_features(self):
        self.assertEqual(url_input("https://Bank.Example/login?otp=1"), "http://bank.example/login?otp=1")
        self.assertEqual(url_input("https://bank.example:443/login"), url_input("http://bank.example:80/login"))
        self.assertNotEqual(url_input("https://bank.example/login"), url_input("https://bank.example.evil.test/login"))
        with self.assertRaises(ValueError):
            url_input("javascript:alert(1)")

    def test_held_out_rows_cannot_enter_training(self):
        require_training_partition([{"partition": "train", "do_not_train": False, "label": 1}])
        for row in ({"partition": "test", "do_not_train": True, "label": 1},
                    {"partition": "validation", "do_not_train": False, "label": 0},
                    {"partition": "train", "do_not_train": False, "label": None}):
            with self.assertRaises(ValueError):
                require_training_partition([row])

    def test_registrable_domain_uses_psl_wildcards_exceptions_and_vietnam_suffixes(self):
        domains = RegisteredDomains("com\nuk\nco.uk\nvn\ncom.vn\n*.ck\n!www.ck\n")
        self.assertEqual(domains("login.shop.example.com.vn"), "example.com.vn")
        self.assertEqual(domains("a.example.co.uk"), "example.co.uk")
        self.assertEqual(domains("a.b.ck"), "a.b.ck")
        self.assertEqual(domains("a.www.ck"), "www.ck")
        self.assertEqual(domains("192.0.2.1"), "192.0.2.1")

    def test_source_smishing_is_not_promoted_without_scope_review(self):
        self.assertEqual(sms_project_label("ham", None), 0)
        self.assertEqual(sms_project_label("Spam", None), 0)
        self.assertIsNone(sms_project_label("Smishing", None))
        self.assertEqual(sms_project_label("Smishing", {"label": 0}), 0)
        self.assertEqual(sms_project_label("Smishing", {"label": 1}), 1)
        self.assertIsNone(sms_project_label("spam", {"label": None}))
        with self.assertRaises(ValueError):
            sms_project_label("missing", None)

    def test_pending_and_community_positive_urls_are_not_primary_training(self):
        self.assertTrue(url_primary_eligible({"label": "phishing", "tier": "gold"}))
        self.assertFalse(url_primary_eligible({"label": "phishing", "tier": "silver"}))
        self.assertFalse(url_primary_eligible({"label": "phishing", "tier": "bronze"}))
        self.assertTrue(url_primary_eligible({"label": "benign", "tier": "silver"}))

    def test_disagreements_require_arbitration_and_name_only_is_not_strict_evidence(self):
        a = [{"vid": "A", "url": "a.com", "verdict": "phishing", "evidence": "name"},
             {"vid": "B", "url": "b.com", "verdict": "legitimate", "evidence": "archive"}]
        b = [dict(a[0]), dict(a[1], verdict="phishing", evidence="urlscan")]
        with self.assertRaises(ValueError):
            merge_human_audit(a, b, [])
        with self.assertRaises(ValueError):
            merge_human_audit(a + [a[0]], a, [])
        with self.assertRaises(ValueError):
            merge_human_audit(a, a, [{"vid": "unknown"}])
        result = merge_human_audit(a, b, [{"vid": "B", "url": "b.com", "final_verdict": "legitimate",
                                         "final_evidence": "archive", "rationale": "own operator"}])
        self.assertFalse(result[0]["strict_human_test_eligible"])
        self.assertTrue(result[1]["strict_human_test_eligible"])
        self.assertEqual(result[1]["label"], 0)
        self.assertFalse(result[1]["expert_verified"])


if __name__ == "__main__":
    unittest.main()
