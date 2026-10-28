"""Train a supervised confirmation head without adding raw SMS alerts."""
import argparse
import hashlib
import json
import pickle
import time
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from scipy.special import expit

from calibrate_supervised import group_splits, inputs, calibration_metrics
from conservative_sms import ConservativeSMS, CalibratedSMS, score_logits
from english_data_expansion import read_jsonl
from english_ham_training import OUT as PREVIOUS, verify
from english_sms_selection import training_weights, validate_rows
from english_sms_training import PARENT, HISTORICAL, historical_nonregression
from model_state import same_model_state
from predict import probability
from predict_hybrid import load_bundle
from smishx_training import export_rows
from train_repaired_hybrid import metrics
from vi_data_workflow import sha, write_json

ROOT=Path(__file__).resolve().parent
OUT=ROOT / 'data/prepared/conservative_sms_english_gate_2026-10-29'
RUN='sms-confirmation-english-20261029'
THRESHOLDS=(.30,.65,.80)
MIN_MARGIN=.05
ENGLISH_CONFIDENCE=.99
GRID=[dict(C=c,weak_weight=w,positive_weight=p,confirmation_shift=s)
      for c in [.05,1,4] for w in [0,.1,.5] for p in [4,16,64] for s in [.5,1,2,4]]
WEAK='source_feed_phishing_with_ai_template_scope_screen'


def cohort_metrics(rows,scores):
    return {lang:{str(t):metrics([r for r in rows if r['language']==lang],
        np.asarray(scores)[[i for i,r in enumerate(rows) if r['language']==lang]],t)
        for t in THRESHOLDS} for lang in ['en','vi']}


def choose(trials,baseline):
    if set(baseline)!={'en','vi'} or any(set(t['cohorts'])!=set(baseline) for t in trials):
        raise ValueError('Both language cohorts are required')
    eligible=[]
    for i,trial in enumerate(trials):
        if trial['positive_margin']>=MIN_MARGIN and all(trial['cohorts'][lang][str(t)]['confusion_matrix_tn_fp_fn_tp'][j] <=
               baseline[lang][str(t)]['confusion_matrix_tn_fp_fn_tp'][j]
               for lang in baseline for t in THRESHOLDS for j in [1,2]):
            eligible.append(i)
    def rank(i):
        matrices=[m['confusion_matrix_tn_fp_fn_tp'] for values in trials[i]['cohorts'].values() for m in values.values()]
        return (sum(m[1] for m in matrices),sum(m[2] for m in matrices),-trials[i]['positive_margin'],i)
    return min(eligible,key=rank) if eligible else None


def fit_head(parent,rows,config):
    selected=[r for r in rows if config['weak_weight'] or r['label_provenance']!=WEAK]
    if {r['label'] for r in selected}!={0,1}:
        raise ValueError('Both supervised target classes are required')
    model=clone(parent).set_params(classifier__C=config['C'])
    weights=training_weights(selected,config['weak_weight'])
    weights*=np.array([config['positive_weight'] if r['label']==1 else 1 for r in selected])
    model.fit(inputs(selected,'sms'),[r['label'] for r in selected],classifier__sample_weight=weights)
    # This confirmation-only intercept offset is selected from training OOF
    # predictions. The raw anchor cap and all application thresholds stay fixed.
    model.named_steps['classifier'].intercept_+=config.get('confirmation_shift',0.)
    return model


def fit_anchor(parent,rows,original_ids):
    return fit_head(parent,[r for r in rows if r['case_id'] in original_ids],
                    dict(C=1,weak_weight=1,positive_weight=1))


def fit_language(rows):
    # Training language metadata retains its source/AI provenance; no expert
    # verification is implied. Uncertain language always keeps the anchor score.
    model=Pipeline([('features',TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),max_features=5000)),
        ('classifier',LogisticRegression(C=1,class_weight='balanced',max_iter=1000,random_state=42))])
    model.fit(inputs(rows,'sms'),[int(r['language']=='en') for r in rows])
    return model


def cv_trials(parent,rows,original_ids):
    splits=group_splits(rows)
    anchor_scores=np.zeros(len(rows))
    english_scores=np.zeros(len(rows))
    for train,held in splits:
        model=fit_anchor(parent,[rows[i] for i in train],original_ids)
        anchor_scores[held]=probability(model,inputs([rows[i] for i in held],'sms'))
        language=fit_language([rows[i] for i in train])
        english_scores[held]=probability(language,inputs([rows[i] for i in held],'sms'))
    baseline=cohort_metrics(rows,anchor_scores)
    trials=[];predictions=[];previous=None;decisions=None
    labels=np.array([r['label'] for r in rows])
    for index,config in enumerate(GRID):
        key=(config['C'],config['weak_weight'],config['positive_weight'])
        if key!=previous:
            decisions=np.zeros(len(rows))
            for train,held in splits:
                model=fit_head(parent,[rows[i] for i in train],{**config,'confirmation_shift':0.})
                decisions[held]=model.decision_function(inputs([rows[i] for i in held],'sms'))
            previous=key
        confirmation=expit(decisions+config['confirmation_shift'])
        confirmation=np.where(english_scores>=ENGLISH_CONFIDENCE,confirmation,1.)
        score=np.minimum(anchor_scores,confirmation)
        margins=[float(np.min(confirmation[(labels==1)&(anchor_scores>=t)]-t))
                 for t in THRESHOLDS if np.any((labels==1)&(anchor_scores>=t))]
        trials.append(dict(config=config,cohorts=cohort_metrics(rows,score),positive_margin=min(margins,default=1.)))
        predictions.append(score)
        if (index+1)%40==0:print(f'  Training-only trials {index+1}/{len(GRID)}',flush=True)
    selected=choose(trials,baseline)
    return dict(baseline=baseline,trials=trials,selected_index=selected),predictions,anchor_scores


def sigmoid(rows,scores):
    model=LogisticRegression(C=1e6,max_iter=1000,random_state=42)
    model.fit(score_logits(scores),[r['label'] for r in rows])
    if model.coef_[0,0]<=0:
        raise ValueError('Calibration must preserve risk ordering')
    return model


def fit(output=OUT):
    if output.exists():raise ValueError('Use a new output; completed experiments are immutable')
    prior=verify(PREVIOUS)
    rows=read_jsonl(PREVIOUS / 'sms_fit_rows.jsonl');validate_rows(rows)
    origin=read_jsonl(PARENT / 'sms_fit_rows.jsonl')
    original_ids={r['case_id'] for r in origin}
    current={r['case_id']:r for r in rows}
    if any(case not in current for case in original_ids):raise ValueError('Anchor fitting membership changed')
    for row in origin:
        for field in ['raw_text','label','label_provenance']:
            if row[field]!=current[row['case_id']][field]:raise ValueError('Anchor source labels changed')
    parent=load_bundle()
    manifest=json.loads((ROOT / 'models/hybrid_manifest.json').read_text(encoding='utf8'))
    if sha(PARENT / 'sms_fit_rows.jsonl')!=manifest['source_sha256']['sms_train']:
        raise ValueError('Active anchor training source mismatch')
    splits=group_splits(rows)
    for train,held in splits:group_splits([rows[i] for i in train])
    output.mkdir(parents=True)
    (output / 'fit_code.py').write_bytes(Path(__file__).read_bytes())
    export_rows(output,'sms_fit_rows',rows)
    export_rows(output,'sms_fold_assignments',[dict(case_id=rows[i]['case_id'],repair_group=rows[i]['repair_group'],fold=fold)
        for fold,(_,held) in enumerate(splits) for i in held])
    protected=dict(prior['protected_inputs_sha256'])
    for path in [PREVIOUS/'sms_fit_rows.jsonl',PREVIOUS/'protocol.json',PREVIOUS/'candidate_manifest.json',
                 PARENT/'sms_fit_rows.jsonl',Path(__file__),ROOT/'conservative_sms.py']:
        protected[str(path.relative_to(ROOT))]=sha(path)
    protocol=dict(run_id=RUN,method='minimum of pinned SMS anchor and supervised confirmation',grid=GRID,
        rows=len(rows),groups=len({r['repair_group'] for r in rows}),original_anchor_rows=len(origin),
        outer_folds=3,inner_folds=3,seed=42,raw_thresholds=THRESHOLDS,
        minimum_confirmation_positive_margin=MIN_MARGIN,
        english_gate_threshold=ENGLISH_CONFIDENCE,
        language_gate_provenance='supervised prepared train language metadata; source/AI, not expert verified',
        selection='No extra per-language FP/FN at any raw threshold; min FP, min FN, max positive margin, grid order',
        calibration='Sigmoid on logit of selected inner OOF minimum scores; never in-sample predictions',
        raw_score_bound='candidate <= pinned parent for every input; unchanged URL head and routing',
        protected_inputs_sha256=protected,all_labels_expert_verified=False,
        historical_tests_used_for_selection=False,new_unlabeled_holdouts_scored=False,
        frozen_files_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()})
    write_json(output/'protocol.json',protocol);verify(output)
    started=time.perf_counter()
    raw=np.zeros(len(rows));calibrated=np.zeros(len(rows));anchor_oof=np.zeros(len(rows));outer=[]
    for fold,(train,held) in enumerate(splits):
        training=[rows[i] for i in train];validation=[rows[i] for i in held]
        print(f'Outer group fold {fold+1}/3: selecting on training groups only',flush=True)
        selection,predictions,_=cv_trials(parent['sms']['model'],training,original_ids)
        write_json(output/f'outer_{fold}_selection.json',selection)
        if selection['selected_index'] is None:raise ValueError('No training-only configuration preserves recall; no historical scoring')
        index=selection['selected_index'];config=GRID[index];outer.append(config)
        calibrator=sigmoid(training,predictions[index])
        anchor=fit_anchor(parent['sms']['model'],training,original_ids)
        support=fit_head(parent['sms']['model'],training,config)
        values=inputs(validation,'sms')
        anchor_oof[held]=probability(anchor,values)
        language=fit_language(training)
        raw[held]=probability(ConservativeSMS(anchor,support,language,ENGLISH_CONFIDENCE),values)
        calibrated[held]=probability(calibrator,score_logits(raw[held]))
    print('Final configuration: selecting on all labeled training groups',flush=True)
    selection,predictions,_=cv_trials(parent['sms']['model'],rows,original_ids)
    write_json(output/'final_selection.json',selection)
    if selection['selected_index'] is None:raise ValueError('No eligible final confirmation configuration')
    index=selection['selected_index'];config=GRID[index]
    calibrator=sigmoid(rows,predictions[index])
    confirmation=fit_head(parent['sms']['model'],rows,config)
    combined=ConservativeSMS(parent['sms']['model'],confirmation,fit_language(rows),ENGLISH_CONFIDENCE)
    candidate={**parent,'sms':{**parent['sms'],'model':combined,
        'probability_model':CalibratedSMS(combined,calibrator),'model_id':RUN+':sms'},'training':dict(parent['training'])}
    before=calibration_metrics([r['label'] for r in rows],raw)
    after=calibration_metrics([r['label'] for r in rows],calibrated)
    calibrated_pass=after['brier']<=before['brier'] and after['log_loss']<=before['log_loss']
    if not same_model_state(parent['url'],candidate['url']):raise ValueError('URL estimator changed')
    export_rows(output,'sms_oof_predictions',[dict(case_id=r['case_id'],label=r['label'],language=r['language'],
        repair_group=r['repair_group'],anchor_score=float(anchor_oof[i]),raw_score=float(raw[i]),
        calibrated_probability=float(calibrated[i])) for i,r in enumerate(rows)])
    oof=cohort_metrics(rows,raw);reference=cohort_metrics(rows,anchor_oof)
    outer_nonregression=all(historical_nonregression({lang:reference[lang][str(t)] for lang in reference},
        {lang:oof[lang][str(t)] for lang in oof}) for t in THRESHOLDS)
    candidate['training'].update(run_id=RUN,text_training_samples=len(rows),
        confirmation_loss_rows=sum(config['weak_weight']>0 or r['label_provenance']!=WEAK for r in rows),
        original_anchor_training_samples=len(origin),all_labels_expert_verified=False,
        method=protocol['method'],calibration_method=protocol['calibration'],
        language_gate_threshold=ENGLISH_CONFIDENCE,language_gate_provenance=protocol['language_gate_provenance'],
        training_manifest_sha256=sha(output/'protocol.json'),calibrated_estimate_available=bool(calibrated_pass),
        text_label_provenance='Inherited supervised labels with retained human, source and AI provenance')
    candidate['training']['label_provenance_counts']={**parent['training']['label_provenance_counts'],
        'sms':dict(Counter(r['label_provenance'] for r in rows))}
    (output/'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate,pickle.HIGHEST_PROTOCOL))
    report=dict(run_id=RUN,rows=len(rows),groups=protocol['groups'],final_config=config,outer_configs=outer,
        nested_oof=oof,nested_anchor_oof=reference,outer_nonregression_pass=bool(outer_nonregression),
        raw_calibration=before,calibrated=after,calibration_gate_pass=bool(calibrated_pass),
        raw_bound_violations=int(np.sum(raw>anchor_oof)),url_state_preserved=True,
        labels_are_source_mixture=True,independent_benchmark=False,fit_seconds=round(time.perf_counter()-started,3))
    write_json(output/'training_report.json',report)
    new_manifest={**manifest,'parent_artifact':manifest,'bundle_sha256':sha(output/'candidate_bundle.pkl'),
        'training':candidate['training'],'release_approved':False,'test_evaluation_performed':False,
        'head_model_ids':dict(sms=RUN+':sms',url=parent['url']['model_id']),
        'source_sha256':{**manifest['source_sha256'],'sms_train':sha(output/'sms_fit_rows.jsonl')},
        'calibration_gate_pass':bool(calibrated_pass and manifest['calibration_gate_pass']),
        'calibration_report_sha256':sha(output/'training_report.json'),
        'calibration_protocol_sha256':sha(output/'protocol.json'),'fit_code_sha256':sha(output/'fit_code.py'),
        'code_sha256':{**manifest['code_sha256'],**{name:hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for name in ['conservative_sms.py','predict.py']}},
        'fitted_rows':len(rows)+parent['training']['url_training_samples'],
        'dataset_files_sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    for key in ['evaluation_sha256','historical_nonregression_pass','all_policy_nonregression_pass']:
        new_manifest.pop(key,None)
    write_json(output/'candidate_manifest.json',new_manifest);verify(output)
    print(json.dumps(report),flush=True)


def evaluate(output=OUT):
    verify(output)
    manifest=json.loads((output/'candidate_manifest.json').read_text(encoding='utf8'))
    with (output/'evaluation.started').open('x',encoding='utf8') as stream:stream.write(manifest['bundle_sha256'])
    parent=load_bundle();candidate=pickle.loads((output/'candidate_bundle.pkl').read_bytes())
    cohorts={};violations=0
    for role in ['validation','test']:
        rows=read_jsonl(HISTORICAL/f'sms_{role}.jsonl');values=inputs(rows,'sms')
        predictions={name:probability(b['sms']['model'],values) for name,b in [('parent',parent),('candidate',candidate)]}
        violations+=int(np.sum(predictions['candidate']>predictions['parent']))
        for lang in ['en','vi']:
            indices=[i for i,r in enumerate(rows) if r['language']==lang]
            if not indices:continue
            subset=[rows[i] for i in indices]
            cohorts[role+'_'+lang]={str(t):{name:metrics(subset,scores[indices],t) for name,scores in predictions.items()}
                for t in THRESHOLDS}
        export_rows(output,'historical_'+role+'_predictions',[dict(case_id=r['case_id'],label=r['label'],language=r['language'],
            parent_score=float(predictions['parent'][i]),candidate_score=float(predictions['candidate'][i])) for i,r in enumerate(rows)])
    gates={str(t):historical_nonregression({k:v[str(t)]['parent'] for k,v in cohorts.items()},
        {k:v[str(t)]['candidate'] for k,v in cohorts.items()}) for t in THRESHOLDS}
    result=dict(run_id=RUN,cohorts=cohorts,raw_threshold_gates=gates,raw_bound_violations=violations,
        historical_nonregression_pass=gates['0.65'],all_policy_nonregression_pass=all(gates.values()),
        historical_tests_used_for_selection=False,historical_tests_reused=True,new_independent_benchmark=False,
        new_unlabeled_holdouts_scored=False,active_model_replaced=False,release_approved=False)
    write_json(output/'evaluation.json',result)
    manifest.update(test_evaluation_performed=True,evaluation_sha256=sha(output/'evaluation.json'),
        historical_nonregression_pass=gates['0.65'],all_policy_nonregression_pass=all(gates.values()))
    write_json(output/'candidate_manifest.json',manifest);verify(output)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['fit','evaluate','verify']);parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args();result={'fit':fit,'evaluate':evaluate,'verify':verify}[args.command](args.output)
    if args.command=='verify':print(json.dumps(dict(verified=True,run_id=result['run_id'])))
