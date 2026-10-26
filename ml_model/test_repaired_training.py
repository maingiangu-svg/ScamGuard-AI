"""A real miniature fit must never learn the held-out vocabulary or skip data hashes."""
import pickle
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import train_repaired_hybrid as training
from repair_training_data import repair_rows, sha, write_json, write_jsonl
from audit_vi_holdout import template_signature
import repair_training_data


def fixture(directory):
    (directory / 'public_suffix_list.dat').write_text('com\n', encoding='utf-8')
    rows = []
    for branch, cohort in (('sms', 'processed_sms'), ('url', 'bundle_url')):
        for i in range(6):
            role = 'train' if i < 4 else 'test'
            content = f'training sample {i} message' if role == 'train' else f'heldoutsentinel unique {i}'
            rows.append({'case_id': f'{branch}-{i}', 'cohort': cohort, 'partition': role,
                         'roots': [] if branch == 'sms' else [f'{branch}{i}.com'],
                         'icann_roots': [] if branch == 'sms' else [f'{branch}{i}.com'],
                         'ambiguous_host_candidates': [],
                         'template': template_signature(content) if branch == 'sms' else '',
                         'model_input': content, 'source_group': '', 'label': i % 2,
                         'raw_text': content, 'url': f'http://{branch}{i}.com/' + content.replace(' ', '-'),
                         'language': 'en', 'label_provenance': 'fixture',
                         'source_trace': 'matches_recorded_source_and_review'})
            if branch == 'url':
                del rows[-1]['raw_text']
    repaired, _ = repair_rows(rows)
    write_jsonl(directory / 'all_rows.jsonl', repaired)
    write_json(directory / 'similarity_edges.json', [])
    for branch, cohort in (('sms', 'processed_sms'), ('url', 'bundle_url')):
        for role in ('train', 'validation', 'test', 'quarantine'):
            write_jsonl(directory / f'{branch}_{role}.jsonl', [r for r in repaired if r['cohort'] == cohort and r['partition'] == role])
    write_json(directory / 'repair_report.json', {'protocol': {'sms': {'variant': 'word_char', 'threshold': .65},
                                                              'url': {'threshold': .5}}})
    write_json(directory / 'frozen.json', {'files_sha256': {p.name: sha(p) for p in directory.iterdir()},
                                         'code_sha256': {}, 'input_sha256': {}})


class RepairedTrainingTests(unittest.TestCase):
    def test_real_fit_learns_train_vocabulary_only_and_binds_weights_to_manifest(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as temporary:
            directory = Path(temporary)
            fixture(directory)
            with patch.object(repair_training_data, 'REF', directory):
                training.fit(directory)
            bundle = pickle.loads((directory / 'candidate_bundle.pkl').read_bytes())
            vocabulary = bundle['sms']['model'].named_steps['features'].transformer_list[0][1].vocabulary_
            self.assertIn('training', vocabulary)
            self.assertNotIn('heldoutsentinel', vocabulary)
            self.assertEqual(bundle['training']['training_manifest_sha256'], sha(directory / 'frozen.json'))
            self.assertEqual(bundle['training']['text_training_samples'], 4)
            self.assertEqual(bundle['training']['url_training_samples'], 4)
            self.assertEqual(bundle['training']['heldout_or_quarantined_rows_fitted'], 0)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                with patch.object(repair_training_data, 'REF', directory):
                    training.fit(directory)

    def test_data_tampering_fails_before_any_fit(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as temporary:
            directory = Path(temporary)
            fixture(directory)
            (directory / 'sms_train.jsonl').write_text('{}\n', encoding='utf-8')
            with patch.object(training, 'training_model') as model, self.assertRaisesRegex(ValueError, 'checksum'):
                training.fit(directory)
            model.assert_not_called()


if __name__ == '__main__':
    unittest.main()
