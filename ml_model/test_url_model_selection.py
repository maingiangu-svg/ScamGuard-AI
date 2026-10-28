"""URL model selection must preserve sparse features and fixed quality gates."""
import json
import tempfile
import unittest
from pathlib import Path

from scipy.sparse import issparse

import test_official_domain_training as previous_tests
from repair_training_data import sha
from url_model_selection import CONFIGS, activate, candidate_model, choose_candidate, validate_selection_rows, verify_selection


def metrics(fp, tp):
    return dict(confusion_matrix_tn_fp_fn_tp=[100 - fp, fp, 100 - tp, tp],
                f1=2 * tp / (100 + tp + fp))


class URLModelSelectionTests(unittest.TestCase):
    def selection_fixture(self, root, passed=True):
        output, models = previous_tests.OfficialDomainTrainingTests().activation_fixture(root)
        candidate = metrics(9, 81) if passed else metrics(11, 81)
        selection = dict(reference=metrics(10, 80), candidates={'sparse_c4': candidate},
                         winner='sparse_c4', gate_pass=passed)
        (output / 'selection.json').write_text(json.dumps(selection), encoding='utf-8')
        (output / 'selection_frozen.json').write_text(json.dumps({name: sha(output / name)
            for name in ['selection.json', 'protocol.json']}), encoding='utf-8')
        manifest_path = output / 'candidate_manifest.json'
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        manifest['selection_gate_pass'] = passed
        manifest['dataset_files_sha256'].update({name: sha(output / name)
            for name in ['selection.json', 'selection_frozen.json']})
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        return output, models

    def test_activation_requires_selection_gate_and_keeps_previous_weights_on_failure(self):
        for passed in [False, True]:
            with tempfile.TemporaryDirectory() as directory:
                output, models = self.selection_fixture(Path(directory), passed)
                if passed:
                    activate(output, models)
                    self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'candidate')
                    self.assertEqual((output / 'previous_active/hybrid_bundle.pkl').read_bytes(), b'original')
                else:
                    with self.assertRaises(ValueError):
                        activate(output, models)
                    self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'original')
                    self.assertFalse((output / 'previous_active').exists())

    def test_changed_selection_evidence_cannot_replace_active_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            output, models = self.selection_fixture(Path(directory))
            (output / 'selection.json').write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Frozen selection evidence changed'):
                verify_selection(output)
            with self.assertRaises(ValueError):
                activate(output, models)
            self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'original')

    def test_selection_never_relaxes_false_alarm_or_detection_constraints(self):
        baseline = metrics(10, 80)
        candidates = {'high_recall': metrics(11, 99), 'few_alarms': metrics(0, 79),
                      'better': metrics(9, 81)}
        winner, passed = choose_candidate(baseline, candidates)
        self.assertEqual(winner, 'better')
        self.assertTrue(passed)
        winner, passed = choose_candidate(baseline, {'high_recall': candidates['high_recall']})
        self.assertEqual(winner, 'high_recall')
        self.assertFalse(passed)

    def test_training_guard_rejects_holdouts_and_conflicting_domain_groups(self):
        valid = dict(case_id='a', partition='train', original_partition='train',
                     do_not_train=False, repair_reasons=[], label=0,
                     roots=['example.com'], icann_roots=['example.com'], repair_group='g')
        validate_selection_rows([valid])
        for changed in [dict(valid, partition='test'), dict(valid, do_not_train=True),
                        dict(valid, original_partition='test'), dict(valid, repair_reasons=['unresolved']),
                        dict(valid, label=None)]:
            with self.assertRaises(ValueError):
                validate_selection_rows([changed])
        with self.assertRaises(ValueError):
            validate_selection_rows([valid, dict(valid, case_id='b', repair_group='other')])

    def test_candidate_learns_both_classes_without_dense_feature_expansion(self):
        for name in CONFIGS:
            model = candidate_model(name)
            urls = ['https://books.example/reading', 'https://books.example/library',
                    'https://office.example/help', 'https://office.example/contact',
                    'http://account-verify.xyz/otp', 'http://account-verify.xyz/password',
                    'http://bank-prize.xyz/claim', 'http://bank-prize.xyz/login']
            model.fit(urls, [0, 0, 0, 0, 1, 1, 1, 1])
            matrix = model.named_steps['features'].transform(urls)
            self.assertTrue(issparse(matrix))
            predictions = model.predict_proba(urls)[:, 1]
            self.assertLess(predictions[:4].mean(), predictions[4:].mean())
            self.assertEqual(list(model.classes_), [0, 1])
        with self.assertRaises(ValueError):
            candidate_model('unfrozen_configuration')


if __name__ == '__main__':
    unittest.main()
