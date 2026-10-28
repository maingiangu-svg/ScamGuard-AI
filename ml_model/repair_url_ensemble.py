"""Fit and verify a supervised residual URL gate without fitting serving-test examples."""
import argparse
import hashlib
import json
import os
import pickle
import shutil
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from accuracy_target_training import OUT as PRIMARY, SOURCE_SHA, classification_metrics, verify_candidate as verify_primary
from audit_training_integrity import url_quality_flags
from calibrate_supervised import calibration_metrics
from data_quality import prepare_urls
from external_training import REF, PINS, RegisteredDomains
from predict import probability
from repair_training_data import ROOT, read_jsonl, sha, write_json, write_jsonl
from url_ensemble import GatedURLClassifier

OUT = ROOT / 'data/prepared/url_regression_repair_2026-10-27'
PARENT_FIT = ROOT / 'data/prepared/calibrated_candidate_2026-10-26_r2'
RUN_ID = 'url-ensemble-20261027'


def prepare(output=OUT):
    verify_primary(PRIMARY)
    source = ROOT / 'data/phishing_site_urls.csv'
    if sha(source) != SOURCE_SHA or sha(REF / 'public_suffix_list.dat') != PINS['public_suffix_list.dat']:
        raise ValueError('Pinned source/PSL mismatch')
    domain = RegisteredDomains((REF / 'public_suffix_list.dat').read_text(encoding='utf-8').split('// ===BEGIN PRIVATE DOMAINS===')[0])
    prior = json.loads((PRIMARY / 'data_frozen.json').read_text(encoding='utf-8'))
    excluded = {'qi.lv', 'belgium.be', 'sunwin.org.vc'}
    for name in prior['inputs_sha256']:
        path = ROOT / name
        if path.suffix == '.jsonl':
            for row in read_jsonl(path):
                hosts = row.get('roots', []) + row.get('icann_roots', []) + row.get('registrable_domains', [])
                if row.get('url'):
                    hosts.append(urlsplit(row['url']).hostname)
                excluded.update(domain(h) for h in hosts if h)
        elif path.name == 'urls_preprocessed.csv':
            excluded.update(domain(urlsplit(u).hostname) for u in pd.read_csv(path, usecols=['url']).url)
        elif path.name == 'smishing_preprocessed.csv':
            for links in pd.read_csv(path, usecols=['urls_json']).urls_json:
                excluded.update(domain(urlsplit(u).hostname) for u in json.loads(links))
    for name in ('url_fit_rows.jsonl', 'fresh_test.jsonl', 'url_test.jsonl'):
        excluded.update(domain(urlsplit(r['url']).hostname) for r in read_jsonl(PRIMARY / name))
    decisions = json.loads((PRIMARY / 'seed_decisions.json').read_text(encoding='utf-8'))
    excluded.update(s['domain'] for s in decisions)
    print('Reserving disjoint calibration and new test owners from the pinned source.', flush=True)
    clean, _, source_audit = prepare_urls(pd.read_csv(source, dtype=str, keep_default_na=False))
    clean['owner'] = clean.host.map(domain)
    clean = clean[~clean.owner.isin(excluded)]
    clean = clean[~clean.url.map(lambda u: bool(url_quality_flags(u)))].copy()
    clean['rank'] = clean.url.map(lambda u: hashlib.sha256(u.encode()).hexdigest())
    clean = clean.sort_values('rank').groupby('owner', sort=False).head(10)
    clean['slot'] = clean.owner.map(lambda d: int(hashlib.sha256(('url-ensemble-v1:' + d).encode()).hexdigest()[:8], 16) % 5)
    output.mkdir(parents=True, exist_ok=False)
    counts = {}
    for slot, (name, limit) in enumerate((('fresh_test', 4000), ('calibration_train', 3000), ('calibration_validation', 3000))):
        selected = clean[clean.slot == slot].head(limit)
        if len(selected) < 1000 or set(selected.label.astype(int)) != {0, 1}:
            raise ValueError('Insufficient disjoint labeled source groups for ' + name)
        role = 'test' if slot == 0 else 'train' if slot == 1 else 'validation'
        rows = [dict(case_id='REPAIR95-' + str(r['source_record']), url=r['url'], label=int(r['label']),
            original_label=r['original_label'], source_record=int(r['source_record']), source_sha256=SOURCE_SHA,
            expert_verified=False, label_provenance='inherited_url_source_not_expert_verified',
            partition=role, original_partition=role, do_not_train=role != 'train', stage=name,
            roots=[r['owner']], icann_roots=[r['owner']], repair_group='REPAIR95-G-' + r['owner'])
            for r in selected.to_dict('records')]
        write_jsonl(output / (name + '.jsonl'), rows)
        counts[name] = dict(rows=len(rows), labels=dict(Counter(str(r['label']) for r in rows)),
                            owners=len({r['roots'][0] for r in rows}))
    write_json(output / 'data_frozen.json', dict(counts=counts, excluded_owners=len(excluded),
        source_audit=source_audit, source_sha256=SOURCE_SHA, psl_sha256=PINS['public_suffix_list.dat'],
        primary_data_manifest_sha256=sha(PRIMARY / 'data_frozen.json'),
        files_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps(counts), flush=True)


def verify_data(output):
    verify_primary(PRIMARY)
    data = json.loads((output / 'data_frozen.json').read_text(encoding='utf-8'))
    if sha(PRIMARY / 'data_frozen.json') != data['primary_data_manifest_sha256']:
        raise ValueError('Primary data identity changed')
    for name, expected in data['files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Reserved data changed: ' + name)
    return data


def fit(output=OUT):
    verify_data(output)
    started = time.perf_counter()
    with (output / 'fit.started').open('x', encoding='utf-8') as claim:
        claim.write(RUN_ID)
    base = pickle.loads((PRIMARY / 'parent_bundle.pkl').read_bytes())
    character = pickle.loads((PRIMARY / 'candidate_bundle.pkl').read_bytes())
    parent_manifest = json.loads((PRIMARY / 'parent_manifest.json').read_text(encoding='utf-8'))
    for branch in ('sms', 'url'):
        if sha(PARENT_FIT / f'{branch}_fit_rows.jsonl') != parent_manifest['source_sha256'][branch + '_train']:
            raise ValueError('Parent fitted-row checksum mismatch')
    parent_rows = read_jsonl(PARENT_FIT / 'url_fit_rows.jsonl')
    parent_ids = {r['case_id']: r for r in parent_rows}
    parent_owners = {owner for row in parent_rows for owner in row['icann_roots']}
    old_oof = {r['case_id']: r for r in read_jsonl(PARENT_FIT / 'url_outer_predictions.jsonl')}
    if old_oof.keys() != parent_ids.keys():
        raise ValueError('Parent OOF membership mismatch')
    for case, row in old_oof.items():
        if row['label'] != parent_ids[case]['label'] or row['repair_group'] != parent_ids[case]['repair_group']:
            raise ValueError('Parent OOF label/group identity mismatch')
    all_rows = read_jsonl(PRIMARY / 'url_fit_rows.jsonl')
    primary_oof = {r['case_id']: r for r in read_jsonl(PRIMARY / 'wide_lr_c4_selection_predictions.jsonl')}
    if primary_oof.keys() != {r['case_id'] for r in all_rows}:
        raise ValueError('Character OOF membership mismatch')
    rows = [r for r in all_rows if not r['case_id'].startswith('OFFICIAL-')]
    labels = np.array([r['label'] for r in rows])
    p = np.array([primary_oof[r['case_id']]['score'] for r in rows])
    o = np.zeros(len(rows))
    unseen = []
    for i, row in enumerate(rows):
        if (row['partition'] != 'train' or row['original_partition'] != 'train' or row['do_not_train']
                or primary_oof[row['case_id']]['label'] != row['label']):
            raise ValueError('Ineligible or misaligned gate training row')
        if row['case_id'] in old_oof:
            o[i] = old_oof[row['case_id']]['raw_score']
        else:
            if set(row['icann_roots']) & parent_owners:
                raise ValueError('Parent score is not owner-held-out')
            unseen.append(i)
    for start in range(0, len(unseen), 256):
        ix = unseen[start:start + 256]
        o[ix] = probability(base['url']['model'], [rows[i]['url'] for i in ix])
    decisions = json.loads((PRIMARY / 'seed_decisions.json').read_text(encoding='utf-8'))
    seeds = [s['url'] for s in decisions if s['status'] == 'added']
    seed_scores = list(zip(probability(character['url']['model'], seeds), probability(base['url']['model'], seeds)))
    if len(seeds) != 10 or any(primary >= .5 for primary, _ in seed_scores):
        raise ValueError('Only the ten accepted cleared fitting seeds may constrain the gate')
    inputs = [PRIMARY / n for n in ('candidate_bundle.pkl', 'candidate_manifest.json', 'parent_bundle.pkl',
        'parent_manifest.json', 'url_fit_rows.jsonl', 'wide_lr_c4_selection_predictions.jsonl',
        'seed_decisions.json', 'sms_fit_rows.jsonl', 'fresh_test.jsonl', 'url_test.jsonl')]
    inputs += [PARENT_FIT / 'url_outer_predictions.jsonl', PARENT_FIT / 'url_fit_rows.jsonl']
    protocol = dict(run_id=RUN_ID, parent_bundle_sha256=sha(PRIMARY / 'parent_bundle.pkl'),
        primary_bundle_sha256=sha(PRIMARY / 'candidate_bundle.pkl'),
        data_manifest_sha256=sha(output / 'data_frozen.json'),
        inputs_sha256={str(p.relative_to(ROOT)): sha(p) for p in inputs},
        code_sha256={name: sha(ROOT / name, True) for name in
                     ('url_ensemble.py', 'repair_url_ensemble.py', 'predict_hybrid.py')},
        gate_oof_rows=len(rows), parent_nested_oof_rows=len(rows) - len(unseen),
        parent_unseen_owner_rows=len(unseen), seed_constraints=10, heldout_seed_constraints=0,
        thresholds_selected_using_test=False, serving_examples_fitted=False, expert_labels_created=0)
    write_json(output / 'protocol.json', protocol)
    model = GatedURLClassifier(character['url']['model'], base['url']['model'])
    model.fit([r['url'] for r in rows], labels, primary_oof=p, parent_oof=o, benign_seed_scores=seed_scores)
    write_json(output / 'gate_training.json', model.training_report_)
    write_jsonl(output / 'gate_oof_scores.jsonl', [dict(case_id=r['case_id'], label=r['label'],
        primary_score=float(p[i]), parent_score=float(o[i]),
        parent_score_origin='nested_group_oof' if r['case_id'] in old_oof else 'unseen_owner_frozen_parent')
        for i, r in enumerate(rows)])
    print(json.dumps(dict(learned_cutoff=model.cutoff_, gate_report=model.training_report_)), flush=True)
    calibration_train = read_jsonl(output / 'calibration_train.jsonl')
    validation = read_jsonl(output / 'calibration_validation.jsonl')
    calibrator = CalibratedClassifierCV(FrozenEstimator(model), method='sigmoid')
    calibrator.fit([r['url'] for r in calibration_train], [r['label'] for r in calibration_train])
    values = [r['url'] for r in validation]
    raw, calibrated = probability(model, values), probability(calibrator, values)
    before = calibration_metrics([r['label'] for r in validation], raw)
    after = calibration_metrics([r['label'] for r in validation], calibrated)
    gate = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    report = dict(raw=before, calibrated=after, gate_pass=bool(gate),
        calibration_fit_rows=len(calibration_train), disjoint_validation_rows=len(validation),
        base_models_refitted=False, source_labels_not_expert_verified=True, sms_gate_inherited=True)
    write_json(output / 'calibration_report.json', report)
    write_jsonl(output / 'calibration_validation_predictions.jsonl', [dict(case_id=r['case_id'], label=r['label'],
        raw_score=float(raw[i]), calibrated_probability=float(calibrated[i])) for i, r in enumerate(validation)])
    sms_rows = read_jsonl(PRIMARY / 'sms_fit_rows.jsonl')
    fitting_rows = all_rows + calibration_train
    write_jsonl(output / 'url_fit_rows.jsonl', fitting_rows)
    write_jsonl(output / 'fit_rows.jsonl', sms_rows + fitting_rows)
    shutil.copy2(PRIMARY / 'sms_fit_rows.jsonl', output / 'sms_fit_rows.jsonl')
    candidate = {**character, 'url': {**character['url'], 'model': model, 'probability_model': calibrator,
        'model_id': RUN_ID + ':url'}, 'training': dict(character['training'])}
    provenance = dict(candidate['training']['label_provenance_counts'])
    provenance['url'] = dict(Counter(r['label_provenance'] for r in fitting_rows))
    candidate['training'].update(run_id=RUN_ID, method='Supervised residual URL ensemble; frozen learned heads; disjoint-owner sigmoid calibration; SMS inherited',
        url_training_samples=len(fitting_rows), raw_url_training_samples=len(all_rows),
        url_calibration_training_samples=len(calibration_train), url_gate_training_samples=len(rows),
        url_ensemble_learned_cutoff=model.cutoff_, label_provenance_counts=provenance,
        training_manifest_sha256=sha(output / 'fit_rows.jsonl'),
        url_ensemble_trained=True, paired_training_samples=0)
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL))
    primary_manifest = json.loads((PRIMARY / 'candidate_manifest.json').read_text(encoding='utf-8'))
    bound = dict(json.loads((output / 'data_frozen.json').read_text(encoding='utf-8'))['files_sha256'])
    bound.update({name: sha(output / name) for name in ('data_frozen.json', 'protocol.json',
        'gate_training.json', 'gate_oof_scores.jsonl', 'url_fit_rows.jsonl', 'sms_fit_rows.jsonl', 'fit_rows.jsonl')})
    manifest = {**primary_manifest, 'parent_artifact': parent_manifest, 'training': candidate['training'],
        'bundle_sha256': sha(output / 'candidate_bundle.pkl'), 'dataset_files_sha256': bound,
        'source_sha256': {b + '_train': sha(output / f'{b}_fit_rows.jsonl') for b in ('sms', 'url')},
        'code_sha256': {**primary_manifest['code_sha256'], 'url_ensemble.py': sha(ROOT / 'url_ensemble.py', True)},
        'head_model_ids': {b: candidate[b]['model_id'] for b in ('sms', 'url')},
        'fitted_rows': len(sms_rows) + len(fitting_rows), 'test_evaluation_performed': False,
        'calibration_protocol_sha256': sha(output / 'protocol.json'),
        'calibration_report_sha256': sha(output / 'calibration_report.json'),
        'calibration_gate_pass': bool(gate and parent_manifest['calibration_gate_pass']),
        'url_gate_selection_pass': model.training_report_['gate_pass'],
        'fit_code_sha256': sha(Path(__file__), True), 'fit_seconds': round(time.perf_counter() - started, 3),
        'url_ensemble_sources': dict(primary_bundle_sha256=protocol['primary_bundle_sha256'],
                                     parent_bundle_sha256=protocol['parent_bundle_sha256'])}
    for obsolete in ('evaluation_sha256', 'activation_eligible'):
        manifest.pop(obsolete, None)
    write_json(output / 'candidate_manifest.json', manifest)
    print(json.dumps(dict(calibration=report, bundle_sha256=manifest['bundle_sha256'])), flush=True)


def verify_candidate(output=OUT):
    verify_data(output)
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    if sha(output / 'data_frozen.json') != protocol['data_manifest_sha256']:
        raise ValueError('Reserved data manifest changed')
    for name, expected in protocol['inputs_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Source artifact/OOF evidence changed: ' + name)
    for name, expected in protocol['code_sha256'].items():
        if sha(ROOT / name, True) != expected:
            raise ValueError('Frozen repair code changed: ' + name)
    manifest = json.loads((output / 'candidate_manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['dataset_files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Fitting evidence changed: ' + name)
    if (sha(output / 'candidate_bundle.pkl') != manifest['bundle_sha256']
            or sha(output / 'calibration_report.json') != manifest['calibration_report_sha256']):
        raise ValueError('Candidate/calibration identity mismatch')
    return protocol, manifest


def evaluate(output=OUT):
    from unittest.mock import patch
    import predict_hybrid as live
    protocol, manifest = verify_candidate(output)
    with (output / 'evaluation.started').open('x', encoding='utf-8') as claim:
        claim.write(manifest['bundle_sha256'])
    candidate = pickle.loads((output / 'candidate_bundle.pkl').read_bytes())
    primary = pickle.loads((PRIMARY / 'candidate_bundle.pkl').read_bytes())
    parent = pickle.loads((PRIMARY / 'parent_bundle.pkl').read_bytes())
    sms_identical = pickle.dumps(candidate['sms']) == pickle.dumps(parent['sms'])
    results = {}
    for cohort, path in [('fresh', output / 'fresh_test.jsonl'),
                         ('previous_fresh_reused', PRIMARY / 'fresh_test.jsonl'),
                         ('historical_reused', PRIMARY / 'url_test.jsonl')]:
        rows = read_jsonl(path)
        results[cohort] = {}
        for name, bundle in [('parent', parent), ('primary', primary), ('candidate', candidate)]:
            scores = np.concatenate([probability(bundle['url']['model'], [r['url'] for r in rows[i:i + 256]])
                                     for i in range(0, len(rows), 256)])
            results[cohort][name] = classification_metrics([r['label'] for r in rows], scores)
            write_jsonl(output / f'{cohort}_{name}_predictions.jsonl', [dict(case_id=r['case_id'], label=r['label'],
                score=float(p)) for r, p in zip(rows, scores)])
    decisions = json.loads((PRIMARY / 'seed_decisions.json').read_text(encoding='utf-8'))
    for name, bundle in [('parent', parent), ('primary', primary), ('candidate', candidate)]:
        scores = probability(bundle['url']['model'], [s['url'] for s in decisions])
        for site, p in zip(decisions, scores):
            site[name + '_score'] = float(p)
    with patch.object(live, 'load_bundle', return_value=candidate):
        direct = live.classify(url='https://qi.lv/F0i')
        mixed = live.classify(text='Hey, are you free for lunch tomorrow?', url='https://qi.lv/F0i')
        long = live.classify(url='https://uccle.monopinion.belgium.be/profiles/sunwinorgvc/badges')
        bare_fb = live.classify(url='https://facebook.com/')
    serving = dict(qi_score=direct['ml_risk_score'], qi_action=direct['action'],
        mixed_url_review=mixed['url_review_required'], mixed_action=mixed['action'],
        long_url_score=long['ml_risk_score'], bare_facebook_action=bare_fb['action'], sms_state_preserved=sms_identical)
    serving_pass = bool(direct['ml_risk_score'] >= 80 and mixed['url_review_required'] and mixed['action'] == 'REVIEW'
        and 50 <= long['ml_risk_score'] < 80 and bare_fb['action'] == 'CLEAR' and sms_identical
        and all(s['candidate_score'] < .5 for s in decisions))
    hist = results['historical_reused']
    old, new = hist['parent']['confusion_matrix_tn_fp_fn_tp'], hist['candidate']['confusion_matrix_tn_fp_fn_tp']
    hist_gate = new[1] <= old[1] and new[3] >= old[3]
    report = dict(bundle_sha256=manifest['bundle_sha256'], metrics=results, serving=serving,
        official_url_checks=decisions, serving_gate_pass=serving_pass,
        fresh_accuracy_above_95=results['fresh']['candidate']['accuracy_above_95'],
        historical_nonregression_gate_pass=hist_gate, source_labels_not_expert_verified=True,
        new_test_is_same_source_not_external_benchmark=True,
        numerical_gates_pass=bool(serving_pass and hist_gate and manifest['calibration_gate_pass']
            and manifest['url_gate_selection_pass'] and results['fresh']['candidate']['accuracy_above_95']))
    write_json(output / 'evaluation.json', report)
    manifest.update(test_evaluation_performed=True, evaluation_sha256=sha(output / 'evaluation.json'))
    write_json(output / 'candidate_manifest.json', manifest)
    print(json.dumps(report), flush=True)


def activate(output=OUT, models=None):
    models = models or ROOT / 'models'
    protocol, manifest = verify_candidate(output)
    evaluation = json.loads((output / 'evaluation.json').read_text(encoding='utf-8'))
    api = json.loads((output / 'api_verification.json').read_text(encoding='utf-8'))
    if (not evaluation['numerical_gates_pass'] or sha(output / 'evaluation.json') != manifest['evaluation_sha256']
            or evaluation['bundle_sha256'] != manifest['bundle_sha256']
            or not manifest['calibration_gate_pass'] or not manifest['url_gate_selection_pass']
            or api.get('exit_code') != 0 or api.get('tests_passed') != 17
            or api.get('bundle_sha256') != manifest['bundle_sha256']
            or api.get('manifest_sha256') != sha(output / 'candidate_manifest.json')
            or any(sha(ROOT.parent / name) != expected for name, expected in api['test_scripts_sha256'].items())
            or sha(models / 'hybrid_bundle.pkl') != protocol['parent_bundle_sha256']
            or sha(models / 'hybrid_manifest.json') != sha(PRIMARY / 'parent_manifest.json')):
        raise ValueError('Numerical/API gate or source/parent binding failed; active model preserved')
    backup = output / 'previous_active'
    backup.mkdir(exist_ok=False)
    for name in ('hybrid_bundle.pkl', 'hybrid_manifest.json'):
        shutil.copy2(models / name, backup / name)
    pairs = [('candidate_bundle.pkl', 'hybrid_bundle.pkl'), ('candidate_manifest.json', 'hybrid_manifest.json')]
    for source, destination in pairs:
        shutil.copy2(output / source, models / (destination + '.tmp'))
    try:
        for _, destination in pairs:
            os.replace(models / (destination + '.tmp'), models / destination)
    except OSError:
        for name in ('hybrid_bundle.pkl', 'hybrid_manifest.json'):
            shutil.copy2(backup / name, models / (name + '.tmp'))
            os.replace(models / (name + '.tmp'), models / name)
        raise
    record = dict(activated=RUN_ID, bundle_sha256=manifest['bundle_sha256'],
        manifest_sha256=sha(output / 'candidate_manifest.json'), api_verification_sha256=sha(output / 'api_verification.json'),
        backup=str(backup), remote_deployment=False)
    write_json(output / 'activation.json', record)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'fit', 'evaluate', 'activate'))
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    {'prepare': prepare, 'fit': fit, 'evaluate': evaluate, 'activate': activate}[args.command](args.output)
