"""Quarantine known label issues and isolate existing holdouts before fresh fitting."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from audit_training_integrity import (audit_domain_hosts, check_sms_trace, read_jsonl,
                                      sha, source_tables, url_identity, url_quality_flags)
from audit_vi_holdout import similarity_edges, template_signature
from external_training import PINS, REF, RegisteredDomains, verify_sources
from round2_experiment import text_input

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / 'data/prepared/integrity_audit_2026-10-26-final'
OUTPUT = ROOT / 'data/prepared/repaired_training_2026-10-26-final'


def content_key(row):
    return ('sms:' + row['model_input'] if row['cohort'] == 'processed_sms'
            else 'url:' + url_identity(row['url']))


def group_keys(row):
    keys = ['domain:' + root for root in row['roots'] if root]
    for field in ('template', 'source_group', 'campaign_id'):
        if row.get(field):
            keys.append(field + ':' + row[field])
    keys.append(content_key(row))
    return keys


def require_isolation(rows, edges=(), require_campaigns=False, require_expert=False):
    """Independent post-repair key intersection check; quarantine is excluded."""
    roles = defaultdict(set)
    retained = {i for i, row in enumerate(rows) if row['partition'] != 'quarantine'}
    for i in retained:
        row = rows[i]
        if row.get('repair_reasons') or (row['partition'] == 'train' and
                                        (row.get('do_not_train', False) or row.get('original_partition', 'train') != 'train')):
            raise ValueError('Unresolved label/format issue or heldout row in retained partition')
        for key in group_keys(rows[i]):
            roles[key].add(rows[i]['partition'])
    overlap = [key for key, partitions in roles.items() if len(partitions) > 1]
    cross_edges = sum(a in retained and b in retained and rows[a]['partition'] != rows[b]['partition']
                      for a, b in edges)
    if overlap or cross_edges:
        raise ValueError('Split isolation failed: shared domain/content/group/similarity')
    campaigns = bool(retained) and all(rows[i].get('campaign_id') and
                                     rows[i].get('campaign_verified_by_source') for i in retained)
    experts = bool(retained) and all(rows[i].get('expert_verified') for i in retained)
    if require_campaigns and not campaigns:
        raise ValueError('Missing verified campaign metadata; campaign independence is unproven')
    if require_expert and not experts:
        raise ValueError('Missing independent expert label verification')
    return {'cross_partition_keys': overlap, 'cross_partition_similarity_edges': int(cross_edges),
            'registered_domain_isolation': 'PASS', 'content_group_isolation': 'PASS',
            'overlap_counts_by_pair': {a + '/' + b: {kind: len({key for key, partitions in roles.items()
                                                              if key.startswith(kind + ':') and {a, b} <= partitions})
                                                    for kind in ('domain', 'sms', 'url', 'template', 'source_group', 'campaign_id')}
                                       for a, b in (('train', 'validation'), ('train', 'test'), ('validation', 'test'))},
            'campaign_independence_proven': bool(campaigns), 'all_labels_expert_verified': bool(experts)}


def repair_rows(rows, edges=()):
    """Preserve labels and original roles; remove earlier-role members of connected groups."""
    if len({row['case_id'] for row in rows}) != len(rows):
        raise ValueError('Duplicate case IDs')
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen, labels = {}, defaultdict(set)
    for i, row in enumerate(rows):
        if type(row['label']) is not int or row['label'] not in (0, 1):
            raise ValueError('Labels must be explicit integers 0/1')
        if row['partition'] not in ('train', 'validation', 'test'):
            raise ValueError('Unknown original partition')
        if not row.get('source_trace') or not row.get('label_provenance'):
            raise ValueError('Missing label evidence')
        labels[content_key(row)].add(row['label'])
        for key in group_keys(row):
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    for a, b in edges:
        parent[find(a)] = find(b)
    members = defaultdict(list)
    for i, row in enumerate(rows):
        members[find(i)].append(row)
    priority = {'train': 0, 'validation': 1, 'test': 2}
    roles = {key: max((r['partition'] for r in values), key=priority.get) for key, values in members.items()}
    groups = {key: 'REPAIR-G-' + hashlib.sha256('|'.join(sorted(r['case_id'] for r in values)).encode()).hexdigest()[:20]
              for key, values in members.items()}
    output = []
    for i, row in enumerate(rows):
        reasons = []
        if row['partition'] != roles[find(i)]:
            reasons.append('connected_group_reserved_for_' + roles[find(i)])
        if row.get('reference_status') in ('source_scope_conflict_pending_review', 'reference_itself_conflicted') or row.get('other_url_source_conflict'):
            reasons.append('reference_label_conflict')
        if row['source_trace'] not in ('matches_recorded_source_and_review', 'inherited_from_checksum_pinned_source'):
            reasons.append('source_trace_unresolved')
        if len(labels[content_key(row)]) > 1:
            reasons.append('identical_model_input_label_conflict')
        if row.get('url_quality_flags'):
            reasons.append('malformed_or_ambiguous_url')
        if row.get('ambiguous_host_candidates'):
            reasons.append('ambiguous_domain_mention')
        partition = 'quarantine' if reasons else row['partition']
        output.append(dict(row, original_partition=row['partition'], partition=partition,
                           do_not_train=partition != 'train', repair_group=groups[find(i)],
                           repair_reasons=reasons, expert_verified_by_repair=False))
    return output, require_isolation(output, edges)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=True) + '\n' for row in rows), encoding='utf-8')


def prepare(output=OUTPUT):
    import csv
    from data_quality import repair_url

    if output.exists():
        raise ValueError('Output already exists; frozen partitions must not be overwritten')
    pins = json.loads((AUDIT / 'output_sha256.json').read_text(encoding='utf-8'))
    audit = json.loads((AUDIT / 'report.json').read_text(encoding='utf-8'))
    # The old active hybrid artifact is historical; no fitted estimator is reused.
    inputs = {ROOT / name.replace('\\', '/'): expected for name, expected in audit['input_sha256'].items()
              if name.replace('\\', '/') != 'models/hybrid_bundle.pkl'}
    for name in ('processed_sms_partitions.jsonl', 'bundle_url_partitions.jsonl', 'label_verification_ledger.jsonl'):
        inputs[AUDIT / name] = pins[name]
    for path, expected in inputs.items():
        if sha(path) != expected:
            raise ValueError('Pinned input mismatch: ' + str(path))
    verify_sources()
    domain = RegisteredDomains((REF / 'public_suffix_list.dat').read_text(encoding='utf-8'))
    tables = source_tables()
    with (ROOT / 'data/phishing_site_urls.csv').open(encoding='utf-8-sig', newline='') as stream:
        originals = list(csv.DictReader(stream))
    ledger = {(r['cohort'], r['case_id']): r for r in read_jsonl(AUDIT / 'label_verification_ledger.jsonl')}
    rows = read_jsonl(AUDIT / 'processed_sms_partitions.jsonl') + read_jsonl(AUDIT / 'bundle_url_partitions.jsonl')
    for row in rows:
        evidence = ledger[(row['cohort'], row['case_id'])]
        if evidence['assigned_label'] != row['label']:
            raise ValueError('Ledger label does not match source row')
        for name in ('reference_status', 'reference_case_ids', 'reference_relationship', 'reference_labels',
                     'source_trace', 'label_provenance', 'other_url_source_conflict'):
            row[name] = evidence[name]
        content = row.get('raw_text', row.get('url'))
        row['hosts'], row['ambiguous_host_candidates'] = audit_domain_hosts(content, domain)
        row['roots'] = sorted({domain(h) for h in row['hosts']})
        row['expert_verified'] = False
        if row['cohort'] == 'processed_sms':
            row['source_trace'] = check_sms_trace(row, tables)
            row['model_input'], row['template'] = text_input(content), template_signature(content)
        else:
            original = originals[row['source_record'] - 1]
            fixed, _ = repair_url(original['URL'])
            if fixed != row['url'] or original['Label'].strip().lower() not in ('good', 'bad') or int(original['Label'].strip().lower() == 'bad') != row['label']:
                raise ValueError('URL source label or content trace mismatch')
            row['source_sha256'] = audit['input_sha256']['data\\phishing_site_urls.csv']
            row['url_quality_flags'] = url_quality_flags(content)
    sms_indices = [i for i, row in enumerate(rows) if row['cohort'] == 'processed_sms' and row['template']]
    signatures = [rows[i]['template'] for i in sms_indices]
    print('Rechecking near-duplicate SMS groups at fixed cosine >= 0.80.', flush=True)
    edges = [(sms_indices[a], sms_indices[b]) for a, b, _ in similarity_edges(signatures, signatures, .80) if a < b]
    repaired, proof = repair_rows(rows, edges)
    proof.update({'similarity_threshold': .80, 'similarity_edges_checked': len(edges),
                  'label_changes': 0, 'new_expert_labels': 0,
                  'known_reference_conflicts_retained': sum(r['partition'] != 'quarantine' and 'reference_label_conflict' in r['repair_reasons'] for r in repaired),
                  'holdout_promoted_to_training': sum(r['partition'] == 'train' and r['original_partition'] != 'train' for r in repaired),
                  'campaign_limit': 'Missing verified campaign IDs/actor/destination/timestamps; content groups are proxies only.',
                  'evaluation_status': 'Reused historical holdouts; not a new untouched benchmark.'})
    output.mkdir(parents=True)
    write_jsonl(output / 'all_rows.jsonl', repaired)
    write_json(output / 'similarity_edges.json', edges)
    for branch, cohort in (('sms', 'processed_sms'), ('url', 'bundle_url')):
        for partition in ('train', 'validation', 'test', 'quarantine'):
            write_jsonl(output / f'{branch}_{partition}.jsonl', [r for r in repaired if r['cohort'] == cohort and r['partition'] == partition])
    summary = {branch: {partition: {'rows': len(selected), 'labels': dict(Counter(str(r['label']) for r in selected)),
                                    'label_provenance': dict(Counter(r['label_provenance'] for r in selected))}
                       for partition in ('train', 'validation', 'test', 'quarantine')
                       for selected in [[r for r in repaired if r['cohort'] == cohort and r['partition'] == partition]]}
               for branch, cohort in (('sms', 'processed_sms'), ('url', 'bundle_url'))}
    report = {'date': '2026-10-26', 'operation': 'applied_quarantine_and_group_isolation',
              'before': {c: dict(Counter(r['partition'] for r in rows if r['cohort'] == c)) for c in ('processed_sms', 'bundle_url')},
              'after': summary, 'quarantine_reasons': dict(Counter(reason for r in repaired for reason in r['repair_reasons'])),
              'proof': proof, 'psl_sha256': PINS['public_suffix_list.dat'],
              'protocol': {'sms': {'variant': 'word_char', 'threshold': .65, 'weights': 'vi=3, source-human=2, other=1'},
                           'url': {'estimator': 'modeling.url_model', 'threshold': .5},
                           'hyperparameter_or_threshold_selection': False, 'fit_on_train_only': True}}
    write_json(output / 'repair_report.json', report)
    if any(sha(path) != expected for path, expected in inputs.items()):
        raise RuntimeError('Input changed during preparation')
    files = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    write_json(output / 'frozen.json', {'files_sha256': files,
                                      'input_sha256': {p.relative_to(ROOT).as_posix(): h for p, h in inputs.items()},
                                      'code_sha256': {name: sha(ROOT / name, True) for name in
                                                      ('repair_training_data.py', 'audit_training_integrity.py', 'audit_vi_holdout.py',
                                                       'external_training.py', 'round2_experiment.py', 'modeling.py', 'preprocess.py',
                                                       'train_repaired_hybrid.py')}})
    print(json.dumps({'after': summary, 'proof': proof}), flush=True)


def verify(output=OUTPUT, require_campaigns=False, require_expert=False):
    frozen = json.loads((output / 'frozen.json').read_text(encoding='utf-8'))
    for name, expected in frozen['files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Frozen dataset checksum mismatch: ' + name)
    for name, expected in frozen['code_sha256'].items():
        if sha(ROOT / name, True) != expected:
            raise ValueError('Frozen preparation code checksum mismatch: ' + name)
    for name, expected in frozen['input_sha256'].items():
        if sha(ROOT / name.replace('\\', '/')) != expected:
            raise ValueError('Pinned input checksum mismatch: ' + name)
    rows = read_jsonl(output / 'all_rows.jsonl')
    domain = RegisteredDomains((REF / 'public_suffix_list.dat').read_text(encoding='utf-8'))
    for row in rows:
        content = row.get('raw_text', row.get('url'))
        hosts, ambiguous = audit_domain_hosts(content, domain)
        if row['roots'] != sorted({domain(h) for h in hosts}) or row['ambiguous_host_candidates'] != ambiguous:
            raise ValueError('Domain evidence does not match raw content')
        if row['cohort'] == 'processed_sms' and (row['model_input'] != text_input(content) or row['template'] != template_signature(content)):
            raise ValueError('SMS grouping evidence does not match raw content')
    edges = json.loads((output / 'similarity_edges.json').read_text(encoding='utf-8'))
    proof = require_isolation(rows, edges, require_campaigns, require_expert)
    # Partition exports must be an exact projection of the bound row manifest.
    for branch, cohort in (('sms', 'processed_sms'), ('url', 'bundle_url')):
        for partition in ('train', 'validation', 'test', 'quarantine'):
            expected = [r for r in rows if r['cohort'] == cohort and r['partition'] == partition]
            if read_jsonl(output / f'{branch}_{partition}.jsonl') != expected:
                raise ValueError('Partition export mismatch')
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify'))
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--require-campaigns', action='store_true')
    parser.add_argument('--require-expert-labels', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output)
    else:
        try:
            print(json.dumps(verify(args.output, args.require_campaigns, args.require_expert_labels)))
        except ValueError as error:
            print(str(error))
            raise SystemExit(2)
