"""Train official URL seeds with provenance and historical owner-domain exclusions."""
import argparse
import hashlib
import json
import os
import pickle
import shutil
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from preprocess import canonicalize_url
from repair_training_data import OUTPUT, ROOT, read_jsonl, sha, write_json, write_jsonl

SEEDS = ROOT / 'data/official_domain_seeds.json'
BASE_FIT = ROOT / 'data/prepared/calibrated_candidate_2026-10-26_r2'
OUT = ROOT / 'data/prepared/official_domains_2026-10-27'
RUN_ID = 'official-domains-20261027'
PROVENANCE = 'user_requested_first_party_url_ai_evidence_review'
DEPENDENCIES = ('official_domain_training.py', 'calibrate_supervised.py',
                'modeling.py', 'preprocess.py', 'repair_training_data.py')


def validate_seeds(data):
    if (type(data.get('label')) is not int or data['label'] != 0
            or data.get('expert_verified') is not False or not data.get('label_scope')
            or data.get('label_provenance') != PROVENANCE):
        raise ValueError('Exact legitimate URL seeds require non-expert label provenance')
    date.fromisoformat(data['reviewed_on'])
    seen = set()
    for site in data['sites']:
        parts = urlsplit(site['url'])
        evidence = urlsplit(site.get('evidence_url', ''))
        if (parts.scheme != 'https' or parts.hostname not in (site['domain'], 'www.' + site['domain'])
                or parts.username is not None or parts.password is not None or parts.port is not None
                or parts.fragment or evidence.scheme != 'https' or not evidence.hostname
                or evidence.username is not None or evidence.password is not None
                or canonicalize_url(site['url']) != site['url'] or site['domain'] in seen):
            raise ValueError('Invalid or duplicate official URL/evidence')
        seen.add(site['domain'])
    if not seen:
        raise ValueError('At least one seed required')


def owner_roots(row):
    return set(row.get('roots', [])) | set(row.get('icann_roots', []))


def prepare_seeds(data, training, excluded):
    validate_seeds(data)
    reserved = {root for row in excluded for root in owner_roots(row)}
    groups, labels = {}, {}
    for row in training:
        if (row['partition'] != 'train' or row['original_partition'] != 'train'
                or row['do_not_train'] or row.get('repair_reasons')):
            raise ValueError('Only accepted original training rows may be fitted')
        for root in owner_roots(row):
            if root in groups and groups[root] != row['repair_group']:
                raise ValueError('Owner domain split across calibration groups')
            groups[root] = row['repair_group']
        labels.setdefault(canonicalize_url(row['url']), set()).add(row['label'])
    accepted, decisions = [], []
    for site in data['sites']:
        domain, url = site['domain'], site['url']
        prior = labels.get(url, set())
        status = ('reserved_domain' if domain in reserved else 'label_conflict' if prior - {0}
                  else 'already_in_training' if prior else 'added')
        decisions.append(dict(site, status=status))
        if status != 'added':
            continue
        accepted.append(dict(site, case_id='OFFICIAL-' + domain, label=0, original_label=0,
            label_provenance=data['label_provenance'], label_scope=data['label_scope'],
            reviewed_on=data['reviewed_on'], expert_verified=False,
            source_trace='first_party_evidence_url_reviewed_by_ai_at_user_request',
            source_sha256=hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
            partition='train', original_partition='train', do_not_train=False, repair_reasons=[],
            cohort='bundle_url', roots=[domain], icann_roots=[domain],
            repair_group=groups.get(domain, 'OFFICIAL-G-' + domain)))
    return accepted, decisions


def verify_run(output):
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    for name, expected in protocol['code_sha256'].items():
        if sha(ROOT / name, True) != expected:
            raise ValueError('Training code changed: ' + name)
    for name, expected in protocol['input_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Frozen training input changed: ' + name)
    return protocol


def fit(output=OUT, base_fit=BASE_FIT, data=OUTPUT):
    import numpy as np
    from calibrate_supervised import calibration_metrics, fit_calibrated, group_splits
    from predict import probability
    from predict_hybrid import load_bundle
    from repair_training_data import verify

    verify(data)
    base = load_bundle()
    manifest = json.loads((ROOT / 'models/hybrid_manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['dataset_files_sha256'].items():
        if sha(base_fit / name) != expected:
            raise ValueError('Base training rows are not bound to the active model')
    old_rows = read_jsonl(base_fit / 'url_fit_rows.jsonl')
    sms_rows = read_jsonl(base_fit / 'sms_fit_rows.jsonl')
    for branch in ('sms', 'url'):
        if sha(base_fit / f'{branch}_fit_rows.jsonl') != manifest['source_sha256'][branch + '_train']:
            raise ValueError('Base branch row binding mismatch')
    seed_data = json.loads(SEEDS.read_text(encoding='utf-8'))
    original = read_jsonl(data / 'all_rows.jsonl')
    fitted_ids = {row['case_id'] for row in old_rows + sms_rows}
    excluded = [row for row in original if row['case_id'] not in fitted_ids]
    added, decisions = prepare_seeds(seed_data, old_rows, excluded)
    if not added:
        raise ValueError('No new eligible training seeds')
    rows = old_rows + added
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(ROOT / 'models/hybrid_bundle.pkl', output / 'parent_bundle.pkl')
    shutil.copy2(ROOT / 'models/hybrid_manifest.json', output / 'parent_manifest.json')
    shutil.copy2(SEEDS, output / 'seeds.json')
    write_jsonl(output / 'url_fit_rows.jsonl', rows)
    shutil.copy2(base_fit / 'sms_fit_rows.jsonl', output / 'sms_fit_rows.jsonl')
    write_jsonl(output / 'fit_rows.jsonl', sms_rows + rows)
    write_jsonl(output / 'url_test.jsonl', read_jsonl(data / 'url_test.jsonl'))
    write_json(output / 'seed_decisions.json', decisions)
    names = ('parent_bundle.pkl', 'parent_manifest.json', 'seeds.json', 'seed_decisions.json',
             'fit_rows.jsonl', 'sms_fit_rows.jsonl', 'url_fit_rows.jsonl', 'url_test.jsonl')
    protocol = dict(run_id=RUN_ID, base_bundle_sha256=manifest['bundle_sha256'],
        code_sha256={name: sha(ROOT / name, True) for name in DEPENDENCIES},
        input_sha256={name: sha(output / name) for name in names},
        repaired_dataset_manifest_sha256=sha(data / 'frozen.json'),
        method='sigmoid', outer_group_folds=3, inner_group_folds=3, seed=42,
        url_threshold=.5, new_row_weight=1, sms_head_preserved=True,
        brier_and_log_loss_must_not_increase=True,
        release_max_false_positive_increase=0, release_max_true_positive_decrease=0,
        threshold_selection_performed=False, new_independent_benchmark=False,
        expert_labels_created=0, holdout_rows_fitted=0)
    write_json(output / 'protocol.json', protocol)
    started = time.perf_counter()
    raw, calibrated = np.zeros(len(rows)), np.zeros(len(rows))
    for fold, (train, heldout) in enumerate(group_splits(rows)):
        print(f'URL nested group fold {fold + 1}/3', flush=True)
        model = fit_calibrated(base['url']['model'], [rows[i] for i in train], 'url')
        values = [rows[i]['url'] for i in heldout]
        raw[heldout] = probability(model.calibrated_classifiers_[0].estimator, values)
        calibrated[heldout] = probability(model, values)
    y = [row['label'] for row in rows]
    before, after = calibration_metrics(y, raw), calibration_metrics(y, calibrated)
    gate = after['brier'] <= before['brier'] and after['log_loss'] <= before['log_loss']
    write_jsonl(output / 'url_outer_predictions.jsonl', [dict(case_id=row['case_id'],
        repair_group=row['repair_group'], label=row['label'], raw_score=float(raw[i]),
        calibrated_probability=float(calibrated[i])) for i, row in enumerate(rows)])
    print(f'URL final calibrated fit: {len(rows)} rows, {len(added)} new seeds', flush=True)
    model = fit_calibrated(base['url']['model'], rows, 'url')
    candidate = {**base, 'url': {**base['url'], 'model': model.calibrated_classifiers_[0].estimator,
                 'probability_model': model, 'model_id': RUN_ID + ':url'}, 'training': dict(base['training'])}
    provenance = dict(base['training']['label_provenance_counts'])
    provenance['url'] = dict(Counter(row['label_provenance'] for row in rows))
    candidate['training'].update(run_id=RUN_ID, url_training_samples=len(rows),
        training_manifest_sha256=sha(output / 'fit_rows.jsonl'),
        method='Supervised official URL expansion; train-only nested-group sigmoid calibration; SMS inherited',
        url_label_provenance='Inherited source labels plus first-party URL seeds reviewed by AI; not expert verified',
        label_provenance_counts=provenance, official_url_seed_samples=len(added),
        official_url_reserved_domains=[d['domain'] for d in decisions if d['status'] == 'reserved_domain'])
    (output / 'candidate_bundle.pkl').write_bytes(pickle.dumps(candidate, protocol=pickle.HIGHEST_PROTOCOL))
    report = dict(raw=before, calibrated=after, gate_pass=bool(gate), sms_gate_inherited=True,
                  sms_parent_calibration_report_sha256=manifest['calibration_report_sha256'],
                  seconds=round(time.perf_counter() - started, 3))
    write_json(output / 'calibration_report.json', report)
    candidate_manifest = {**manifest, 'parent_artifact': manifest,
        'bundle_sha256': sha(output / 'candidate_bundle.pkl'), 'training': candidate['training'],
        'source_sha256': {branch + '_train': sha(output / f'{branch}_fit_rows.jsonl') for branch in ('sms', 'url')},
        'dataset_files_sha256': {name: sha(output / name) for name in names},
        'fitted_rows': len(rows) + len(sms_rows), 'test_evaluation_performed': False,
        'fit_code_sha256': sha(Path(__file__), True), 'fit_seconds': report['seconds'],
        'calibration_protocol_sha256': sha(output / 'protocol.json'),
        'calibration_report_sha256': sha(output / 'calibration_report.json'),
        'calibration_gate_pass': bool(gate and manifest['calibration_gate_pass'])}
    write_json(output / 'candidate_manifest.json', candidate_manifest)
    verify_run(output)
    print(json.dumps(dict(added=len(added), decisions=decisions, calibration=report)), flush=True)


def checked_candidate(output):
    protocol = verify_run(output)
    manifest = json.loads((output / 'candidate_manifest.json').read_text(encoding='utf-8'))
    for name, expected in [('candidate_bundle.pkl', manifest['bundle_sha256']),
                           ('protocol.json', manifest['calibration_protocol_sha256']),
                           ('calibration_report.json', manifest['calibration_report_sha256'])]:
        if sha(output / name) != expected:
            raise ValueError('Candidate evidence changed: ' + name)
    for name, expected in manifest['dataset_files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Candidate fit rows changed: ' + name)
    if (manifest['training']['training_manifest_sha256'] != sha(output / 'fit_rows.jsonl')
            or any(manifest['source_sha256'][branch + '_train'] != sha(output / f'{branch}_fit_rows.jsonl')
                   for branch in ('sms', 'url'))):
        raise ValueError('Training manifest/branch binding mismatch')
    return protocol, manifest


def release_gate(before, after, calibration_pass):
    old, new = before['confusion_matrix_tn_fp_fn_tp'], after['confusion_matrix_tn_fp_fn_tp']
    return bool(calibration_pass and new[1] <= old[1] and new[3] >= old[3])


def evaluate(output=OUT):
    import numpy as np
    from predict import probability
    from train_repaired_hybrid import metrics

    _, manifest = checked_candidate(output)
    # Exclusive claim is made before reading historical test predictions.
    with (output / 'evaluation.started').open('x', encoding='utf-8') as claim:
        claim.write(manifest['bundle_sha256'])
    baseline = pickle.loads((output / 'parent_bundle.pkl').read_bytes())
    candidate = pickle.loads((output / 'candidate_bundle.pkl').read_bytes())
    rows = read_jsonl(output / 'url_test.jsonl')
    results = {}
    for name, bundle in [('baseline', baseline), ('candidate', candidate)]:
        scores = np.concatenate([probability(bundle['url']['model'], [r['url'] for r in rows[i:i + 256]])
                                 for i in range(0, len(rows), 256)])
        results[name] = metrics(rows, scores, .5)
        write_jsonl(output / f'{name}_test_predictions.jsonl', [dict(case_id=r['case_id'],
            label=r['label'], score=float(p)) for r, p in zip(rows, scores)])
    seeds = json.loads((output / 'seed_decisions.json').read_text(encoding='utf-8'))
    for site in seeds:
        for name, bundle in [('baseline', baseline), ('candidate', candidate)]:
            site[name + '_score'] = float(probability(bundle['url']['model'], [site['url']])[0])
    report = dict(bundle_sha256=manifest['bundle_sha256'], protocol_sha256=sha(output / 'protocol.json'),
        metrics=results, seed_sanity_checks=seeds, seed_results_are_independent_accuracy=False,
        historical_test_reused=True, new_independent_benchmark=False,
        release_gate_pass=release_gate(results['baseline'], results['candidate'], manifest['calibration_gate_pass']))
    write_json(output / 'evaluation.json', report)
    manifest.update(test_evaluation_performed=True, evaluation_sha256=sha(output / 'evaluation.json'))
    write_json(output / 'candidate_manifest.json', manifest)
    print(json.dumps(report), flush=True)


def activate(output=OUT, models=None):
    models = models or ROOT / 'models'
    protocol, manifest = checked_candidate(output)
    report = json.loads((output / 'evaluation.json').read_text(encoding='utf-8'))
    calibration = json.loads((output / 'calibration_report.json').read_text(encoding='utf-8'))
    if (sha(output / 'evaluation.json') != manifest['evaluation_sha256']
            or report['bundle_sha256'] != manifest['bundle_sha256']
            or report['protocol_sha256'] != manifest['calibration_protocol_sha256']
            or not calibration['gate_pass'] or not manifest['calibration_gate_pass']
            or not report['release_gate_pass']
            or not release_gate(report['metrics']['baseline'], report['metrics']['candidate'], True)
            or sha(models / 'hybrid_bundle.pkl') != protocol['base_bundle_sha256']
            or sha(models / 'hybrid_manifest.json') != protocol['input_sha256']['parent_manifest.json']):
        raise ValueError('Release/calibration gate failed or parent/evidence changed; active model preserved')
    backup = output / 'previous_active'
    backup.mkdir(exist_ok=False)
    for name in ('hybrid_bundle.pkl', 'hybrid_manifest.json'):
        shutil.copy2(models / name, backup / name)
    for source, destination in [('candidate_bundle.pkl', 'hybrid_bundle.pkl'),
                                ('candidate_manifest.json', 'hybrid_manifest.json')]:
        temporary = models / (destination + '.tmp')
        shutil.copy2(output / source, temporary)
        os.replace(temporary, models / destination)
    write_json(output / 'activation.json', dict(activated=RUN_ID, bundle_sha256=manifest['bundle_sha256'],
                                               backup=str(backup)))
    print(json.dumps(dict(activated=RUN_ID, backup=str(backup))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('fit', 'evaluate', 'activate'))
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    {'fit': fit, 'evaluate': evaluate, 'activate': activate}[args.command](args.output)
