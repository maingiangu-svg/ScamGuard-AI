"""Guard train-only, group-isolated predictions used for label review."""
import unittest

import numpy as np
from sklearn.dummy import DummyClassifier

from audit_labels import grouped_probabilities, validate_training_rows


def examples():
    return [dict(case_id=f'CASE-{i}', partition='train', original_partition='train',
                 do_not_train=False, repair_reasons=[], repair_group=f'GROUP-{i // 2}',
                 label=i % 2, label_provenance='source_not_expert', raw_text=f'message {i}')
            for i in range(12)]


class LabelAuditTests(unittest.TestCase):
    def test_heldout_quarantined_and_missing_provenance_rows_are_rejected(self):
        for changes in ({'partition': 'test'}, {'original_partition': 'validation'},
                        {'do_not_train': True}, {'repair_reasons': ['conflict']},
                        {'label_provenance': ''}, {'repair_group': ''}, {'label': True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_training_rows([{**examples()[0], **changes}])

    def test_duplicate_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_training_rows([examples()[0], examples()[0]])

    def test_every_prediction_comes_from_a_model_that_has_not_seen_its_group(self):
        fitted = []

        class RecordingModel(DummyClassifier):
            def fit(self, x, y, **kwargs):
                self.seen = set(x)
                fitted.append(self)
                return super().fit(x, y, **kwargs)

            def predict_proba(self, x):
                for value in x:
                    group = int(value.split()[-1]) // 2
                    self_test.assertFalse({f'message {2 * group}', f'message {2 * group + 1}'} & self.seen)
                return super().predict_proba(x)

        self_test = self
        rows = examples()
        probabilities, folds, proof = grouped_probabilities(
            rows, lambda: RecordingModel(strategy='prior'), [r['raw_text'] for r in rows], 3)
        self.assertEqual(len(fitted), 3)
        self.assertEqual(probabilities.shape, (12, 2))
        np.testing.assert_allclose(probabilities.sum(axis=1), 1)
        self.assertEqual(set(folds), {0, 1, 2})
        self.assertTrue(all(folds[i] == folds[i + 1] for i in range(0, 12, 2)))
        self.assertTrue(all(p['shared_groups'] == 0 for p in proof))
        self.assertEqual(sum(p['heldout_rows'] for p in proof), 12)

    def test_insufficient_groups_and_single_class_folds_fail_closed(self):
        with self.assertRaises(ValueError):
            grouped_probabilities(examples(), lambda: DummyClassifier(), ['x'] * 12, 7)
        rows = [{**r, 'label': 0} for r in examples()]
        with self.assertRaises(ValueError):
            grouped_probabilities(rows, lambda: DummyClassifier(), ['x'] * 12, 3)

    def test_a_minority_class_confined_to_one_group_cannot_leak_into_its_own_prediction(self):
        rows = [{**r, 'label': int(r['repair_group'] == 'GROUP-0')} for r in examples()]
        with self.assertRaisesRegex(ValueError, 'missing class'):
            grouped_probabilities(rows, lambda: DummyClassifier(), ['x'] * 12, 3)


if __name__ == '__main__':
    unittest.main()
