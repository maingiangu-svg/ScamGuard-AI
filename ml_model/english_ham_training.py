"""Fit the frozen SMS configuration with admitted source-ham additions."""
import argparse
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import numpy as np

from calibrate_supervised import group_splits, inputs, calibration_metrics
from english_data_expansion import OUT as POSITIVE, domains, read_jsonl, require_train
from english_ham_expansion import OUT as DATA, BASE, verify as verify_data
from english_sms_selection import validate_rows, fit_probability
from english_sms_training import make_training_rows, historical_nonregression, HISTORICAL
from model_state import same_model_state
from predict import probability
from predict_hybrid import load_bundle
from round2_experiment import text_input
from smishx_training import export_rows
from train_repaired_hybrid import metrics
from vi_data_workflow import sha, write_json

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'data/prepared/english_ham_training_2026-10-29'
SELECTION = ROOT / 'data/prepared/english_sms_selection_2026-10-28/training_report.json'
RUN = 'english-ham-20261029'
CONFIG = dict(C=16, weak_weight=.5)
THRESHOLDS = (.30, .65, .80)


def validate_additions(base, added):
    require_train(added)
    for row in added:
        if (row.get('label') != 0 or row.get('source_label') != 'ham' or
            row.get('label_provenance') != 'uci_source_ham_proxy_not_expert_smishing_verdict' or
            row.get('original_partition') != 'train' or row.get('language') != 'en' or
            not np.isfinite(row.get('language_confidence', 0)) or row.get('language_confidence', 0) < .95 or
            row.get('expert_verified') is not False or row.get('human_verified') is not False or
            not row.get('group') or set(row.get('group_roles', [])) & {'test','validation','quarantine'}):
            raise ValueError('Only isolated, source-labeled English ham can be added')
    combined = base + added
    if (len({r['case_id'] for r in combined}) != len(combined) or
        len({text_input(r['raw_text']) for r in combined}) != len(combined)):
        raise ValueError('Repeated case identity or model input')


def diagnostic_gates(cohorts):
    if not cohorts:
        raise ValueError('Historical cohorts are required')
    return {str(t):historical_nonregression({k:v[str(t)]['parent'] for k,v in cohorts.items()},
        {k:v[str(t)]['candidate'] for k,v in cohorts.items()}) for t in THRESHOLDS}


def verify(output=OUT):
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf8'))
    for name, expected in protocol['protected_inputs_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Protected training input changed: ' + name)
    for name, expected in protocol['frozen_files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Frozen preparation changed: ' + name)
    manifest_path = output / 'candidate_manifest.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf8'))
        if sha(output / 'candidate_bundle.pkl') != manifest['bundle_sha256']:
            raise ValueError('Candidate weights changed')
        for name, expected in manifest['dataset_files_sha256'].items():
            if sha(output / name) != expected:
                raise ValueError('Candidate evidence changed: ' + name)
        if manifest.get('evaluation_sha256') and sha(output / 'evaluation.json') != manifest['evaluation_sha256']:
            raise ValueError('Historical evaluation changed')
    return protocol


def fit(output=OUT):
    if output.exists():
        raise ValueError('Use a new directory; never refit a completed experiment')
    verify_data()
    selection = json.loads(SELECTION.read_text(encoding='utf8'))
    if selection['final_selected'] != CONFIG:
        raise ValueError('Previous training-only configuration changed')
    parent = load_bundle()
    parent_manifest = json.loads((ROOT / 'models/hybrid_manifest.json').read_text(encoding='utf8'))
    base, added = read_jsonl(BASE), read_jsonl(DATA / 'sms_train_additions.jsonl')
    validate_rows(base); validate_additions(base, added)
    if len(base) != 4124 or len(added) != 62:
        raise ValueError('This frozen experiment requires 4,124 prior and 62 new rows')
    ordinary = domains()
    # Digit masking can merge text variants with different domain owners.
    positive_source = {r['source_record']:r for r in read_jsonl(POSITIVE / 'source_sms.jsonl')}
    variants = {}
    for row in base:
        if row.get('label_provenance') == 'source_feed_phishing_with_ai_template_scope_screen':
            variants[text_input(row['raw_text'])] = sorted({d for n in row['merged_source_records']
                for d in ordinary(positive_source[n]['raw_text'])})
    for row in added:
        variants[text_input(row['raw_text'])] = sorted({d for text in row['variant_texts'] for d in ordinary(text)})
    key_domains = lambda text: sorted(set(ordinary(text)) | set(variants.get(text_input(text), [])))
    rows = make_training_rows(base, added, key_domains)
    validate_rows(rows)
    splits = group_splits(rows)
    for train, held in splits:
        group_splits([rows[i] for i in train])  # Validate inner folds before fitting.
    output.mkdir(parents=True)
    export_rows(output, 'sms_fit_rows', rows)
    export_rows(output, 'sms_fold_assignments', [dict(case_id=rows[i]['case_id'], fold=fold,
        repair_group=rows[i]['repair_group']) for fold, (_, held) in enumerate(splits) for i in held])
    (output / 'fit_code.py').write_bytes(Path(__file__).read_bytes())
    data_protocol = json.loads((DATA / 'protocol.json').read_text(encoding='utf8'))
    protected = dict(data_protocol['protected_inputs_sha256'])
    paths = [DATA / 'protocol.json', DATA / 'final_report.json', DATA / 'sms_train_additions.jsonl',
        SELECTION, POSITIVE / 'source_sms.jsonl', POSITIVE / 'sms_validation_candidates.jsonl',
        POSITIVE / 'sms_test_candidates.jsonl', POSITIVE / 'url_source_review_pool.jsonl',
        HISTORICAL / 'sms_validation.jsonl', HISTORICAL / 'sms_test.jsonl']
    paths += [ROOT / name for name in ['english_ham_training.py', 'english_sms_training.py',
        'english_sms_selection.py', 'calibrate_supervised.py', 'model_state.py', 'predict.py',
        'round2_experiment.py', 'audit_vi_holdout.py', 'vi_data_workflow.py', 'external_training.py',
        'predict_hybrid.py', 'smishx_training.py', 'english_ham_expansion.py', 'english_data_expansion.py']]
    paths.append(ROOT / 'data/reference/external_2026-10-25/public_suffix_list.dat')
    for path in paths:
        protected[str(path.relative_to(ROOT))] = sha(path)
    protocol = dict(run_id=RUN, config=CONFIG, hyperparameters_retuned=False,
        rows=len(rows), groups=len({r['repair_group'] for r in rows}), new_negative_rows=len(added),
        languages=dict(Counter(r['language'] for r in rows)), labels=dict(Counter(str(r['label']) for r in rows)),
        label_provenance=dict(Counter(r['label_provenance'] for r in rows)),
        sample_weights='vi=3; source-human=2; NCSU weak source=0.5; remaining including UCI=1',
        outer_folds=3, inner_folds=3, seed=42, sms_threshold=.65, url_threshold=.5,
        diagnostic_thresholds=THRESHOLDS, similarity_threshold=.80,
        historical_tests_used_for_selection=False, new_unlabeled_holdouts_scored=False,
        all_labels_expert_verified=False, parent_bundle_sha256=parent_manifest['bundle_sha256'],
        protected_inputs_sha256=protected,
        frozen_files_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()})
    write_json(output / 'protocol.json', protocol)
    verify(output)
    started = time.perf_counter()
    raw, calibrated = np.zeros(len(rows)), np.zeros(len(rows))
    for fold, (train, held) in enumerate(splits):
        print(f'Nested grouped SMS fold {fold+1}/3', flush=True)
        model = fit_probability(parent['sms']['model'], [rows[i] for i in train], CONFIG)
        values = inputs([rows[i] for i in held], 'sms')
        raw[held] = probability(model.calibrated_classifiers_[0].estimator, values)
        calibrated[held] = probability(model, values)
    labels = [r['label'] for r in rows]
    before, after = calibration_metrics(labels, raw), calibration_metrics(labels, calibrated)
    calibration_pass = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    export_rows(output, 'sms_oof_predictions', [dict(case_id=r['case_id'], language=r['language'],
        label=r['label'], repair_group=r['repair_group'], raw_score=float(raw[i]),
        calibrated_probability=float(calibrated[i])) for i,r in enumerate(rows)])
    print(f'Final supervised fit on {len(rows)} rows', flush=True)
    model = fit_probability(parent['sms']['model'], rows, CONFIG)
    candidate = {**parent, 'sms':{**parent['sms'], 'model':model.calibrated_classifiers_[0].estimator,
        'probability_model':model, 'model_id':RUN+':sms'}, 'training':dict(parent['training'])}
    if not same_model_state(candidate['url'], parent['url']):
        raise ValueError('URL head changed')
    candidate['training'].update(run_id=RUN, text_training_samples=len(rows),
        method='Fixed previous training-only config; nested grouped sigmoid calibration; URL inherited',
        text_label_provenance='Historical mixed labels; NCSU feed phishing/AI scope screen; UCI source ham proxy',
        all_labels_expert_verified=False, new_english_training_samples=338+len(added),
        new_english_ham_training_samples=len(added), hyperparameters_retuned=False,
        training_manifest_sha256=sha(output / 'protocol.json'))
    candidate['training']['label_provenance_counts'] = {**parent['training']['label_provenance_counts'],
        'sms':protocol['label_provenance']}
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, pickle.HIGHEST_PROTOCOL))
    added_ids = {r['case_id'] for r in added}
    added_indices = [i for i,r in enumerate(rows) if r['case_id'] in added_ids]
    report = dict(run_id=RUN, rows=len(rows), groups=protocol['groups'], fixed_config=CONFIG,
        raw_calibration=before, calibrated=after, calibration_gate_pass=bool(calibration_pass),
        oof_classification=metrics(rows,raw,.65),
        oof_by_language={lang:metrics([r for r in rows if r['language']==lang],
            raw[[i for i,r in enumerate(rows) if r['language']==lang]],.65) for lang in ['en','vi']},
        new_ham_oof=metrics([rows[i] for i in added_indices], raw[added_indices],.65),
        source_label_metrics_not_expert_accuracy=True, independent_benchmark=False,
        url_state_preserved=True, fit_seconds=round(time.perf_counter()-started,3))
    write_json(output / 'training_report.json', report)
    manifest = {**parent_manifest, 'parent_artifact':parent_manifest, 'training':candidate['training'],
        'bundle_sha256':sha(output / 'candidate_bundle.pkl'), 'release_approved':False,
        'test_evaluation_performed':False, 'fitted_rows':len(rows)+parent['training']['url_training_samples'],
        'source_sha256':{**parent_manifest['source_sha256'], 'sms_train':sha(output / 'sms_fit_rows.jsonl')},
        'head_model_ids':dict(sms=RUN+':sms', url=parent['url']['model_id']),
        'calibration_gate_pass':bool(calibration_pass and parent_manifest['calibration_gate_pass']),
        'calibration_report_sha256':sha(output / 'training_report.json'),
        'calibration_protocol_sha256':sha(output / 'protocol.json'),
        'fit_code_sha256':sha(output / 'fit_code.py'), 'fit_seconds':report['fit_seconds'],
        'dataset_files_sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    for key in ['evaluation_sha256','historical_nonregression_pass','all_policy_nonregression_pass']:
        manifest.pop(key, None)
    write_json(output / 'candidate_manifest.json', manifest)
    verify(output)
    print(json.dumps(report), flush=True)


def evaluate(output=OUT):
    verify(output)
    manifest = json.loads((output / 'candidate_manifest.json').read_text(encoding='utf8'))
    # Exclusive creation rejects concurrent or repeated historical scoring.
    with (output / 'evaluation.started').open('x', encoding='utf8') as stream:
        stream.write(manifest['bundle_sha256'])
    parent = load_bundle()
    candidate = pickle.loads((output / 'candidate_bundle.pkl').read_bytes())
    cohorts = {}
    for role in ['validation','test']:
        rows = read_jsonl(HISTORICAL / f'sms_{role}.jsonl')
        values = inputs(rows,'sms')
        predictions = {name:probability(b['sms']['model'], values)
                       for name,b in [('parent',parent),('candidate',candidate)]}
        for lang in ['en','vi']:
            indices = [i for i,r in enumerate(rows) if r['language']==lang]
            if not indices:continue
            subset = [rows[i] for i in indices]
            cohorts[role+'_'+lang] = {str(t):{name:metrics(subset,scores[indices],t)
                for name,scores in predictions.items()} for t in THRESHOLDS}
        export_rows(output, 'historical_'+role+'_predictions', [dict(case_id=r['case_id'], language=r['language'],
            label=r['label'], parent_score=float(predictions['parent'][i]),
            candidate_score=float(predictions['candidate'][i])) for i,r in enumerate(rows)])
    gates = diagnostic_gates(cohorts)
    result = dict(run_id=RUN, bundle_sha256=manifest['bundle_sha256'], cohorts=cohorts,
        raw_threshold_gates=gates, historical_nonregression_pass=gates['0.65'],
        all_policy_nonregression_pass=all(gates.values()),
        policy_scope='Raw SMS diagnostic thresholds; not rounded full-app actions or independent URL review',
        historical_tests_reused=True, new_independent_benchmark=False,
        historical_tests_used_for_selection=False, new_unlabeled_holdouts_scored=False,
        active_model_replaced=False, release_approved=False)
    write_json(output / 'evaluation.json', result)
    manifest.update(test_evaluation_performed=True, evaluation_sha256=sha(output / 'evaluation.json'),
        historical_nonregression_pass=gates['0.65'], all_policy_nonregression_pass=all(gates.values()))
    write_json(output / 'candidate_manifest.json', manifest)
    write_json(output / 'release_decision.json', dict(run_id=RUN, disposition='not_activated',
        release_approved=False, historical_nonregression_pass=gates['0.65'],
        all_policy_nonregression_pass=all(gates.values()), calibration_gate_pass=manifest['calibration_gate_pass'],
        bundle_sha256=manifest['bundle_sha256'], evaluation_sha256=manifest['evaluation_sha256'],
        training_report_sha256=sha(output / 'training_report.json'), active_model_replaced=False))
    verify(output)
    print(json.dumps(result), flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['fit','evaluate','verify'])
    parser.add_argument('--output',type=Path,default=OUT)
    args = parser.parse_args()
    result = {'fit':fit,'evaluate':evaluate,'verify':verify}[args.command](args.output)
    if args.command=='verify':print(json.dumps(dict(verified=True,run_id=result['run_id'])))
