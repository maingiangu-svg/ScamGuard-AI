"""Data repair must preserve labels, provenance and quarantine uncertainty."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from data_quality import prepare_sms, prepare_urls, read_spam_reference, repair_url


class DataQualityTests(unittest.TestCase):
    def test_reference_recovers_complete_messages_without_guessing_labels(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'data') as directory:
            path = Path(directory) / 'reference.zip'
            with ZipFile(path, 'w') as archive:
                archive.writestr('SMSSpamCollection', 'ham\tSay "hi", then call\nspam\tClaim now\n')
            checksum = hashlib.sha256(path.read_bytes()).hexdigest()
            frame = read_spam_reference(path, checksum)
            self.assertEqual(frame.raw_text.tolist(), ['Say "hi", then call', 'Claim now'])
            self.assertEqual(frame.label.tolist(), [0, 1])
            self.assertEqual(frame.source_record.tolist(), [1, 2])
            with self.assertRaisesRegex(ValueError, 'checksum'):
                read_spam_reference(path, 'wrong')

    def test_url_repairs_are_explicit_and_do_not_guess_hostnames(self):
        examples = {
            'hxxps://example[.]com/A': 'https://example.com/A',
            'example.com/Secure Login.html?x=hello': 'http://example.com/Secure%20Login.html?x=hello',
            'https://EXAMPLE.COM/A%20B?q=%2F': 'https://example.com/A%20B?q=%2F',
        }
        for raw, expected in examples.items():
            with self.subTest(raw=raw):
                self.assertEqual(repair_url(raw)[0], expected)
        for raw in ['http://exa mple.com/a', 'http://example.com/a\nb',
                    'ftp://example.com/a', 'example..com/a', 'example.com:/a', '?',
                    "'example.com/A space'", 'https://exam"ple.com/A',
                    'example.com/file.exe Trojan.Agent', 'example.com/a HTTP/1.1',
                    'example.com/a?token=bad token', 'example.com/a<br/>b',
                    'example.com/a another.example.org/b']:
            with self.subTest(raw=raw):
                self.assertEqual(repair_url(raw)[0], '')

    def test_repaired_url_conflicts_and_bad_labels_are_quarantined(self):
        frame = pd.DataFrame({'URL': ['hxxp://a[.]com/x', 'http://a.com/x',
                                     'safe.org/', 'safe.org/', 'other.org/', 'bad host.com/'],
                              'Label': ['bad', 'good', 'good', 'good', 'unknown', 'bad']})
        clean, review, audit = prepare_urls(frame)
        self.assertEqual(clean.url.tolist(), ['http://safe.org/'])
        self.assertEqual(clean.label.tolist(), [0])
        self.assertEqual(audit['conflicting_groups'], 1)
        self.assertEqual(audit['duplicates_removed'], 1)
        self.assertEqual(set(review.source_record), {1, 2, 5, 6})
        self.assertEqual(frame.Label.tolist()[4], 'unknown')

    def test_sms_weak_labels_are_not_promoted_or_auxiliary_labels_invented(self):
        frame = pd.DataFrame({'message': ['Hello  world', 'hello world', 'Keep me', 'keep me', 'missing'],
                              'smishing label': ['0', '1', '0', '0', ''],
                              'spam label': ['', 'Smishing', '', '0', '']})
        clean, review, audit = prepare_sms(frame)
        self.assertEqual(clean.normalized_text.tolist(), ['keep me'])
        self.assertEqual(clean.label.tolist(), [0])
        self.assertEqual(clean.label_provenance.tolist(), ['weak_keyword_derived'])
        self.assertEqual(set(review.source_record), {1, 2, 5})
        self.assertEqual(audit['conflicting_groups'], 1)
        self.assertEqual(frame['spam label'].tolist(), ['', 'Smishing', '', '0', ''])


if __name__ == '__main__':
    unittest.main()
