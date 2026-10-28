"""Prepare real English SMS additions; no training, scoring or URL requests."""
import argparse
import csv
import hashlib
import json
import re
import sys
import ast
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from audit_training_integrity import audit_domain_hosts
from audit_vi_holdout import template_signature, similarity_edges
from external_training import REF, RegisteredDomains
from round2_experiment import text_input
from smishx_training import export_rows
from vi_data_workflow import audit_rows, historical_rows, sha, write_json, write_forms
from data_quality import repair_url
from audit_training_integrity import url_identity

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data/reference/english_expansion_2026-10-28/ncsu_sms_phishing'
OUT = ROOT / 'data/prepared/english_expansion_2026-10-28'
SOURCE_SHA = 'd125c394af792faeb2b71b3f7100cad3b4cece02aff78cb4ec1fb9e7db90f230'
COMMIT = 'a4f18cedc9909cbf8234eea3c2028080a1e95cd4'


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def parse_message(fields, record):
    # The pinned source has six header names but seven fields in every data row.
    # Preserve the extra fifth field without claiming its undocumented meaning.
    if len(fields) != 7 or not fields[0].isdigit():
        raise ValueError('Unexpected pinned-source message shape')
    return dict(case_id='NCSU-' + fields[0], source_record=record,
        source_message_id=fields[0], source_object_id=fields[1], raw_text=fields[3],
        source_unheaded_field=fields[4], source_time=fields[5], source_time_error=fields[6],
        timestamp_provenance='right_aligned_source_time_columns_extra_field_preserved',
        source='wspr-ncsu/sms-phishing', source_commit=COMMIT, source_sha256=SOURCE_SHA,
        source_label=1, source_label_provenance='authors_url_feed_based_phishing_selection',
        label=None, label_provenance='pending_project_scope_review',
        expert_verified=False, human_verified=False, license='MIT repository; attribution retained',
        do_not_train=True, role='unused')


def assign_partition(row):
    if row['disposition'] != 'training_review_candidate':
        return 'quarantine'
    if 'train' in row['group_roles']:
        return 'train'
    bucket = int(digest(row['group'])[:8], 16) % 10
    return 'test' if bucket == 0 else 'validation' if bucket == 1 else 'train'


def apply_scope(row, decisions):
    decision = decisions.get(row['template_id'])
    scope = decision.get('scope') if decision else 'pending'
    allowed = {'retain_source_phishing', 'exclude_promotion', 'uncertain', 'other_language', 'pending'}
    if scope not in allowed or (decision and not decision.get('rationale', '').strip()):
        raise ValueError('Invalid template scope review')
    accepted = (scope == 'retain_source_phishing' and row.get('language') == 'en'
                and row.get('language_confidence', 0) >= .95)
    if (accepted and row.get('source_label') != 1) or (decision and decision.get('expert_verified')):
        raise ValueError('Scope review cannot invent source targets or expert verification')
    return dict(row, label=1 if accepted else None,
        partition='quarantine' if decision and not accepted else row['partition'],
        original_partition=row['partition'],
        label_provenance='source_feed_phishing_with_ai_template_scope_screen' if accepted else 'pending_or_excluded_scope',
        scope_review=decision, scope_review_provenance='ai_template_content_screen_not_independent_verification',
        expert_verified=False, human_verified=False,
        do_not_train=not (accepted and row['partition'] == 'train'))


def require_train(rows):
    for row in rows:
        if row.get('partition') != 'train' or row.get('do_not_train', True) or type(row.get('label')) is not int or row['label'] not in (0, 1):
            raise ValueError('Heldout, unresolved or quarantined record cannot be training')


def cap_additions(rows):
    counts = Counter()
    result = []
    for row in sorted(rows, key=lambda r: digest(r['case_id'])):
        if not row['do_not_train']:
            template, group = 'template:' + row['template_id'], 'group:' + row['group']
            if counts[template] >= 3 or counts[group] >= 20:
                row = dict(row, partition='quarantine', do_not_train=True,
                           disposition='redundant_template_or_group_cap')
            else:
                counts[template] += 1
                counts[group] += 1
        result.append(row)
    return result


def read_jsonl(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def domains():
    content = (REF / 'public_suffix_list.dat').read_text(encoding='utf-8')
    private = RegisteredDomains(content)
    owner = RegisteredDomains(content.split('// ===BEGIN PRIVATE DOMAINS===')[0])

    @lru_cache(maxsize=200000)
    def keys(text):
        if re.fullmatch(r'https?://[^\s\\]+', text, re.I):
            try:
                hosts = [urlsplit(text).hostname]
            except ValueError:
                hosts, _ = audit_domain_hosts(text, private)
        else:
            hosts, _ = audit_domain_hosts(text, private)
        hosts = [h for h in hosts if h]
        return sorted({'psl:' + private(h) for h in hosts} | {'icann:' + owner(h) for h in hosts})
    return keys


def intake(output=OUT):
    if output.exists():
        raise ValueError('Use a new output directory; never overwrite a data package')
    manifest = json.loads((SOURCE / 'source_manifest.json').read_text(encoding='utf-8'))
    if manifest['commit'] != COMMIT or sha(SOURCE / 'phishing_messages.csv') != SOURCE_SHA:
        raise ValueError('Pinned SMS source mismatch')
    for name, metadata in manifest['files'].items():
        if sha(SOURCE / name) != metadata['sha256']:
            raise ValueError('Source checksum mismatch: ' + name)
    sys.path.insert(0, str(ROOT.parent / '.local-runtime/english-data-libs'))
    from langid.langid import LanguageIdentifier, model
    identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)
    output.mkdir(parents=True)
    write_json(output / 'protocol.json', dict(date='2026-10-28', source_manifest=manifest,
        scope='data preparation only; no fitting or inference', language_method='langid 1.1.6 all 97 languages, normalized confidence >=0.95, at least 5 words',
        language_is_automated_not_verified=True, similarity_threshold=.80,
        novel_group_assignment='sha256(group) mod 10: 0 test; 1 validation; 2..9 train',
        project_scope='Keep source phishing labels only after explicit AI template scope screening; advertisements remain unresolved',
        source_header_repair='All rows have 7 fields for 6 header names; preserve unheaded field 5 and right-align time/error fields 6/7',
        model_sha256={str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'models').glob('*') if p.is_file()},
        code_sha256=sha(Path(__file__))))
    with (SOURCE / 'phishing_messages.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream)
        if next(reader) != ['messageID', 'objectID', 'destination number', 'message', 'time', 'error in time']:
            raise ValueError('Source header changed')
        source = [parse_message(fields, record) for record, fields in enumerate(reader, 1)]
    export_rows(output, 'source_sms', source)
    merged = {}
    for row in source:
        key = text_input(row['raw_text'])
        if key not in merged:
            merged[key] = dict(row, merged_source_records=[], merged_case_ids=[])
        merged[key]['merged_source_records'].append(row['source_record'])
        merged[key]['merged_case_ids'].append(row['case_id'])
    screening = {}
    candidates = []
    for i, row in enumerate(merged.values()):
        template = template_signature(row['raw_text'])
        if template not in screening:
            masked = re.sub(r'(?:https?|hxxps?)://\S+|www\.\S+', ' ', row['raw_text'], flags=re.I)
            words = re.findall(r'[^\W\d_]+', masked)
            lang, score = identifier.classify(masked) if len(words) >= 5 else ('unresolved', 0.)
            screening[template] = (lang, float(score))
        lang, score = screening[template]
        candidates.append(dict(row, template=template, template_id=digest(template),
            language=lang, language_confidence=score,
            language_provenance='automated_langid_1.1.6_not_human_verified'))
        if i % 5000 == 0:
            print(json.dumps(dict(stage='language', completed=i, total=len(merged))), flush=True)
    export_rows(output, 'deduplicated_sms', candidates)
    report = dict(raw_source_rows=len(source), unique_model_inputs=len(candidates),
        unique_templates=len(screening), languages=dict(Counter(r['language'] for r in candidates)),
        english_confident=sum(r['language'] == 'en' and r['language_confidence'] >= .95 for r in candidates))
    write_json(output / 'intake_report.json', report)
    print(json.dumps(report), flush=True)


def group(output=OUT):
    if (output / 'group_frozen.json').exists():
        raise ValueError('Grouping is already frozen')
    candidates = read_jsonl(output / 'deduplicated_sms.jsonl')
    history, hashes = historical_rows(output)
    # The old raw source is already exposed; matching records are never a new test.
    raw_source = ROOT / 'data/smishing_combined.csv'
    with raw_source.open(encoding='utf-8-sig', newline='') as stream:
        history.extend(dict(raw_text=r['message'], role='train') for r in csv.DictReader(stream))
    hashes[str(raw_source.relative_to(ROOT))] = sha(raw_source)
    history = list({(r['raw_text'], r['role']): r for r in history}.values())
    write_json(output / 'historical_inputs.json', hashes)
    base_domains = domains()
    merged_domains = defaultdict(set)
    for row in read_jsonl(output / 'source_sms.jsonl'):
        merged_domains[text_input(row['raw_text'])].update(base_domains(row['raw_text']))

    def key_domains(text):
        return sorted(set(base_domains(text)) | merged_domains.get(text_input(text), set()))
    print(json.dumps(dict(stage='exact_grouping', candidates=len(candidates), historical=len(history))), flush=True)
    initial = audit_rows(candidates, history, key_domains)
    all_rows = candidates + history
    templates = [template_signature(r['raw_text']) for r in all_rows]
    unique = {}
    for i, signature in enumerate(templates):
        if signature:
            unique.setdefault(signature, i)
    query = {}
    for i, r in enumerate(initial):
        if r['disposition'] == 'training_review_candidate' and r['language'] == 'en' and r['language_confidence'] >= .95:
            query.setdefault(templates[i], i)
    print(json.dumps(dict(stage='similarity', queries=len(query), references=len(unique))), flush=True)
    query_text, query_indices = list(query), list(query.values())
    reference_text, reference_indices = list(unique), list(unique.values())
    edges = [(query_indices[a], reference_indices[b]) for a, b, score in
             similarity_edges(query_text, reference_text, .80) if query_indices[a] != reference_indices[b]]
    audited = audit_rows(candidates, history, key_domains, edges)
    for r in audited:
        r['partition'] = assign_partition(r)
        r['do_not_train'] = True
    export_rows(output, 'grouped_sms', audited)
    write_json(output / 'similarity_edges.json', edges)
    counts = Counter(r['template_id'] for r in audited if r['partition'] == 'train')
    examples = {}
    for r in audited:
        if r['partition'] == 'train' and r['language'] == 'en' and r['language_confidence'] >= .95:
            examples.setdefault(r['template_id'], r)
    # Frequent templates first, then deterministic ties; actual review is explicit.
    selected = sorted(examples.values(), key=lambda r: (-counts[r['template_id']], r['template_id']))[:300]
    export_rows(output, 'scope_review_candidates', [dict(r, template_rows=counts[r['template_id']]) for r in selected])
    frozen = dict(historical_files=len(hashes), historical_records=len(history), similarity_edges=len(edges),
        partitions=dict(Counter(r['partition'] for r in audited)),
        confident_english_partitions=dict(Counter(r['partition'] for r in audited if r['language']=='en' and r['language_confidence']>=.95)),
        independent_campaigns_proven=False, independent_human_benchmark=False,
        files_sha256={name:sha(output / name) for name in ['grouped_sms.jsonl', 'deduplicated_sms.jsonl',
            'historical_inputs.json', 'similarity_edges.json', 'scope_review_candidates.jsonl']})
    write_json(output / 'group_frozen.json', frozen)
    print(json.dumps(frozen), flush=True)


def verify_inputs(output):
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    frozen = json.loads((output / 'group_frozen.json').read_text(encoding='utf-8'))
    for name, expected in frozen['files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Frozen grouping input changed: ' + name)
    protected = protocol['model_sha256'] | json.loads((output / 'historical_inputs.json').read_text(encoding='utf-8'))
    for name, expected in protected.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Protected historical/model file changed: ' + name)
    for name, metadata in protocol['source_manifest']['files'].items():
        if sha(SOURCE / name) != metadata['sha256']:
            raise ValueError('Source file changed: ' + name)
    return protected


def export_url_pool(output):
    """Campaign membership is context, never a per-URL adjudication."""
    path = SOURCE / 'phishing_campaigns.csv'
    source_hash = sha(path)
    records = {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        campaigns = list(csv.DictReader(stream))
    for number, campaign in enumerate(campaigns, 1):
        urls = ast.literal_eval(campaign['urls'])
        if not isinstance(urls, list) or any(not isinstance(u, str) for u in urls):
            raise ValueError('Invalid source campaign URL list')
        for original in urls:
            fixed, reason = repair_url(original)
            key = url_identity(fixed) if fixed else 'invalid:' + original
            if key not in records:
                records[key] = dict(case_id='NCSU-URL-' + digest(key)[:20], url=fixed or original,
                    original_urls=[], source_campaign_records=[], related_source_campaign_ids=[],
                    source='wspr-ncsu/sms-phishing/phishing_campaigns.csv', source_commit=COMMIT,
                    source_sha256=source_hash, label=None, original_label=None,
                    label_provenance='source_campaign_association_no_individual_url_verdict',
                    language=None, language_note='SMS language does not determine page language',
                    expert_verified=False, human_verified=False, do_not_train=True,
                    partition='review_pool', repair_action=reason,
                    evidence_note='Campaign file includes phishing-associated and potentially benign/opt-out URLs; no per-URL verdict exported',
                    source_time_ranges=[], license='MIT repository; attribution retained')
            row = records[key]
            row['original_urls'].append(original)
            row['source_campaign_records'].append(number)
            row['related_source_campaign_ids'].append(campaign['campaignID'])
            row['source_time_ranges'].append([campaign['start timestamp'], campaign['stop timestamp']])
    export_rows(output, 'url_source_review_pool', list(records.values()))
    return dict(source_campaigns=len(campaigns), unique_url_candidates=len(records),
                individually_verified_url_labels=0, english_page_language_verified=0)


def finalize(output=OUT):
    if (output / 'final_report.json').exists():
        raise ValueError('Completed data packages are immutable')
    protected = verify_inputs(output)
    notes = json.loads((output / 'scope_decisions.json').read_text(encoding='utf-8'))
    if notes['source_sha256'] != SOURCE_SHA or notes['review_candidates_sha256'] != sha(output / 'scope_review_candidates.jsonl'):
        raise ValueError('Scope decisions do not match the frozen review sample')
    sample = {r['template_id']:r for r in read_jsonl(output / 'scope_review_candidates.jsonl')}
    decisions = notes['decisions']
    if set(decisions) != set(sample):
        raise ValueError('Every sampled template needs an explicit review decision')
    for key, decision in decisions.items():
        if decision['representative_case_id'] != sample[key]['case_id'] or decision['input_sha256'] != digest(sample[key]['raw_text']):
            raise ValueError('Scope review identity mismatch')
    rows = [apply_scope(r, decisions) for r in read_jsonl(output / 'grouped_sms.jsonl')]
    active = ROOT / 'data/prepared/url_regression_repair_final_2026-10-27/sms_fit_rows.jsonl'
    baseline = [r for r in read_jsonl(active) if r.get('language') == 'en']
    require_train(baseline)
    baseline_inputs = {text_input(r['raw_text']):r['label'] for r in baseline}
    for row in rows:
        key = text_input(row['raw_text'])
        if key in baseline_inputs:
            row.update(partition='quarantine', do_not_train=True,
                disposition='active_model_input_duplicate_or_label_conflict')
    accepted_before_caps = sum(not r['do_not_train'] for r in rows)
    rows = cap_additions(rows)
    additions = [r for r in rows if not r['do_not_train']]
    require_train(additions)
    if not additions:
        raise ValueError('No qualified new training additions')
    merged = baseline + additions
    if len({text_input(r['raw_text']) for r in merged}) != len(merged):
        raise ValueError('New training data overlaps active model input identities')
    exports = {'sms_train_additions':additions, 'sms_train_english_merged':merged,
        'sms_validation_candidates':[r for r in rows if r['partition']=='validation' and r['language']=='en' and r['language_confidence']>=.95],
        'sms_test_candidates':[r for r in rows if r['partition']=='test' and r['language']=='en' and r['language_confidence']>=.95],
        'sms_training_review_pool':[r for r in rows if r['partition']=='train' and r['label'] is None and r['language']=='en' and r['language_confidence']>=.95],
        'sms_quarantine':[r for r in rows if r['partition']=='quarantine' or r['language']!='en' or r['language_confidence']<.95 or
                          (r.get('scope_review') and r['scope_review']['scope']!='retain_source_phishing')]}
    for name, values in exports.items():
        export_rows(output, name, values)
    membership = [dict(source_record=record, case_id=r['case_id'], group=r['group'], partition=r['partition'],
        label=r['label'], language=r['language'], do_not_train=r['do_not_train'],
        scope=(r.get('scope_review') or {}).get('scope','pending'), disposition=r['disposition'])
        for r in rows for record in r['merged_source_records']]
    if sorted(r['source_record'] for r in membership) != list(range(1,68030)):
        raise ValueError('Source membership does not reconcile every raw row')
    export_rows(output, 'source_membership', membership)
    test_groups = {}
    for row in exports['sms_test_candidates']:
        test_groups.setdefault(row['group'], row)
    if test_groups:
        write_forms(list(test_groups.values())[:150], output / 'blind_holdout_review')
    urls = export_url_pool(output)
    for name, expected in protected.items():
        if sha(ROOT / name) != expected:
            raise ValueError('Protected input changed during preparation')
    key_domains = domains()
    train_domains = {d for r in additions for d in key_domains(r['raw_text'])}
    overlap = {}
    for role in ['validation','test']:
        held = exports['sms_' + role + '_candidates']
        overlap[role] = len(train_domains & {d for r in held for d in key_domains(r['raw_text'])})
        if overlap[role] or {r['group'] for r in additions} & {r['group'] for r in held}:
            raise ValueError('New data split isolation failed')
    (output / 'workflow_code.py').write_bytes(Path(__file__).read_bytes())
    report = dict(date='2026-10-28', source_rows=68029, source_membership_reconciled=True,
        exports={name:len(values) for name,values in exports.items()},
        baseline_english_rows=len(baseline), baseline_english_positive=sum(r['label']==1 for r in baseline),
        added_positive=len(additions), added_groups=len({r['group'] for r in additions}),
        accepted_before_redundancy_caps=accepted_before_caps,
        redundancy_caps=dict(max_per_template=3, max_per_group=20),
        merged_english_labels=dict(Counter(str(r['label']) for r in merged)),
        scope_review_decisions=dict(Counter(d['scope'] for d in decisions.values())),
        train_holdout_domain_overlap=overlap, historical_and_model_hashes_unchanged=True,
        source_label_scope_screen='AI review of explicit templates; retained source feed targets; variants inherit template screen, not independent expert labels',
        human_benchmark_complete=False, expert_labels_created=0, model_trained=False,
        url_pool=urls, files_sha256={p.name:sha(p) for p in sorted(output.glob('*')) if p.is_file()})
    write_json(output / 'final_report.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['intake', 'group', 'finalize'])
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    {'intake': intake, 'group': group, 'finalize': finalize}[args.command](args.output)
