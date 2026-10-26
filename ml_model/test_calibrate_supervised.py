import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from calibrate_supervised import activate, calibration_metrics, candidate_training_rows, fit_calibrated, group_splits, validate_review
from expert_review import digest
from repair_training_data import sha


def row(case, group, label=0, partition='train'):
    return dict(case_id=case, repair_group=group, label=label, raw_text=case,
                partition=partition, original_partition=partition, do_not_train=partition != 'train',
                label_provenance='source', expert_verified=False)


class CalibrationTests(unittest.TestCase):
    def activation_fixture(self, root):
        output, data, review, package, serving = [root / name for name in ('out', 'data', 'review', 'package', 'serving')]
        for directory in (output, data, review, package, serving):
            directory.mkdir()
        source = dict(row('A', 'group'), cohort='processed_sms')
        contents = json.dumps(source) + '\n'
        (data / 'all_rows.jsonl').write_text(contents)
        for name, text in [('fit_rows.jsonl', contents), ('sms_fit_rows.jsonl', contents),
                           ('url_fit_rows.jsonl', ''), ('fit_code.py', '# frozen source\n')]:
            (output / name).write_text(text)
        (serving / 'hybrid_bundle.pkl').write_bytes(b'original')
        (serving / 'hybrid_manifest.json').write_text('{}')
        (output / 'candidate_bundle.pkl').write_bytes(b'candidate')
        (review / 'user_decisions.json').write_text('{}')
        identities = {'A': dict(branch='sms', input_sha256=digest('A'))}
        (package / 'identities.json').write_text(json.dumps(identities))
        decision = dict(case_id='A', branch='sms', input_sha256=digest('A'), proposed_label=0,
                        provenance='ai_content_review', expert_verified=False,
                        quarantine_required=False, automatic_training_eligible=False)
        (review / 'ai_review.jsonl').write_text(json.dumps(decision) + '\n')
        protocol = dict(base_bundle_sha256=sha(serving / 'hybrid_bundle.pkl'),
                        review_sha256=sha(review / 'ai_review.jsonl'),
                        user_decisions_sha256=sha(review / 'user_decisions.json'),
                        review_package_identities_sha256=sha(package / 'identities.json'))
        (output / 'protocol.json').write_text(json.dumps(protocol))
        report = dict(gate_pass=True, metrics={branch: dict(gate_pass=True) for branch in ('sms', 'url')})
        (output / 'calibration_report.json').write_text(json.dumps(report))
        manifest = dict(calibration_gate_pass=True, bundle_sha256=sha(output / 'candidate_bundle.pkl'),
            calibration_report_sha256=sha(output / 'calibration_report.json'),
            calibration_protocol_sha256=sha(output / 'protocol.json'), fit_code_sha256=sha(output / 'fit_code.py', True),
            dataset_files_sha256={name: sha(output / name) for name in
                                   ('fit_rows.jsonl', 'sms_fit_rows.jsonl', 'url_fit_rows.jsonl')},
            source_sha256={branch + '_train': sha(output / (branch + '_fit_rows.jsonl')) for branch in ('sms', 'url')},
            training=dict(training_manifest_sha256=sha(output / 'fit_rows.jsonl'), run_id='fixture'))
        (output / 'candidate_manifest.json').write_text(json.dumps(manifest))
        return output, data, review, review / 'user_decisions.json', package, serving

    def test_activation_backs_up_prior_weights_and_installs_bound_candidate(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            args = self.activation_fixture(Path(folder))
            with patch('calibrate_supervised.verify', return_value={}):
                result = activate(*args)
            self.assertEqual(result['activated'], 'fixture')
            self.assertEqual((args[0] / 'previous_active/hybrid_bundle.pkl').read_bytes(), b'original')
            self.assertEqual((args[-1] / 'hybrid_bundle.pkl').read_bytes(), b'candidate')

    def test_activation_rejects_every_bound_input_tamper_before_replacing_weights(self):
        for index, filename in [(0, 'candidate_bundle.pkl'), (0, 'calibration_report.json'),
                                (0, 'protocol.json'), (0, 'fit_code.py'), (0, 'fit_rows.jsonl'),
                                (0, 'sms_fit_rows.jsonl'), (2, 'ai_review.jsonl'),
                                (2, 'user_decisions.json'), (4, 'identities.json'), (5, 'hybrid_bundle.pkl')]:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
                args = self.activation_fixture(Path(folder))
                path = args[index] / filename
                path.write_bytes(path.read_bytes() + b' ')
                before = (args[-1] / 'hybrid_bundle.pkl').read_bytes()
                with patch('calibrate_supervised.verify', return_value={}), self.assertRaises(ValueError):
                    activate(*args)
                self.assertEqual((args[-1] / 'hybrid_bundle.pkl').read_bytes(), before)
                self.assertFalse((args[0] / 'previous_active').exists())

    def test_failed_candidate_cannot_replace_serving_weights(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder)
            serving = root / 'serving'
            serving.mkdir()
            (serving / 'hybrid_bundle.pkl').write_bytes(b'original')
            (root / 'candidate_manifest.json').write_text(json.dumps({'calibration_gate_pass': False}))
            with self.assertRaises(ValueError):
                activate(root, root, root, root / 'missing.json', root, serving)
            self.assertEqual((serving / 'hybrid_bundle.pkl').read_bytes(), b'original')

    def test_review_membership_and_provenance_cannot_be_truncated_or_forged(self):
        expected = {'A': dict(branch='sms', input_sha256=digest('A'))}
        decision = dict(case_id='A', branch='sms', input_sha256=digest('A'), provenance='ai_content_review',
                        proposed_label='unknown', quarantine_required=True, expert_verified=False,
                        automatic_training_eligible=False)
        self.assertEqual(set(validate_review([decision], expected)), {'A'})
        for records in [[], [decision, decision], [dict(decision, case_id='B')],
                        [dict(decision, expert_verified=True)], [dict(decision, quarantine_required=False)],
                        [dict(decision, input_sha256=digest('changed'))], [dict(decision, branch='url')]]:
            with self.assertRaises(ValueError):
                validate_review(records, expected)

    def test_unapproved_review_disagreement_cannot_enter_candidate_fit(self):
        with self.assertRaises(ValueError):
            candidate_training_rows([row('A', 'g')], set(), {}, {'A': 1})
        self.assertEqual(candidate_training_rows([row('A', 'g')], {'A'}, {}, {'A': 1}), [])

    def test_unknown_cases_exclude_their_whole_group_and_user_labels_keep_provenance(self):
        rows = [row('A', 'shared'), row('B', 'shared'), row('C', 'other'), row('T', 'test', partition='test')]
        override = {'C': dict(label=1, provenance='user_decision', input_sha256=digest('C'), rationale='User approved.')}
        kept = candidate_training_rows(rows, {'A'}, override)
        self.assertEqual([r['case_id'] for r in kept], ['C'])
        self.assertEqual(kept[0]['label'], 1)
        self.assertEqual(kept[0]['label_provenance'], 'user_decision')
        self.assertFalse(kept[0]['expert_verified'])
        self.assertEqual(rows[2]['label'], 0)

    def test_user_override_cannot_touch_holdout_or_changed_content(self):
        for rows, override in [([row('T', 'g', partition='test')], {'T': dict(label=1, provenance='user_decision', input_sha256=digest('T'), rationale='review')}),
                               ([row('A', 'g')], {'A': dict(label=1, provenance='user_decision', input_sha256=digest('changed'), rationale='review')})]:
            with self.assertRaises(ValueError):
                candidate_training_rows(rows, set(), override)

    def test_groups_are_disjoint_and_sigmoid_outputs_valid_probabilities(self):
        rows = [dict(raw_text=('ordinary meeting ' if label == 0 else 'account password link ') + str(i),
                     label=label, repair_group=f'{label}-{i}') for label in (0, 1) for i in range(12)]
        splits = group_splits(rows, 3)
        for train, calibrate in splits:
            self.assertFalse({rows[i]['repair_group'] for i in train} & {rows[i]['repair_group'] for i in calibrate})
        estimator = Pipeline([('tfidf', TfidfVectorizer()), ('classifier', LogisticRegression())])
        model = fit_calibrated(estimator, rows, 'sms', 3)
        scores = model.predict_proba(['ordinary meeting', 'account password'])[:, 1]
        self.assertTrue(np.isfinite(scores).all())
        self.assertTrue(((scores >= 0) & (scores <= 1)).all())

    def test_calibration_metrics_are_not_accuracy_or_safety_guarantees(self):
        metrics = calibration_metrics([0, 1], [.1, .9])
        self.assertAlmostEqual(metrics['brier'], .01)
        self.assertAlmostEqual(metrics['log_loss'], -np.log(.9))
        self.assertEqual(metrics['rows'], 2)
        self.assertNotIn('safe', metrics)


if __name__ == '__main__':
    unittest.main()
