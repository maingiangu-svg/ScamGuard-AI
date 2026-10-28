import unittest

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from url_ensemble import GatedURLClassifier, learn_cutoff


class Scores:
    def __init__(self, values):
        self.values = values
        self.classes_ = np.array([0, 1])

    def predict_proba(self, values):
        p = np.array([self.values.get(v, .1) for v in values])
        return np.column_stack((1 - p, p))


class URLProvenanceGateTests(unittest.TestCase):
    def training(self):
        # The parent catches a source-bad example missed by the character head.
        y = np.array([0] * 100 + [1] * 100)
        primary = np.array([.1] * 100 + [.95] * 99 + [.2])
        parent = np.array([.1] * 99 + [.75] + [.95] * 100)
        seeds = [(.1, .775)]
        return y, primary, parent, seeds

    def test_cutoff_is_learned_from_labels_and_preserves_benign_training_seeds(self):
        y, primary, parent, seeds = self.training()
        cutoff, report = learn_cutoff(y, primary, parent, seeds)
        self.assertLessEqual(cutoff, .95)
        self.assertGreater(cutoff, .775)
        self.assertTrue(report['gate_pass'])
        self.assertEqual(report['selected']['confusion_matrix_tn_fp_fn_tp'], [100, 0, 0, 100])

    def test_benign_seed_constraint_cannot_be_traded_for_higher_training_recall(self):
        y, primary, parent, seeds = self.training()
        primary[-2:] = [.2, .2]
        parent[-2:] = [.76, .96]
        cutoff, report = learn_cutoff(y, primary, parent, seeds)
        self.assertGreater(cutoff, .775)
        self.assertEqual(report['selected']['confusion_matrix_tn_fp_fn_tp'][3], 99)

    def test_predict_keeps_primary_scores_and_only_recovers_strong_parent_evidence(self):
        y, primary, parent, seeds = self.training()
        model = GatedURLClassifier(Scores({'recover': .2, 'clear': .1}),
                                   Scores({'recover': .96, 'clear': .775}))
        model.fit(np.arange(len(y)), y, primary_oof=primary, parent_oof=parent, benign_seed_scores=seeds)
        self.assertEqual(model.predict_proba(['recover', 'clear'])[:, 1].tolist(), [.96, .1])
        self.assertEqual(model.predict(['recover', 'clear']).tolist(), [1, 0])

    def test_missing_oof_or_invalid_scores_cannot_silently_train_on_fitted_predictions(self):
        model = GatedURLClassifier(Scores({}), Scores({}))
        with self.assertRaises(ValueError):
            model.fit(['example'], [0])
        with self.assertRaises(ValueError):
            learn_cutoff([0, 1], [.1, float('nan')], [.2, .9], [])

    def test_disjoint_calibration_uses_frozen_model_without_refitting_heads_or_gate(self):
        y, primary, parent, seeds = self.training()
        model = GatedURLClassifier(Scores({'recover': .2, 'clear': .1}), Scores({'recover': .96, 'clear': .775}))
        model.fit(np.arange(len(y)), y, primary_oof=primary, parent_oof=parent, benign_seed_scores=seeds)
        before = model.cutoff_
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method='sigmoid')
        calibrated.fit(['recover', 'clear'] * 20, [1, 0] * 20)
        self.assertEqual(model.cutoff_, before)
        p = calibrated.predict_proba(['recover', 'clear'])[:, 1]
        self.assertTrue(np.isfinite(p).all())
        self.assertGreater(p[0], p[1])


if __name__ == '__main__':
    unittest.main()
