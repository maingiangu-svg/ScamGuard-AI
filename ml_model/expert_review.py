"""Prepare independent blind annotation forms; never create expert labels automatically."""
import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def display(value):
    return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else value


def create_package(rows, output):
    if not rows or len({r['case_id'] for r in rows}) != len(rows):
        raise ValueError('Unique case IDs and nonempty input are required')
    output.mkdir(parents=True, exist_ok=False)
    ordered = list(rows)
    random.Random(42).shuffle(ordered)
    fields = ['case_id', 'branch', 'input', 'input_sha256', 'expert_label', 'reviewer',
              'reviewed_at', 'evidence', 'rationale']
    records = [dict(case_id=r['case_id'], branch=r['branch'], input=display(r['input']),
                    input_sha256=digest(r['input']), expert_label='', reviewer='', reviewed_at='',
                    evidence='', rationale='') for r in ordered]
    for name in ('reviewer-a.csv', 'reviewer-b.csv'):
        with (output / name).open('w', encoding='utf-8-sig', newline='') as file:
            writer = csv.DictWriter(file, fields); writer.writeheader(); writer.writerows(records)
    identities = {r['case_id']: dict(branch=r['branch'], input_sha256=digest(r['input']),
                                   display_sha256=digest(display(r['input']))) for r in rows}
    (output / 'identities.json').write_text(json.dumps(identities, indent=2), encoding='utf-8')
    report = dict(cases=len(rows), labels_created=0, expert_verification_by_tool=False,
                  model_or_dataset_modified=False, blind_order_seed=42,
                  original_label_or_model_score_in_forms=False,
                  branches={branch: sum(r['branch'] == branch for r in rows) for branch in sorted({r['branch'] for r in rows})})
    (output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def inspect_reviews(directory):
    identities = json.loads((directory / 'identities.json').read_text(encoding='utf-8'))
    reviews = []
    for name in ('reviewer-a.csv', 'reviewer-b.csv'):
        with (directory / name).open(encoding='utf-8-sig', newline='') as file:
            rows = list(csv.DictReader(file))
        if len(rows) != len(identities) or {r['case_id'] for r in rows} != identities.keys():
            raise ValueError('Review case identity mismatch')
        for row in rows:
            expected = identities[row['case_id']]
            if (row['input_sha256'] != expected['input_sha256'] or row['branch'] != expected['branch']
                    or digest(row['input']) != expected['display_sha256']):
                raise ValueError('Review content identity mismatch')
        reviews.append({r['case_id']: r for r in rows})
    pending = disagreements = agreed = unknown = 0
    for case in identities:
        a, b = [review[case] for review in reviews]
        complete = lambda r: r['expert_label'] in ('0', '1', 'unknown') and all(
            r.get(field, '').strip() for field in ('reviewer', 'reviewed_at', 'evidence', 'rationale'))
        if not complete(a) or not complete(b):
            pending += 1; continue
        if a['reviewer'].strip().casefold() == b['reviewer'].strip().casefold():
            raise ValueError('Two independent reviewers are required')
        if 'unknown' in (a['expert_label'], b['expert_label']): unknown += 1
        elif a['expert_label'] != b['expert_label']: disagreements += 1
        else: agreed += 1
    return dict(cases=len(identities), pending=pending, disagreements=disagreements, unknown=unknown,
                agreed=agreed, complete=pending == 0 and disagreements == 0 and unknown == 0,
                expert_verification_by_tool=False, labels_or_model_changed=0)


def record_ai_review(package, decisions, output):
    """Record content triage without signing either independent expert form."""
    identities = json.loads((package / 'identities.json').read_text(encoding='utf-8'))
    with (package / 'reviewer-a.csv').open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    if len(rows) != len(identities) or {row['case_id'] for row in rows} != identities.keys():
        raise ValueError('Review case identity mismatch')
    if set(decisions) - identities.keys():
        raise ValueError('Unknown review case ID')
    records = []
    reviewed_at = datetime.now(timezone.utc).isoformat()
    for row in rows:
        identity = identities[row['case_id']]
        if (digest(row['input']) != identity['display_sha256'] or row['branch'] != identity['branch']
                or row['input_sha256'] != identity['input_sha256']):
            raise ValueError('Review content identity mismatch')
        decision = decisions.get(row['case_id'])
        if row['branch'] == 'sms' and decision is None:
            raise ValueError('Every SMS needs an explicit content review')
        label = decision.get('label') if decision else 'unknown'
        if (label != 'unknown' and (type(label) is not int or label not in (0, 1))) \
                or (decision and (decision.get('expert_verified') or not decision.get('rationale', '').strip())):
            raise ValueError('AI review cannot create expert verification or an unsupported label')
        if row['branch'] == 'url' and label != 'unknown':
            raise ValueError('URL-only evidence cannot verify a positive or negative label')
        records.append(dict(case_id=row['case_id'], branch=row['branch'],
            input_sha256=identity['input_sha256'], proposed_label=label,
            provenance='ai_content_review' if row['branch'] == 'sms' else 'url_evidence_sufficiency_check',
            reviewer='Codex (AI)', reviewed_at=reviewed_at, expert_verified=False,
            quarantine_required=label == 'unknown', automatic_training_eligible=False,
            rationale=decision['rationale'] if decision else
                'Only a URL string is available; no dated capture or independent page evidence verifies its historical label.'))
    output.mkdir(parents=True, exist_ok=False)
    (output / 'ai_review.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n'
                                                   for row in records), encoding='utf-8')
    (output / 'quarantine_case_ids.json').write_text(json.dumps([
        row['case_id'] for row in records if row['quarantine_required']], indent=2), encoding='utf-8')
    summary = dict(cases=len(records), sms_content_reviewed=sum(r['branch'] == 'sms' for r in records),
        url_evidence_audited=sum(r['branch'] == 'url' for r in records),
        ai_label_proposals=sum(r['proposed_label'] != 'unknown' for r in records),
        unresolved=sum(r['quarantine_required'] for r in records), expert_labels_created=0,
        automatic_dataset_changes=0, benchmark_ready=False)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'verify', 'ai-review'])
    parser.add_argument('--audit', type=Path, default=Path(__file__).parent / 'data/prepared/label_audit_2026-10-26')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--decisions', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        records = []
        for branch in ('sms', 'url'):
            records.extend(dict(json.loads(line), branch=branch) for line in
                           (args.audit / f'{branch}_blind_review.jsonl').read_text(encoding='utf-8').splitlines() if line)
        result = create_package(records, args.output)
    elif args.command == 'ai-review':
        if args.package is None or args.decisions is None:
            parser.error('ai-review requires --package and --decisions')
        result = record_ai_review(args.package, json.loads(args.decisions.read_text(encoding='utf-8')), args.output)
    else:
        result = inspect_reviews(args.output)
    print(json.dumps(result, ensure_ascii=False))
    if args.command == 'verify' and not result['complete']:
        raise SystemExit(2)
