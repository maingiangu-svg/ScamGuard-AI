"""Fit fixed supervised heads on repaired train partitions; bind weights to exact row manifests."""
import argparse
import json
import os
import pickle
import shutil
import time
from collections import Counter
from pathlib import Path

import numpy as np
import sklearn
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

from modeling import url_model
from repair_training_data import OUTPUT, ROOT, read_jsonl, sha, verify, write_json, write_jsonl
from round2_experiment import training_model, text_input

RUN_ID = 'hybrid-isolated-20261026'


def fit(directory):
    verify(directory)
    if (directory / 'candidate_bundle.pkl').exists():
        raise ValueError('Fitted artifact already exists; do not refit after seeing test scores')
    protocol = json.loads((directory / 'repair_report.json').read_text(encoding='utf-8'))['protocol']
    started = time.perf_counter()
    heads, counts = {}, {}
    for branch in ('sms', 'url'):
        rows = read_jsonl(directory / f'{branch}_train.jsonl')
        if not rows or any(r['partition'] != 'train' or r['do_not_train'] or r['original_partition'] != 'train' or r['repair_reasons'] for r in rows):
            raise ValueError('Only accepted original training rows may be fitted')
        y = np.array([r['label'] for r in rows])
        if set(y) != {0, 1}:
            raise ValueError('Both labeled classes required')
        print(f'Fitting {branch} on {len(rows)} isolated training rows.', flush=True)
        if branch == 'sms':
            model = training_model(protocol['sms']['variant'])
            weights = np.array([3.0 if r['language'] == 'vi' else 2.0 if r.get('human_verified_by_source') else 1.0 for r in rows])
            model.fit([text_input(r['raw_text']) for r in rows], y, classifier__sample_weight=weights)
        else:
            model = url_model().fit([r['url'] for r in rows], y)
        heads[branch] = {'model': model, 'threshold': protocol[branch]['threshold'], 'model_id': RUN_ID + ':' + branch}
        counts[branch] = len(rows)
    training = {'run_id': RUN_ID, 'method': 'Independent supervised SMS and URL heads refitted after label quarantine and connected group isolation',
                'text_training_samples': counts['sms'], 'url_training_samples': counts['url'],
                'paired_training_samples': 0, 'synthetic_pairs': 0, 'probability_calibrated': False,
                'target': 'SMS project smishing scope; URL upstream good/bad scope',
                'text_label_provenance': 'Mixed source-human, inherited source, AI review and user scope decisions; not all expert verified',
                'url_label_provenance': 'Inherited source good/bad labels; not independently expert verified',
                'registered_domain_isolation': True, 'campaign_independence_proven': False,
                'all_labels_expert_verified': False, 'known_label_conflicts_fitted': 0,
                'heldout_or_quarantined_rows_fitted': 0, 'hyperparameters_retuned': False,
                'training_manifest_sha256': sha(directory / 'frozen.json')}
    bundle = {'artifact_type': 'routed_supervised_models', 'sklearn_version': sklearn.__version__,
              'sms': heads['sms'], 'url': heads['url'], 'training': training, 'paired_fusion_trained': False}
    content = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
    (directory / 'candidate_bundle.pkl').write_bytes(content)
    manifest = {'bundle_sha256': sha(directory / 'candidate_bundle.pkl'),
                'source_sha256': {branch + '_train': sha(directory / f'{branch}_train.jsonl') for branch in heads},
                'code_sha256': {name: sha(ROOT / name, True) for name in
                                ('preprocess.py', 'modeling.py', 'round2_experiment.py', 'audit_vi_holdout.py')},
                'code_hash_normalization': 'CRLF to LF for Windows/Linux parity',
                'training': training, 'fitted_rows': sum(counts.values()), 'test_evaluation_performed': False,
                'fit_code_sha256': sha(Path(__file__), True), 'fit_seconds': round(time.perf_counter() - started, 3),
                'dataset_files_sha256': json.loads((directory / 'frozen.json').read_text(encoding='utf-8'))['files_sha256'],
                'threshold_provenance': {'sms': 'Existing fixed 0.65; inherited historical validation choice, not reselected',
                                         'url': 'Existing fixed 0.50; no threshold selection'}}
    write_json(directory / 'candidate_manifest.json', manifest)
    verify(directory)
    print(json.dumps({'fit_rows': counts, 'bundle_sha256': manifest['bundle_sha256'], 'seconds': manifest['fit_seconds']}), flush=True)


def metrics(rows, scores, threshold):
    y = np.array([r['label'] for r in rows])
    predicted = np.array(scores) >= threshold
    return {'rows': len(rows), 'threshold': threshold, 'labels': dict(Counter(str(r['label']) for r in rows)),
            'confusion_matrix_tn_fp_fn_tp': confusion_matrix(y, predicted, labels=[0, 1]).ravel().tolist(),
            'precision': float(precision_score(y, predicted, zero_division=0)),
            'recall': float(recall_score(y, predicted, zero_division=0)),
            'f1': float(f1_score(y, predicted, zero_division=0))}


def evaluate(directory):
    proof = verify(directory)
    manifest = json.loads((directory / 'candidate_manifest.json').read_text(encoding='utf-8'))
    if sha(directory / 'candidate_bundle.pkl') != manifest['bundle_sha256'] or sha(directory / 'frozen.json') != manifest['training']['training_manifest_sha256']:
        raise ValueError('Fitted artifact/data binding mismatch')
    if (directory / 'evaluation.json').exists():
        raise ValueError('Evaluation already recorded; do not tune on reused tests')
    bundle = pickle.loads((directory / 'candidate_bundle.pkl').read_bytes())
    result = {'run_id': RUN_ID, 'bundle_sha256': manifest['bundle_sha256'], 'proof': proof,
              'holdouts_reused_from_prior_experiments': True, 'new_independent_benchmark': False,
              'all_labels_expert_verified': False, 'metrics': {}}
    for branch in ('sms', 'url'):
        head = bundle[branch]
        for partition in ('validation', 'test'):
            rows = read_jsonl(directory / f'{branch}_{partition}.jsonl')
            if not rows:
                continue
            values = [text_input(r['raw_text']) if branch == 'sms' else r['url'] for r in rows]
            scores = np.concatenate([head['model'].predict_proba(values[start:start + 256])[:, 1]
                                     for start in range(0, len(values), 256)])
            report = metrics(rows, scores, head['threshold'])
            report['by_label_provenance'] = {source: metrics([rows[i] for i in indices], scores[indices], head['threshold'])
                                            for source in sorted({r['label_provenance'] for r in rows})
                                            for indices in [[i for i, r in enumerate(rows) if r['label_provenance'] == source]]}
            report['distinct_repair_groups'] = len({r['repair_group'] for r in rows})
            result['metrics'][branch + '_' + partition] = report
            write_jsonl(directory / f'{branch}_{partition}_predictions.jsonl',
                        [dict(case_id=r['case_id'], label=r['label'], score=float(score),
                              prediction=int(score >= head['threshold'])) for r, score in zip(rows, scores)])
    verify(directory)
    write_json(directory / 'evaluation.json', result)
    print(json.dumps(result), flush=True)


def activate(directory):
    verify(directory)
    manifest = json.loads((directory / 'candidate_manifest.json').read_text(encoding='utf-8'))
    evaluation = json.loads((directory / 'evaluation.json').read_text(encoding='utf-8'))
    if sha(directory / 'candidate_bundle.pkl') != manifest['bundle_sha256'] or evaluation['bundle_sha256'] != manifest['bundle_sha256']:
        raise ValueError('Evaluation and fitted bundle do not match')
    if sha(directory / 'frozen.json') != manifest['training']['training_manifest_sha256'] or sha(Path(__file__), True) != manifest['fit_code_sha256']:
        raise ValueError('Training manifest or fit code changed')
    models = ROOT / 'models'
    backup = directory / 'previous_active'
    backup.mkdir(exist_ok=False)
    for name in ('hybrid_bundle.pkl', 'hybrid_manifest.json'):
        shutil.copyfile(models / name, backup / name)
    manifest.update(test_evaluation_performed=True, evaluation_sha256=sha(directory / 'evaluation.json'))
    # Stage both first; checksum verification fails closed during the brief rename interval.
    shutil.copyfile(directory / 'candidate_bundle.pkl', models / 'hybrid_bundle.tmp')
    write_json(models / 'hybrid_manifest.tmp', manifest)
    os.replace(models / 'hybrid_bundle.tmp', models / 'hybrid_bundle.pkl')
    os.replace(models / 'hybrid_manifest.tmp', models / 'hybrid_manifest.json')
    print(json.dumps({'activated': RUN_ID, 'bundle_sha256': manifest['bundle_sha256'], 'backup': str(backup)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('fit', 'evaluate', 'activate'))
    parser.add_argument('--data', type=Path, default=OUTPUT)
    args = parser.parse_args()
    {'fit': fit, 'evaluate': evaluate, 'activate': activate}[args.command](args.data)
