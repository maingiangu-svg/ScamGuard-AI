"""Read-only label provenance and split audit. No fitting, relabeling or scoring."""
import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zipfile import ZipFile

import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import train_test_split

from audit_vi_holdout import audit_hostnames, template_signature, write_rows
from external_training import RegisteredDomains, semantic_sms_notes, verify_sources
from preprocess import canonicalize_url, clean_messages
from round2_experiment import text_input
from train_meta_fusion import clean_urls, holdout_split, message_groups

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
PREPARED = DATA / 'prepared'
SMS_DIR = PREPARED / 'smishx_training_2026-10-25'
URL_DIR = PREPARED / 'external_training_2026-10-25'
REF = DATA / 'reference/external_2026-10-25'
DEFAULT_OUTPUT = PREPARED / 'integrity_audit_2026-10-26'


def sha(path, normalize=False):
    content = Path(path).read_bytes()
    return hashlib.sha256(content.replace(b'\r\n', b'\n') if normalize else content).hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def exact_sms(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def url_identity(value):
    parts = urlsplit(canonicalize_url(value))
    return urlunsplit(('', parts.netloc, parts.path or '/', parts.query, ''))


def audit_domain_hosts(text, domain):
    """Find extra path-bearing bare/defanged URLs; keep ambiguous prose separate."""
    hosts = set(audit_hostnames(text))
    refanged = re.sub(r'hxxp(?=s?://)', 'http', text, flags=re.I).replace('[.]', '.')
    candidates = set()
    pattern = r'(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}\b'
    for match in re.finditer(pattern, refanged, re.I):
        host = match.group().lower()
        labels = host.split('.')
        if not any('.'.join(labels[i:]) in domain.exact for i in range(len(labels))):
            continue
        path = refanged[match.end():]
        scheme = refanged[max(0, match.start() - 8):match.start()].lower()
        if host.startswith('www.') or path.startswith(('/', '?')) or re.match(r'^:\d+(?:/|\b)', path) or scheme.endswith(('http://', 'https://')):
            hosts.add(host)
        elif host not in hosts:
            candidates.add(host)
    return sorted(hosts), sorted(candidates)


def reference_status(label, labels):
    if not labels:
        return 'no_published_reference_match'
    if len(labels) > 1:
        return 'reference_itself_conflicted'
    return ('agrees_with_published_reference' if label in labels else
            'source_scope_conflict_pending_review')


def url_quality_flags(value):
    flags = []
    if re.search(r'\\[rn]', value):
        flags.append('literal_escaped_line_separator')
    if '\\' in value:
        flags.append('browser_parser_backslash_ambiguity')
    if re.search(r'[\x00-\x1f\x7f]', value):
        flags.append('control_character')
    return flags


def overlap_records(cohort, rows, field, kind):
    index = defaultdict(lambda: defaultdict(list))
    for row in rows:
        values = row[field] if isinstance(row[field], list) else [row[field]]
        for key in set(values) - {''}:
            index[key][row['partition']].append(row['case_id'])
    return [{'cohort': cohort, 'kind': kind, 'key': key, 'left_partition': a,
             'right_partition': b, 'left_case_ids': sorted(roles[a]), 'right_case_ids': sorted(roles[b])}
            for key, roles in sorted(index.items()) for a, b in combinations(
                sorted(roles, key=lambda role: {'train': 0, 'validation': 1, 'test': 2}.get(role, 3)), 2)]


def safe_training_plan(rows):
    """Quarantine connected training groups that touch any existing holdout."""
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, row in enumerate(rows):
        keys = ['domain:' + d for d in row['roots']]
        if row.get('template'):
            keys.append('sms-template:' + row['template'])
        if row.get('source_group'):
            keys.append('source-group:' + row['source_group'])
        for key in keys:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    reserved = {find(i) for i, row in enumerate(rows) if row['partition'] != 'train'}
    tests = {find(i) for i, row in enumerate(rows) if row['partition'] == 'test'}
    output = []
    for i, row in enumerate(rows):
        heldout = row['partition'] != 'train'
        blocked = find(i) in reserved
        validation_blocked = row['partition'] == 'validation' and find(i) in tests
        output.append({'case_id': row['case_id'], 'cohort': row.get('cohort', ''),
                       'partition': row['partition'], 'label': row.get('label'),
                       'conservative_component': 'AUDIT-G-' + str(find(i)),
                       'do_not_train': heldout or blocked,
                       'eligible_under_group_isolation': not heldout and not blocked,
                       'eligible_for_validation': row['partition'] == 'validation' and not validation_blocked,
                       'recommended_partition': 'quarantine' if validation_blocked or (not heldout and blocked) else row['partition'],
                       'reason': 'validation_component_touches_test' if validation_blocked else 'reserved_holdout' if heldout else
                       'training_component_touches_holdout' if blocked else 'no_detected_group_overlap',
                       'campaign_independence_proven': False,
                       'expert_verified': False})
    return output


def reconstruct_bundle(metadata):
    raw = pd.read_csv(DATA / 'smishing_combined.csv').rename(columns={'message': 'raw_text', 'smishing label': 'label'})
    sms, sms_audit = clean_messages(raw)
    train, test = holdout_split(sms.label.to_numpy(), message_groups(sms))
    split_ids = {'sms_train': train.tolist(), 'sms_holdout': test.tolist()}
    sms['partition'] = 'test'
    sms.loc[train, 'partition'] = 'train'
    sms_hosts = {urlsplit(u).hostname for row in sms.urls_json for u in json.loads(row)}
    urls, _ = clean_urls(DATA / 'phishing_site_urls.csv', sms_hosts)
    if len(urls) > 50000:
        _, selected = train_test_split(np.arange(len(urls)), test_size=50000, stratify=urls.label, random_state=42)
        urls = urls.iloc[selected].reset_index(drop=True)
    train, test = holdout_split(urls.label.to_numpy(), urls.host.to_numpy())
    split_ids.update(url_train=train.tolist(), url_holdout=test.tolist())
    urls['partition'] = 'test'
    urls.loc[train, 'partition'] = 'train'
    if len(split_ids['sms_train']) != metadata['text_training_samples'] or len(train) != metadata['url_training_samples']:
        raise ValueError('Reconstructed partition counts do not match the active source model')
    return sms.to_dict('records'), urls.to_dict('records'), split_ids, sms_audit


def source_tables():
    with (DATA / 'reference/english_sms_2026-10-25/smishx/data/dataset.csv').open(encoding='utf-8-sig', newline='') as stream:
        smishx = list(csv.DictReader(stream))
    with ZipFile(REF / 'Dataset_5971.zip') as archive:
        mishra = list(csv.DictReader(io.StringIO(archive.read('Dataset_5971.csv').decode('utf-8-sig'))))
    with (DATA / 'reference/vietnamese_sms_dataset/train.csv').open(encoding='utf-8-sig', newline='') as stream:
        vietnamese = list(csv.DictReader(stream))
    notes = semantic_sms_notes()
    vi_review = {r['case_id']:r for r in read_jsonl(PREPARED / 'review_2026-10-25/round2/latest_train_review_with_user_decisions.jsonl')}
    old_review = {r['source_record']:r for r in read_jsonl(PREPARED / 'review_2026-10-25/sms_200_ai_review.jsonl')}
    return smishx, mishra, vietnamese, notes, vi_review, old_review


def check_sms_trace(row, tables):
    smishx, mishra, vietnamese, notes, vi_review, old_review = tables
    source = row['source']
    n = row.get('source_record')
    # Older exported rows omitted source_record, but retained its exact OLD-N ID.
    if n is None and source == 'project_legacy_review' and re.fullmatch(r'OLD-\d+', row['case_id']):
        n = int(row['case_id'][4:])
    if n is None:
        return 'unresolved_source_record'
    if source == 'smishx':
        original = smishx[n - 1]
        text, label = original['SMS'], int(original['label'] == 'smishing')
        original_label = original['label']
    elif source == 'mishra_soni_5971':
        original = mishra[n - 1]
        text, original_label = original['TEXT'], original['LABEL']
        label = notes[n]['label'] if n in notes else 0 if original_label.lower() in {'ham', 'spam'} else None
    elif source == 'project_reviewed_vi':
        original = vietnamese[n - 1]
        text, original_label = original['message'], original['label']
        label = vi_review[row['case_id']]['resolved_label']
    elif source == 'project_legacy_review':
        original = old_review[n]
        text, label = original['raw_text'], original['proposed_label']
        original_label = original['original_label']
    else:
        return 'unresolved_source'
    return 'matches_recorded_source_and_review' if (
        exact_sms(text) == exact_sms(row['raw_text']) and label == row['label']
        and str(original_label) == str(row['original_label'])) else 'source_trace_mismatch'


def main(output, require_clean=False):
    if output.exists():
        raise ValueError('Audit output already exists; choose a new --output directory')
    report_path = ROOT / 'models/training_report.json'
    metadata = json.loads(report_path.read_text(encoding='utf-8'))['metadata']
    hybrid = json.loads((ROOT / 'models/hybrid_manifest.json').read_text(encoding='utf-8'))
    frozen = json.loads((SMS_DIR / 'selection_frozen.json').read_text(encoding='utf-8'))
    protected = {DATA / n: expected for n, expected in metadata['source_sha256'].items()}
    protected.update({ROOT / 'models/model_bundle.pkl': hybrid['source_sha256']['url'],
                      ROOT / 'models/hybrid_bundle.pkl': hybrid['bundle_sha256']})
    protected.update({SMS_DIR / name: expected for name, expected in frozen['files_sha256'].items()})
    protected[DATA / 'reference/english_sms_2026-10-25/smishx/data/dataset.csv'] = '8d65e373b17477c34e8f1c619e6f59d249e8fca21276cabdd03a55d11a469285'
    if any(sha(p) != expected for p, expected in protected.items()):
        raise ValueError('An input artifact differs from its pinned source hash')
    if sha(ROOT / 'train_meta_fusion.py', True) != metadata['training_code_sha256'] or sha(ROOT / 'data_quality.py') != metadata['data_quality_sha256']:
        raise ValueError('Training/preparation code does not match the selected source run')
    if sklearn.__version__ != metadata['sklearn_version']:
        raise ValueError('Reconstruction requires the source estimator runtime')
    verify_sources()
    for name in ('url_train.jsonl', 'url_validation.jsonl', 'url_test.jsonl', 'url_human_audit_all_200.jsonl'):
        p = URL_DIR / name
        protected[p] = sha(p)
    for p in (ROOT / 'models').glob('*.pkl'):
        protected.setdefault(p, sha(p))
    protected[REF / 'public_suffix_list.dat'] = sha(REF / 'public_suffix_list.dat')
    output.mkdir(parents=True)
    print('Pinned artifacts verified; reconstructing source partitions without fitting.', flush=True)
    sms, urls, ids, sms_audit = reconstruct_bundle(metadata)
    domain = RegisteredDomains((REF / 'public_suffix_list.dat').read_text(encoding='utf-8'))
    cohorts = {'bundle_sms': sms, 'bundle_url': urls, 'processed_sms': [], 'processed_url': []}
    for role in ('train', 'validation', 'test'):
        cohorts['processed_sms'] += read_jsonl(SMS_DIR / (role + '.jsonl'))
        cohorts['processed_url'] += read_jsonl(URL_DIR / ('url_' + role + '.jsonl'))
    overlaps = []
    for cohort, rows in cohorts.items():
        for i, row in enumerate(rows):
            row.setdefault('case_id', cohort.upper() + '-' + str(i))
            row['cohort'] = cohort
            row['label'] = int(row['label'])
            if 'raw_text' in row:
                row['model_extractor_roots'] = sorted({domain(h) for h in audit_hostnames(row['raw_text'])})
                row['hosts'], row['ambiguous_host_candidates'] = audit_domain_hosts(row['raw_text'], domain)
            else:
                row['hosts'] = [urlsplit(row['url']).hostname]
                row['ambiguous_host_candidates'] = []
            row['roots'] = sorted({domain(h) for h in row['hosts']})
            row['template'] = template_signature(row['raw_text']) if 'raw_text' in row else ''
            row['model_input'] = (text_input(row['raw_text']) if cohort == 'processed_sms' else
                                  row.get('normalized_text', '') if cohort == 'bundle_sms' else '')
            row['source_group'] = cohort + ':' + row['group'] if 'group' in row else ''
        for field, kind in [('hosts', 'hostname'), ('roots', 'registered_domain'),
                            ('template', 'sms_template_proxy'), ('model_input', 'identical_sms_model_input')]:
            overlaps += overlap_records(cohort, rows, field, kind)
        write_rows(output, cohort + '_partitions', rows)
        print(cohort, 'rows', len(rows), 'cross-split registered domains',
              sum(r['cohort'] == cohort and r['kind'] == 'registered_domain' for r in overlaps), flush=True)
    old_ids = json.loads((ROOT / 'models/split_ids.json').read_text(encoding='utf-8'))
    split_comparison = {k: old_ids.get(k) == value for k, value in ids.items()}
    (output / 'reconstructed_bundle_split_ids.json').write_text(json.dumps(ids), encoding='utf-8')
    write_rows(output, 'cross_split_overlap', overlaps)
    write_rows(output, 'ambiguous_domain_mentions_pending_review',
               [{'cohort': r['cohort'], 'case_id': r['case_id'], 'partition': r['partition'],
                 'candidates': r['ambiguous_host_candidates'], 'content': r['raw_text']}
                for rows in cohorts.values() for r in rows if r['ambiguous_host_candidates']])

    # Match independent source labels by exact content, never by a plausible name.
    tables = source_tables()
    sms_refs, sms_ref_ids = defaultdict(set), defaultdict(list)
    for i, row in enumerate(tables[0], 1):
        key = exact_sms(row['SMS'])
        sms_refs[key].add(int(row['label'] == 'smishing'))
        sms_ref_ids[key].append('SMISHX-' + str(i))
    audit_rows = read_jsonl(URL_DIR / 'url_human_audit_all_200.jsonl')
    url_refs, url_ref_ids = defaultdict(set), defaultdict(list)
    for row in audit_rows:
        if row['strict_human_test_eligible']:
            key = url_identity(row['url'])
            url_refs[key].add(row['label'])
            url_ref_ids[key].append(row['case_id'])
    phishvn_refs = defaultdict(set)
    with ZipFile(REF / 'PhishVN_v3.1.0_open.zip') as archive:
        phishvn = csv.DictReader(io.StringIO(archive.read('data/dataset_url.csv').decode('utf-8-sig')))
        for row in phishvn:
            try:
                phishvn_refs[url_identity(row['url'])].add(int(row['label'] == 'phishing'))
            except (ValueError, UnicodeError):
                continue
    ledger = []
    for cohort, rows in cohorts.items():
        for row in rows:
            is_sms = 'raw_text' in row
            key = exact_sms(row['raw_text']) if is_sms else url_identity(row['url'])
            refs, ref_ids = (sms_refs, sms_ref_ids) if is_sms else (url_refs, url_ref_ids)
            status = reference_status(row['label'], refs.get(key, set()))
            trace = check_sms_trace(row, tables) if cohort == 'processed_sms' else 'inherited_from_checksum_pinned_source'
            other = phishvn_refs.get(key, set()) if not is_sms else set()
            ledger.append({'cohort': cohort, 'case_id': row['case_id'], 'partition': row['partition'],
                           'assigned_label': row['label'], 'source_trace': trace,
                           'source_record_recovered_from_case_id': cohort == 'processed_sms' and 'source_record' not in row,
                           'label_provenance': row.get('label_provenance', 'weak_keyword_derived' if is_sms else 'inherited_url_source_not_expert_verified'),
                           'reference_status': status, 'reference_case_ids': ref_ids.get(key, []),
                           'reference_relationship': 'same_annotation_source' if row.get('source') == 'smishx' else
                           'different_annotation_source_same_public_message' if refs.get(key) else 'no_reference_match',
                           'reference_labels': sorted(refs.get(key, set())),
                           'url_quality_flags': [] if is_sms else url_quality_flags(row['url']),
                           'other_url_source_labels': sorted(other),
                           'other_url_source_conflict': bool(other and len(other) == 1 and row['label'] not in other),
                           'expert_verified_by_this_audit': False,
                           'human_review_required': status != 'agrees_with_published_reference' or trace == 'source_trace_mismatch',
                           'proposed_corrected_label': None,
                           'content': row['raw_text'] if is_sms else row['url']})
    write_rows(output, 'label_verification_ledger', ledger)
    conflicts = [r for r in ledger if r['reference_status'] in {'source_scope_conflict_pending_review', 'reference_itself_conflicted'}
                 or r['other_url_source_conflict'] or r['source_trace'] == 'source_trace_mismatch']
    write_rows(output, 'label_conflicts_pending_review', conflicts)
    write_rows(output, 'url_format_issues_pending_review', [r for r in ledger if r['url_quality_flags']])

    active = cohorts['processed_sms'] + cohorts['bundle_url']
    combined = overlap_records('active_hybrid_cross_corpus', active, 'roots', 'registered_domain')
    # This conservative combined-corpus check is separate from branch metrics.
    write_rows(output, 'active_combined_domain_overlap', combined)
    plan = safe_training_plan(active)
    write_rows(output, 'future_group_isolation_plan', plan)
    eligible = {r['case_id'] for r in plan if r['eligible_under_group_isolation']}
    reserved = [r for r in active if r['partition'] != 'train']
    kept = [r for r in active if r['case_id'] in eligible]
    remaining_roots = {d for r in kept for d in r['roots']} & {d for r in reserved for d in r['roots']}
    remaining_templates = {r['template'] for r in kept if r['template']} & {r['template'] for r in reserved if r['template']}
    valid_validation = {r['case_id'] for r in plan if r['eligible_for_validation']}
    validation_rows = [r for r in active if r['case_id'] in valid_validation]
    test_rows = [r for r in active if r['partition'] == 'test']
    remaining_val_roots = {d for r in validation_rows for d in r['roots']} & {d for r in test_rows for d in r['roots']}
    remaining_val_templates = {r['template'] for r in validation_rows if r['template']} & {r['template'] for r in test_rows if r['template']}
    assert not remaining_roots and not remaining_templates, 'Conservative exclusion plan did not remove detectable overlap'
    assert not remaining_val_roots and not remaining_val_templates, 'Validation/test exclusion plan did not remove detectable overlap'
    active_ids = {r['case_id'] for r in active if r['partition'] == 'train'}
    write_rows(output, 'active_training_label_review_queue',
               [r for r in ledger if r['cohort'] in {'processed_sms', 'bundle_url'} and r['case_id'] in active_ids and r['human_review_required']])
    summary = {}
    for cohort in cohorts:
        records = [r for r in ledger if r['cohort'] == cohort]
        summary[cohort] = {'rows': len(records),
                           'partitions': dict(Counter(r['partition'] for r in records)),
                           'provenance': dict(Counter(r['label_provenance'] for r in records)),
                           'source_trace': dict(Counter(r['source_trace'] for r in records)),
                           'reference_status': dict(Counter(r['reference_status'] for r in records)),
                           'reference_relationship': dict(Counter(r['reference_relationship'] for r in records)),
                           'training_reference_conflicts': sum(r['partition'] == 'train' and r['reference_status'] == 'source_scope_conflict_pending_review' for r in records),
                           'url_format_issues_by_partition': dict(Counter(r['partition'] for r in records if r['url_quality_flags'])),
                           'other_url_source_conflicts': sum(r['other_url_source_conflict'] for r in records)}
    preserved = all(sha(p) == expected for p, expected in protected.items())
    report = {'date': '2026-10-26', 'operation': 'read_only_label_and_partition_audit',
              'active_model': 'hybrid-20261025', 'source_bundle_run': metadata['run_id'],
              'no_fit_no_relabel_no_test_prediction': True, 'protected_inputs_unchanged': preserved,
              'audit_code_sha256': sha(Path(__file__)),
              'input_sha256': {str(p.relative_to(ROOT)): h for p, h in protected.items()},
              'runtime': {'sklearn': sklearn.__version__, 'numpy': np.__version__, 'pandas': pd.__version__},
              'partition_reconstruction': {'method': 'same pinned source bytes, normalized training code hash, runtime and deterministic sampling/splitting; no fitting',
                                            'matches_reported_counts': True, 'old_split_ids_match': split_comparison,
                                            'old_split_counts': {k: len(old_ids[k]) for k in ids},
                                            'reconstructed_counts': {k: len(v) for k, v in ids.items()},
                                            'original_split_export_bound_to_active_artifact': False},
              'cohorts': summary,
              'overlap_summary': dict(Counter(r['cohort'] + ':' + r['kind'] + ':' + r['left_partition'] + '/' + r['right_partition'] for r in overlaps)),
              'extraction': {'method': 'Union of frozen model URL extraction and PSL-validated path-bearing bare/defanged URL indicators',
                             'ambiguous_bare_mentions': {c:sum(bool(r['ambiguous_host_candidates']) for r in rows) for c,rows in cohorts.items()},
                             'limit': 'Sentence fragments such as Smallie.is are not silently treated as verified domains. Ambiguous mentions remain a separate review queue.'},
              'future_plan': {'counts': dict(Counter(r['reason'] for r in plan)),
                              'remaining_train_holdout_registered_domain_overlap': len(remaining_roots),
                              'remaining_train_holdout_exact_template_overlap': len(remaining_templates),
                              'remaining_validation_test_registered_domain_overlap': len(remaining_val_roots),
                              'remaining_validation_test_exact_template_overlap': len(remaining_val_templates),
                              'applied_to_existing_models': False},
              'campaign_proof': {'status': 'not_proven', 'ground_truth_campaign_ids_available': False,
                                  'method': 'exact SMS templates, identical model inputs, PSL domains and connected-component exclusion plan',
                                  'limit': 'Shared templates/platform domains are proxies, not independently established campaign identities. No archived destination/actor/timestamp coverage for every row.'},
              'label_proof': {'all_labels_independently_verified': False, 'expert_annotations_created': 0,
                              'limit': 'Source SmishX rows match their original annotation source, not an independent re-annotation. Cross-source agreement on the same public message is also not new expert verification. Disagreements may reflect spam/smishing definitions or collection-time changes. No labels are automatically overwritten.'},
              'zero_leakage_certificate': 'FAIL' if combined else 'NOT_PROVEN_CAMPAIGNS',
              'overall': 'FAIL_domain_isolation_and_unresolved_labels',
              'source_sms_cleaning_audit': sms_audit}
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not preserved:
        raise RuntimeError('A protected input changed during the audit')
    print(json.dumps({'output': str(output), 'overall': report['overall'], 'protected_inputs_unchanged': preserved,
                      'old_split_ids_match': split_comparison, 'cohorts': summary}, ensure_ascii=True), flush=True)
    return 2 if require_clean else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--require-clean', action='store_true', help='exit nonzero when the requested no-leakage/all-labels-verified proof is unavailable')
    args = parser.parse_args()
    raise SystemExit(main(args.output, args.require_clean))
