"""Select sparse supervised URL heads on training groups; preserve historical tests."""
import argparse
import json
import os
import pickle
import shutil
import time
from collections import Counter

import numpy as np
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from calibrate_supervised import calibration_metrics, fit_calibrated, group_splits
from modeling import url_matrix
from official_domain_training import OUT as PREVIOUS, checked_candidate, owner_roots, release_gate, verify_run
from predict import probability
from repair_training_data import ROOT, read_jsonl, sha, write_json, write_jsonl
from train_repaired_hybrid import metrics

OUT = ROOT / 'data/prepared/url_training_round2_2026-10-27'
RUN_ID = 'sparse-url-20261027'
CONFIGS = {'sparse_c1': 1.0, 'sparse_c4': 4.0, 'sparse_c16': 16.0}
DEPENDENCIES = ('url_model_selection.py', 'official_domain_training.py', 'calibrate_supervised.py',
                'modeling.py', 'preprocess.py', 'repair_training_data.py')


def candidate_model(name):
    if name not in CONFIGS:
        raise ValueError('Unknown frozen model configuration')
    return Pipeline([
        ('features', FeatureUnion([
            ('numeric', Pipeline([('extract', FunctionTransformer(url_matrix)), ('scale', StandardScaler())])),
            ('characters', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=20000,
                                          min_df=2, sublinear_tf=True, dtype=np.float64)),
        ])),
        ('classifier', LogisticRegression(C=CONFIGS[name], solver='liblinear', max_iter=1000, random_state=42)),
    ])


def choose_candidate(baseline, candidates):
    eligible = [name for name, result in candidates.items() if release_gate(baseline, result, True)]
    choices = eligible or list(candidates)
    if not choices:
        raise ValueError('No candidate results')
    winner = min(choices, key=lambda name: (-candidates[name]['f1'],
                 candidates[name]['confusion_matrix_tn_fp_fn_tp'][1], name))
    return winner, bool(eligible)


def validate_selection_rows(rows):
    seen, groups = set(), {}
    for row in rows:
        if (row['case_id'] in seen or row['partition'] != 'train' or row['original_partition'] != 'train'
                or row['do_not_train'] or row.get('repair_reasons')
                or type(row['label']) is not int or row['label'] not in (0, 1)):
            raise ValueError('Only unique accepted original training rows may enter selection')
        seen.add(row['case_id'])
        for root in owner_roots(row):
            if root in groups and groups[root] != row['repair_group']:
                raise ValueError('Owner domain split across selection groups')
            groups[root] = row['repair_group']


def verify_selection(output):
    protocol = verify_run(output)
    frozen = json.loads((output / 'selection_frozen.json').read_text(encoding='utf-8'))
    for name, expected in frozen.items():
        if sha(output / name) != expected:
            raise ValueError('Frozen selection evidence changed: ' + name)
    report = json.loads((output / 'selection.json').read_text(encoding='utf-8'))
    winner, passed = choose_candidate(report['reference'], report['candidates'])
    if report['winner'] != winner or report['gate_pass'] is not passed:
        raise ValueError('Selected candidate does not match the frozen comparison')
    return protocol, report


def select(output=OUT):
    previous_protocol, _ = checked_candidate(PREVIOUS)
    if sha(ROOT / 'models/hybrid_bundle.pkl') != previous_protocol['base_bundle_sha256']:
        raise ValueError('Active parent changed; this experiment requires a new protocol')
    rows = read_jsonl(PREVIOUS / 'url_fit_rows.jsonl')
    validate_selection_rows(rows)
    splits = group_splits(rows)
    output.mkdir(parents=True, exist_ok=False)
    names = ('parent_bundle.pkl', 'parent_manifest.json', 'seeds.json', 'seed_decisions.json',
             'fit_rows.jsonl', 'sms_fit_rows.jsonl', 'url_fit_rows.jsonl', 'url_test.jsonl')
    for name in names:
        shutil.copy2(PREVIOUS / name, output / name)
    membership = np.full(len(rows), -1)
    for fold, (_, heldout) in enumerate(splits):
        membership[heldout] = fold
    write_jsonl(output / 'selection_folds.jsonl', [dict(case_id=row['case_id'],
        repair_group=row['repair_group'], heldout_fold=int(membership[i])) for i, row in enumerate(rows)])
    names += ('selection_folds.jsonl',)
    protocol = dict(run_id=RUN_ID, base_bundle_sha256=previous_protocol['base_bundle_sha256'],
        code_sha256={name: sha(ROOT / name, True) for name in DEPENDENCIES},
        input_sha256={name: sha(output / name) for name in names},
        configurations=CONFIGS, vectorizer_features=20000, min_df=2, solver='liblinear',
        selection_group_folds=3, outer_group_folds=3, inner_group_folds=3, seed=42,
        method='sigmoid', url_threshold=.5, new_row_weight=1, sms_head_preserved=True,
        brier_and_log_loss_must_not_increase=True,
        release_max_false_positive_increase=0, release_max_true_positive_decrease=0,
        historical_tests_used_in_selection=False, threshold_selection_performed=False,
        expert_labels_created=0, holdout_rows_fitted=0, new_independent_benchmark=False)
    write_json(output / 'protocol.json', protocol)
    parent = pickle.loads((output / 'parent_bundle.pkl').read_bytes())
    results, files = {}, ['protocol.json']
    y = np.array([row['label'] for row in rows])
    urls = np.array([row['url'] for row in rows], dtype=object)
    for name in ['reference'] + list(CONFIGS):
        scores = np.zeros(len(rows))
        for fold, (train, heldout) in enumerate(splits):
            print(f'{name}: training-only owner-domain fold {fold + 1}/3', flush=True)
            model = clone(parent['url']['model']) if name == 'reference' else candidate_model(name)
            model.fit(urls[train], y[train])
            scores[heldout] = probability(model, urls[heldout])
        results[name] = metrics(rows, scores, .5)
        filename = name + '_selection_predictions.jsonl'
        write_jsonl(output / filename, [dict(case_id=r['case_id'], label=r['label'],
            score=float(p), heldout_fold=int(membership[i])) for i, (r, p) in enumerate(zip(rows, scores))])
        files.append(filename)
        print(json.dumps(dict(configuration=name, metrics=results[name])), flush=True)
    reference = results.pop('reference')
    winner, passed = choose_candidate(reference, results)
    report = dict(reference=reference, candidates=results, winner=winner, gate_pass=passed,
                  historical_test_used=False, selection_estimate_not_independent_accuracy=True)
    write_json(output / 'selection.json', report)
    files.append('selection.json')
    write_json(output / 'selection_frozen.json', {name: sha(output / name) for name in files})
    verify_selection(output)
    print(json.dumps(report), flush=True)


def fit(output=OUT):
    protocol, selection = verify_selection(output)
    if (output / 'candidate_bundle.pkl').exists() or (output / 'fit.started').exists():
        raise ValueError('Candidate fitting already started; no refitting after evaluation')
    (output / 'fit.started').write_text(selection['winner'], encoding='utf-8')
    rows = read_jsonl(output / 'url_fit_rows.jsonl')
    validate_selection_rows(rows)
    parent = pickle.loads((output / 'parent_bundle.pkl').read_bytes())
    parent_manifest = json.loads((output / 'parent_manifest.json').read_text(encoding='utf-8'))
    estimator = candidate_model(selection['winner'])
    started = time.perf_counter()
    raw, calibrated = np.zeros(len(rows)), np.zeros(len(rows))
    for fold, (train, heldout) in enumerate(group_splits(rows)):
        print(f'Selected {selection["winner"]}: nested calibration fold {fold + 1}/3', flush=True)
        model = fit_calibrated(estimator, [rows[i] for i in train], 'url')
        urls = [rows[i]['url'] for i in heldout]
        raw[heldout] = probability(model.calibrated_classifiers_[0].estimator, urls)
        calibrated[heldout] = probability(model, urls)
    labels = [row['label'] for row in rows]
    before, after = calibration_metrics(labels, raw), calibration_metrics(labels, calibrated)
    gate = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    write_jsonl(output / 'url_outer_predictions.jsonl', [dict(case_id=r['case_id'],
        repair_group=r['repair_group'], label=r['label'], raw_score=float(raw[i]),
        calibrated_probability=float(calibrated[i])) for i, r in enumerate(rows)])
    print(f'Final calibrated {selection["winner"]}: {len(rows)} URL rows', flush=True)
    model = fit_calibrated(estimator, rows, 'url')
    candidate = {**parent, 'url': {**parent['url'], 'model': model.calibrated_classifiers_[0].estimator,
        'probability_model': model, 'model_id': RUN_ID + ':url'}, 'training': dict(parent['training'])}
    provenance = dict(parent['training']['label_provenance_counts'])
    provenance['url'] = dict(Counter(row['label_provenance'] for row in rows))
    decisions = json.loads((output / 'seed_decisions.json').read_text(encoding='utf-8'))
    candidate['training'].update(run_id=RUN_ID, url_training_samples=len(rows),
        training_manifest_sha256=sha(output / 'fit_rows.jsonl'),
        method='Training-group-selected sparse supervised URL head with grouped sigmoid calibration; SMS inherited',
        url_label_provenance='Inherited source labels plus first-party URL seeds reviewed by AI; not expert verified',
        label_provenance_counts=provenance, official_url_seed_samples=sum(d['status'] == 'added' for d in decisions),
        official_url_reserved_domains=[d['domain'] for d in decisions if d['status'] == 'reserved_domain'],
        hyperparameters_retuned=True, selection_used_historical_test=False,
        selected_url_configuration=selection['winner'])
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL))
    report = dict(raw=before, calibrated=after, gate_pass=bool(gate), sms_gate_inherited=True,
        sms_parent_calibration_report_sha256=parent_manifest['calibration_report_sha256'],
        configuration_selection_bias_possible=True, seconds=round(time.perf_counter() - started, 3))
    write_json(output / 'calibration_report.json', report)
    names = list(protocol['input_sha256']) + ['selection.json', 'selection_frozen.json']
    manifest = {**parent_manifest, 'parent_artifact': parent_manifest,
        'bundle_sha256': sha(output / 'candidate_bundle.pkl'), 'training': candidate['training'],
        'source_sha256': {branch + '_train': sha(output / f'{branch}_fit_rows.jsonl') for branch in ('sms', 'url')},
        'dataset_files_sha256': {name: sha(output / name) for name in names},
        'fitted_rows': len(read_jsonl(output / 'fit_rows.jsonl')), 'test_evaluation_performed': False,
        'fit_code_sha256': sha(ROOT / 'url_model_selection.py', True), 'fit_seconds': report['seconds'],
        'calibration_protocol_sha256': sha(output / 'protocol.json'),
        'calibration_report_sha256': sha(output / 'calibration_report.json'),
        'calibration_gate_pass': bool(gate and parent_manifest['calibration_gate_pass']),
        'selection_gate_pass': selection['gate_pass']}
    write_json(output / 'candidate_manifest.json', manifest)
    checked_candidate(output)
    print(json.dumps(report), flush=True)


def activate(output=OUT, models=None):
    models = models or ROOT / 'models'
    protocol, selection = verify_selection(output)
    _, manifest = checked_candidate(output)
    report = json.loads((output / 'evaluation.json').read_text(encoding='utf-8'))
    calibration = json.loads((output / 'calibration_report.json').read_text(encoding='utf-8'))
    if (not selection['gate_pass'] or manifest['selection_gate_pass'] is not True
            or not manifest['calibration_gate_pass'] or not calibration['gate_pass']
            or sha(output / 'evaluation.json') != manifest['evaluation_sha256']
            or report['bundle_sha256'] != manifest['bundle_sha256']
            or report['protocol_sha256'] != manifest['calibration_protocol_sha256']
            or not report['release_gate_pass']
            or not release_gate(report['metrics']['baseline'], report['metrics']['candidate'], True)
            or sha(models / 'hybrid_bundle.pkl') != protocol['base_bundle_sha256']
            or sha(models / 'hybrid_manifest.json') != protocol['input_sha256']['parent_manifest.json']):
        raise ValueError('Selection/calibration/release gate failed or evidence/parent changed')
    backup = output / 'previous_active'
    backup.mkdir(exist_ok=False)
    for name in ('hybrid_bundle.pkl', 'hybrid_manifest.json'):
        shutil.copy2(models / name, backup / name)
    for source, destination in [('candidate_bundle.pkl', 'hybrid_bundle.pkl'),
                                ('candidate_manifest.json', 'hybrid_manifest.json')]:
        temporary = models / (destination + '.tmp')
        shutil.copy2(output / source, temporary)
        os.replace(temporary, models / destination)
    record = dict(activated=RUN_ID, bundle_sha256=manifest['bundle_sha256'], backup=str(backup))
    write_json(output / 'activation.json', record)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    from official_domain_training import evaluate

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('select', 'fit', 'evaluate', 'activate'))
    parser.add_argument('--output', type=type(OUT), default=OUT)
    args = parser.parse_args()
    {'select': select, 'fit': fit, 'evaluate': evaluate, 'activate': activate}[args.command](args.output)
