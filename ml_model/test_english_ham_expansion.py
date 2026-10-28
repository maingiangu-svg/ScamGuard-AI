import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import english_ham_expansion as intake
from english_ham_expansion import parse_source, deduplicate, admit, historical_group_edges
from vi_data_workflow import audit_rows


class EnglishHamExpansionTests(unittest.TestCase):
    def archive(self, content):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('SMSSpamCollection', content)
        return stream.getvalue()

    def test_parser_preserves_tabs_record_numbers_and_source_labels(self):
        rows = parse_source(self.archive('ham\tHello\tthere\nspam\tA prize\nham\tSee you soon\n'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['raw_text'], 'Hello\tthere')
        self.assertEqual(rows[1]['source_record'], 3)
        self.assertEqual(rows[0]['source_label'], 'ham')
        self.assertEqual(rows[0]['label'], 0)
        self.assertFalse(rows[0]['expert_verified'])
        self.assertFalse(rows[0]['human_verified'])
        self.assertTrue(rows[0]['do_not_train'])
        for content in ('maybe\tHi\n', 'ham\n', 'ham\t   \n'):
            with self.assertRaises(ValueError):
                parse_source(self.archive(content))

    def test_duplicate_variants_keep_every_source_record_and_domain(self):
        rows = parse_source(self.archive('ham\tPay 12345 to www.example12345.com\nham\tPay 67890 to www.example67890.com\n'))
        merged = deduplicate(rows)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['merged_source_records'], [1, 2])
        self.assertEqual(len(merged[0]['variant_texts']), 2)

    def test_admission_never_rescues_heldout_unknown_or_conflicting_rows(self):
        row = dict(case_id='UCI-HAM-1', raw_text='Meet me at the station tomorrow please',
                   source_label='ham', label=0, language='en', language_confidence=.99,
                   disposition='training_review_candidate', group_roles=['train'],
                   expert_verified=False, human_verified=False)
        allowed = admit(row, set())
        self.assertEqual(allowed['partition'], 'train')
        self.assertFalse(allowed['do_not_train'])
        changes = [dict(disposition='reserved_historical_test'),
                   dict(disposition='reserved_historical_validation'), dict(disposition='quarantine'),
                   dict(group_roles=['train', 'test']), dict(group_roles=['quarantine']),
                   dict(language='unresolved'), dict(language_confidence=.5),
                   dict(label=1), dict(source_label='spam')]
        for change in changes:
            with self.subTest(change=change):
                blocked = admit(dict(row, **change), set())
                self.assertTrue(blocked['do_not_train'])
                self.assertEqual(blocked['partition'], 'quarantine')
        from round2_experiment import text_input
        self.assertTrue(admit(row, {text_input(row['raw_text'])})['do_not_train'])

    def test_recorded_historical_group_bridge_keeps_test_component_blocked(self):
        rows = [dict(case_id='new', raw_text='Meeting at the library tomorrow morning', role='unused')]
        history = [dict(raw_text=rows[0]['raw_text'], role='train'),
                   dict(raw_text='A completely unrelated heldout case', role='test')]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'data/prepared') as tmp:
            path = Path(tmp) / 'old.jsonl'
            path.write_text(''.join(json.dumps(dict(r, repair_group='earlier-connected-group'))+'\n'
                                    for r in history), encoding='utf8')
            with patch.object(intake, 'ROOT', Path(tmp)):
                edges = historical_group_edges(history, {'old.jsonl':'unused'}, len(rows))
            grouped = audit_rows(rows, history, lambda text: [], edges)
            self.assertEqual(grouped[0]['disposition'], 'reserved_historical_test')
            self.assertTrue(grouped[0]['do_not_train'])


if __name__ == '__main__':
    unittest.main()
