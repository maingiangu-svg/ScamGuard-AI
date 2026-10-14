"""Run with: .venv/Scripts/python -m unittest discover -s ml_model -v"""

import runpy
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.ensemble import GradientBoostingClassifier

ROOT = Path(__file__).resolve().parent


def load_training():
    with patch("subprocess.check_call"):
        return runpy.run_path(str(ROOT / "train.py"))


class TrainingTests(unittest.TestCase):
    def test_installed_dependencies_are_not_reinstalled(self):
        with patch("subprocess.check_call", side_effect=AssertionError("Unexpected pip install")):
            runpy.run_path(str(ROOT / "train.py"))

    def test_url_features_match_prediction(self):
        training = load_training()
        prediction = runpy.run_path(str(ROOT / "predict.py"))
        for url in ("google.com", "https://www.google.com/", "http://bank-login.vip/verify"):
            with self.subTest(url=url):
                np.testing.assert_allclose(
                    training["extract_url_features"](url),
                    prediction["extract_url_features"](url),
                )

    def test_url_training_preserves_gradient_boosting_with_sparse_input(self):
        training = load_training()
        urls = [f"https://safe{i}.org/help" for i in range(10)]
        urls += [f"http://bank-login{i}.vip/verify" for i in range(10)]
        data = pd.DataFrame({"url": urls, "label": ["good"] * 10 + ["bad"] * 10})
        with ExitStack() as stack:
            for matrix_type in (sp.coo_array, sp.coo_matrix, sp.csr_array, sp.csr_matrix):
                original = matrix_type.toarray

                def guard(matrix, *args, _original=original, **kwargs):
                    if matrix.shape[1] > 13:
                        raise AssertionError("Dense feature matrix allocation")
                    return _original(matrix, *args, **kwargs)

                stack.enter_context(patch.object(matrix_type, "toarray", autospec=True, side_effect=guard))
            vectorizer, classifier, metrics = training["train_url_model"](data)
        self.assertIsInstance(classifier, GradientBoostingClassifier)
        features = sp.hstack([
            sp.csr_matrix(training["build_url_feature_matrix"](urls)),
            vectorizer.transform(urls),
        ])
        np.testing.assert_array_equal(classifier.predict(features), [0] * 10 + [1] * 10)
        self.assertEqual(metrics["url_samples"], 20)
        self.assertTrue(all(np.isfinite(metrics[key]) for key in ("url_accuracy", "url_f1", "url_auc")))


if __name__ == "__main__":
    unittest.main()
