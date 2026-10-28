"""Train an isolated supervised SMS candidate; retain the complete serving URL head."""
import argparse
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import numpy as np

from audit_vi_holdout import similarity_edges, template_signature
from calibrate_supervised import fit_calibrated, group_splits, inputs, calibration_metrics
from english_data_expansion import OUT as DATA, domains, digest, read_jsonl, require_train
from predict import probability
from predict_hybrid import load_bundle
from smishx_training import export_rows
from train_repaired_hybrid import metrics
from vi_data_workflow import audit_rows, sha, write_json

ROOT = Path(__file__).resolve().parent
PARENT = ROOT / 'data/prepared/url_regression_repair_final_2026-10-27'
HISTORICAL = ROOT / 'data/prepared/repaired_training_2026-10-26-icann'
OUT = ROOT / 'data/prepared/english_sms_training_2026-10-28'
RUN = 'english-sms-20261028'


def make_training_rows(base, additions, domain_keys):
    rows = base + additions
    require_train(rows)
    if len({r['case_id'] for r in rows}) != len(rows) or any(r.get('original_partition') != 'train' for r in rows):
        raise ValueError('Repeated identity or non-training source role')
    edges, previous = [], {}
    for i, row in enumerate(rows):
        key = ('base:' + row['repair_group'] if i < len(base) else
               'addition:' + row.get('group', row.get('repair_group', row['case_id'])))
        if key in previous:
            edges.append((previous[key], i))
        previous[key] = i
    signatures = [template_signature(r['raw_text']) for r in rows]
    edges.extend((a,b) for a,b,score in similarity_edges(signatures, signatures, .80) if a < b)
    grouped = audit_rows([dict(r, role='train', previous_repair_group=r.get('repair_group'),
                               previous_expansion_group=r.get('group')) for r in rows], [], domain_keys, edges)
    return [dict(r, repair_group=r['group']) for r in grouped]


def historical_nonregression(before, after):
    if before.keys() != after.keys():
        return False
    return all(after[k]['confusion_matrix_tn_fp_fn_tp'][1] <= before[k]['confusion_matrix_tn_fp_fn_tp'][1]
               and after[k]['confusion_matrix_tn_fp_fn_tp'][2] <= before[k]['confusion_matrix_tn_fp_fn_tp'][2]
               for k in before)


def verify(output):
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    for path, expected in protocol['protected_inputs_sha256'].items():
        if sha(ROOT / path) != expected:
            raise ValueError('Protected source/parent changed: '+path)
    if sha(output / 'sms_fit_rows.jsonl') != protocol['fit_rows_sha256']:
        raise ValueError('Frozen fitting rows changed')
    if sha(output / 'fit_code.py') != protocol['fit_code_sha256']:
        raise ValueError('Frozen fit code changed')
    return protocol


def fit(output=OUT):
    if output.exists():
        raise ValueError('Use a new experiment directory; never refit a completed run')
    expansion = json.loads((DATA / 'final_report.json').read_text(encoding='utf-8'))
    for name, expected in expansion['files_sha256'].items():
        if sha(DATA / name) != expected:
            raise ValueError('Expansion data binding mismatch: '+name)
    manifest = json.loads((ROOT / 'models/hybrid_manifest.json').read_text(encoding='utf-8'))
    if sha(PARENT / 'sms_fit_rows.jsonl') != manifest['source_sha256']['sms_train']:
        raise ValueError('The active parent no longer matches the expected SMS fitting export')
    base = load_bundle()
    base_rows = read_jsonl(PARENT / 'sms_fit_rows.jsonl')
    added = read_jsonl(DATA / 'sms_train_additions.jsonl')
    if len(added) != expansion['added_positive']:
        raise ValueError('Unexpected addition membership')
    source_rows = {r['source_record']:r for r in read_jsonl(DATA / 'source_sms.jsonl')}
    ordinary_domains = domains()
    variants = {r['raw_text']:sorted({d for n in r['merged_source_records']
        for d in ordinary_domains(source_rows[n]['raw_text'])}) for r in added}
    key_domains = lambda text: sorted(set(ordinary_domains(text)) | set(variants.get(text, [])))
    rows = make_training_rows(base_rows, added, key_domains)
    output.mkdir(parents=True)
    export_rows(output, 'sms_fit_rows', rows)
    (output / 'fit_code.py').write_bytes(Path(__file__).read_bytes())
    protected = [ROOT / 'models/hybrid_bundle.pkl', ROOT / 'models/hybrid_manifest.json',
        PARENT / 'sms_fit_rows.jsonl', DATA / 'sms_train_additions.jsonl', DATA / 'final_report.json',
        DATA / 'sms_validation_candidates.jsonl', DATA / 'sms_test_candidates.jsonl',
        DATA / 'url_source_review_pool.jsonl', HISTORICAL / 'sms_validation.jsonl', HISTORICAL / 'sms_test.jsonl']
    protocol = dict(run_id=RUN, method='Fixed parent SMS estimator; nested grouped sigmoid calibration; URL inherited',
        training_rows=len(rows), new_english_rows=len(added), languages=dict(Counter(r['language'] for r in rows)),
        labels=dict(Counter(str(r['label']) for r in rows)), groups=len({r['repair_group'] for r in rows}),
        provenance=dict(Counter(r['label_provenance'] for r in rows)), outer_folds=3, inner_folds=3,
        seed=42, similarity_threshold=.80, sms_threshold=.65, url_threshold=.50,
        sample_weights='Vietnamese 3; source-human 2; remaining source/AI 1, unchanged',
        hyperparameters_retuned=False, new_unlabeled_holdouts_scored=False,
        historical_evaluation='reused diagnostics only; never model/threshold selection',
        independent_campaigns_proven=False, all_labels_expert_verified=False,
        fit_rows_sha256=sha(output / 'sms_fit_rows.jsonl'), fit_code_sha256=sha(output / 'fit_code.py'),
        parent_bundle_sha256=manifest['bundle_sha256'],
        protected_inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in protected})
    write_json(output / 'protocol.json', protocol)
    started = time.perf_counter()
    raw, calibrated = np.zeros(len(rows)), np.zeros(len(rows))
    for fold, (train, held) in enumerate(group_splits(rows)):
        print(f'SMS nested group fold {fold+1}/3', flush=True)
        model = fit_calibrated(base['sms']['model'], [rows[i] for i in train], 'sms')
        values = inputs([rows[i] for i in held], 'sms')
        raw[held] = probability(model.calibrated_classifiers_[0].estimator, values)
        calibrated[held] = probability(model, values)
    labels = [r['label'] for r in rows]
    before, after = calibration_metrics(labels,raw), calibration_metrics(labels,calibrated)
    calibration_pass = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    export_rows(output, 'sms_oof_predictions', [dict(case_id=r['case_id'], label=r['label'],
        repair_group=r['repair_group'], raw_score=float(raw[i]), calibrated_probability=float(calibrated[i]))
        for i,r in enumerate(rows)])
    print(f'Final supervised SMS fit on {len(rows)} labeled training rows', flush=True)
    model = fit_calibrated(base['sms']['model'], rows, 'sms')
    candidate = {**base, 'sms':{**base['sms'], 'model':model.calibrated_classifiers_[0].estimator,
        'probability_model':model, 'model_id':RUN+':sms'}, 'training':dict(base['training'])}
    url_unchanged = pickle.dumps(candidate['url']) == pickle.dumps(base['url'])
    if not url_unchanged:
        raise ValueError('URL head changed during SMS-only fitting')
    candidate['training'].update(run_id=RUN, text_training_samples=len(rows),
        text_label_provenance='Existing mixed labels plus source feed phishing with AI template scope screen; not expert verified',
        method=protocol['method'], training_manifest_sha256=sha(output / 'protocol.json'),
        all_labels_expert_verified=False, hyperparameters_retuned=False,
        new_english_training_samples=len(added))
    candidate['training']['label_provenance_counts']={**base['training']['label_provenance_counts'], 'sms':protocol['provenance']}
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate,pickle.HIGHEST_PROTOCOL))
    report = dict(run_id=RUN, rows=len(rows), groups=protocol['groups'], raw=before, calibrated=after,
        calibration_gate_pass=bool(calibration_pass), oof_classification=metrics(rows,raw,.65),
        oof_by_language={lang:metrics([r for r in rows if r['language']==lang],
            raw[[i for i,r in enumerate(rows) if r['language']==lang]],.65) for lang in ['en','vi']},
        url_head_unchanged=url_unchanged, source_label_metrics_not_expert_accuracy=True,
        fit_seconds=round(time.perf_counter()-started,3))
    write_json(output / 'training_report.json', report)
    candidate_manifest = {**manifest, 'parent_artifact':manifest,
        'bundle_sha256':sha(output / 'candidate_bundle.pkl'), 'training':candidate['training'],
        'source_sha256':{**manifest['source_sha256'],'sms_train':sha(output / 'sms_fit_rows.jsonl')},
        'dataset_files_sha256':{name:sha(output / name) for name in ['sms_fit_rows.jsonl','sms_oof_predictions.jsonl','protocol.json','training_report.json']},
        'head_model_ids':{'sms':RUN+':sms','url':base['url']['model_id']},
        'calibration_gate_pass':bool(calibration_pass and manifest['calibration_gate_pass']),
        'fitted_rows':len(rows)+base['training']['url_training_samples'], 'test_evaluation_performed':False,
        'fit_code_sha256':sha(output / 'fit_code.py'), 'fit_seconds':report['fit_seconds'],
        'calibration_report_sha256':sha(output / 'training_report.json'),
        'calibration_protocol_sha256':sha(output / 'protocol.json')}
    candidate_manifest.pop('evaluation_sha256',None)
    write_json(output / 'candidate_manifest.json', candidate_manifest)
    verify(output)
    print(json.dumps(report),flush=True)


def evaluate(output=OUT):
    verify(output)
    if (output / 'evaluation.started').exists():
        raise ValueError('Historical evaluation already used; no repeated test tuning')
    manifest = json.loads((output / 'candidate_manifest.json').read_text(encoding='utf-8'))
    if sha(output / 'candidate_bundle.pkl') != manifest['bundle_sha256']:
        raise ValueError('Candidate weights changed')
    for name, expected in manifest['dataset_files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Candidate evidence changed')
    (output / 'evaluation.started').write_text(manifest['bundle_sha256'],encoding='utf-8')
    candidate = pickle.loads((output / 'candidate_bundle.pkl').read_bytes())
    parent = load_bundle()
    before, after, all_metrics = {}, {}, {}
    for role in ['validation','test']:
        rows = read_jsonl(HISTORICAL / ('sms_'+role+'.jsonl'))
        values = inputs(rows,'sms')
        predictions={name:probability(bundle['sms']['model'],values) for name,bundle in [('parent',parent),('candidate',candidate)]}
        for lang in ['en','vi']:
            indices=[i for i,r in enumerate(rows) if r['language']==lang]
            if not indices:
                continue
            subset=[rows[i] for i in indices]; key=role+'_'+lang
            before[key]=metrics(subset,predictions['parent'][indices],.65)
            after[key]=metrics(subset,predictions['candidate'][indices],.65)
            all_metrics[key]={'parent':before[key],'candidate':after[key],
                'review_policy_30':{name:metrics(subset,scores[indices],.30) for name,scores in predictions.items()},
                'block_policy_80':{name:metrics(subset,scores[indices],.80) for name,scores in predictions.items()}}
        export_rows(output, 'historical_'+role+'_predictions', [dict(case_id=r['case_id'],language=r['language'],
            label=r['label'],parent_score=float(predictions['parent'][i]),candidate_score=float(predictions['candidate'][i]))
            for i,r in enumerate(rows)])
    result=dict(run_id=RUN, bundle_sha256=manifest['bundle_sha256'], historical_diagnostics=all_metrics,
        historical_nonregression_pass=historical_nonregression(before,after),
        calibration_gate_pass=manifest['calibration_gate_pass'], new_independent_benchmark=False,
        new_unlabeled_holdouts_scored=False, active_model_replaced=False,
        all_labels_expert_verified=False)
    write_json(output / 'evaluation.json',result)
    verify(output)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['fit','evaluate'])
    parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    {'fit':fit,'evaluate':evaluate}[args.command](args.output)
