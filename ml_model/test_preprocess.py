import unittest
import pandas as pd
import preprocess as p


class PreprocessTests(unittest.TestCase):
    def test_vietnamese_words_and_money_are_preserved_or_masked(self):
        text = p.normalize_text('Công an yêu cầu trả 100 triệu và 500 vnđ. OTP 123456')
        self.assertIn('công an', text)
        self.assertEqual(text.count('<money>'), 2)
        self.assertIn('<otp>', text)

    def test_all_links_are_extracted_and_masked(self):
        text, urls = p.extract_urls('See HTTPS://EXAMPLE.COM/A and https://bank-login.vip/verify.')
        self.assertEqual(urls, ['https://example.com/A', 'https://bank-login.vip/verify'])
        self.assertEqual(text.count('<URL>'), 2)

    def test_url_host_is_case_insensitive_but_path_is_not(self):
        self.assertEqual(p.canonicalize_url(' HTTPS://EXAMPLE.COM:443/A?B=c#frag '), 'https://example.com/A?B=c')
        self.assertEqual(p.extract_13_features('HTTPS://EXAMPLE.COM/A'), p.extract_13_features('https://example.com/A'))
        self.assertEqual(p.extract_13_features('http://example.com?next=/login')[1], 11)

    def test_brand_boundaries(self):
        self.assertEqual(p.extract_13_features('https://www.vietcombank.com.vn/login')[11], 0)
        self.assertEqual(p.extract_13_features('https://notfacebook.com/login')[11], 1)

    def test_invalid_schemes_are_rejected(self):
        for url in ('file:///secret', 'javascript:alert(1)', 'http://', 'http://example.com:wrong'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                p.canonicalize_url(url)

    def test_conflicts_are_quarantined_after_normalization(self):
        frame = pd.DataFrame({'raw_text': ['Hello  world', 'hello world', 'Keep me', 'keep me'], 'label': [0, 1, 0, 0]})
        cleaned, audit = p.clean_messages(frame)
        self.assertEqual(cleaned.normalized_text.tolist(), ['keep me'])
        self.assertEqual(audit['conflicting_groups_removed'], 1)
        with self.assertRaises(ValueError):
            p.clean_messages(pd.DataFrame({'raw_text': ['bad label'], 'label': [2]}))


if __name__ == '__main__':
    unittest.main()
