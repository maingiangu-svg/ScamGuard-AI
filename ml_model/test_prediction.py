import unittest
import os
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import predict


class Estimator:
    def __init__(self, probabilities):
        self.probabilities = probabilities
    def predict_proba(self, rows):
        values = [self.probabilities.get(row, 0.2) for row in rows]
        return np.array([[1 - p, p] for p in values])


class PredictionTests(unittest.TestCase):
    def test_missing_bundle_does_not_produce_safe_prediction(self):
        with patch.object(predict, 'load_bundle', side_effect=FileNotFoundError()):
            result = predict.classify(text='hello')
        self.assertFalse(result['model_ready'])
        self.assertIsNone(result['ml_risk_score'])
        self.assertEqual(result['ml_confidence'], 0)

    def test_error_in_estimator_does_not_become_fifty_percent(self):
        broken = Estimator({})
        broken.predict_proba = lambda _: (_ for _ in ()).throw(RuntimeError('broken'))
        with patch.object(predict, 'load_bundle', return_value={'text_model': broken}):
            result = predict.classify(text='hello')
        self.assertFalse(result['model_ready'])
        self.assertIsNone(result['ml_risk_score'])

    def test_all_links_are_scored_and_missing_meta_is_not_replaced_by_constants(self):
        bundle = {'url_model': Estimator({'https://first.com/': 0.1, 'https://second.com/': 0.95}),
                  'metadata': {}}
        with patch.object(predict, 'load_bundle', return_value=bundle):
            result = predict.classify(url='https://second.com/')
        self.assertEqual(result['ml_risk_score'], 95)

        self.assertEqual(result['action'], 'BLOCK')
        bundle['text_model'] = Estimator({})
        with patch.object(predict, 'load_bundle', return_value=bundle):
            result = predict.classify(text='See https://first.com/ and https://second.com/')
        self.assertFalse(result['model_ready'])
        self.assertIsNone(result['ml_risk_score'])

        class Combiner:
            def predict_proba(self, rows):
                return np.column_stack([1 - rows[:, 1], rows[:, 1]])
        bundle['meta_model'] = Combiner()
        with patch.object(predict, 'load_bundle', return_value=bundle):
            result = predict.classify(text='See https://first.com/ and https://second.com/')
        self.assertTrue(result['model_ready'])
        self.assertEqual(len(result['url_result']['urls']), 2)
        self.assertEqual(result['ml_risk_score'], 95)

    def test_stale_pipeline_bundle_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'models') as directory:
            target = Path(directory) / 'model_bundle.pkl'
            target.write_bytes(pickle.dumps({'metadata': {'pipeline_fingerprint': 'outdated'}}))
            with patch.dict(os.environ, {'SCAMGUARD_MODEL_PATH': str(target)}):
                with self.assertRaisesRegex(ValueError, 'version mismatch'):
                    predict.load_bundle()


if __name__ == '__main__':
    unittest.main()
