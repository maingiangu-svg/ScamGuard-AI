"""Expand supervised URL data and measure a strict 95% accuracy target on reserved owners."""
import argparse
import hashlib
import json
import math
import pickle
import shutil
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.base import clone
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from audit_training_integrity import url_quality_flags
from data_quality import prepare_urls
from calibrate_supervised import calibration_metrics, fit_calibrated, group_splits
from external_training import REF, RegisteredDomains
from official_domain_training import OUT as SEED_RUN, checked_candidate, owner_roots, release_gate
from predict import probability
from modeling import url_matrix
from repair_training_data import OUTPUT as REPAIRED, ROOT, read_jsonl, sha, write_json, write_jsonl
from train_repaired_hybrid import metrics
from url_model_selection import validate_selection_rows

OUT = ROOT / 'data/prepared/accuracy95_2026-10-27'
RUN_ID = 'accuracy95-url-20261027'
SOURCE_SHA = 'b1a7c26b354632c80817e10af154c4e5007f9480fb43a8ac2730491500fa2780'
CONFIGS = ('wide_lr_c1', 'wide_lr_c4', 'numeric_trees', 'svd_boost')
DEPENDENCIES = ('accuracy_target_training.py', 'url_model_selection.py', 'official_domain_training.py',
                'calibrate_supervised.py', 'data_quality.py', 'modeling.py', 'preprocess.py')


def classification_metrics(labels, scores):
    rows = [dict(label=int(y)) for y in labels]
    result = metrics(rows, scores, .5)
    predicted = np.asarray(scores) >= .5
    result.update(accuracy=float(accuracy_score(labels, predicted)),
                  balanced_accuracy=float(balanced_accuracy_score(labels, predicted)))
    p, n, z = result['accuracy'], len(rows), 1.959963984540054
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    result['accuracy_wilson_95ci'] = [center - half, center + half]
    result['accuracy_above_95'] = p > .95
    result['majority_class_accuracy'] = max(Counter(labels).values()) / n
    return result


def choose_model(reference, candidates):
    nonregressing = [name for name, result in candidates.items() if release_gate(reference, result, True)]
    eligible = [name for name in nonregressing if candidates[name]['accuracy'] > .95]
    choices = eligible or nonregressing or list(candidates)
    winner = min(choices, key=lambda name: (-candidates[name]['accuracy'], -candidates[name]['f1'],
                                          candidates[name]['confusion_matrix_tn_fp_fn_tp'][1], name))
    return winner, bool(eligible)


def partition_new_urls(rows, excluded, train_limit=40000, test_limit=4000):
    buckets, counts = [[], []], Counter()
    for row in sorted(rows, key=lambda r: (hashlib.sha256(r['url'].encode()).hexdigest(), r['url'])):
        owner = row['owner']
        if owner in excluded or counts[owner] >= 10:
            continue
        test = int(hashlib.sha256(('accuracy95-v1:' + owner).encode()).hexdigest()[:8], 16) % 5 == 0
        bucket = buckets[int(test)]
        if len(bucket) < (test_limit if test else train_limit):
            bucket.append(row)
            counts[owner] += 1
    return tuple(buckets)


def prepare(output=OUT):
    checked_candidate(SEED_RUN)
    source = ROOT / 'data/phishing_site_urls.csv'
    if sha(source) != SOURCE_SHA:
        raise ValueError('Original labeled URL source checksum mismatch')
    psl = (REF / 'public_suffix_list.dat').read_text(encoding='utf-8')
    owner = RegisteredDomains(psl.split('// ===BEGIN PRIVATE DOMAINS===')[0])
    excluded = {'qi.lv', 'belgium.be', 'sunwin.org.vc'}
    inputs = {str(source.relative_to(ROOT)): SOURCE_SHA}
    original = read_jsonl(REPAIRED / 'all_rows.jsonl')
    excluded.update(root for row in original for root in owner_roots(row))
    inputs[str((REPAIRED / 'all_rows.jsonl').relative_to(ROOT))] = sha(REPAIRED / 'all_rows.jsonl')
    legacy = ROOT / 'data/urls_preprocessed.csv'
    excluded.update(owner(urlsplit(url).hostname) for url in pd.read_csv(legacy, usecols=['url']).url)
    inputs[str(legacy.relative_to(ROOT))] = sha(legacy)
    legacy_sms = ROOT / 'data/smishing_preprocessed.csv'
    for links in pd.read_csv(legacy_sms, usecols=['urls_json']).urls_json:
        excluded.update(owner(urlsplit(url).hostname) for url in json.loads(links))
    inputs[str(legacy_sms.relative_to(ROOT))] = sha(legacy_sms)
    external = ROOT / 'data/prepared/external_training_2026-10-25'
    for path in sorted(external.glob('*.jsonl')):
        if 'predictions' in path.name or 'errors' in path.name:
            continue
        for row in read_jsonl(path):
            hosts = row.get('registrable_domains', []) + row.get('roots', [])
            if row.get('url'):
                hosts.append(urlsplit(row['url']).hostname)
            excluded.update(owner(h) for h in hosts if h)
        inputs[str(path.relative_to(ROOT))] = sha(path)
    seeds = json.loads((SEED_RUN / 'seeds.json').read_text(encoding='utf-8'))
    excluded.update(site['domain'] for site in seeds['sites'])
    print('Repairing the pinned full URL source and reserving new owner domains.', flush=True)
    clean, _, audit = prepare_urls(pd.read_csv(source, dtype=str, keep_default_na=False))
    clean['owner'] = clean.host.map(owner)
    clean = clean[~clean.owner.isin(excluded)].copy()
    clean = clean[~clean.url.map(lambda u: bool(url_quality_flags(u)))].copy()
    new_train, fresh = partition_new_urls(clean.to_dict('records'), excluded)
    if len(fresh) < 1000 or {int(r['label']) for r in fresh} != {0, 1}:
        raise ValueError('Insufficient fresh labeled groups; no fabricated completion')
    output.mkdir(parents=True, exist_ok=False)
    def record(row, partition):
        return dict(url=row['url'], label=int(row['label']), original_label=row['original_label'],
            case_id='SOURCE95-' + str(row['source_record']), source_record=int(row['source_record']),
            source_sha256=SOURCE_SHA, source_file='phishing_site_urls.csv',
            label_provenance='inherited_url_source_not_expert_verified', expert_verified=False,
            partition=partition, original_partition=partition, do_not_train=partition != 'train',
            repair_reasons=[], repair_group='SOURCE95-G-' + row['owner'],
            roots=[row['owner']], icann_roots=[row['owner']], cohort='bundle_url')
    added = [record(row, 'train') for row in new_train]
    fresh = [record(row, 'test') for row in fresh]
    base_rows = read_jsonl(SEED_RUN / 'url_fit_rows.jsonl')
    rows = base_rows + added
    if ({r for row in rows for r in owner_roots(row)} & {r for row in fresh for r in owner_roots(row)}):
        raise ValueError('Fresh holdout owner overlap')
    write_jsonl(output / 'url_fit_rows.jsonl', rows)
    write_jsonl(output / 'fresh_test.jsonl', fresh)
    sms = read_jsonl(SEED_RUN / 'sms_fit_rows.jsonl')
    write_jsonl(output / 'fit_rows.jsonl', sms + rows)
    for name in ('parent_bundle.pkl', 'parent_manifest.json', 'sms_fit_rows.jsonl',
                 'url_test.jsonl', 'seeds.json', 'seed_decisions.json'):
        shutil.copy2(SEED_RUN / name, output / name)
    report = dict(new_train=len(added), total_url_train=len(rows), fresh_test=len(fresh),
        fresh_labels=dict(Counter(str(r['label']) for r in fresh)), excluded_owner_domains=len(excluded),
        new_train_labels=dict(Counter(str(r['label']) for r in added)), source_audit=audit,
        fresh_expert_verified=False, same_source_as_training=True, not_external_independent_benchmark=True,
        fresh_ever_fitted=False, inputs_sha256=inputs,
        files_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()})
    write_json(output / 'data_frozen.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('inputs_sha256', 'files_sha256', 'source_audit')}), flush=True)


def candidate_model(name):
    numeric = Pipeline([('extract', FunctionTransformer(url_matrix)), ('scale', StandardScaler())])
    if name == 'numeric_trees':
        return Pipeline([('features', FunctionTransformer(url_matrix)),
            ('classifier', ExtraTreesClassifier(n_estimators=300, min_samples_leaf=2,
                                                max_features=1.0, random_state=42, n_jobs=2))])
    if name in ('wide_lr_c1', 'wide_lr_c4'):
        chars = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 6), max_features=50000,
                                min_df=2, sublinear_tf=True, dtype=np.float64)
        classifier = LogisticRegression(C=1 if name == 'wide_lr_c1' else 4,
                                         solver='liblinear', max_iter=1000, random_state=42)
    elif name == 'svd_boost':
        chars = Pipeline([('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5),
                    max_features=5000, min_df=2, sublinear_tf=True, dtype=np.float32)),
                          ('svd', TruncatedSVD(n_components=64, n_iter=5, random_state=42))])
        classifier = HistGradientBoostingClassifier(max_iter=200, max_depth=6, min_samples_leaf=15,
                          l2_regularization=1, early_stopping=False, random_state=42)
    else:
        raise ValueError('Unknown frozen configuration')
    return Pipeline([('features', FeatureUnion([('numeric', numeric), ('characters', chars)])),
                     ('classifier', classifier)])


def verify_data(output):
    data = json.loads((output / 'data_frozen.json').read_text(encoding='utf-8'))
    for name, expected in data['inputs_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Source/exclusion input changed: ' + name)
    for name, expected in data['files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Frozen data changed: ' + name)
    return data


def verify_run(output):
    verify_data(output)
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    if sha(output / 'data_frozen.json') != protocol['data_manifest_sha256']:
        raise ValueError('Data manifest changed')
    for name, expected in protocol['code_sha256'].items():
        if sha(ROOT / name, True) != expected:
            raise ValueError('Frozen code changed: ' + name)
    if sha(output / 'folds.jsonl') != protocol['folds_sha256']:
        raise ValueError('Training fold membership changed')
    return protocol


def select(output=OUT):
    verify_data(output)
    if (output / 'protocol.json').exists():
        raise ValueError('Selection already started; no repeated search')
    rows = read_jsonl(output / 'url_fit_rows.jsonl')
    validate_selection_rows(rows)
    splits = group_splits(rows)
    fold_ids = np.full(len(rows), -1)
    for fold, (_, heldout) in enumerate(splits):
        fold_ids[heldout] = fold
    write_jsonl(output / 'folds.jsonl', [dict(case_id=r['case_id'], repair_group=r['repair_group'],
                                           heldout_fold=int(fold_ids[i])) for i, r in enumerate(rows)])
    protocol = dict(run_id=RUN_ID, configurations=CONFIGS, seed=42, threshold=.5,
        target_accuracy_strictly_greater_than=.95, historical_and_fresh_tests_used_in_selection=False,
        code_sha256={name: sha(ROOT / name, True) for name in DEPENDENCIES},
        data_manifest_sha256=sha(output / 'data_frozen.json'), folds_sha256=sha(output / 'folds.jsonl'),
        selection_folds=3, outer_calibration_folds=3, inner_calibration_folds=3,
        expert_labels_created=0, threshold_search=False, sms_head_preserved=True,
        new_external_independent_benchmark=False)
    write_json(output / 'protocol.json', protocol)
    base = pickle.loads((output / 'parent_bundle.pkl').read_bytes())
    urls, labels = np.array([r['url'] for r in rows], dtype=object), np.array([r['label'] for r in rows])
    results = {}
    for name in ('reference',) + CONFIGS:
        scores = np.zeros(len(rows))
        for fold, (train, heldout) in enumerate(splits):
            print(f'{name}: isolated training-domain fold {fold + 1}/3 ({len(train)} fit rows)', flush=True)
            model = clone(base['url']['model']) if name == 'reference' else candidate_model(name)
            model.fit(urls[train], labels[train])
            scores[heldout] = probability(model, urls[heldout])
        results[name] = classification_metrics(labels, scores)
        write_jsonl(output / f'{name}_selection_predictions.jsonl', [dict(case_id=r['case_id'],
            label=r['label'], score=float(scores[i]), heldout_fold=int(fold_ids[i])) for i, r in enumerate(rows)])
        print(json.dumps(dict(configuration=name, metrics=results[name])), flush=True)
    reference = results.pop('reference')
    winner, passed = choose_model(reference, results)
    write_json(output / 'selection.json', dict(reference=reference, candidates=results, winner=winner,
        target_selection_gate_pass=passed, selection_estimate_has_selection_bias=True))
    files = ['protocol.json', 'selection.json'] + [name + '_selection_predictions.jsonl' for name in ('reference',) + CONFIGS]
    write_json(output / 'selection_frozen.json', {name: sha(output / name) for name in files})
    print(json.dumps(dict(selected=winner, target_selection_gate_pass=passed)), flush=True)


def verify_selection(output):
    verify_run(output)
    frozen = json.loads((output / 'selection_frozen.json').read_text(encoding='utf-8'))
    for name, expected in frozen.items():
        if sha(output / name) != expected:
            raise ValueError('Frozen selection evidence changed: ' + name)
    selection = json.loads((output / 'selection.json').read_text(encoding='utf-8'))
    winner, passed = choose_model(selection['reference'], selection['candidates'])
    if selection['winner'] != winner or selection['target_selection_gate_pass'] is not passed:
        raise ValueError('Invalid winner or target gate')
    return selection


def fit(output=OUT):
    import time
    selection = verify_selection(output)
    with (output / 'fit.started').open('x', encoding='utf-8') as claim:
        claim.write(selection['winner'])
    rows = read_jsonl(output / 'url_fit_rows.jsonl')
    validate_selection_rows(rows)
    base = pickle.loads((output / 'parent_bundle.pkl').read_bytes())
    parent_manifest = json.loads((output / 'parent_manifest.json').read_text(encoding='utf-8'))
    raw, calibrated = np.zeros(len(rows)), np.zeros(len(rows))
    estimator, started = candidate_model(selection['winner']), time.perf_counter()
    for fold, (train, heldout) in enumerate(group_splits(rows)):
        print(f'{selection["winner"]}: nested calibration fold {fold + 1}/3', flush=True)
        model = fit_calibrated(estimator, [rows[i] for i in train], 'url')
        urls = [rows[i]['url'] for i in heldout]
        raw[heldout] = probability(model.calibrated_classifiers_[0].estimator, urls)
        calibrated[heldout] = probability(model, urls)
    labels = [r['label'] for r in rows]
    before, after = calibration_metrics(labels, raw), calibration_metrics(labels, calibrated)
    gate = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    write_jsonl(output / 'calibration_predictions.jsonl', [dict(case_id=r['case_id'], label=r['label'],
        repair_group=r['repair_group'], raw_score=float(raw[i]), calibrated_probability=float(calibrated[i]))
        for i, r in enumerate(rows)])
    print(f'Final supervised fit: {len(rows)} URLs ({selection["winner"]})', flush=True)
    model = fit_calibrated(estimator, rows, 'url')
    candidate = {**base, 'url': {**base['url'], 'model': model.calibrated_classifiers_[0].estimator,
        'probability_model': model, 'model_id': RUN_ID + ':url'}, 'training': dict(base['training'])}
    provenance = dict(base['training']['label_provenance_counts'])
    provenance['url'] = dict(Counter(r['label_provenance'] for r in rows))
    candidate['training'].update(run_id=RUN_ID, method='Expanded supervised URL training; train-group selection; grouped sigmoid calibration; SMS inherited',
        url_training_samples=len(rows), training_manifest_sha256=sha(output / 'fit_rows.jsonl'),
        url_label_provenance='Inherited source good/bad labels plus 10 AI-reviewed official URL seeds; not expert verified',
        label_provenance_counts=provenance, selected_url_configuration=selection['winner'],
        official_url_seed_samples=10, hyperparameters_retuned=True, selection_used_historical_test=False,
        fresh_test_used_in_fitting=False)
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL))
    report = dict(raw=before, calibrated=after, gate_pass=bool(gate), selection_bias_possible=True,
                  sms_gate_inherited=True, fit_seconds=round(time.perf_counter() - started, 3))
    write_json(output / 'calibration_report.json', report)
    data_files = json.loads((output / 'data_frozen.json').read_text(encoding='utf-8'))['files_sha256']
    bound = {**data_files, **{name: sha(output / name) for name in
        ('data_frozen.json', 'protocol.json', 'folds.jsonl', 'selection.json', 'selection_frozen.json')}}
    manifest = {**parent_manifest, 'parent_artifact': parent_manifest, 'training': candidate['training'],
        'bundle_sha256': sha(output / 'candidate_bundle.pkl'), 'dataset_files_sha256': bound,
        'source_sha256': {branch + '_train': sha(output / f'{branch}_fit_rows.jsonl') for branch in ('sms', 'url')},
        'head_model_ids': {branch: candidate[branch]['model_id'] for branch in ('sms', 'url')},
        'fitted_rows': len(read_jsonl(output / 'fit_rows.jsonl')), 'test_evaluation_performed': False,
        'fit_code_sha256': sha(Path(__file__), True), 'fit_seconds': report['fit_seconds'],
        'calibration_protocol_sha256': sha(output / 'protocol.json'),
        'calibration_report_sha256': sha(output / 'calibration_report.json'),
        'calibration_gate_pass': bool(gate and parent_manifest['calibration_gate_pass'])}
    write_json(output / 'candidate_manifest.json', manifest)
    print(json.dumps(report), flush=True)


def verify_candidate(output):
    verify_selection(output)
    manifest = json.loads((output / 'candidate_manifest.json').read_text(encoding='utf-8'))
    if (sha(output / 'candidate_bundle.pkl') != manifest['bundle_sha256']
            or sha(output / 'calibration_report.json') != manifest['calibration_report_sha256']):
        raise ValueError('Candidate artifact/calibration changed')
    for name, expected in manifest['dataset_files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Candidate input changed: ' + name)
    return manifest


def evaluate(output=OUT):
    from unittest.mock import patch
    import predict_hybrid as live
    manifest = verify_candidate(output)
    with (output / 'evaluation.started').open('x', encoding='utf-8') as claim:
        claim.write(manifest['bundle_sha256'])
    baseline = pickle.loads((output / 'parent_bundle.pkl').read_bytes())
    candidate = pickle.loads((output / 'candidate_bundle.pkl').read_bytes())
    results = {}
    for cohort, file in [('fresh', 'fresh_test.jsonl'), ('historical', 'url_test.jsonl')]:
        rows = read_jsonl(output / file)
        results[cohort] = {}
        for name, bundle in [('baseline', baseline), ('candidate', candidate)]:
            scores = np.concatenate([probability(bundle['url']['model'], [r['url'] for r in rows[i:i + 256]])
                                     for i in range(0, len(rows), 256)])
            results[cohort][name] = classification_metrics([r['label'] for r in rows], scores)
            write_jsonl(output / f'{cohort}_{name}_predictions.jsonl', [dict(case_id=r['case_id'],
                label=r['label'], score=float(p)) for r, p in zip(rows, scores)])
    seeds = json.loads((output / 'seed_decisions.json').read_text(encoding='utf-8'))
    urls = [s['url'] for s in seeds]
    for name, bundle in [('baseline', baseline), ('candidate', candidate)]:
        for site, score in zip(seeds, probability(bundle['url']['model'], urls)):
            site[name + '_score'] = float(score)
    with patch.object(live, 'load_bundle', return_value=candidate):
        direct = live.classify(url='https://qi.lv/F0i')
        mixed = live.classify(text='Hey, are you free for lunch tomorrow?', url='https://qi.lv/F0i')
        long = live.classify(url='https://uccle.monopinion.belgium.be/profiles/sunwinorgvc/badges')
    serving = dict(qi_score=direct['ml_risk_score'], qi_action=direct['action'],
        mixed_url_review_required=mixed['url_review_required'], mixed_action=mixed['action'],
        long_url_score=long['ml_risk_score'],
        sms_head_byte_identical=pickle.dumps(baseline['sms']) == pickle.dumps(candidate['sms']))
    serving_pass = (direct['ml_risk_score'] >= 80 and mixed['url_review_required']
        and mixed['action'] == 'REVIEW' and 50 <= long['ml_risk_score'] < 80
        and all(s['candidate_score'] < .5 for s in seeds) and serving['sms_head_byte_identical'])
    selection = json.loads((output / 'selection.json').read_text(encoding='utf-8'))
    old_gate = release_gate(results['historical']['baseline'], results['historical']['candidate'], True)
    fresh_pass = results['fresh']['candidate']['accuracy_above_95']
    report = dict(bundle_sha256=manifest['bundle_sha256'], metrics=results, official_url_checks=seeds,
        source_labels_not_expert_verified=True, fresh_test_previously_unused_by_these_fits=True,
        historical_diagnostic_reused=True, new_external_independent_benchmark=False,
        fresh_accuracy_above_95=fresh_pass, historical_nonregression_gate_pass=old_gate,
        serving_checks=serving, serving_gate_pass=bool(serving_pass),
        eligible_for_activation=bool(fresh_pass and old_gate and serving_pass
            and manifest['calibration_gate_pass'] and selection['target_selection_gate_pass']))
    write_json(output / 'evaluation.json', report)
    manifest.update(test_evaluation_performed=True, evaluation_sha256=sha(output / 'evaluation.json'),
                    activation_eligible=report['eligible_for_activation'])
    write_json(output / 'candidate_manifest.json', manifest)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'select', 'fit', 'evaluate'))
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    {'prepare': prepare, 'select': select, 'fit': fit, 'evaluate': evaluate}[args.command](args.output)
