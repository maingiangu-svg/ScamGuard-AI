"""Admit unused source-labeled English ham; no inference or model fitting."""
import argparse
import io
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

from audit_vi_holdout import similarity_edges, template_signature
from english_data_expansion import cap_additions, digest, domains, read_jsonl, require_train
from round2_experiment import text_input
from smishx_training import export_rows
from vi_data_workflow import audit_rows, historical_rows, sha, write_json

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data/reference/uci_sms_spam_collection.zip'
SOURCE_SHA = '1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3'
BASE = ROOT / 'data/prepared/english_sms_training_2026-10-28/sms_fit_rows.jsonl'
OUT = ROOT / 'data/prepared/english_ham_expansion_2026-10-28'


def parse_source(content):
    rows = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        # Do not execute or extract archive paths. Preserve embedded tab characters.
        text = archive.read('SMSSpamCollection').decode('utf-8-sig')
    for number, line in enumerate(text.split('\n'), 1):
        line = line.rstrip('\r')
        if not line:
            continue
        label, separator, message = line.partition('\t')
        if label not in ('ham', 'spam') or not separator or not message.strip():
            raise ValueError('Invalid UCI record at line ' + str(number))
        if label == 'ham':
            rows.append(dict(case_id=f'UCI-HAM-{number}', source_record=number, raw_text=message,
                source='UCI SMS Spam Collection', source_url='https://archive.ics.uci.edu/dataset/228/sms+spam+collection',
                source_sha256=SOURCE_SHA, source_label='ham', label=0,
                label_provenance='uci_source_ham_proxy_not_expert_smishing_verdict',
                license='Original archive readme license/disclaimer; attribution retained',
                expert_verified=False, human_verified=False,
                human_verified_by_source=False, do_not_train=True, role='unused'))
    return rows


def deduplicate(rows):
    merged = {}
    for row in rows:
        key = text_input(row['raw_text'])
        if key not in merged:
            merged[key] = dict(row, merged_source_records=[], variant_texts=[],
                               template_id=digest(template_signature(row['raw_text'])))
        merged[key]['merged_source_records'].append(row['source_record'])
        if row['raw_text'] not in merged[key]['variant_texts']:
            merged[key]['variant_texts'].append(row['raw_text'])
    return list(merged.values())


def admit(row, fitted_inputs):
    reason = ('already_fitted_model_input' if text_input(row['raw_text']) in fitted_inputs else
              'source_target_mismatch' if row.get('source_label') != 'ham' or type(row.get('label')) is not int or row['label'] != 0 else
              'protected_historical_component' if row.get('disposition') != 'training_review_candidate' or
                  set(row.get('group_roles', [])) & {'test', 'validation', 'quarantine'} else
              'language_not_confident_english' if row.get('language') != 'en' or row.get('language_confidence', 0) < .95 else
              '')
    return dict(row, partition='quarantine' if reason else 'train',
                original_partition='quarantine' if reason else 'train',
                do_not_train=bool(reason), admission_reason=reason or 'source_ham_isolated_training_only')


def historical_group_edges(history, hashes, offset):
    """Retain earlier connected groups even when their original edges are absent."""
    indices = {r['raw_text']: offset+i for i, r in enumerate(history)}
    edges = set()
    for name in hashes:
        path = ROOT / name
        if path.suffix != '.jsonl':
            continue
        first = {}
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                index = indices.get(row.get('raw_text') or row.get('url'))
                if index is None:
                    continue
                for field in ('repair_group', 'group', 'group_id'):
                    group = row.get(field)
                    if not isinstance(group, str) or not group:
                        continue
                    key = (field, group)
                    previous = first.setdefault(key, index)
                    if previous != index:
                        edges.add((previous, index))
    return sorted(edges)


def prepare(output=OUT):
    if output.exists():
        raise ValueError('Use a new output; never overwrite an experiment')
    if sha(SOURCE) != SOURCE_SHA:
        raise ValueError('Pinned UCI archive mismatch')
    output.mkdir(parents=True)
    (output / 'prepare_code.py').write_bytes(Path(__file__).read_bytes())
    base = read_jsonl(BASE)
    require_train(base)
    source = parse_source(SOURCE.read_bytes())
    candidates = deduplicate(source)
    export_rows(output, 'source_ham', source)
    with zipfile.ZipFile(SOURCE) as archive:
        (output / 'source_readme.txt').write_bytes(archive.read('readme'))
    protected = {str(p.relative_to(ROOT)): sha(p) for p in [SOURCE, BASE,
        ROOT / 'models/hybrid_bundle.pkl', ROOT / 'models/hybrid_manifest.json']}
    print('Reading historical roles and groups', flush=True)
    history, hashes = historical_rows(output)
    # Previously inspected raw Combined data is exposed training material, not a fresh test.
    import csv
    raw_source = ROOT / 'data/smishing_combined.csv'
    with raw_source.open(encoding='utf-8-sig', newline='') as stream:
        history.extend(dict(raw_text=r['message'], role='train') for r in csv.DictReader(stream))
    hashes[str(raw_source.relative_to(ROOT))] = sha(raw_source)
    history = list({(r['raw_text'], r['role']): r for r in history}.values())
    write_json(output / 'historical_inputs.json', hashes)
    edges = historical_group_edges(history, hashes, len(candidates))
    print(f'Historical records {len(history)}; retained group edges {len(edges)}', flush=True)
    key_domains = domains()
    variant_domains = {text_input(r['raw_text']): sorted({d for text in r['variant_texts'] for d in key_domains(text)})
                       for r in candidates}

    def all_domains(text):
        return sorted(set(key_domains(text)) | set(variant_domains.get(text_input(text), [])))

    initial = audit_rows(candidates, history, all_domains, edges)
    fitted = {text_input(r['raw_text']) for r in base}
    sys.path.insert(0, str(ROOT.parent / '.local-runtime/english-data-libs'))
    from langid.langid import LanguageIdentifier, model
    identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)
    for i, row in enumerate(initial):
        masked = re.sub(r'(?:https?|hxxps?)://\S+|www\.\S+', ' ', row['raw_text'], flags=re.I)
        eligible = row['disposition'] == 'training_review_candidate' and text_input(row['raw_text']) not in fitted
        language, confidence = identifier.classify(masked) if eligible and len(re.findall(r'[^\W\d_]+', masked)) >= 5 else ('unresolved', 0.)
        candidates[i].update(language=language, language_confidence=float(confidence),
            language_provenance='automated_langid_1.1.6_all_languages_min_5_words_not_human_verified')
    signatures = [template_signature(r['raw_text']) for r in candidates + history]
    references = {}
    for i, signature in enumerate(signatures):
        if signature:
            references.setdefault(signature, i)
    queries = {}
    for i, row in enumerate(initial):
        if not admit(dict(row, **{k:candidates[i][k] for k in ('language','language_confidence')}), fitted)['do_not_train']:
            queries.setdefault(signatures[i], i)
    print(f'Near-duplicate queries {len(queries)}; references {len(references)}', flush=True)
    query_indices, reference_indices = list(queries.values()), list(references.values())
    near = [(query_indices[a], reference_indices[b]) for a,b,score in
            similarity_edges(list(queries), list(references), .80) if query_indices[a] != reference_indices[b]] if queries else []
    grouped = audit_rows(candidates, history, all_domains, edges + near)
    rows = cap_additions([admit(r, fitted) for r in grouped])
    additions = [r for r in rows if not r['do_not_train']]
    blocked = [r for r in rows if r['do_not_train']]
    require_train(additions)
    if len({text_input(r['raw_text']) for r in base + additions}) != len(base + additions):
        raise ValueError('Repeated fitting input')
    export_rows(output, 'sms_train_additions', additions)
    export_rows(output, 'sms_quarantine', blocked)
    export_rows(output, 'sms_train_merged', base + additions)
    write_json(output / 'similarity_edges.json', edges + near)
    write_json(output / 'protocol.json', dict(source_sha256=SOURCE_SHA, base_fit_rows_sha256=sha(BASE),
        source_label_semantics='ham (legitimate SMS) is a source proxy for project negative, not expert smishing verification',
        supervised_labels_only=True, models_fitted=0, models_scored=0, thresholds_changed=False,
        benchmark_created=False, historical_test_scoring=False,
        similarity_threshold=.80, template_cap=3, component_cap=20,
        protected_inputs_sha256=protected | hashes,
        code_sha256={p.name:sha(p) for p in [Path(__file__), ROOT / 'english_data_expansion.py',
            ROOT / 'audit_vi_holdout.py', ROOT / 'vi_data_workflow.py', ROOT / 'round2_experiment.py',
            ROOT / 'smishx_training.py']},
        files_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()}))
    report = dict(raw_ham_rows=len(source), unique_model_inputs=len(rows),
        unused_before_isolation=sum(text_input(r['raw_text']) not in fitted for r in rows),
        admitted_negative_rows=len(additions), admitted_groups=len({r['group'] for r in additions}),
        admitted_templates=len({template_signature(r['raw_text']) for r in additions}),
        blocked_rows=len(blocked), blocked_reasons=dict(Counter(r['admission_reason'] for r in blocked)),
        cap_blocked_rows=sum(r['admission_reason']=='source_ham_isolated_training_only' for r in blocked),
        base_rows=len(base), merged_rows=len(base+additions), merged_labels=dict(Counter(str(r['label']) for r in base+additions)),
        models_fitted=0, models_scored=0, expert_labels_created=0, independent_benchmark_created=False,
        source_url=source[0]['source_url'], protected_inputs_unchanged=True,
        files_sha256={p.name:sha(p) for p in output.iterdir() if p.is_file()})
    write_json(output / 'final_report.json', report)
    verify(output)
    print(json.dumps(report), flush=True)


def verify(output=OUT):
    protocol = json.loads((output / 'protocol.json').read_text(encoding='utf-8'))
    for name, expected in protocol['protected_inputs_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Protected input changed: ' + name)
    for name, expected in protocol['code_sha256'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('Preparation code changed: ' + name)
    report = json.loads((output / 'final_report.json').read_text(encoding='utf-8'))
    for name, expected in report['files_sha256'].items():
        if sha(output / name) != expected:
            raise ValueError('Package file changed: ' + name)
    additions = read_jsonl(output / 'sms_train_additions.jsonl')
    require_train(additions)
    if any(admit(r, set())['do_not_train'] for r in additions):
        raise ValueError('Invalid negative admission')
    return dict(verified=True, additions=len(additions), models_modified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare','verify'])
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    print(json.dumps(verify(args.output)) if args.command == 'verify' else prepare(args.output))
