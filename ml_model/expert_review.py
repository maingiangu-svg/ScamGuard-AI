"""Prepare independent blind annotation forms; never create expert labels automatically."""
import argparse
import csv
import hashlib
import json
import random
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'verify'])
    parser.add_argument('--audit', type=Path, default=Path(__file__).parent / 'data/prepared/label_audit_2026-10-26')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        records = []
        for branch in ('sms', 'url'):
            records.extend(dict(json.loads(line), branch=branch) for line in
                           (args.audit / f'{branch}_blind_review.jsonl').read_text(encoding='utf-8').splitlines() if line)
        result = create_package(records, args.output)
    else:
        result = inspect_reviews(args.output)
    print(json.dumps(result, ensure_ascii=False))
    if args.command == 'verify' and not result['complete']:
        raise SystemExit(2)
