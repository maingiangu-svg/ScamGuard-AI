import unittest
from unittest.mock import patch

from predict_hybrid import classify, load_bundle
from predict_links import classify_links


class LinkBatchTests(unittest.TestCase):
    def test_matches_existing_scores_and_actions_with_one_verified_model_load(self):
        urls = ['https://www.facebook.com/', 'https://qi.lv/F0i',
                'https://uccle.monopinion.belgium.be/profiles/sunwinorgvc/badges']
        expected = [classify('', url) for url in urls]
        with patch('predict_links.load_bundle', wraps=load_bundle) as loader:
            result = classify_links(urls)
        self.assertTrue(result['model_ready'])
        self.assertEqual(loader.call_count, 1)
        for actual, baseline in zip(result['results'], expected):
            self.assertEqual(actual['riskScore'], baseline['ml_risk_score'])
            self.assertEqual(actual['model_id'], baseline['url_result']['model_id'])
            self.assertEqual(actual['riskLevel'], {'CLEAR': 'LOW', 'REVIEW': 'MEDIUM', 'BLOCK': 'HIGH'}[baseline['action']])

    def test_rejects_unbounded_nonweb_and_sensitive_inputs_before_loading(self):
        for urls in [None, [], ['https://example.com/'] * 21, ['javascript:alert(1)'],
                     ['https://user:password@example.com/'], ['https://example.com/?secret=1'], ['https://']]:
            with self.subTest(urls=urls), patch('predict_links.load_bundle') as loader:
                self.assertFalse(classify_links(urls)['model_ready'])
                loader.assert_not_called()

    def test_model_failure_never_produces_a_safe_result(self):
        with patch('predict_links.load_bundle', side_effect=ValueError('checksum mismatch')):
            result = classify_links(['https://example.com/'])
        self.assertFalse(result['model_ready'])
        self.assertNotIn('results', result)


if __name__ == '__main__':
    unittest.main()
