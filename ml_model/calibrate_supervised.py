"""Group-isolated source-label calibration; never fit historical holdouts."""
import argparse
import json
import os
import pickle
import shutil
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import StratifiedGroupKFold

from expert_review import digest
from predict import probability
from predict_hybrid import load_bundle
from repair_training_data import OUTPUT, ROOT, read_jsonl, sha, verify, write_json, write_jsonl
from round2_experiment import text_input


def validate_review(rows, expected):
    lookup = {row['case_id']: row for row in rows}
    if len(lookup) != len(rows) or lookup.keys() != expected.keys():
        raise ValueError('Review membership does not match the original blind package')
    for case, row in lookup.items():
        identity = expected[case]
        proposal = row.get('proposed_label')
        if (row.get('branch') != identity['branch'] or row.get('input_sha256') != identity['input_sha256']
                or row.get('expert_verified') is not False or row.get('automatic_training_eligible') is not False
                or (proposal != 'unknown' and (type(proposal) is not int or proposal not in (0, 1)))
                or row.get('quarantine_required') is not (proposal == 'unknown')
                or row.get('provenance') != ('ai_content_review' if row['branch'] == 'sms' else 'url_evidence_sufficiency_check')
                or (row['branch'] == 'url' and proposal != 'unknown')):
            raise ValueError('Invalid review identity, provenance or quarantine status')
    return lookup


def candidate_training_rows(rows, excluded, overrides, reviewed_labels=None):
    lookup = {row['case_id']: row for row in rows}
    if len(lookup) != len(rows) or (set(excluded) | set(overrides)) - lookup.keys():
        raise ValueError('Unknown or repeated case identity')
    groups = {lookup[case]['repair_group'] for case in excluded}
    for case, decision in overrides.items():
        row = lookup[case]
        if (row['partition'] != 'train' or row['original_partition'] != 'train' or row['do_not_train']
                or row['repair_group'] in groups or decision.get('provenance') != 'user_decision'
                or type(decision.get('label')) is not int or decision['label'] not in (0, 1)
                or decision.get('expert_verified') or not decision.get('rationale')
                or decision.get('input_sha256') != digest(row.get('raw_text') or row.get('url', ''))):
            raise ValueError('Invalid user decision, content identity or held-out override')
    accepted = []
    for row in rows:
        if row['partition'] != 'train' or row['do_not_train'] or row['repair_group'] in groups:
            continue
        if row['original_partition'] != 'train' or row.get('repair_reasons'):
            raise ValueError('Only accepted original training rows may be fitted')
        record = dict(row)
        if (reviewed_labels and row['case_id'] in reviewed_labels
                and reviewed_labels[row['case_id']] != 'unknown'
                and reviewed_labels[row['case_id']] != row['label'] and row['case_id'] not in overrides):
            raise ValueError('Review disagreement needs an approved user decision or quarantine')
        if row['case_id'] in overrides:
            record.update(pre_review_label=row['label'], label=overrides[row['case_id']]['label'],
                          label_provenance='user_decision', expert_verified=False,
                          user_decision=overrides[row['case_id']])
        accepted.append(record)
    return accepted


def group_splits(rows, folds=3):
    y = np.array([row['label'] for row in rows])
    groups = np.array([row['repair_group'] for row in rows])
    if set(y) != {0, 1} or any(len(set(groups[y == label])) < folds for label in (0, 1)):
        raise ValueError('Both classes need enough independent groups for calibration')
    splits = list(StratifiedGroupKFold(folds, shuffle=True, random_state=42).split(np.zeros(len(y)), y, groups))
    for train, calibrate in splits:
        if set(groups[train]) & set(groups[calibrate]) or set(y[train]) != {0, 1} or set(y[calibrate]) != {0, 1}:
            raise ValueError('Leaking groups or absent calibration class')
    return splits


def inputs(rows, branch):
    return np.array([text_input(row['raw_text']) if branch == 'sms' else row['url'] for row in rows], dtype=object)


def fit_calibrated(estimator, rows, branch, folds=3):
    model = CalibratedClassifierCV(clone(estimator), method='sigmoid', cv=group_splits(rows, folds),
                                   ensemble=False, n_jobs=1)
    fit_params = {}
    if branch == 'sms':
        fit_params['classifier__sample_weight'] = np.array([
            3.0 if row.get('language') == 'vi' else 2.0 if row.get('human_verified_by_source') else 1.0
            for row in rows])
    model.fit(inputs(rows, branch), np.array([row['label'] for row in rows]), **fit_params)
    return model


def calibration_metrics(labels, scores):
    y, p = np.asarray(labels), np.asarray(scores, dtype=float)
    if not len(y) or len(y) != len(p) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Invalid probability predictions')
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(np.mean(bins == i) * abs(float(p[bins == i].mean() - y[bins == i].mean()))
              for i in range(10) if np.any(bins == i))
    return dict(rows=len(y), labels=dict(Counter(str(int(value)) for value in y)),
                brier=float(brier_score_loss(y, p)), log_loss=float(log_loss(y, p, labels=[0, 1])),
                ece_10_bins=float(ece))


def brier_delta_interval(rows, raw, calibrated):
    groups, membership = np.unique([row['repair_group'] for row in rows], return_inverse=True)
    labels = np.array([row['label'] for row in rows])
    delta = (np.asarray(calibrated) - labels) ** 2 - (np.asarray(raw) - labels) ** 2
    sums = np.bincount(membership, weights=delta)
    counts = np.bincount(membership)
    rng = np.random.default_rng(42)
    samples = []
    for _ in range(500):
        draw = rng.integers(0, len(groups), len(groups))
        samples.append(sums[draw].sum() / counts[draw].sum())
    return [float(value) for value in np.quantile(samples, [.025, .975])]


def fit(data, review, overrides_path, output, review_package):
    proof = verify(data)
    base = load_bundle()
    source_manifest = json.loads((ROOT / 'models/hybrid_manifest.json').read_text(encoding='utf-8'))
    review_rows = read_jsonl(review / 'ai_review.jsonl')
    identities = json.loads((review_package / 'identities.json').read_text(encoding='utf-8'))
    review_lookup = validate_review(review_rows, identities)
    excluded = {row['case_id'] for row in review_rows if row['quarantine_required']}
    overrides = json.loads(overrides_path.read_text(encoding='utf-8'))
    all_rows = read_jsonl(data / 'all_rows.jsonl')
    for row in all_rows:
        if row['case_id'] in review_lookup:
            expected = digest(row.get('raw_text') or row.get('url', ''))
            if (expected != review_lookup[row['case_id']]['input_sha256'] or row['partition'] != 'train'
                    or review_lookup[row['case_id']]['branch'] != ('sms' if row['cohort'] == 'processed_sms' else 'url')):
                raise ValueError('Review does not match the frozen training content')
            proposal = review_lookup[row['case_id']]['proposed_label']
            if proposal != 'unknown' and proposal != row['label'] and row['case_id'] not in overrides:
                excluded.add(row['case_id'])
    rows = candidate_training_rows(all_rows, excluded, overrides,
                                   {case: row['proposed_label'] for case, row in review_lookup.items()})
    output.mkdir(parents=True, exist_ok=False)
    protocol = dict(method='sigmoid', ensemble=False, outer_group_folds=3, inner_group_folds=3, seed=42,
                    brier_and_log_loss_must_not_increase=True, fit_partitions=['train'],
                    all_labels_expert_verified=False, new_independent_benchmark=False,
                    base_bundle_sha256=source_manifest['bundle_sha256'], fit_code_sha256=sha(Path(__file__), True),
                    review_sha256=sha(review / 'ai_review.jsonl'), user_decisions_sha256=sha(overrides_path),
                    review_package_identities_sha256=sha(review_package / 'identities.json'))
    write_json(output / 'protocol.json', protocol)
    (output / 'fit_code.py').write_bytes(Path(__file__).read_bytes())
    write_jsonl(output / 'fit_rows.jsonl', rows)
    started = time.perf_counter()
    candidate = {**base, 'training': dict(base['training'])}
    results, counts, provenance, fit_hashes = {}, {}, {}, {}
    for branch in ('sms', 'url'):
        branch_rows = [row for row in rows if (row['cohort'] == 'processed_sms') == (branch == 'sms')]
        counts[branch] = len(branch_rows)
        write_jsonl(output / f'{branch}_fit_rows.jsonl', branch_rows)
        fit_hashes[branch + '_train'] = sha(output / f'{branch}_fit_rows.jsonl')
        provenance[branch] = dict(Counter(row['label_provenance'] for row in branch_rows))
        raw_scores, calibrated_scores = np.zeros(len(branch_rows)), np.zeros(len(branch_rows))
        for fold, (train, heldout) in enumerate(group_splits(branch_rows)):
            print(f'{branch}: nested group fold {fold + 1}/3', flush=True)
            model = fit_calibrated(base[branch]['model'], [branch_rows[i] for i in train], branch)
            values = inputs([branch_rows[i] for i in heldout], branch)
            raw_scores[heldout] = probability(model.calibrated_classifiers_[0].estimator, values)
            calibrated_scores[heldout] = probability(model, values)
        labels = [row['label'] for row in branch_rows]
        before, after = calibration_metrics(labels, raw_scores), calibration_metrics(labels, calibrated_scores)
        passed = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
        results[branch] = dict(raw=before, calibrated=after, gate_pass=passed,
            brier_delta_group_bootstrap_95ci=brier_delta_interval(branch_rows, raw_scores, calibrated_scores))
        write_jsonl(output / f'{branch}_outer_predictions.jsonl', [dict(case_id=row['case_id'],
            repair_group=row['repair_group'], label=row['label'], raw_score=float(raw_scores[i]),
            calibrated_probability=float(calibrated_scores[i])) for i, row in enumerate(branch_rows)])
        print(f'{branch}: final source-label calibration on {len(branch_rows)} train rows', flush=True)
        model = fit_calibrated(base[branch]['model'], branch_rows, branch)
        candidate[branch] = {**base[branch], 'model': model.calibrated_classifiers_[0].estimator,
                             'probability_model': model, 'model_id': 'group-calibrated-20261026:' + branch}
    candidate['training'].update(run_id='group-calibrated-20261026', text_training_samples=counts['sms'],
        url_training_samples=counts['url'], training_manifest_sha256=sha(output / 'fit_rows.jsonl'),
        method='Supervised source-label heads with train-only nested-group sigmoid calibration',
        probability_calibrated=False, calibrated_estimate_available=True,
        calibrated_estimate_scope='source-label estimate; not expert-verified population fraud probability',
        all_labels_expert_verified=False, known_label_conflicts_fitted=0,
        heldout_or_quarantined_rows_fitted=0, label_provenance_counts=provenance,
        human_user_decisions=len(overrides), review_unknown_cases_excluded=len(excluded))
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL))
    report = dict(protocol=protocol, fit_rows=counts, label_provenance_counts=provenance, metrics=results,
                  gate_pass=all(result['gate_pass'] for result in results.values()), proof=proof,
                  expert_labels_created=0, historical_test_used_in_fit_or_gate=False,
                  new_independent_vietnamese_benchmark=False, seconds=round(time.perf_counter() - started, 3))
    write_json(output / 'calibration_report.json', report)
    manifest = {**source_manifest, 'bundle_sha256': sha(output / 'candidate_bundle.pkl'),
        'parent_artifact': {'bundle_sha256': source_manifest['bundle_sha256'],
                            'source_sha256': source_manifest['source_sha256'],
                            'dataset_files_sha256': source_manifest['dataset_files_sha256']},
        'source_sha256': fit_hashes,
        'dataset_files_sha256': {name: sha(output / name) for name in
            ('fit_rows.jsonl', 'sms_fit_rows.jsonl', 'url_fit_rows.jsonl', 'protocol.json')},
        'training': candidate['training'], 'fitted_rows': sum(counts.values()), 'test_evaluation_performed': False,
        'fit_code_sha256': protocol['fit_code_sha256'], 'fit_seconds': report['seconds'],
        'calibration_protocol_sha256': sha(output / 'protocol.json'),
        'calibration_report_sha256': sha(output / 'calibration_report.json'),
        'calibration_gate_pass': report['gate_pass']}
    if 'evaluation_sha256' in manifest:
        manifest['parent_artifact']['evaluation_sha256'] = manifest.pop('evaluation_sha256')
    write_json(output / 'candidate_manifest.json', manifest)
    print(json.dumps(report), flush=True)
    return report


def activate(output, data, review, overrides_path, review_package, models=None):
    models = models or ROOT / 'models'
    manifest = json.loads((output / 'candidate_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('calibration_gate_pass') is not True:
        raise ValueError('A passed calibration gate is required before activation')
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    report = json.loads((output / 'calibration_report.json').read_text(encoding='utf-8'))
    if (report.get('gate_pass') is not True or any(not report['metrics'][branch]['gate_pass'] for branch in ('sms', 'url'))
            or sha(output / 'candidate_bundle.pkl') != manifest['bundle_sha256']
            or sha(output / 'calibration_report.json') != manifest['calibration_report_sha256']
            or sha(output / 'protocol.json') != manifest['calibration_protocol_sha256']
            or sha(output / 'fit_code.py', True) != manifest['fit_code_sha256']
            or sha(review / 'ai_review.jsonl') != protocol['review_sha256']
            or sha(overrides_path) != protocol['user_decisions_sha256']
            or sha(review_package / 'identities.json') != protocol['review_package_identities_sha256']
            or sha(models / 'hybrid_bundle.pkl') != protocol['base_bundle_sha256']):
        raise ValueError('Candidate, source or calibration evidence binding mismatch')
    for name, expected in manifest['dataset_files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Fitted row export checksum mismatch')
    for branch in ('sms', 'url'):
        if sha(output / f'{branch}_fit_rows.jsonl') != manifest['source_sha256'][branch + '_train']:
            raise ValueError('Fitted branch export checksum mismatch')
    verify(data)
    source_rows = read_jsonl(data / 'all_rows.jsonl')
    source_lookup = {row['case_id']: row for row in source_rows}
    identities = json.loads((review_package / 'identities.json').read_text(encoding='utf-8'))
    reviewed = validate_review(read_jsonl(review / 'ai_review.jsonl'), identities)
    overrides = json.loads(overrides_path.read_text(encoding='utf-8'))
    excluded = {case for case, row in reviewed.items() if row['quarantine_required']
                or (row['proposed_label'] != source_lookup[case]['label'] and case not in overrides)}
    expected_rows = candidate_training_rows(source_rows, excluded, overrides,
                                           {case: row['proposed_label'] for case, row in reviewed.items()})
    fitted_rows = read_jsonl(output / 'fit_rows.jsonl')
    if fitted_rows != expected_rows or sha(output / 'fit_rows.jsonl') != manifest['training']['training_manifest_sha256']:
        raise ValueError('Candidate does not match reviewed eligible training rows')
    backup = output / 'previous_active'
    backup.mkdir(exist_ok=False)
    for name in ('hybrid_bundle.pkl', 'hybrid_manifest.json'):
        shutil.copy2(models / name, backup / name)
    for source, destination in [('candidate_bundle.pkl', 'hybrid_bundle.pkl'), ('candidate_manifest.json', 'hybrid_manifest.json')]:
        temporary = models / (destination + '.new')
        shutil.copy2(output / source, temporary)
        os.replace(temporary, models / destination)
    record = dict(activated=manifest['training']['run_id'], bundle_sha256=manifest['bundle_sha256'],
                  backup=str(backup), activation_code_sha256=sha(Path(__file__), True),
                  calibrated_estimate_scope='source labels; not independently expert-verified Vietnamese fraud risk')
    write_json(output / 'activation.json', record)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=OUTPUT)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--review-package', type=Path, default=ROOT / 'data/prepared/expert_review_2026-10-26')
    parser.add_argument('--user-decisions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()
    result = activate(args.output, args.data, args.review, args.user_decisions, args.review_package) if args.activate else \
        fit(args.data, args.review, args.user_decisions, args.output, args.review_package)
    if args.activate:
        print(json.dumps(result))
    elif not result['gate_pass']:
        raise SystemExit(2)
