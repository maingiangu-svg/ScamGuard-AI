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
    def test_source_calibrated_estimate_is_separate_from_raw_alert_score(self):
        models = bundle('hello', .1)
        models['sms']['probability_model'] = Estimator({text_input('hello'): .2})
        with patch.object(live, 'load_bundle', return_value=models):
            result = live.classify(text='hello')
        self.assertEqual(result['ml_risk_score'], 10)
        self.assertEqual(result['model_prediction_label'], 0)
        self.assertAlmostEqual(result['calibrated_probability'], .2)
        self.assertEqual(result['calibration_status'], 'source_label_calibrated')
        self.assertFalse(result['calibrated_probability_expert_verified'])

    def test_uncalibrated_artifact_never_invents_a_calibrated_estimate(self):
        with patch.object(live, 'load_bundle', return_value=bundle('hello', .1)):
            result = live.classify(text='hello')
        self.assertIsNone(result['calibrated_probability'])
        self.assertEqual(result['calibration_status'], 'unavailable')

    def test_incomplete_url_only_input_is_invalid_before_either_model_runs(self):
        for raw in ["https://", "http://", " HTTPS:// \n", "https:", "https:/",
                    "https://?query=1", "https://.", "www.", "(https://)"]:
            for field in ["text", "url"]:
                with self.subTest(raw=raw, field=field), patch.object(live, "load_bundle", return_value=bundle(raw, 1.0)) as loader:
                    result = live.classify(**{field: raw})
                    self.assertEqual(result.get("error"), "INVALID_URL")
                    self.assertIsNone(result["ml_risk_score"])
                    self.assertNotIn("decision_branch", result)
                    loader.assert_not_called()

    def test_actual_message_mentioning_an_incomplete_url_remains_sms_input(self):
        text = "The link starts with https:// but I did not copy the rest"
        models = bundle(text, .1)
        with patch.object(live, "load_bundle", return_value=models):
            result = live.classify(text=text)
        self.assertEqual(result["decision_branch"], "sms")
        self.assertEqual(result["ml_risk_score"], 10)

    def test_url_only_routing_ignores_whitespace_wrappers_and_multiple_links(self):
        url = "https://uccle.monopinion.belgium.be/profiles/sunwinorgvc/badges"
        other = "https://example.com/"
        for text in [url, " " + url, "\n\t" + url + " \r\n", "(" + url + ")",
                     "[" + url + "]", url + " \n " + other]:
            models = bundle(text, .89, {url: .6969195741583459, other: .1})
            with self.subTest(text=text), patch.object(live, "load_bundle", return_value=models):
                result = live.classify(text=text)
            self.assertEqual(result["mode"], "hybrid_url_only")
            self.assertEqual(result["decision_branch"], "url")
            self.assertIsNone(result["text_result"])
            self.assertEqual(models["sms"]["model"].rows, [])
            self.assertEqual(result["ml_risk_score"], 70)
            self.assertFalse(result["url_review_required"])

    def test_schemeless_domains_are_extracted_in_full_including_unlisted_tlds(self):
        for raw in ["sunwin.org.vc", "sub.example.com.au/Case?next=1", "example.dev",
                    "example.xn--p1ai"]:
            url = "http://" + raw
            models = bundle(urls={url: .8770976968115821})
            with self.subTest(raw=raw), patch.object(live, "load_bundle", return_value=models):
                result = live.classify(text=" " + raw + " ")
            self.assertEqual(models["url"]["model"].rows, [url])
            self.assertEqual(result["extracted_url"], url)
            self.assertEqual(result["decision_branch"], "url")
            self.assertIsNone(result["text_result"])
            self.assertEqual(result["ml_risk_score"], 88)

    def test_real_text_around_complete_bare_domains_still_uses_sms_and_url_heads(self):
        text = "Kiểm tra sunwin.org.vc, rồi gọi lại."
        url = "http://sunwin.org.vc"
        models = bundle(text, .1, {url: .88})
        with patch.object(live, "load_bundle", return_value=models):
            result = live.classify(text=text)
        self.assertEqual(models["sms"]["model"].rows, [text_input(text)])
        self.assertEqual(models["url"]["model"].rows, [url])
        self.assertEqual(result["decision_branch"], "sms")
        self.assertEqual(result["ml_risk_score"], 10)
        self.assertTrue(result["url_review_required"])

    def test_email_addresses_and_decimal_numbers_are_not_extracted_as_urls(self):
        for text in ["Email name@sunwin.org.vc", "Version 1.23.45"]:
            with self.subTest(text=text), patch.object(live, "load_bundle", return_value=bundle(text)):
                result = live.classify(text=text)
            self.assertEqual(result["decision_branch"], "sms")
            self.assertIsNone(result["url_result"])

    def test_url_only_alerts_use_the_raw_url_threshold_not_the_sms_review_band(self):
        url = "https://www.facebook.com/"
        for raw, expected_label, expected_action in [
            (.06, 0, "CLEAR"), (.347895, 0, "CLEAR"), (.4999, 0, "CLEAR"),
            (.5, 1, "REVIEW"), (.79, 1, "REVIEW"), (.9, 1, "BLOCK"),
        ]:
            with self.subTest(raw=raw), patch.object(live, "load_bundle", return_value=bundle(urls={url: raw})):
                result = live.classify(url=url)
            self.assertEqual(result["model_prediction_label"], expected_label)
            self.assertEqual(result["action"], expected_action)
            self.assertEqual(result["ml_risk_score"], round(raw * 100))
            self.assertEqual(result["url_result"]["score"], raw)

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
        import hashlib

        text = "Hey, are you free for lunch tomorrow?"
        url = "https://qi.lv/F0i"
        with tempfile.TemporaryDirectory(dir=live.ROOT / 'models') as directory:
            output = Path(directory) / 'historical.pkl'
            sms_source = Path(directory) / 'source-sms.pkl'
            sms_fixture = {'sklearn_version': live.sklearn.__version__,
                           'sms': {'model': Estimator({text_input(text): .23}), 'threshold': .65}}
            sms_source.write_bytes(pickle.dumps(sms_fixture))
            checksum = hashlib.sha256(sms_source.read_bytes()).hexdigest()
            with patch.object(package_hybrid, 'OUTPUT', output), \
                 patch.object(package_hybrid, 'SMS_SOURCE', sms_source), \
                 patch.object(package_hybrid, 'EXPECTED_SHA256', checksum), \
                 patch.object(package_hybrid, 'load_processed_bundle', return_value=sms_fixture) as sms_loader, \
                 patch('predict_processed.load_processed_bundle', return_value=sms_fixture):
                package_hybrid.package()
                expected_sms = processed_classify(text=text)['text_result']['score']
                sms_source.write_bytes(b'corrupted source')
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    package_hybrid.package()
                self.assertEqual(sms_loader.call_count, 1)
            models = pickle.loads(output.read_bytes())
        self.assertEqual(float(probability(models['sms']['model'], [text_input(text)])[0]),
                         expected_sms)
        self.assertEqual(float(probability(models['url']['model'], [url])[0]),
                         bundle_classify(url=url)["url_result"]["score"])

    def test_active_repaired_weights_are_bound_to_training_manifests(self):
        manifest = json.loads(live.MANIFEST.read_text(encoding='utf-8'))
        models = live.load_bundle()
        self.assertEqual(models['training'], manifest['training'])
        self.assertEqual(models['training']['run_id'], 'sms-confirmation-english-20261029')
        self.assertEqual(models['training']['text_training_samples'], 4186)
        self.assertEqual(models['training']['url_training_samples'], 74309)
        self.assertTrue(manifest['calibration_gate_pass'])
        self.assertEqual(manifest['parent_artifact']['bundle_sha256'],
                         '26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008')
        parent = manifest['parent_artifact']
        self.assertEqual(parent['training']['run_id'], 'url-ensemble-20261027')
        self.assertEqual(parent['training']['text_training_samples'], 3786)
        self.assertEqual(parent['training']['url_training_samples'], 74309)
        self.assertEqual(parent['parent_artifact']['bundle_sha256'],
                         '6a0fd38b35570bff4b0ae56dd52a07747a6670d3dc2eceda304e1f10898314d0')
        grandparent = parent['parent_artifact']
        self.assertEqual(grandparent['training']['run_id'], 'group-calibrated-20261026')
        self.assertEqual(grandparent['training']['url_training_samples'], 31299)
        self.assertEqual(grandparent['parent_artifact']['bundle_sha256'],
                         '9a49b7278cfb1b9da00f8ebc6970653a9de3320f3037db3ee190109926d1bd3a')
        for gate in ['release_approved', 'historical_nonregression_pass',
                     'all_policy_nonregression_pass', 'full_application_nonregression_pass']:
            self.assertIs(manifest[gate], True)
        self.assertEqual(models['training']['confirmation_loss_rows'], 3848)
        self.assertEqual(models['training']['language_gate_threshold'], .99)
        self.assertIn('conservative_sms.py', manifest['code_sha256'])
        self.assertEqual(models['url']['model_id'], parent['head_model_ids']['url'])
        self.assertEqual(models['sms']['model_id'], manifest['head_model_ids']['sms'])
        self.assertTrue(models['training']['calibrated_estimate_available'])
        self.assertFalse(models['training']['probability_calibrated'])
        self.assertEqual(models['training']['heldout_or_quarantined_rows_fitted'], 0)
        self.assertTrue(models['training']['registered_domain_isolation'])
        self.assertTrue(models['training']['icann_owner_domain_isolation'])
        self.assertFalse(models['training']['campaign_independence_proven'])
        self.assertFalse(models['training']['all_labels_expert_verified'])
        self.assertIn('sms_fit_rows.jsonl', manifest['dataset_files_sha256'])
        self.assertEqual(manifest['source_sha256']['sms_train'],
                         manifest['dataset_files_sha256']['sms_fit_rows.jsonl'])
        # The URL estimator is inherited with its complete prior fitting proof.
        self.assertIn('url_fit_rows.jsonl', parent['dataset_files_sha256'])
        self.assertEqual(manifest['source_sha256']['url_train'], parent['source_sha256']['url_train'])
        self.assertEqual(manifest['source_sha256']['url_train'],
                         parent['dataset_files_sha256']['url_fit_rows.jsonl'])

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
