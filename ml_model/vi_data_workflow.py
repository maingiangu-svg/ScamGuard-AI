"""Offline Vietnamese data audit and blind annotation; labels never imply expertise."""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from audit_vi_holdout import template_signature, similarity_edges
from expert_review import digest, display

ROOT = Path(__file__).resolve().parent
PREPARED = ROOT / 'data/prepared'
SOURCE = ROOT / 'data/reference/vietnamese_sms_dataset'
OUT = PREPARED / 'vi_readiness_2026-10-27-final'
LABELS = ('legitimate', 'spam', 'scam')
REVIEW_LABELS = (*LABELS, 'unknown')


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def write_jsonl(path, rows):
    Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_rows(rows, historical, domains, edges=()):
    """Protect whole connected components; historical group bridges count too."""
    if len({r['case_id'] for r in rows}) != len(rows):
        raise ValueError('Repeated case identity')
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def keys(row):
        text = row['raw_text']
        result = ['content:' + digest(' '.join(text.casefold().split())),
                  'template:' + digest(template_signature(text))]
        result += ['domain:' + owner for owner in domains(text)]
        return result

    records = [(*keys(r),) for r in rows + historical]
    for record in records:
        for key in record[1:]:
            parent[find(key)] = find(record[0])
    for a, b in edges:
        parent[find(records[a][0])] = find(records[b][0])
    roles = defaultdict(set)
    for record, row in zip(records, rows + historical):
        role = row.get('role', row.get('source_role', 'unused'))
        roles[find(record[0])].add(role)
    result = []
    for i, row in enumerate(rows):
        group = find(records[i][0])
        seen = roles[group]
        disposition = ('quarantine' if 'quarantine' in seen else
                       'reserved_historical_test' if 'test' in seen else
                       'reserved_historical_validation' if 'validation' in seen else
                       'training_review_candidate')
        result.append(dict(row, group='VI3-' + digest(group)[:16],
                           group_roles=sorted(seen), disposition=disposition,
                           do_not_train=disposition != 'training_review_candidate'))
    return result


def merge_annotations(rows, decisions):
    if set(decisions) - {r['case_id'] for r in rows}:
        raise ValueError('Unknown annotation case')
    result = []
    for row in rows:
        decision = decisions.get(row['case_id'])
        if decision is not None and (decision.get('label') not in REVIEW_LABELS
                or decision.get('input_sha256') != digest(row['raw_text'])
                or decision.get('expert_verified')
                or decision.get('provenance') not in ('ai_semantic_review', 'user_decision')
                or not decision.get('rationale', '').strip()):
            raise ValueError('Invalid annotation identity, label or provenance')
        result.append(dict(row, label=decision['label'] if decision else 'unknown',
            label_provenance=decision['provenance'] if decision else 'pending_review',
            annotation=decision, human_verified=False, expert_verified=False))
    return result


def write_forms(rows, output):
    if not rows or len({r['case_id'] for r in rows}) != len(rows):
        raise ValueError('Nonempty unique annotation membership required')
    output.mkdir(parents=True, exist_ok=False)
    identities = {r['case_id']: dict(input_sha256=digest(r['raw_text']),
                                    display_sha256=digest(display(r['raw_text']))) for r in rows}
    ordered = list(rows)
    random.Random(42).shuffle(ordered)
    fields = ['case_id', 'message', 'input_sha256', 'label', 'reviewer', 'reviewer_kind',
              'reviewed_at', 'evidence', 'rationale']
    for name in ['reviewer-a.csv', 'reviewer-b.csv']:
        with (output / name).open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fields); writer.writeheader()
            for r in ordered:
                writer.writerow(dict.fromkeys(fields, '') | dict(case_id=r['case_id'],
                    message=display(r['raw_text']), input_sha256=digest(r['raw_text'])))
    write_json(output / 'identities.json', identities)


def review_gate(output):
    identities = json.loads((output / 'identities.json').read_text(encoding='utf-8'))
    reviews = []
    for name in ['reviewer-a.csv', 'reviewer-b.csv']:
        with (output / name).open(encoding='utf-8-sig', newline='') as stream:
            records = list(csv.DictReader(stream))
        lookup = {r['case_id']: r for r in records}
        if len(lookup) != len(records) or lookup.keys() != identities.keys():
            raise ValueError('Annotation identity mismatch')
        for case, row in lookup.items():
            identity = identities[case]
            if (row['input_sha256'] != identity['input_sha256']
                    or digest(row['message']) != identity['display_sha256']):
                raise ValueError('Annotation input identity mismatch')
            if row['label'] and row['label'] not in REVIEW_LABELS:
                raise ValueError('Invalid review label')
        reviews.append(lookup)
    counts = Counter()
    for case in identities:
        a, b = [lookup[case] for lookup in reviews]
        def complete(row):
            if not all(row.get(k, '').strip() for k in ['reviewer', 'reviewed_at', 'evidence', 'rationale']):
                return False
            try:
                date.fromisoformat(row['reviewed_at'])
            except ValueError:
                return False
            return row['reviewer_kind'] == 'human' and row['label'] in REVIEW_LABELS
        if not complete(a) or not complete(b):
            counts['pending'] += 1
        elif a['reviewer'].strip().casefold() == b['reviewer'].strip().casefold():
            raise ValueError('Two independent human reviewers are required')
        elif 'unknown' in (a['label'], b['label']):
            counts['unknown'] += 1
        elif a['label'] != b['label']:
            counts['disagreements'] += 1
        else:
            counts['agreed'] += 1
    return dict(cases=len(identities), counts=dict(counts),
                human_review_complete=bool(identities) and counts['agreed'] == len(identities),
                expert_qualifications_verified=False)


def historical_rows(output):
    """Read old role-bearing exports, not inferred model predictions or new labels."""
    history, hashes = {}, {}
    for path in sorted(PREPARED.rglob('*.jsonl')):
        if output == path.parent or output in path.parents:
            continue
        superseded = next((p for p in path.parents if p != PREPARED and
                           (p / 'audit_superseded.json').is_file()), None)
        if superseded:
            notice = json.loads((superseded / 'audit_superseded.json').read_text(encoding='utf-8'))
            if path.relative_to(superseded).as_posix() not in notice['retain_actual_fit_or_scored_exports']:
                continue
        count = 0
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                text = row.get('raw_text') or row.get('url')
                if not isinstance(text, str) or not text.strip():
                    continue
                values = {row.get(k) for k in ['partition', 'original_partition', 'effective_group_partition']}
                roles = values & {'train', 'test', 'validation', 'quarantine'}
                disposition_role = {'training_review_candidate': 'train', 'quarantine': 'quarantine',
                                    'reserved_historical_test': 'test',
                                    'reserved_historical_validation': 'validation'}.get(row.get('disposition'))
                if disposition_role:
                    roles.add(disposition_role)
                if path.stem in ('fit_rows', 'development_predictions') and row.get('source_role') == 'train':
                    roles.add('train')
                if row.get('source_split') == 'provider_test' or 'test' in path.stem.split('_'):
                    roles.add('test')
                if 'validation' in path.stem.split('_'):
                    roles.add('validation')
                if not roles:
                    continue
                for role in roles:
                    history[(text, role)] = dict(raw_text=text, role=role)
                count += 1
        if count:
            hashes[str(path.relative_to(ROOT))] = sha(path)
    return list(history.values()), hashes


def provider_rows():
    def read(name):
        with (SOURCE / name).open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))
    train, test = read('train.csv'), read('test.csv')
    full = read('full_dataset.csv')
    source_sha = sha(SOURCE / 'full_dataset.csv')
    train_index, test_index = defaultdict(list), defaultdict(list)
    for role, records, index in [('train', train, train_index), ('test', test, test_index)]:
        for i, r in enumerate(records, 1):
            index[(r['message'], r['label'])].append(i)
    result = []
    for i, r in enumerate(full, 1):
        key = (r['message'], r['label'])
        if key not in train_index and key not in test_index:
            raise ValueError('Provider full row absent from its train/test exports')
        result.append(dict(case_id=f'VIFULL-{i:04}', raw_text=r['message'],
            original_label=r['label'], source_role='test' if key in test_index else 'train',
            provider_train_records=train_index[key], provider_test_records=test_index[key],
            source_message_id=r['message_id'], source_date=r['date'], source_record=i,
            source='trannguyenthaituan/vietnamese_sms_dataset', license='CC BY 4.0',
            source_sha256=source_sha))
    return result


def prepare(output=OUT):
    from functools import lru_cache
    from audit_training_integrity import audit_domain_hosts
    from external_training import RegisteredDomains, REF, PINS
    if output.exists():
        raise FileExistsError('Preparation already exists; preserve frozen membership and reviews')
    source_hashes = {name: sha(SOURCE / name) for name in ['full_dataset.csv', 'train.csv', 'test.csv', 'README.md']}
    snapshot = json.loads((PREPARED / 'review_2026-10-25/round2/source_snapshot.json').read_text(encoding='utf-8'))
    for name, expected in source_hashes.items():
        key = 'data\\reference\\vietnamese_sms_dataset\\' + name
        if snapshot.get(key) != expected:
            raise ValueError('Pinned Vietnamese source changed: ' + name)
    psl = REF / 'public_suffix_list.dat'
    if sha(psl) != PINS[psl.name]:
        raise ValueError('Pinned Public Suffix List changed')
    content = psl.read_text(encoding='utf-8')
    domain = RegisteredDomains(content)
    icann = RegisteredDomains(content.split('// ===BEGIN PRIVATE DOMAINS===')[0])
    @lru_cache(maxsize=None)
    def domains(text):
        hosts, _ = audit_domain_hosts(text, domain)
        return sorted({owner for h in hosts for owner in [domain(h), icann(h)]})
    rows = provider_rows()
    print('Reading historical training, holdout and quarantine exports.', flush=True)
    history, history_hashes = historical_rows(output)
    print(f'Grouping {len(rows)} source rows against {len(history)} unique historical text/role records.', flush=True)
    # Keep URL-only rows in the owner graph, but out of the SMS similarity matrix.
    historical_sms = [(i, r) for i, r in enumerate(history) if not r['raw_text'].startswith(('http://', 'https://'))]
    queries = [template_signature(r['raw_text']) for r in rows]
    refs = [template_signature(r['raw_text']) for _, r in historical_sms]
    edges = [(a, b) for a, b, _ in similarity_edges(queries, queries, .80) if a < b]
    edges += [(a, len(rows) + historical_sms[b][0]) for a, b, _ in similarity_edges(queries, refs, .80)]
    audited = audit_rows(rows, history, domains, edges)
    for row in audited:
        row['domains'] = domains(row['raw_text'])
        row['input_sha256'] = digest(row['raw_text'])
    output.mkdir(parents=True)
    write_jsonl(output / 'corpus_audit.jsonl', audited)
    write_json(output / 'historical_inputs.json', history_hashes)
    write_json(output / 'similarity_edges.json', edges)
    report = dict(source_rows=len(rows), source_labels=dict(Counter(r['original_label'] for r in rows)),
        groups=len({r['group'] for r in audited}), disposition=dict(Counter(r['disposition'] for r in audited)),
        historical_files=len(history_hashes), historical_text_role_records=len(history),
        source_hashes=source_hashes, psl_sha256=sha(psl), similarity_threshold=.80,
        historical_test_rows_reassigned_to_train=0, fresh_benchmark_rows=0,
        campaign_independence_proven=False, expert_labels_created=0)
    write_json(output / 'audit_report.json', report)
    fields = ['case_id', 'message', 'source_url', 'source_record', 'published_at', 'received_at',
              'message_origin', 'reuse_basis', 'evidence', 'campaign_id', 'campaign_evidence']
    with (output / 'new_messages_intake.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        csv.DictWriter(stream, fields).writeheader()
    write_json(output / 'protocol.json', dict(date='2026-10-27', labels=LABELS, unresolved='unknown',
        ai_labels_authorized_by_user=True, independent_human_review_pending=True,
        new_real_test_target=[300, 500], minimum_per_class=30, minimum_groups_per_class=10,
        test_not_used_for_training_or_selection=True, historical_evaluation_scope='reused_diagnostic_only',
        artifact_changes_authorized=False, source='https://huggingface.co/datasets/trannguyenthaituan/vietnamese_sms_dataset',
        source_hashes=source_hashes, corpus_audit_sha256=sha(output / 'corpus_audit.jsonl'),
        code_sha256=sha(Path(__file__))))
    print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'review-status'])
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output)
    else:
        status = review_gate(args.output)
        print(json.dumps(status))
        if not status['human_review_complete']:
            raise SystemExit(2)
