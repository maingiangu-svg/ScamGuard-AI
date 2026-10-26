import csv
import tempfile
import unittest
from pathlib import Path

from expert_review import create_package, inspect_reviews, record_ai_review


class ExpertReviewTests(unittest.TestCase):
    def test_ai_review_is_separate_from_expert_labels_and_unknowns_remain_quarantined(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder) / 'review'
            create_package([dict(case_id='A', branch='sms', input='example message'),
                            dict(case_id='B', branch='url', input='https://example.com/')], root)
            before = (root / 'reviewer-a.csv').read_bytes()
            result = record_ai_review(root, {'A': {'label': 0, 'rationale': 'Content review only.'}}, Path(folder) / 'ai')
            self.assertEqual(result['ai_label_proposals'], 1)
            self.assertEqual(result['unresolved'], 1)
            self.assertEqual(result['expert_labels_created'], 0)
            self.assertFalse(result['benchmark_ready'])
            self.assertEqual((root / 'reviewer-a.csv').read_bytes(), before)
            self.assertEqual(inspect_reviews(root)['pending'], 2)

    def test_ai_review_rejects_fabricated_expertise_or_url_only_labels(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder) / 'review'
            create_package([dict(case_id='B', branch='url', input='https://example.com/')], root)
            for decision in [dict(label=0, rationale='Brand alone'),
                             dict(label='unknown', rationale='No evidence', expert_verified=True)]:
                with self.assertRaises(ValueError):
                    record_ai_review(root, {'B': decision}, Path(folder) / 'ai')

    def test_ai_review_requires_every_sms_and_preserves_input_identity(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder) / 'review'
            create_package([dict(case_id='A', branch='sms', input='original')], root)
            with self.assertRaises(ValueError):
                record_ai_review(root, {}, Path(folder) / 'ai')
            path = root / 'reviewer-a.csv'
            path.write_text(path.read_text(encoding='utf-8-sig').replace('original', 'changed'), encoding='utf-8-sig')
            with self.assertRaises(ValueError):
                record_ai_review(root, {'A': dict(label=0, rationale='review')}, Path(folder) / 'ai')

    def test_blind_forms_preserve_content_identity_without_model_labels(self):
        rows = [dict(case_id='A', branch='sms', input='=FORMULA()', label=1, score=.99),
                dict(case_id='B', branch='url', input='https://example.com/', label=0)]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder) / 'review'
            report = create_package(rows, root)
            self.assertEqual(report['cases'], 2)
            with (root / 'reviewer-a.csv').open(encoding='utf-8-sig', newline='') as file:
                records = list(csv.DictReader(file))
            self.assertNotIn('score', records[0])
            self.assertNotIn('label', records[0])
            self.assertTrue(all(r['expert_label'] == '' for r in records))
            self.assertEqual(next(r for r in records if r['case_id'] == 'A')['input'], "'=FORMULA()")
            self.assertFalse(inspect_reviews(root)['complete'])
            with self.assertRaises(FileExistsError):
                create_package(rows, root)

    def test_mismatched_id_or_input_hash_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder) / 'review'
            create_package([dict(case_id='A', branch='sms', input='original')], root)
            path = root / 'reviewer-a.csv'
            path.write_text(path.read_text(encoding='utf-8-sig').replace('original', 'changed'), encoding='utf-8-sig')
            with self.assertRaisesRegex(ValueError, 'identity'):
                inspect_reviews(root)

    def test_same_reviewer_cannot_supply_both_independent_decisions(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as folder:
            root = Path(folder) / 'review'
            create_package([dict(case_id='A', branch='sms', input='original')], root)
            for name in ('reviewer-a.csv', 'reviewer-b.csv'):
                path = root / name
                with path.open(encoding='utf-8-sig', newline='') as file:
                    reader = csv.DictReader(file)
                    fields, records = reader.fieldnames, list(reader)
                records[0].update(expert_label='1', reviewer='same-person', reviewed_at='2026-10-26',
                                  evidence='source evidence', rationale='scope rationale')
                with path.open('w', encoding='utf-8-sig', newline='') as file:
                    writer = csv.DictWriter(file, fields); writer.writeheader(); writer.writerows(records)
            with self.assertRaisesRegex(ValueError, 'independent'):
                inspect_reviews(root)


if __name__ == '__main__':
    unittest.main()
