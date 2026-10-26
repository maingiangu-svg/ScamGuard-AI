"""Train-only cleanlab review; never relabel, refit, or activate the serving model."""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from modeling import url_model
from repair_training_data import OUTPUT, read_jsonl, sha, verify, write_json, write_jsonl
from round2_experiment import training_model, text_input


def validate_training_rows(rows):
    if not rows or len({r['case_id'] for r in rows}) != len(rows):
        raise ValueError('Nonempty, unique training case IDs required')
    for row in rows:
        if (row.get('partition') != 'train' or row.get('original_partition') != 'train'
                or row.get('do_not_train') is not False or row.get('repair_reasons') != []
                or not row.get('repair_group') or not row.get('label_provenance')
                or type(row.get('label')) is not int or row['label'] not in (0, 1)):
            raise ValueError('Only accepted original training rows with group and label provenance are allowed')


def grouped_probabilities(rows, make_model, inputs, folds=5, weights=None):
    validate_training_rows(rows)
    groups = np.array([r['repair_group'] for r in rows])
    labels = np.array([r['label'] for r in rows])
    if folds < 2 or len(set(groups)) < folds or set(labels) != {0, 1} or len(inputs) != len(rows):
        raise ValueError('Two classes, aligned inputs and enough independent groups required')
    probabilities = np.full((len(rows), 2), np.nan)
    assignments = np.full(len(rows), -1)
    proof = []
    splitter = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=42)
    for fold, (train, heldout) in enumerate(splitter.split(inputs, labels, groups)):
        shared = set(groups[train]) & set(groups[heldout])
        if shared or set(labels[train]) != {0, 1} or np.any(assignments[heldout] != -1):
            raise ValueError('Invalid cross-validation fold: leakage, missing class or repeated prediction')
        print(f'Fold {fold + 1}/{folds}: fit {len(train)}, predict {len(heldout)}.', flush=True)
        model = make_model()
        fit_options = {'classifier__sample_weight': np.asarray(weights)[train]} if weights is not None else {}
        model.fit([inputs[i] for i in train], labels[train], **fit_options)
        if list(model.classes_) != [0, 1]:
            raise ValueError('Unexpected probability class ordering')
        probabilities[heldout] = model.predict_proba([inputs[i] for i in heldout])
        assignments[heldout] = fold
        proof.append(dict(fold=fold, train_rows=len(train), heldout_rows=len(heldout),
                          shared_groups=len(shared), train_labels=dict(Counter(map(str, labels[train]))),
                          heldout_labels=dict(Counter(map(str, labels[heldout])))))
    if (np.any(assignments < 0) or not np.isfinite(probabilities).all()
            or np.any((probabilities < 0) | (probabilities > 1))
            or not np.allclose(probabilities.sum(axis=1), 1)):
        raise ValueError('Every training row needs exactly one valid out-of-group probability')
    return probabilities, assignments, proof


def audit(directory, output, folds=5):
    import cleanlab
    from cleanlab.filter import find_label_issues
    from cleanlab.rank import get_label_quality_scores

    isolation = verify(directory)
    protocol = json.loads((directory / 'repair_report.json').read_text(encoding='utf-8'))['protocol']
    output.mkdir(parents=True, exist_ok=False)
    report = dict(cleanlab_version=cleanlab.__version__, folds=folds, seed=42,
                  method='StratifiedGroupKFold using frozen connected repair_group identities',
                  purpose='Training label review candidates only; not an independent model benchmark',
                  labels_changed=0, serving_model_changed=False, expert_labels_created=0,
                  validation_or_test_predictions_used=False, isolation=isolation,
                  frozen_manifest_sha256=sha(directory / 'frozen.json'),
                  audit_code_sha256=sha(Path(__file__), True), branches={})
    for branch in ('sms', 'url'):
        rows = read_jsonl(directory / f'{branch}_train.jsonl')
        validate_training_rows(rows)
        weights = None
        if branch == 'sms':
            inputs = [text_input(r['raw_text']) for r in rows]
            weights = [3.0 if r['language'] == 'vi' else 2.0 if r.get('human_verified_by_source') else 1.0 for r in rows]
            make_model = lambda: training_model(protocol['sms']['variant'])
        else:
            inputs, make_model = [r['url'] for r in rows], url_model
        probabilities, assignments, proof = grouped_probabilities(rows, make_model, inputs, folds, weights)
        labels = np.array([r['label'] for r in rows])
        ranked = find_label_issues(labels, probabilities, return_indices_ranked_by='self_confidence', n_jobs=1)
        quality = get_label_quality_scores(labels, probabilities)
        findings = [dict(case_id=rows[i]['case_id'], repair_group=rows[i]['repair_group'],
                         original_label=rows[i]['label'], original_source_label=rows[i].get('original_label'),
                         label_provenance=rows[i]['label_provenance'], expert_verified=rows[i].get('expert_verified', False),
                         source_record=rows[i].get('source_record'), source_sha256=rows[i].get('source_sha256'),
                         fold=int(assignments[i]), label_quality=float(quality[i]),
                         out_of_group_score=float(probabilities[i, 1]), review_status='unreviewed',
                         expert_label=None) for i in ranked]
        write_jsonl(output / f'{branch}_findings.jsonl', findings)
        # A separate blind queue avoids displaying model suggestions to human annotators.
        write_jsonl(output / f'{branch}_blind_review.jsonl',
                    [dict(case_id=rows[i]['case_id'], input=rows[i].get('raw_text', rows[i].get('url')),
                          expert_label=None, reviewer=None, rationale=None) for i in ranked])
        write_jsonl(output / f'{branch}_out_of_group_predictions.jsonl',
                    [dict(case_id=r['case_id'], fold=int(assignments[i]), original_label=r['label'],
                          score=float(probabilities[i, 1]), label_quality=float(quality[i])) for i, r in enumerate(rows)])
        report['branches'][branch] = dict(rows=len(rows), train_sha256=sha(directory / f'{branch}_train.jsonl'),
                                         labels=dict(Counter(str(r['label']) for r in rows)),
                                         groups=len({r['repair_group'] for r in rows}), candidates=len(findings),
                                         candidates_by_label=dict(Counter(str(r['original_label']) for r in findings)),
                                         candidates_by_provenance=dict(Counter(r['label_provenance'] for r in findings)),
                                         fold_proof=proof)
        write_json(output / 'summary.json', report)
    verify(directory)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=OUTPUT)
    parser.add_argument('--output', type=Path, required=True, help='New, private output directory; do not place under public/')
    parser.add_argument('--folds', type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(audit(args.data, args.output, args.folds), ensure_ascii=False), flush=True)
