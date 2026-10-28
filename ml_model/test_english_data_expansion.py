"""Regression checks for source fidelity, label scope and holdout protection."""
import json
from pathlib import Path
import tempfile
import unittest

from english_data_expansion import parse_message, apply_scope, assign_partition, require_train, export_rows, cap_additions
from vi_data_workflow import audit_rows


class EnglishExpansionTests(unittest.TestCase):
    def test_pinned_source_extra_column_does_not_shift_time_or_message(self):
        row = parse_message(['4', 'obj', '+123', 'Hello\u2028friend', 'Unheaded field',
                             '1651510753.0', '7200.0'], 5)
        self.assertEqual(row['raw_text'], 'Hello\u2028friend')
        self.assertEqual(row['source_time'], '1651510753.0')
        self.assertEqual(row['source_time_error'], '7200.0')
        self.assertEqual(row['source_unheaded_field'], 'Unheaded field')
        self.assertIsNone(row['label'])
        self.assertEqual(row['source_label'], 1)
        self.assertFalse(row['expert_verified'])
        with self.assertRaises(ValueError):
            parse_message(['bad', 'width'], 1)

    def test_scope_screen_never_promotes_promotion_or_unreviewed_rows(self):
        row = dict(template_id='t', label=None, source_label=1, language='en',
                   language_confidence=.99, partition='train', do_not_train=True)
        self.assertIsNone(apply_scope(row, {})['label'])
        for scope in ['exclude_promotion', 'uncertain', 'other_language']:
            checked = apply_scope(row, {'t': dict(scope=scope, rationale='Reviewed content')})
            self.assertIsNone(checked['label'])
            self.assertTrue(checked['do_not_train'])
        approved = apply_scope(row, {'t': dict(scope='retain_source_phishing', rationale='Credential impersonation')})
        self.assertEqual(approved['label'], 1)
        self.assertEqual(approved['label_provenance'], 'source_feed_phishing_with_ai_template_scope_screen')
        self.assertFalse(approved['expert_verified'])
        self.assertFalse(approved['do_not_train'])
        held = apply_scope(dict(row, partition='test'), {'t': dict(scope='retain_source_phishing', rationale='Reviewed')})
        self.assertTrue(held['do_not_train'])
        with self.assertRaises(ValueError):
            apply_scope(dict(row, source_label=0), {'t': dict(scope='retain_source_phishing', rationale='Unsupported override')})
        with self.assertRaises(ValueError):
            apply_scope(row, {'t': dict(scope='retain_source_phishing', rationale='AI', expert_verified=True)})

    def test_historical_bridge_and_reserved_groups_cannot_become_training(self):
        rows = [dict(case_id='new', raw_text='Click https://a.example.com/claim', role='unused')]
        historical = [dict(raw_text='Other text https://b.example.com/login', role='test')]
        grouped = audit_rows(rows, historical, lambda text: ['example.com'])
        self.assertEqual(assign_partition(grouped[0]), 'quarantine')
        self.assertEqual(assign_partition(dict(grouped[0], disposition='training_review_candidate',
                                               group_roles=['unused', 'train'])), 'train')
        for role in ['test', 'validation', 'quarantine']:
            with self.assertRaises(ValueError):
                require_train([dict(label=1, partition=role, do_not_train=False)])
        with self.assertRaises(ValueError):
            require_train([dict(label=None, partition='train', do_not_train=False)])

    def test_unicode_exports_remain_one_record_per_line(self):
        test_root = Path(__file__).resolve().parent / 'data/prepared'
        with tempfile.TemporaryDirectory(dir=test_root) as tmp:
            rows = [dict(case_id='x', raw_text='Hello\u2028friend\u0085again', label=None)]
            export_rows(Path(tmp), 'sample', rows)
            lines = (Path(tmp) / 'sample.jsonl').read_text(encoding='utf-8').splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), rows[0])

    def test_repeated_templates_cannot_dominate_training(self):
        rows = [dict(case_id=str(i), template_id='same', group='g', partition='train',
                     label=1, do_not_train=False) for i in range(20)]
        capped = cap_additions(rows)
        retained = [r for r in capped if not r['do_not_train']]
        self.assertEqual(len(retained), 3)
        self.assertEqual({r['case_id'] for r in retained},
                         {r['case_id'] for r in cap_additions(list(reversed(rows))) if not r['do_not_train']})
        distinct = [dict(r, template_id=r['case_id']) for r in rows + [dict(rows[0], case_id='extra')]]
        self.assertEqual(sum(not r['do_not_train'] for r in cap_additions(distinct)), 20)


if __name__ == '__main__':
    unittest.main()
