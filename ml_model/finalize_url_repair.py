"""Record a temperature-calibration revision without changing the frozen residual gate."""
import argparse
import json
import pickle
import shutil
from pathlib import Path

from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from calibrate_supervised import calibration_metrics
from predict import probability
from repair_training_data import ROOT, read_jsonl, sha, write_json, write_jsonl
from repair_url_ensemble import OUT as SOURCE, activate, evaluate, verify_candidate

OUT = ROOT / 'data/prepared/url_regression_repair_final_2026-10-27'


def fit(output=OUT):
    protocol, manifest = verify_candidate(SOURCE)
    if (SOURCE / 'evaluation.started').exists():
        raise ValueError('Calibration revision must precede fresh-test evaluation')
    candidate = pickle.loads((SOURCE / 'candidate_bundle.pkl').read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    for name in manifest['dataset_files_sha256']:
        if name != 'protocol.json':
            shutil.copy2(SOURCE / name, output / name)
    shutil.copy2(SOURCE / 'calibration_report.json', output / 'sigmoid_failed_report.json')
    protocol = {**protocol, 'code_sha256': {**protocol['code_sha256'],
        'finalize_url_repair.py': sha(Path(__file__), True)},
        'calibration_method': 'temperature', 'calibration_validation_used_for_method_selection': True,
        'source_repair_bundle_sha256': manifest['bundle_sha256'],
        'failed_sigmoid_report_sha256': sha(SOURCE / 'calibration_report.json'),
        'fresh_test_used_in_calibration_selection': False}
    write_json(output / 'protocol.json', protocol)
    raw = candidate['url']['model']
    train = read_jsonl(output / 'calibration_train.jsonl')
    validation = read_jsonl(output / 'calibration_validation.jsonl')
    calibrated = CalibratedClassifierCV(FrozenEstimator(raw), method='temperature')
    calibrated.fit([r['url'] for r in train], [r['label'] for r in train])
    urls, labels = [r['url'] for r in validation], [r['label'] for r in validation]
    before = calibration_metrics(labels, probability(raw, urls))
    probabilities = probability(calibrated, urls)
    after = calibration_metrics(labels, probabilities)
    passed = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    report = dict(method='temperature', raw=before, calibrated=after, gate_pass=bool(passed),
        calibration_fit_rows=len(train), disjoint_validation_rows=len(validation),
        calibration_validation_used_for_method_selection=True, family_candidates_seen=['sigmoid', 'temperature'],
        fresh_test_used=False, raw_heads_and_gate_refitted=False, source_labels_not_expert_verified=True,
        sms_gate_inherited=True)
    write_json(output / 'calibration_report.json', report)
    write_jsonl(output / 'calibration_validation_predictions.jsonl', [dict(case_id=r['case_id'],
        label=r['label'], calibrated_probability=float(p)) for r, p in zip(validation, probabilities)])
    candidate['url']['probability_model'] = calibrated
    candidate['training']['method'] = candidate['training']['method'].replace('sigmoid', 'temperature')
    candidate['training']['url_calibration_method'] = 'temperature'
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL))
    manifest.update(bundle_sha256=sha(output / 'candidate_bundle.pkl'), training=candidate['training'],
        dataset_files_sha256={**manifest['dataset_files_sha256'], 'protocol.json': sha(output / 'protocol.json'),
                              'sigmoid_failed_report.json': sha(output / 'sigmoid_failed_report.json')},
        fit_code_sha256=sha(Path(__file__), True), calibration_protocol_sha256=sha(output / 'protocol.json'),
        calibration_report_sha256=sha(output / 'calibration_report.json'), calibration_gate_pass=bool(passed),
        calibration_method_revision='Temperature selected on disjoint calibration validation; fresh test untouched')
    write_json(output / 'candidate_manifest.json', manifest)
    verify_candidate(output)
    print(json.dumps(dict(calibration=report, bundle_sha256=manifest['bundle_sha256'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('fit', 'evaluate', 'activate'))
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    {'fit': fit, 'evaluate': evaluate, 'activate': activate}[args.command](args.output)
