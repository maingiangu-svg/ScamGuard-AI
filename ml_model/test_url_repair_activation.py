import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import repair_url_ensemble as repair
from repair_training_data import ROOT, sha, write_json


class URLRepairActivationTests(unittest.TestCase):
    def fixture(self, root):
        output, models, primary = root / 'output', root / 'models', root / 'primary'
        for path in (output, models, primary):
            path.mkdir()
        (models / 'hybrid_bundle.pkl').write_bytes(b'old')
        (models / 'hybrid_manifest.json').write_bytes(b'{}')
        (primary / 'parent_manifest.json').write_bytes(b'{}')
        (output / 'candidate_bundle.pkl').write_bytes(b'candidate')
        evaluation = dict(numerical_gates_pass=True, bundle_sha256=sha(output / 'candidate_bundle.pkl'))
        write_json(output / 'evaluation.json', evaluation)
        manifest = dict(bundle_sha256=evaluation['bundle_sha256'],
            evaluation_sha256=sha(output / 'evaluation.json'), calibration_gate_pass=True, url_gate_selection_pass=True)
        write_json(output / 'candidate_manifest.json', manifest)
        protocol = dict(parent_bundle_sha256=sha(models / 'hybrid_bundle.pkl'))
        api = dict(exit_code=0, tests_passed=17, bundle_sha256=manifest['bundle_sha256'],
            manifest_sha256=sha(output / 'candidate_manifest.json'), test_scripts_sha256={
                'scripts/analyze.integration.test.mjs': sha(ROOT.parent / 'scripts/analyze.integration.test.mjs'),
                'scripts/api-security.integration.test.mjs': sha(ROOT.parent / 'scripts/api-security.integration.test.mjs')})
        write_json(output / 'api_verification.json', api)
        return output, models, primary, protocol, manifest, api

    def test_verified_candidate_replaces_local_weights_with_a_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            output, models, primary, protocol, manifest, _ = self.fixture(Path(directory))
            with patch.object(repair, 'PRIMARY', primary), patch.object(repair, 'verify_candidate', return_value=(protocol, manifest)):
                repair.activate(output, models)
            self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'candidate')
            self.assertEqual((output / 'previous_active/hybrid_bundle.pkl').read_bytes(), b'old')
            self.assertFalse(json.loads((output / 'activation.json').read_text())['remote_deployment'])

    def test_failed_or_missing_api_evidence_preserves_current_weights(self):
        for missing in (False, True):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                output, models, primary, protocol, manifest, api = self.fixture(Path(directory))
                if missing:
                    (output / 'api_verification.json').unlink()
                else:
                    api['exit_code'] = 1
                    write_json(output / 'api_verification.json', api)
                with patch.object(repair, 'PRIMARY', primary), patch.object(repair, 'verify_candidate', return_value=(protocol, manifest)):
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        repair.activate(output, models)
                self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'old')
                self.assertFalse((output / 'previous_active').exists())

    def test_changed_verification_script_cannot_authorize_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            output, models, primary, protocol, manifest, api = self.fixture(Path(directory))
            api['test_scripts_sha256']['scripts/analyze.integration.test.mjs'] = 'wrong'
            write_json(output / 'api_verification.json', api)
            with patch.object(repair, 'PRIMARY', primary), patch.object(repair, 'verify_candidate', return_value=(protocol, manifest)):
                with self.assertRaises(ValueError):
                    repair.activate(output, models)
            self.assertEqual((models / 'hybrid_bundle.pkl').read_bytes(), b'old')
