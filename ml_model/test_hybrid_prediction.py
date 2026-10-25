"""Routing must preserve the selected supervised heads and independent review."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import predict_hybrid as live
from round2_experiment import text_input


class Estimator:
    def __init__(self, scores):
        self.scores, self.rows = scores, []

    def predict_proba(self, rows):
        self.rows = list(rows)
        return np.array([[1 - self.scores.get(row, .1), self.scores.get(row, .1)] for row in rows])


def bundle(text="hello", sms_score=.1, urls=None):
    return {"sms": {"model": Estimator({text_input(text): sms_score}), "threshold": .65,
                    "model_id": "processed-20261025:sms"},
            "url": {"model": Estimator(urls or {}), "threshold": .5,
                    "model_id": "20261025T152344Z:url"},
            "training": {"run_id": "hybrid-20261025", "paired_training_samples": 0}}


class HybridPredictionTests(unittest.TestCase):
    def test_sms_keeps_the_processed_preprocessing_and_score(self):
        text = "Mã 123456: [https://Bank.Example/Login]"
        models = bundle(text, .7)
        with patch.object(live, "load_bundle", return_value=models):
            result = live.classify(text=text)
        self.assertEqual(models["sms"]["model"].rows, [text_input(text)])
        self.assertEqual(result["ml_risk_score"], 70)
        self.assertEqual(result["model_prediction_label"], 1)
        self.assertEqual(result["decision_threshold"], .65)
        self.assertEqual(result["decision_branch"], "sms")
        self.assertIsNone(result["meta_formula"])

    def test_url_only_preserves_https_path_case_and_uses_the_bundle_head(self):
        url = "https://bank.example/F0i"
        models = bundle(urls={url: .891488})
        with patch.object(live, "load_bundle", return_value=models):
            result = live.classify(text=url)
        self.assertEqual(models["sms"]["model"].rows, [])
        self.assertEqual(models["url"]["model"].rows, [url])
        self.assertIsNone(result["text_result"])
        self.assertEqual(result["ml_risk_score"], 89)
        self.assertEqual(result["decision_threshold"], .5)
        self.assertEqual(result["decision_branch"], "url")

    def test_risky_url_requires_review_without_inflating_sms_or_using_old_fusion(self):
        url = "https://bank.example/F0i"
        text = "Hello " + url
        with patch.object(live, "load_bundle", return_value=bundle(text, .1, {url: .89})):
            result = live.classify(text=text)
        self.assertEqual(result["ml_risk_score"], 10)
        self.assertEqual(result["model_prediction_label"], 0)
        self.assertEqual(result["url_result"]["score"], .89)
        self.assertTrue(result["url_review_required"])
        self.assertEqual(result["action"], "REVIEW")
        self.assertEqual(result["ml_label"], "SUSPICIOUS")
        self.assertIsNone(result["meta_formula"])

    def test_url_review_uses_unrounded_half_threshold_without_hiding_sms_risk(self):
        url = "https://example.com/"
        text = "Hello " + url
        for score, review in [(.4999, False), (.5, True)]:
            with self.subTest(score=score), patch.object(live, "load_bundle", return_value=bundle(text, .1, {url: score})):
                result = live.classify(text=text)
            self.assertEqual(result["url_review_required"], review)
        with patch.object(live, "load_bundle", return_value=bundle(text, .95, {url: .1})):
            result = live.classify(text=text)
        self.assertEqual(result["action"], "BLOCK")
        self.assertEqual(result["ml_risk_score"], 95)

    def test_all_explicit_and_embedded_urls_are_scored_with_max_url_only(self):
        urls = {"https://one.example/": .1, "https://two.example/F0i": .9}
        models = bundle(urls=urls)
        with patch.object(live, "load_bundle", return_value=models):
            result = live.classify(text="https://one.example/", url="https://two.example/F0i")
        self.assertEqual(len(result["url_result"]["urls"]), 2)
        self.assertEqual(result["ml_risk_score"], 90)
        self.assertEqual(result["extracted_url"], "https://two.example/F0i")

    def test_missing_or_invalid_bundle_never_falls_back(self):
        with patch.object(live, "load_bundle", side_effect=ValueError("internal path")):
            result = live.classify(text="hello")
        self.assertFalse(result["model_ready"])
        self.assertIsNone(result["ml_risk_score"])
        self.assertNotIn("internal path", json.dumps(result))

    def test_checksum_is_checked_before_unpickling(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / "models") as directory:
            target = Path(directory) / "invalid.pkl"
            target.write_bytes(b"untrusted")
            with patch.dict(live.os.environ, {"SCAMGUARD_MODEL_PATH": str(target)}), patch.object(live.pickle, "loads") as unpickle:
                with self.assertRaisesRegex(ValueError, "checksum"):
                    live.load_bundle()
                unpickle.assert_not_called()

    def test_invalid_and_excessive_inputs_are_unavailable(self):
        for args in [{"text": ""}, {"text": 4}, {"url": "file:///secret"},
                     {"text": "x" * 20001}, {"url": "https://example.com/" + "x" * 4096},
                     {"text": " ".join(f"https://host{i}.example/" for i in range(21))}]:
            with self.subTest(args=str(args)[:80]):
                self.assertFalse(live.classify(**args)["model_ready"])

    def test_historical_packager_preserves_source_scores_without_replacing_active_model(self):
        import pickle
        import package_hybrid
        from predict import probability
        from predict import classify as bundle_classify
        from predict_processed import classify as processed_classify

        text = "Hey, are you free for lunch tomorrow?"
        url = "https://qi.lv/F0i"
        with tempfile.TemporaryDirectory(dir=live.ROOT / 'models') as directory:
            output = Path(directory) / 'historical.pkl'
            with patch.object(package_hybrid, 'OUTPUT', output):
                package_hybrid.package()
            models = pickle.loads(output.read_bytes())
        self.assertEqual(float(probability(models['sms']['model'], [text_input(text)])[0]),
                         processed_classify(text=text)["text_result"]["score"])
        self.assertEqual(float(probability(models['url']['model'], [url])[0]),
                         bundle_classify(url=url)["url_result"]["score"])

    def test_active_repaired_weights_are_bound_to_training_manifests(self):
        manifest = json.loads(live.MANIFEST.read_text(encoding='utf-8'))
        models = live.load_bundle()
        self.assertEqual(models['training'], manifest['training'])
        self.assertEqual(models['training']['run_id'], 'hybrid-isolated-20261026-icann')
        self.assertEqual(models['training']['text_training_samples'], 3800)
        self.assertEqual(models['training']['url_training_samples'], 32777)
        self.assertEqual(models['training']['heldout_or_quarantined_rows_fitted'], 0)
        self.assertTrue(models['training']['registered_domain_isolation'])
        self.assertTrue(models['training']['icann_owner_domain_isolation'])
        self.assertFalse(models['training']['campaign_independence_proven'])
        self.assertFalse(models['training']['all_labels_expert_verified'])
        for branch in ('sms', 'url'):
            self.assertIn(branch + '_train.jsonl', manifest['dataset_files_sha256'])
            self.assertEqual(manifest['source_sha256'][branch + '_train'],
                             manifest['dataset_files_sha256'][branch + '_train.jsonl'])

    def test_historical_packager_cannot_overwrite_the_repaired_default(self):
        import package_hybrid
        with patch.object(package_hybrid, 'load_processed_bundle') as loader:
            with self.assertRaisesRegex(ValueError, 'repaired'):
                package_hybrid.package()
            loader.assert_not_called()

    def test_helper_checksums_allow_checkout_line_endings_but_reject_code_changes(self):
        manifest = json.loads(live.MANIFEST.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / "models") as directory:
            root = Path(directory)
            for name in manifest["code_sha256"]:
                source = (live.ROOT / name).read_bytes().replace(b'\r\n', b'\n')
                (root / name).write_bytes(source.replace(b'\n', b'\r\n'))
            with patch.object(live, "ROOT", root):
                self.assertEqual(live.load_bundle()["training"], manifest['training'])
                (root / "preprocess.py").write_bytes(b"changed code")
                with patch.object(live.pickle, "loads") as unpickle:
                    with self.assertRaisesRegex(ValueError, "preprocessing checksum"):
                        live.load_bundle()
                    unpickle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
