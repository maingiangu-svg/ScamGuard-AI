"""A 95% target must measure held-out accuracy without changing labels or gates."""
import json
import tempfile
import unittest
from pathlib import Path

from accuracy_target_training import candidate_model, choose_model, classification_metrics, partition_new_urls, verify_data
from repair_training_data import sha


class AccuracyTargetTests(unittest.TestCase):
    def test_reserved_test_export_cannot_change_after_freezing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            heldout = output / 'fresh_test.jsonl'
            heldout.write_text('reserved source-labeled rows', encoding='utf-8')
            (output / 'data_frozen.json').write_text(json.dumps(dict(inputs_sha256={},
                files_sha256={'fresh_test.jsonl': sha(heldout)})), encoding='utf-8')
            verify_data(output)
            heldout.write_text('easier test rows', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Frozen data changed'):
                verify_data(output)

    def test_frozen_estimators_use_url_features_and_no_random_row_early_stopping(self):
        self.assertEqual(candidate_model('wide_lr_c1').named_steps['classifier'].C, 1)
        self.assertEqual(candidate_model('wide_lr_c4').named_steps['classifier'].C, 4)
        self.assertEqual(candidate_model('numeric_trees').named_steps['classifier'].n_estimators, 300)
        self.assertFalse(candidate_model('svd_boost').named_steps['classifier'].early_stopping)
        with self.assertRaises(ValueError):
            candidate_model('unregistered_search')

    def test_accuracy_is_not_precision_and_requires_strictly_above_95(self):
        scores = [.1] * 90 + [.9] * 5 + [.1] * 5
        result = classification_metrics([0] * 90 + [1] * 10, scores)
        self.assertEqual(result['accuracy'], .95)
        self.assertEqual(result['precision'], 1.0)
        self.assertEqual(result['recall'], .5)
        self.assertFalse(result['accuracy_above_95'])
        self.assertLess(result['accuracy_wilson_95ci'][0], .95)

    def test_selection_preserves_alarm_and_detection_constraints(self):
        reference = dict(confusion_matrix_tn_fp_fn_tp=[96, 4, 10, 90], accuracy=.93, f1=.9)
        candidates = {
            'target': dict(confusion_matrix_tn_fp_fn_tp=[97, 3, 5, 95], accuracy=.96, f1=.95),
            'too_many_alarms': dict(confusion_matrix_tn_fp_fn_tp=[95, 5, 0, 100], accuracy=.975, f1=.97),
            'too_many_misses': dict(confusion_matrix_tn_fp_fn_tp=[100, 0, 11, 89], accuracy=.945, f1=.93)}
        winner, passed = choose_model(reference, candidates)
        self.assertEqual(winner, 'target')
        self.assertTrue(passed)
        _, passed = choose_model(reference, {'bad': candidates['too_many_alarms']})
        self.assertFalse(passed)

    def test_new_domains_are_disjoint_deterministic_capped_and_keep_source_labels(self):
        rows = [dict(url=f'https://site{i}.example/p{j}', owner=f'site{i}.example', label=i % 2,
                     source_record=i * 20 + j) for i in range(40) for j in range(20)]
        train, test = partition_new_urls(rows, {'site0.example'}, train_limit=1000, test_limit=1000)
        reverse = partition_new_urls(list(reversed(rows)), {'site0.example'}, train_limit=1000, test_limit=1000)
        self.assertEqual((train, test), reverse)
        self.assertTrue(train and test)
        self.assertFalse({r['owner'] for r in train} & {r['owner'] for r in test})
        self.assertNotIn('site0.example', {r['owner'] for r in train + test})
        self.assertTrue(all(sum(r['owner'] == d for r in train + test) <= 10
                            for d in {r['owner'] for r in train + test}))
        lookup = {r['url']: r for r in rows}
        self.assertTrue(all(r['label'] == lookup[r['url']]['label'] for r in train + test))


if __name__ == '__main__':
    unittest.main()
