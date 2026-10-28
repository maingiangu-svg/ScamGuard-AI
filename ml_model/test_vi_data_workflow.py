import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vi_data_workflow import audit_rows, historical_rows, merge_annotations, review_gate, write_forms


class VietnameseDataWorkflowTests(unittest.TestCase):
    def test_latest_training_filename_is_not_a_test_and_new_exports_keep_their_roles(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as directory:
            root = Path(directory)
            (root / 'latest_train_review.jsonl').write_text(json.dumps(
                dict(raw_text='training example', partition='train')) + '\n', encoding='utf-8')
            (root / 'historical_predictions.jsonl').write_text(json.dumps(
                dict(raw_text='held out example', disposition='reserved_historical_test')) + '\n', encoding='utf-8')
            with patch('vi_data_workflow.PREPARED', root):
                rows, _ = historical_rows(root / 'future-run')
            self.assertEqual({(r['raw_text'], r['role']) for r in rows},
                             {('training example', 'train'), ('held out example', 'test')})

    def test_holdout_and_quarantine_protect_connected_groups(self):
        rows = [dict(case_id='A', raw_text='alpha message', source_role='train'),
                dict(case_id='B', raw_text='beta message', source_role='train'),
                dict(case_id='C', raw_text='unrelated message', source_role='test')]
        history = [dict(raw_text='alpha message', role='test')]
        actual = audit_rows(rows, history, lambda text: [], [(0, 1)])
        self.assertEqual([r['disposition'] for r in actual],
                         ['reserved_historical_test', 'reserved_historical_test', 'reserved_historical_test'])
        self.assertEqual(actual[0]['group'], actual[1]['group'])
        self.assertTrue(all(r['do_not_train'] for r in actual))

    def test_domain_and_template_bridges_are_transitive(self):
        rows = [dict(case_id='A', raw_text='first distinctive content', source_role='train'),
                dict(case_id='B', raw_text='second distinctive content', source_role='train')]
        domains = {'first distinctive content': ['a.example'], 'second distinctive content': ['b.example'],
                   'historical bridge': ['a.example', 'b.example']}
        history = [dict(raw_text='historical bridge', role='validation')]
        actual = audit_rows(rows, history, lambda text: domains.get(text, []))
        self.assertEqual(actual[0]['group'], actual[1]['group'])
        self.assertTrue(all(r['disposition'] == 'reserved_historical_validation' for r in actual))

    def test_unknown_labels_and_ai_provenance_cannot_become_human_labels(self):
        rows = [dict(case_id='A', raw_text='original text', original_label='1')]
        from vi_data_workflow import digest
        decision = dict(label='unknown', rationale='Needs sender context',
                        input_sha256=digest('original text'), provenance='ai_semantic_review')
        actual = merge_annotations(rows, {'A': decision})[0]
        self.assertEqual(actual['label'], 'unknown')
        self.assertEqual(actual['original_label'], '1')
        self.assertFalse(actual['expert_verified'])
        for change in [dict(label='legitimate', expert_verified=True), dict(input_sha256='wrong')]:
            with self.assertRaises(ValueError):
                merge_annotations(rows, {'A': dict(decision, **change)})

    def test_blind_forms_refuse_overwrite_and_require_two_real_decisions(self):
        from vi_data_workflow import digest
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as directory:
            out = Path(directory) / 'forms'
            rows = [dict(case_id='A', raw_text='=FORMULA()', original_label='1',
                         label='scam', evidence_url='https://example.org/report')]
            write_forms(rows, out)
            self.assertFalse(review_gate(out)['human_review_complete'])
            with self.assertRaises(FileExistsError):
                write_forms(rows, out)
            for person, name in [('Alice', 'reviewer-a.csv'), ('Bob', 'reviewer-b.csv')]:
                path = out / name
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream)
                    fields, records = reader.fieldnames, list(reader)
                self.assertNotIn('original_label', fields)
                self.assertTrue(records[0]['message'].startswith("'="))
                self.assertEqual(records[0]['input_sha256'], digest('=FORMULA()'))
                records[0].update(label='scam', reviewer=person, reviewer_kind='human',
                                  reviewed_at='2026-10-27', evidence='Public report', rationale='Impersonation')
                with path.open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.DictWriter(stream, fields)
                    writer.writeheader(); writer.writerows(records)
            self.assertTrue(review_gate(out)['human_review_complete'])
            path.write_text(path.read_text(encoding='utf-8-sig').replace('Bob', 'Alice'), encoding='utf-8-sig')
            with self.assertRaisesRegex(ValueError, 'independent'):
                review_gate(out)

    def test_unknown_or_incomplete_or_ai_reviewer_blocks_gate(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as directory:
            out = Path(directory) / 'forms'
            write_forms([dict(case_id='A', raw_text='message')], out)
            for name in ['reviewer-a.csv', 'reviewer-b.csv']:
                path = out / name
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream); fields, rows = reader.fieldnames, list(reader)
                rows[0].update(label='scam', reviewer=name, reviewer_kind='ai',
                               reviewed_at='2026-10-27', evidence='report', rationale='review')
                with path.open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.DictWriter(stream, fields); writer.writeheader(); writer.writerows(rows)
            self.assertFalse(review_gate(out)['human_review_complete'])


if __name__ == '__main__':
    unittest.main()
