"""A model explicitly rejected by release diagnostics must not serve a risk score."""
import hashlib
import json
import os
import pickle
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sklearn
import predict_hybrid as live
from test_hybrid_prediction import bundle


class ModelReleaseGateTests(unittest.TestCase):
    def with_manifest(self,flags,callback):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'data/prepared') as directory:
            root=Path(directory); content=pickle.dumps({**bundle(),
                'artifact_type':'routed_supervised_models','paired_fusion_trained':False,
                'sklearn_version':sklearn.__version__})
            model=root/'model.pkl';model.write_bytes(content)
            manifest=root/'manifest.json'
            manifest.write_text(json.dumps(dict(bundle_sha256=hashlib.sha256(content).hexdigest(),
                                               code_sha256={},**flags)),encoding='utf-8')
            with patch.object(live,'MANIFEST',manifest),patch.dict(os.environ,{'SCAMGUARD_MODEL_PATH':str(model)}):
                callback()

    def test_declared_failure_or_nonboolean_approval_cannot_serve(self):
        def reject():
            with self.assertRaises(ValueError):live.load_bundle()
            result=live.classify(text='hello')
            self.assertFalse(result['model_ready'])
            self.assertIsNone(result['ml_risk_score'])
            self.assertEqual(result['action'],'UNAVAILABLE')
        for key in ['historical_nonregression_pass','all_policy_nonregression_pass','release_approved']:
            for value in [False,None,'true',1]:
                with self.subTest(key=key,value=value):self.with_manifest({key:value},reject)

    def test_legacy_and_explicitly_passed_manifests_preserve_loading(self):
        for flags in [{},{'historical_nonregression_pass':True,'all_policy_nonregression_pass':True,'release_approved':True}]:
            with self.subTest(flags=flags):
                self.with_manifest(flags,lambda:self.assertEqual(live.load_bundle()['sms']['threshold'],.65))


if __name__=='__main__':unittest.main()
