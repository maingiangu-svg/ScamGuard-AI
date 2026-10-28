import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from vi_supervised_experiment import benchmark_gate, evaluate_diagnostic, fit, redact_message, training_rows


class VietnameseExperimentTests(unittest.TestCase):
    def test_real_fit_freezes_membership_and_diagnostic_cannot_be_reused(self):
        from vi_data_workflow import digest, sha, write_json, write_jsonl
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as directory:
            root = Path(directory)
            rows = []
            for label, text in [('legitimate', 'Thong bao giao dich hoan tat'),
                                ('spam', 'Quang cao goi cuoc uu dai'),
                                ('scam', 'Gia mao ngan hang lay mat khau')]:
                for i in range(5):
                    raw = text + f' nhom {i}'
                    role = 'train' if i < 4 else 'test'
                    rows.append(dict(case_id=f'{label}-{i}', raw_text=raw, model_text=raw,
                        input_sha256=digest(raw), model_text_sha256=digest(raw), label=label,
                        label_provenance='ai_semantic_review', source_role=role, group=f'{label}-{i}',
                        do_not_train=role == 'test', disposition='training_review_candidate'
                        if role == 'train' else 'reserved_historical_test'))
            corpus = root / 'reviewed_corpus.jsonl'
            write_jsonl(corpus, rows)
            write_json(root / 'annotations_frozen.json', dict(corpus_sha256=sha(corpus)))
            with contextlib.redirect_stdout(io.StringIO()):
                fit(corpus, root / 'experiment')
                result = evaluate_diagnostic(corpus, root / 'experiment')
            fitted = [json.loads(s) for s in (root / 'experiment/fit_rows.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(fitted), 12)
            self.assertTrue(all(r['source_role'] == 'train' for r in fitted))
            self.assertEqual(result['metrics']['rows'], 3)
            with self.assertRaises(FileExistsError):
                evaluate_diagnostic(corpus, root / 'experiment')
            corpus.write_text(corpus.read_text(encoding='utf-8') + '\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Frozen'):
                fit(corpus, root / 'another-run')

    def test_redaction_masks_residual_contacts_credentials_and_long_identifiers(self):
        text = 'Email test@example.org. Mat khau moi la: Secret123! TK 1234567890123 OTP 876543'
        masked = redact_message(text)
        for secret in ['test@example.org', 'Secret123!', '1234567890123', '876543']:
            self.assertNotIn(secret, masked)
        self.assertIn('[EMAIL]', masked)
        self.assertIn('[SECRET]', masked)

    def test_fit_cannot_accept_test_quarantine_or_unknown(self):
        rows = [dict(case_id='A', label='scam', disposition='training_review_candidate',
                     do_not_train=False, raw_text='original', group='one', expert_verified=False)]
        self.assertEqual(training_rows(rows), rows)
        for change in [dict(do_not_train=True), dict(disposition='reserved_historical_test'),
                       dict(label='unknown'), dict(disposition='quarantine')]:
            self.assertEqual(training_rows([dict(rows[0], **change)]), [])

    def test_ai_and_historical_data_never_pass_as_new_independent_benchmark(self):
        base = dict(case_id='A', raw_text='text', label='scam', group='one',
                    label_provenance='ai_semantic_review', message_origin='real_received',
                    reuse_basis='CC BY 4.0', independently_reviewed=False,
                    historical_exposure=False, campaign_verified=False)
        self.assertFalse(benchmark_gate([base], set())['ready'])
        self.assertFalse(benchmark_gate([dict(base, independently_reviewed=True,
                           historical_exposure=True)], set())['ready'])
        self.assertFalse(benchmark_gate([dict(base, independently_reviewed=True)], {'one'})['ready'])


if __name__ == '__main__':
    unittest.main()
