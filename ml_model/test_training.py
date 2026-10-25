"""Regression checks for the production training contract."""
import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from modeling import meta_features, text_model, url_model
from preprocess import clean_messages
from train_meta_fusion import message_groups, holdout_split, clean_urls


class TrainingTests(unittest.TestCase):
    def test_url_training_uses_repairs_and_excludes_new_conflicts_and_sms_hosts(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'data') as directory:
            path = Path(directory) / 'urls.csv'
            pd.DataFrame({'URL': ['hxxp://a[.]com/x', 'http://a.com/x',
                                  'b.org/Log In', 'shared.org/a'],
                          'Label': ['bad', 'good', 'bad', 'good']}).to_csv(path, index=False)
            urls, conflicts = clean_urls(path, {'shared.org'})
        self.assertEqual(conflicts, 1)
        self.assertEqual(urls.url.tolist(), ['http://b.org/Log%20In'])

    def test_linked_domains_and_normalized_text_cannot_cross_split(self):
        frame = pd.DataFrame({
            "raw_text": ["first http://same.com/a", "second http://same.com/b",
                         "repeated http://one.com/a", "repeated http://two.com/b"] +
                        [f"ordinary message {i}" for i in range(30)],
            "label": [1, 0, 1, 0] + [i % 2 for i in range(30)],
        })
        clean, _ = clean_messages(frame)
        groups = message_groups(clean)
        self.assertEqual(groups[0], groups[1])
        self.assertEqual(groups[2], groups[3])
        train, test = holdout_split(clean.label.to_numpy(), groups)
        self.assertFalse(set(groups[train]) & set(groups[test]))

    def test_models_fit_and_predict_using_the_same_transform(self):
        texts = ["normal lunch meeting"] * 10 + ["urgent claim free prize"] * 10
        labels = np.array([0] * 10 + [1] * 10)
        model = text_model().fit(texts, labels)
        self.assertLess(model.predict_proba(["normal lunch meeting"])[0, 1], 0.5)
        self.assertGreater(model.predict_proba(["urgent claim free prize"])[0, 1], 0.5)
        urls = [f"https://safe{i}.org/help" for i in range(25)]
        urls += [f"http://bank-login{i}.vip/verify" for i in range(25)]
        fitted = url_model().fit(urls, np.array([0] * 25 + [1] * 25))
        self.assertEqual(fitted.predict_proba(urls).shape, (50, 2))
        self.assertLessEqual(fitted.named_steps["classifier"].n_features_in_, 1013)

    def test_interaction_is_product_not_an_independent_probability(self):
        np.testing.assert_allclose(meta_features([0.2, 0.8], [0.9, 0.5]),
                                   [[0.2, 0.9, 0.18], [0.8, 0.5, 0.4]])


if __name__ == "__main__":
    unittest.main()
