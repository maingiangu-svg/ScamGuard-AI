"""Isolated three-class supervised SMS experiment; no serving model activation."""
import argparse
import json
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold

from round2_experiment import text_input, training_model
from vi_data_workflow import (LABELS, OUT, PREPARED, ROOT, digest, merge_annotations,
                             read_jsonl, review_gate, sha, write_forms, write_json, write_jsonl)


def redact_message(text):
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', text)
    text = re.sub(r'((?:mat khau|mật khẩu|password)(?:\s+(?:moi|mới))?'
                  r'(?:\s+(?:la|là))?\s*[:=]\s*)\S+', r'\1[SECRET]', text, flags=re.I)
    return re.sub(r'\d{4,}(?:[- ]\d{3,})*', '[NUMBER]', text)


def annotate(output, decisions_path):
    """Reuse explicit old semantic decisions; new decisions are checksum-bound AI/user labels."""
    audit = read_jsonl(output / 'corpus_audit.jsonl')
    if (output / 'reviewed_corpus.jsonl').exists():
        raise FileExistsError('Annotations already frozen; use a separate revision')
    legitimate = {'service_notification', 'authentication_notification', 'public_information',
                  'account_status_notification', 'order_warranty_notification',
                  'service_status_notification', 'telco_service_notification', 'greeting'}
    spam = {'telco_or_service_promotion', 'other_advertisement', 'bonus_or_gambling_promotion',
            'gambling_or_bonus_promotion', 'commercial_promotion', 'out_of_scope_promotion', 'telco_paid_promotion'}
    old = defaultdict(list)
    paths = ['round2/latest_train_review_with_user_decisions.jsonl', 'round2/reviewed_validation.jsonl',
             'round2/test_reviewed_all.jsonl', 'vi_ai_review.jsonl']
    review_root = PREPARED / 'review_2026-10-25'
    for name in paths:
        for r in read_jsonl(review_root / name):
            category = r.get('category') or r.get('ai_category')
            label = r.get('resolved_label', r.get('resolved_review_label', r.get('ai_proposed_label')))
            mapped = ('scam' if label == 1 else 'legitimate' if label == 0 and category in legitimate
                      else 'spam' if label == 0 and category in spam else 'unknown')
            old[r['raw_text']].append((mapped, r))
    decisions = {}
    for row in audit:
        matches = old.get(row['raw_text'], [])
        labels = {label for label, _ in matches}
        if len(labels) == 1 and labels != {'unknown'}:
            label, source = matches[-1]
            decisions[row['case_id']] = dict(label=label, input_sha256=digest(row['raw_text']),
                provenance='user_decision' if source.get('label_provenance') in ('user_scope_decision', 'user_decision')
                else 'ai_semantic_review', rationale=source.get('rationale_vi') or 'Recorded semantic review',
                inherited_review_case=source['case_id'], inherited_category=source.get('category') or source.get('ai_category'),
                expert_verified=False)
    new = json.loads(decisions_path.read_text(encoding='utf-8'))
    decisions.update(new)
    rows = merge_annotations(audit, decisions)
    for row in rows:
        row['model_text'] = redact_message(row['raw_text'])
        if row['annotation'] and row['annotation'].get('redacted_text'):
            row['model_text'] = redact_message(row['annotation']['redacted_text'])
        row['model_text_sha256'] = digest(row['model_text'])
    write_jsonl(output / 'reviewed_corpus.jsonl', rows)
    write_json(output / 'annotations_frozen.json', dict(
        corpus_sha256=sha(output / 'reviewed_corpus.jsonl'), decisions_sha256=sha(decisions_path),
        code_sha256=sha(Path(__file__)), previous_review_hashes={n: sha(review_root / n) for n in paths},
        label_counts=dict(Counter(r['label'] for r in rows)),
        training_labels=dict(Counter(r['label'] for r in training_rows(rows))),
        new_ai_decisions=len(new), expert_labels_created=0,
        independently_human_verified=False))
    chosen = sorted(rows, key=lambda r: digest('vi3-review:' + r['case_id']))
    sample = []
    for label in (*LABELS, 'unknown'):
        sample.extend([r for r in chosen if r['label'] == label][:125])
    # Blind human forms intentionally contain no AI label or model output.
    write_forms([dict(r, raw_text=r['model_text']) for r in sample], output / 'blind_review')
    write_json(output / 'blind_review/source_mapping.json', {r['case_id']: dict(
        source_input_sha256=r['input_sha256'], form_input_sha256=r['model_text_sha256']) for r in sample})
    write_jsonl(output / 'training_review_queue.jsonl', [r for r in rows if not r['do_not_train'] and r['label'] == 'unknown'])
    return json.loads((output / 'annotations_frozen.json').read_text(encoding='utf-8'))


def training_rows(rows):
    return [r for r in rows if r.get('disposition') == 'training_review_candidate'
            and r.get('do_not_train') is False and r.get('label') in LABELS]


def benchmark_gate(rows, fitted_groups, review_directory=None):
    """Readiness preflight only. Actual human review forms must also be verified."""
    counts = Counter(r.get('label') for r in rows)
    groups = {r['group'] for r in rows}
    reasons = []
    if len(rows) < 300:
        reasons.append('fewer_than_300_real_messages')
    if any(counts[label] < 30 for label in LABELS):
        reasons.append('fewer_than_30_messages_in_a_class')
    if any(len({r['group'] for r in rows if r.get('label') == label}) < 10 for label in LABELS):
        reasons.append('fewer_than_10_groups_in_a_class')
    if groups & fitted_groups:
        reasons.append('fitting_group_overlap')
    for field, required in [('message_origin', 'real_received'), ('independently_reviewed', True),
                            ('historical_exposure', False)]:
        if any(r.get(field) != required for r in rows):
            reasons.append('missing_or_invalid_' + field)
    if any(not r.get('reuse_basis') for r in rows):
        reasons.append('reuse_basis_missing')
    if any(r.get('label_provenance') != 'dual_human_review' for r in rows):
        reasons.append('labels_not_dual_human_review')
    if review_directory is None:
        reasons.append('bound_human_review_required')
    elif not review_gate(review_directory)['human_review_complete']:
        reasons.append('human_reviews_incomplete')
    else:
        import csv
        with (review_directory / 'reviewer-a.csv').open(encoding='utf-8-sig', newline='') as stream:
            reviewed = {r['case_id']: r for r in csv.DictReader(stream)}
        if set(reviewed) != {r['case_id'] for r in rows} or any(
                reviewed[r['case_id']]['label'] != r.get('label') or
                reviewed[r['case_id']]['input_sha256'] != digest(r.get('model_text', r['raw_text'])) for r in rows):
            reasons.append('human_reviews_do_not_match_benchmark')
    if any(not r.get('freshness_audit_sha256') for r in rows):
        reasons.append('freshness_audit_required')
    return dict(rows=len(rows), label_counts=dict(counts), groups=len(groups), ready=not reasons,
                reasons=sorted(set(reasons)), campaign_independence_proven=False)


def metrics(rows, predicted):
    actual = [r['label'] for r in rows]
    matrix = confusion_matrix(actual, predicted, labels=list(LABELS))
    y = np.array([label == 'scam' for label in actual])
    p = np.array([label == 'scam' for label in predicted])
    tp, fp, fn, tn = (int((y & p).sum()), int((~y & p).sum()),
                      int((y & ~p).sum()), int((~y & ~p).sum()))
    return dict(rows=len(rows), groups=len({r['group'] for r in rows}),
        classification=classification_report(actual, predicted, labels=list(LABELS),
            output_dict=True, zero_division=0), confusion_matrix=matrix.tolist(), label_order=LABELS,
        scam_binary=dict(tn=tn, fp=fp, fn=fn, tp=tp,
            precision=tp / (tp + fp) if tp + fp else 0,
            recall=tp / (tp + fn) if tp + fn else 0),
        label_provenance=dict(Counter(r['label_provenance'] for r in rows)),
        expert_verified_accuracy=False)


def fit(corpus, output):
    if output.exists():
        raise FileExistsError('Use a new experiment; completed runs cannot be overwritten')
    annotations = json.loads((corpus.parent / 'annotations_frozen.json').read_text(encoding='utf-8'))
    if sha(corpus) != annotations['corpus_sha256']:
        raise ValueError('Frozen annotation corpus changed')
    all_rows = read_jsonl(corpus)
    for r in all_rows:
        if r['input_sha256'] != digest(r['raw_text']) or r['model_text_sha256'] != digest(r['model_text']):
            raise ValueError('Annotated content identity changed')
    rows = training_rows(all_rows)
    if any(r['source_role'] != 'train' for r in rows):
        raise ValueError('Provider test cannot enter fitting')
    for label in LABELS:
        if len({r['group'] for r in rows if r['label'] == label}) < 3:
            raise ValueError('Each class needs at least three training groups: ' + label)
    labels = np.array([r['label'] for r in rows])
    groups = np.array([r['group'] for r in rows])
    texts = np.array([text_input(r.get('model_text', r['raw_text'])) for r in rows], dtype=object)
    folds = list(StratifiedGroupKFold(3, shuffle=True, random_state=42).split(texts, labels, groups))
    for train, validation in folds:
        if set(groups[train]) & set(groups[validation]) or set(labels[train]) != set(LABELS):
            raise ValueError('Invalid grouped development fold')
    output.mkdir(parents=True)
    write_jsonl(output / 'fit_rows.jsonl', rows)
    protocol = dict(corpus_sha256=sha(corpus), fit_rows_sha256=sha(output / 'fit_rows.jsonl'),
        code_sha256=sha(Path(__file__)), configuration='existing_word_char_lr_c1',
        dependency_sha256={name: sha(ROOT / name) for name in
                           ['round2_experiment.py', 'modeling.py', 'preprocess.py', 'vi_data_workflow.py']},
        folds=3, seed=42, decision_rule='three_class_argmax',
        source_labels_preserved=True, test_used_in_selection=False,
        independent_test_available=False, activation_authorized=False,
        runtime_bundle_sha256=sha(ROOT / 'models/hybrid_bundle.pkl'),
        runtime_manifest_sha256=sha(ROOT / 'models/hybrid_manifest.json'))
    write_json(output / 'protocol.json', protocol)
    (output / 'frozen_fit_code.py').write_bytes(Path(__file__).read_bytes())
    predictions = np.empty(len(rows), dtype=object)
    for fold, (train, validation) in enumerate(folds):
        estimator = training_model('word_char')
        estimator.fit(texts[train], labels[train])
        predictions[validation] = estimator.predict(texts[validation])
        for index in validation:
            rows[index]['development_fold'] = fold
    write_jsonl(output / 'development_predictions.jsonl', [dict(r, prediction=p)
                for r, p in zip(rows, predictions)])
    estimator = training_model('word_char')
    estimator.fit(texts, labels)
    with (output / 'research_model.pkl').open('wb') as stream:
        pickle.dump(estimator, stream)
    report = dict(training_rows=len(rows), training_labels=dict(Counter(labels)),
        training_groups=len(set(groups)), development=metrics(rows, predictions),
        development_scope='grouped_training_only_oof_not_independent_test',
        model_sha256=sha(output / 'research_model.pkl'),
        protocol_sha256=sha(output / 'protocol.json'), active_model_changed=False)
    write_json(output / 'fit_report.json', report)
    print(json.dumps(report, ensure_ascii=False))
    return report


def evaluate_diagnostic(corpus, output):
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    report = json.loads((output / 'fit_report.json').read_text(encoding='utf-8'))
    if (sha(corpus) != protocol['corpus_sha256']
            or sha(output / 'fit_rows.jsonl') != protocol['fit_rows_sha256']
            or sha(output / 'research_model.pkl') != report['model_sha256']
            or sha(output / 'protocol.json') != report['protocol_sha256']):
        raise ValueError('Frozen corpus/model/protocol identity changed')
    if (output / 'diagnostic.started').exists():
        raise FileExistsError('Historical diagnostic already used; do not tune against it')
    fitted = read_jsonl(output / 'fit_rows.jsonl')
    fitted_groups = {r['group'] for r in fitted}
    fitted_domains = {d for r in fitted for d in r.get('domains', [])}
    rows = [r for r in read_jsonl(corpus) if r.get('disposition') == 'reserved_historical_test'
            and r.get('label') in LABELS]
    if not rows or any(r['group'] in fitted_groups or fitted_domains.intersection(r.get('domains', [])) for r in rows):
        raise ValueError('Empty or leaking historical diagnostic')
    (output / 'diagnostic.started').write_text(sha(corpus), encoding='utf-8')
    with (output / 'research_model.pkl').open('rb') as stream:
        estimator = pickle.load(stream)
    predicted = estimator.predict([text_input(r.get('model_text', r['raw_text'])) for r in rows])
    write_jsonl(output / 'historical_predictions.jsonl', [dict(r, prediction=p)
                for r, p in zip(rows, predicted)])
    result = dict(scope='reused_historical_ai_label_diagnostic_not_new_benchmark',
                  metrics=metrics(rows, predicted), independent_benchmark=benchmark_gate([], fitted_groups),
                  total_reserved_rows=sum(r.get('disposition') == 'reserved_historical_test' for r in read_jsonl(corpus)),
                  unknown_labels_excluded=True,
                  protocol_sha256=report['protocol_sha256'], model_sha256=report['model_sha256'],
                  active_model_changed=False)
    # Bootstrap by isolated groups; row-wise sampling would overcount repeated templates.
    group_ids, inverse = np.unique([r['group'] for r in rows], return_inverse=True)
    correct = np.array([r['label'] == p for r, p in zip(rows, predicted)], dtype=float)
    sums, sizes = np.bincount(inverse, weights=correct), np.bincount(inverse)
    rng = np.random.default_rng(42)
    draws = [rng.integers(len(group_ids), size=len(group_ids)) for _ in range(1000)]
    result['group_bootstrap_accuracy_95ci'] = np.quantile(
        [sums[d].sum() / sizes[d].sum() for d in draws], [.025, .975]).tolist()
    write_json(output / 'historical_diagnostic.json', result)
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['annotate', 'fit', 'diagnose'])
    parser.add_argument('--corpus', type=Path, default=OUT / 'reviewed_corpus.jsonl')
    parser.add_argument('--output', type=Path, default=OUT / 'experiment')
    parser.add_argument('--decisions', type=Path)
    args = parser.parse_args()
    if args.command == 'annotate':
        print(json.dumps(annotate(args.corpus.parent, args.decisions or args.corpus.parent / 'ai_decisions.json'), ensure_ascii=False))
    else:
        {'fit': fit, 'diagnose': evaluate_diagnostic}[args.command](args.corpus, args.output)
