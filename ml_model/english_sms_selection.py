"""Select SMS regularization and weak-source weight using training groups only."""
import argparse
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV

from calibrate_supervised import group_splits, inputs, calibration_metrics
from english_data_expansion import require_train, read_jsonl
from english_sms_training import verify as verify_previous, historical_nonregression, HISTORICAL
from predict import probability
from predict_hybrid import load_bundle
from round2_experiment import text_input
from smishx_training import export_rows
from train_repaired_hybrid import metrics
from vi_data_workflow import sha, write_json

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT / 'data/prepared/english_sms_training_2026-10-28'
OUT = ROOT / 'data/prepared/english_sms_selection_2026-10-28'
RUN = 'english-selected-20261028'
GRID = [dict(C=c, weak_weight=w) for c in [.25,1,4,16] for w in [1,.5]]


def validate_rows(rows):
    require_train(rows)
    if not rows or any(r.get('original_partition')!='train' or not r.get('repair_group')
                       or not isinstance(r.get('raw_text'),str) or not r['raw_text'].strip() for r in rows):
        raise ValueError('Only traceable labeled training groups can be fitted')
    if len({r['case_id'] for r in rows})!=len(rows) or len({text_input(r['raw_text']) for r in rows})!=len(rows):
        raise ValueError('Repeated case or model input')


def training_weights(rows, weak_weight):
    return np.array([3. if r.get('language')=='vi' else 2. if r.get('human_verified_by_source')
        else weak_weight if r.get('label_provenance')=='source_feed_phishing_with_ai_template_scope_screen'
        else 1. for r in rows])


def select_config(trials):
    if 'c1_w1' not in trials:
        raise ValueError('The fixed baseline comparison is required')
    if any(set(t['cohorts'])!={'en','vi'} for t in trials.values()):
        raise ValueError('Both language cohorts are required for every trial')
    baseline=trials['c1_w1']['cohorts']
    eligible=[key for key,t in trials.items() if all(
        t['cohorts'][lang]['confusion_matrix_tn_fp_fn_tp'][1]<=baseline[lang]['confusion_matrix_tn_fp_fn_tp'][1]
        and t['cohorts'][lang]['confusion_matrix_tn_fp_fn_tp'][3]>=baseline[lang]['confusion_matrix_tn_fp_fn_tp'][3]
        for lang in ['en','vi'])]
    def rank(key):
        t=trials[key]; matrices=[m['confusion_matrix_tn_fp_fn_tp'] for m in t['cohorts'].values()]
        return (sum(m[1] for m in matrices),-sum(m[3] for m in matrices),t['review_fp'],
                t['config']['C'],t['config']['weak_weight'])
    return min(eligible,key=rank)


def estimator(parent, config):
    return clone(parent).set_params(classifier__C=config['C'])


def fit_raw(parent, rows, config):
    model=estimator(parent,config)
    model.fit(inputs(rows,'sms'),np.array([r['label'] for r in rows]),
              classifier__sample_weight=training_weights(rows,config['weak_weight']))
    return model


def fit_probability(parent, rows, config):
    model=CalibratedClassifierCV(estimator(parent,config),method='sigmoid',
        cv=group_splits(rows),ensemble=False,n_jobs=1)
    model.fit(inputs(rows,'sms'),np.array([r['label'] for r in rows]),
              classifier__sample_weight=training_weights(rows,config['weak_weight']))
    return model


def cohort_metrics(rows, scores):
    return {lang:metrics([r for r in rows if r['language']==lang],
        np.asarray(scores)[[i for i,r in enumerate(rows) if r['language']==lang]],.65)
        for lang in ['en','vi']}


def cv_trials(parent, rows):
    splits=group_splits(rows)
    trials={}
    for config in GRID:
        scores=np.zeros(len(rows))
        for train,held in splits:
            model=fit_raw(parent,[rows[i] for i in train],config)
            scores[held]=probability(model,inputs([rows[i] for i in held],'sms'))
        key=f"c{config['C']:g}_w{config['weak_weight']:g}"
        trials[key]=dict(config=config,cohorts=cohort_metrics(rows,scores),
                        review_fp=metrics(rows,scores,.30)['confusion_matrix_tn_fp_fn_tp'][1])
    return trials


def verify(output):
    protocol=json.loads((output/'protocol.json').read_text(encoding='utf-8'))
    for path,expected in protocol['protected_inputs_sha256'].items():
        if sha(ROOT/path)!=expected:raise ValueError('Protected input changed: '+path)
    if sha(output/'sms_fit_rows.jsonl')!=protocol['fit_rows_sha256'] or sha(output/'fit_code.py')!=protocol['code_sha256']:
        raise ValueError('Frozen fitting rows or source changed')
    return protocol


def fit(output=OUT):
    if output.exists():raise ValueError('Use a new directory; completed selections cannot be overwritten')
    old_protocol=verify_previous(PREVIOUS)
    manifest=json.loads((ROOT/'models/hybrid_manifest.json').read_text(encoding='utf-8'))
    parent=load_bundle(); rows=read_jsonl(PREVIOUS/'sms_fit_rows.jsonl'); validate_rows(rows)
    if parent['sms']['model'].get_params()['classifier__C']!=1:
        raise ValueError('This experiment requires the fixed C=1 serving parent')
    output.mkdir(parents=True)
    (output/'fit_code.py').write_bytes(Path(__file__).read_bytes())
    export_rows(output,'sms_fit_rows',rows)
    protected=dict(old_protocol['protected_inputs_sha256'])
    for path in [PREVIOUS/'sms_fit_rows.jsonl',PREVIOUS/'protocol.json', ROOT/'calibrate_supervised.py',
                 ROOT/'english_sms_training.py',ROOT/'round2_experiment.py']:
        protected[str(path.relative_to(ROOT))]=sha(path)
    protocol=dict(run_id=RUN,grid=GRID,outer_group_folds=3,inner_group_folds=3,seed=42,
        selection='Per-language FP <= baseline and TP >= baseline; minimize FP, maximize TP, minimize review FP, smaller C, smaller weak weight',
        fixed_sms_threshold=.65,fixed_review_threshold=.30,fixed_block_threshold=.80,
        fit_rows_sha256=sha(output/'sms_fit_rows.jsonl'),code_sha256=sha(output/'fit_code.py'),
        protected_inputs_sha256=protected,historical_tests_used_for_selection=False,
        new_unlabeled_holdouts_scored=False,all_labels_expert_verified=False)
    write_json(output/'protocol.json',protocol)
    started=time.perf_counter(); raw=np.zeros(len(rows)); calibrated=np.zeros(len(rows)); outer=[]
    for fold,(train,held) in enumerate(group_splits(rows)):
        subset=[rows[i] for i in train]
        print(f'Outer group fold {fold+1}/3: selecting on its training groups only',flush=True)
        trials=cv_trials(parent['sms']['model'],subset); key=select_config(trials); config=trials[key]['config']
        write_json(output/f'outer_{fold+1}_selection.json',dict(selected=key,trials=trials))
        model=fit_probability(parent['sms']['model'],subset,config); values=inputs([rows[i] for i in held],'sms')
        raw[held]=probability(model.calibrated_classifiers_[0].estimator,values)
        calibrated[held]=probability(model,values)
        outer.append(config)
        print(json.dumps(dict(fold=fold+1,selected=config)),flush=True)
    print('Selecting the final configuration on all training groups',flush=True)
    trials=cv_trials(parent['sms']['model'],rows); key=select_config(trials); config=trials[key]['config']
    write_json(output/'selection_frozen.json',dict(selected=key,config=config,trials=trials,
        protocol_sha256=sha(output/'protocol.json'),test_used=False))
    print(json.dumps(dict(final_selected=config)),flush=True)
    model=fit_probability(parent['sms']['model'],rows,config)
    candidate={**parent,'sms':{**parent['sms'],'model':model.calibrated_classifiers_[0].estimator,
        'probability_model':model,'model_id':RUN+':sms'},'training':dict(parent['training'])}
    labels=[r['label'] for r in rows]; before=calibration_metrics(labels,raw); after=calibration_metrics(labels,calibrated)
    passed=after['brier']<=before['brier'] and after['log_loss']<=before['log_loss']
    candidate['training'].update(run_id=RUN,text_training_samples=len(rows),method='Nested-group supervised SMS model selection; frozen URL head',
        training_manifest_sha256=sha(output/'protocol.json'),hyperparameters_retuned=True,
        selected_sms_configuration=config,new_english_training_samples=338,
        text_label_provenance='Mixed source/manual/AI/user labels plus feed-source English with AI template screening; not expert verified')
    candidate['training']['label_provenance_counts']={**parent['training']['label_provenance_counts'],
        'sms':dict(Counter(r['label_provenance'] for r in rows))}
    (output/'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate,pickle.HIGHEST_PROTOCOL))
    export_rows(output,'nested_oof_predictions',[dict(case_id=r['case_id'],label=r['label'],language=r['language'],
        repair_group=r['repair_group'],raw_score=float(raw[i]),calibrated_probability=float(calibrated[i])) for i,r in enumerate(rows)])
    report=dict(run_id=RUN,training_rows=len(rows),training_groups=len({r['repair_group'] for r in rows}),
        final_selected=config,outer_selected=outer,nested_oof=cohort_metrics(rows,raw),
        final_selection_cv=trials[key],baseline_selection_cv=trials['c1_w1'],
        raw_calibration=before,calibrated=after,calibration_gate_pass=bool(passed),
        nested_selection_estimate_not_independent_benchmark=True,fit_seconds=round(time.perf_counter()-started,3))
    write_json(output/'training_report.json',report)
    new_manifest={**manifest,'parent_artifact':manifest,'bundle_sha256':sha(output/'candidate_bundle.pkl'),
        'training':candidate['training'],'source_sha256':{**manifest['source_sha256'],'sms_train':sha(output/'sms_fit_rows.jsonl')},
        'head_model_ids':{'sms':RUN+':sms','url':parent['url']['model_id']},
        'calibration_gate_pass':bool(passed and manifest['calibration_gate_pass']),
        'calibration_report_sha256':sha(output/'training_report.json'),
        'calibration_protocol_sha256':sha(output/'protocol.json'),
        'fit_code_sha256':sha(output/'fit_code.py'),'fit_seconds':report['fit_seconds'],
        'test_evaluation_performed':False,'fitted_rows':len(rows)+parent['training']['url_training_samples'],
        'dataset_files_sha256':{p.name:sha(p) for p in output.glob('*') if p.is_file()}}
    new_manifest.pop('evaluation_sha256',None)
    write_json(output/'candidate_manifest.json',new_manifest);verify(output)
    print(json.dumps(report),flush=True)


def evaluate(output=OUT):
    verify(output)
    if (output/'evaluation.started').exists():raise ValueError('Historical diagnostics already evaluated; no repeated test tuning')
    manifest=json.loads((output/'candidate_manifest.json').read_text(encoding='utf-8'))
    if sha(output/'candidate_bundle.pkl')!=manifest['bundle_sha256']:raise ValueError('Candidate weights changed')
    for name,expected in manifest['dataset_files_sha256'].items():
        if sha(output/name)!=expected:raise ValueError('Selection evidence changed: '+name)
    (output/'evaluation.started').write_text(manifest['bundle_sha256'],encoding='utf-8')
    parent=load_bundle();candidate=pickle.loads((output/'candidate_bundle.pkl').read_bytes());cohorts={}
    for role in ['validation','test']:
        rows=read_jsonl(HISTORICAL/f'sms_{role}.jsonl');values=inputs(rows,'sms')
        predictions={name:probability(b['sms']['model'],values) for name,b in [('parent',parent),('candidate',candidate)]}
        for lang in ['en','vi']:
            indices=[i for i,r in enumerate(rows) if r['language']==lang]
            if not indices:continue
            subset=[rows[i] for i in indices]
            cohorts[role+'_'+lang]={str(t):{name:metrics(subset,scores[indices],t) for name,scores in predictions.items()}
                                   for t in [.30,.65,.80]}
        export_rows(output,'historical_'+role+'_predictions',[dict(case_id=r['case_id'],label=r['label'],language=r['language'],
            parent_score=float(predictions['parent'][i]),candidate_score=float(predictions['candidate'][i])) for i,r in enumerate(rows)])
    gates={threshold:historical_nonregression({k:v[threshold]['parent'] for k,v in cohorts.items()},
        {k:v[threshold]['candidate'] for k,v in cohorts.items()}) for threshold in ['0.3','0.65','0.8']}
    result=dict(run_id=RUN,cohorts=cohorts,threshold_gates=gates,historical_nonregression_pass=gates['0.65'],
        all_policy_nonregression_pass=all(gates.values()),new_independent_benchmark=False,
        historical_tests_used_for_selection=False,active_model_replaced=False,new_unlabeled_holdouts_scored=False)
    write_json(output/'evaluation.json',result)
    manifest.update(test_evaluation_performed=True,historical_evaluation_reused=True,
        evaluation_sha256=sha(output/'evaluation.json'),historical_nonregression_pass=result['historical_nonregression_pass'])
    write_json(output/'candidate_manifest.json',manifest);verify(output)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['fit','evaluate']);parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args();{'fit':fit,'evaluate':evaluate}[args.command](args.output)
