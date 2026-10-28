"""Official URL seeds must not bypass labels or historical holdout isolation."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from official_domain_training import activate, prepare_seeds, release_gate, validate_seeds, verify_run
from repair_training_data import sha


def ledger():
    return dict(reviewed_on='2026-10-27', label=0, expert_verified=False,
                label_scope='exact first-party URL only',
                label_provenance='user_requested_first_party_url_ai_evidence_review',
                sites=[dict(domain='youtube.com', url='https://www.youtube.com/',
                            evidence_url='https://about.youtube/')])


def row(case, url, root='youtube.com', group='existing-group', label=0, partition='train'):
    return dict(case_id=case, url=url, roots=[root], icann_roots=[root],
                repair_group=group, label=label, partition=partition,
                original_partition=partition, do_not_train=partition != 'train')


class OfficialDomainTrainingTests(unittest.TestCase):
    def activation_fixture(self, root):
        output, models = root / 'run', root / 'models'
        output.mkdir()
        models.mkdir()
        for name, content in [('hybrid_bundle.pkl', b'original'), ('hybrid_manifest.json', b'{}')]:
            (models / name).write_bytes(content)
        for name in ['fit_rows.jsonl', 'sms_fit_rows.jsonl', 'url_fit_rows.jsonl']:
            (output / name).write_text('fitted rows', encoding='utf-8')
        (output / 'parent_manifest.json').write_bytes(b'{}')
        (output / 'candidate_bundle.pkl').write_bytes(b'candidate')
        (output / 'calibration_report.json').write_text('{"gate_pass": true}', encoding='utf-8')
        files = {name: sha(output / name) for name in
                 ['fit_rows.jsonl', 'sms_fit_rows.jsonl', 'url_fit_rows.jsonl', 'parent_manifest.json']}
        protocol = dict(code_sha256={}, input_sha256=files,
                        base_bundle_sha256=sha(models / 'hybrid_bundle.pkl'))
        (output / 'protocol.json').write_text(json.dumps(protocol), encoding='utf-8')
        manifest = dict(bundle_sha256=sha(output / 'candidate_bundle.pkl'),
            calibration_protocol_sha256=sha(output / 'protocol.json'),
            calibration_report_sha256=sha(output / 'calibration_report.json'),
            calibration_gate_pass=True, dataset_files_sha256=files,
            training=dict(training_manifest_sha256=files['fit_rows.jsonl']),
            source_sha256={branch + '_train': files[branch + '_fit_rows.jsonl'] for branch in ('sms', 'url')})
        scores = dict(confusion_matrix_tn_fp_fn_tp=[90, 10, 5, 95])
        report = dict(bundle_sha256=manifest['bundle_sha256'],
            protocol_sha256=manifest['calibration_protocol_sha256'], release_gate_pass=True,
            metrics=dict(baseline=scores, candidate=scores))
        (output / 'evaluation.json').write_text(json.dumps(report), encoding='utf-8')
        manifest['evaluation_sha256'] = sha(output / 'evaluation.json')
        (output / 'candidate_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return output, models

    def test_activation_backs_up_parent_and_installs_bound_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            output, models = self.activation_fixture(Path(directory))
            activate(output, models)
            self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'candidate')
            self.assertEqual((output / 'previous_active/hybrid_bundle.pkl').read_bytes(), b'original')

    def test_activation_rejects_artifact_evidence_and_parent_tampering_before_any_write(self):
        for location, filename in [('run', 'candidate_bundle.pkl'), ('run', 'fit_rows.jsonl'),
                ('run', 'protocol.json'), ('run', 'calibration_report.json'), ('run', 'evaluation.json'),
                ('models', 'hybrid_bundle.pkl'), ('models', 'hybrid_manifest.json')]:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output, models = self.activation_fixture(root)
                target = root / location / filename
                target.write_bytes(target.read_bytes() + b' ')
                before = (models / 'hybrid_bundle.pkl').read_bytes()
                with self.assertRaises(ValueError):
                    activate(output, models)
                self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), before)
                self.assertFalse((output / 'previous_active').exists())

    def test_holdout_domain_is_blocked_even_when_new_url_has_never_been_seen(self):
        for branch_content in ['url', 'sms']:
            heldout = row('heldout', 'https://youtube.com/old', partition='test')
            if branch_content == 'sms':
                heldout['raw_text'] = 'Watch https://youtube.com/old'
            accepted, decisions = prepare_seeds(ledger(), [], [heldout])
            self.assertEqual(accepted, [])
            self.assertEqual(decisions[0]['status'], 'reserved_domain')

    def test_seed_joins_existing_owner_group_for_calibration_and_retains_evidence(self):
        accepted, decisions = prepare_seeds(ledger(), [row('old', 'http://youtube.com/watch?v=1')], [])
        self.assertEqual(accepted[0]['repair_group'], 'existing-group')
        self.assertEqual(accepted[0]['label'], 0)
        self.assertFalse(accepted[0]['expert_verified'])
        self.assertEqual(accepted[0]['evidence_url'], 'https://about.youtube/')
        self.assertEqual(decisions[0]['status'], 'added')

    def test_exact_duplicate_is_not_upweighted_and_conflicting_label_is_not_overwritten(self):
        for label, status in [(0, 'already_in_training'), (1, 'label_conflict')]:
            existing = row('old', 'https://www.youtube.com/', label=label)
            original = copy.deepcopy(existing)
            accepted, decisions = prepare_seeds(ledger(), [existing], [])
            self.assertEqual(accepted, [])
            self.assertEqual(decisions[0]['status'], status)
            self.assertEqual(existing, original)

    def test_unresolved_training_domain_is_blocked(self):
        excluded = row('excluded', 'https://youtube.com/other', partition='quarantine')
        accepted, decisions = prepare_seeds(ledger(), [], [excluded])
        self.assertEqual(accepted, [])
        self.assertEqual(decisions[0]['status'], 'reserved_domain')

    def test_rejects_spoofed_host_credentials_missing_evidence_and_fake_expert_status(self):
        for url in ['https://youtube.com.attacker.example/', 'https://youtube.com@www.youtube.com/',
                    'http://www.youtube.com/', 'https://www.youtube.com:8443/']:
            data = ledger()
            data['sites'][0]['url'] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_seeds(data)
        for field, value in [('expert_verified', True), ('label', 1), ('reviewed_on', '')]:
            data = ledger()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_seeds(data)
        data = ledger()
        data['sites'][0]['evidence_url'] = ''
        with self.assertRaises(ValueError):
            validate_seeds(data)

    def test_preparation_rejects_nontraining_rows_and_split_owner_groups(self):
        for rows in [[row('bad', 'https://youtube.com/', partition='test')],
                     [row('a', 'https://youtube.com/a'), row('b', 'https://youtube.com/b', group='other')]]:
            with self.assertRaises(ValueError):
                prepare_seeds(ledger(), rows, [])

    def test_release_rejects_more_false_alarms_missed_attacks_or_failed_calibration(self):
        baseline = dict(confusion_matrix_tn_fp_fn_tp=[90, 10, 5, 95])
        for counts, calibration, expected in [([91, 9, 4, 96], True, True),
                ([90, 10, 5, 95], True, True), ([89, 11, 4, 96], True, False),
                ([91, 9, 6, 94], True, False), ([91, 9, 4, 96], False, False)]:
            self.assertEqual(release_gate(baseline, dict(confusion_matrix_tn_fp_fn_tp=counts),
                                          calibration), expected)

    def test_changed_fit_export_is_rejected_by_frozen_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            source = output / 'fit_rows.jsonl'
            source.write_text('original fit data', encoding='utf-8')
            (output / 'protocol.json').write_text(json.dumps(dict(code_sha256={},
                input_sha256={'fit_rows.jsonl': sha(source)})), encoding='utf-8')
            verify_run(output)
            source.write_text('test data slipped into training', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Frozen training input changed'):
                verify_run(output)


if __name__ == '__main__':
    unittest.main()
