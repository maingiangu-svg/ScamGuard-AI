"""The live adapter must use the fitted processed-model contract exactly."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

import predict_processed as live
from round2_experiment import text_input


class RecordingEstimator:
    def __init__(self, score):
        self.score, self.rows = score, []

    def predict_proba(self, rows):
        self.rows = list(rows)
        return np.array([[1 - self.score, self.score] for _ in rows])


def bundle(text_score=.7, url_score=.95):
    return {"sms": {"model": RecordingEstimator(text_score), "threshold": .65},
            "url": {"model": RecordingEstimator(url_score), "threshold": .22}}


class ProcessedPredictionTests(unittest.TestCase):
    def test_sms_keeps_urls_and_uses_its_own_threshold_without_rescaling(self):
        models = bundle()
        text = "Your account: [https://Bank.Example/login] code 123456"
        with patch.object(live, "load_processed_bundle", return_value=models):
            result = live.classify(text=text)
        self.assertTrue(result["model_ready"])
        self.assertEqual(models["sms"]["model"].rows, [text_input(text)])
        self.assertEqual(result["ml_risk_score"], 70)
        self.assertEqual(result["model_prediction_label"], 1)
        self.assertEqual(result["decision_threshold"], .65)
        self.assertEqual(result["decision_branch"], "sms")
        self.assertEqual(result["mode"], "processed_text")
        self.assertEqual(result["url_result"]["score"], .95)
        self.assertIsNone(result["meta_formula"])

    def test_url_only_uses_http_collapsing_and_url_threshold(self):
        models = bundle(url_score=.25)
        with patch.object(live, "load_processed_bundle", return_value=models):
            result = live.classify(text="https://Bank.Example/login")
        self.assertEqual(models["url"]["model"].rows, ["http://bank.example/login"])
        self.assertIsNone(result["text_result"])
        self.assertEqual(result["model_prediction_label"], 1)
        self.assertEqual(result["decision_threshold"], .22)
        self.assertEqual(result["mode"], "processed_url_only")

    def test_failed_new_model_does_not_fall_back_or_produce_a_safe_verdict(self):
        with patch.object(live, "load_processed_bundle", side_effect=ValueError("bad checksum")):
            result = live.classify(text="hello")
        self.assertFalse(result["model_ready"])
        self.assertIsNone(result["ml_risk_score"])
        self.assertNotIn("model_prediction_label", result)
        self.assertNotIn("bad checksum", json.dumps(result))

    def test_all_urls_are_reported_but_do_not_replace_the_sms_score(self):
        with patch.object(live, "load_processed_bundle", return_value=bundle(text_score=.1)):
            result = live.classify(text="Read https://one.example/ and https://two.example/")
        self.assertEqual(result["ml_risk_score"], 10)
        self.assertEqual(result["model_prediction_label"], 0)
        self.assertEqual(len(result["url_result"]["urls"]), 2)

    def test_corrupt_artifact_is_rejected_before_pickle_loading(self):
        root = Path(__file__).resolve().parent / "data/prepared"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(root))
            target = Path(directory) / "invalid.pkl"
            target.write_bytes(b"not a trusted model")
            with patch.dict(live.os.environ, {"SCAMGUARD_MODEL_PATH": str(target)}):
                with patch.object(live.pickle, "loads") as unpickle:
                    with self.assertRaisesRegex(ValueError, "checksum"):
                        live.load_processed_bundle()
                    unpickle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
