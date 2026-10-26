"""Offline evidence check. Does not fetch URLs or certify labels/campaigns."""
import hashlib,json,sys
from pathlib import Path
from collections import defaultdict
base=Path(__file__).resolve().parent
manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
for name,expected in manifest['files_sha256'].items():
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected, 'Changed file: '+name
rows=[json.loads(line) for line in (base/'SPLIT_MEMBERSHIP.jsonl').open(encoding='utf-8')]
index={r['case_id']:r for r in rows}
assert len(index)==len(rows), 'Duplicate case IDs'
roles=defaultdict(set)
for row in rows:
    if row['partition']=='quarantine':continue
    assert row['partition']==row['original_partition'], 'Partition promotion'
    keys=['domain:'+d for d in row['roots']]+['icann:'+d for d in row['icann_roots']]
    keys += [k+':'+row[k] for k in ['repair_group','source_group','content_key_sha256','template_sha256'] if row[k]]
    for key in keys:roles[key].add(row['partition'])
assert not any(len(value)>1 for value in roles.values()), 'Cross-split domain/content/group'
for a,b in json.loads((base/'SIMILARITY_EDGES.json').read_text(encoding='utf-8')):
    a,b=index[a],index[b]
    if 'quarantine' not in (a['partition'],b['partition']):
        assert a['partition']==b['partition'], 'Cross-split similarity edge'
for branch in ['SMS','URL']:
    test=[json.loads(line) for line in (base/(branch+'_TEST.jsonl')).open(encoding='utf-8')]
    cohort='processed_sms' if branch=='SMS' else 'bundle_url'
    assert {r['case_id'] for r in test}=={r['case_id'] for r in rows if r['cohort']==cohort and r['partition']=='test'}
    assert all(type(r['label']) is int and r['label'] in (0,1) and r['do_not_train'] and r['partition']=='test' for r in test)
for row in [json.loads(line) for line in (base/'REVIEW_NHAN_MAU_THUAN.jsonl').open(encoding='utf-8')]:
    assert index[row['case_id']]['partition']=='quarantine', 'Retained conflicting label'
print('PASS: file hashes, memberships, ICANN/private domains, exact content, groups and similarity edges')
retained=[r for r in rows if r['partition']!='quarantine']
if '--require-campaigns' in sys.argv and not all(r.get('campaign_id') and r.get('campaign_verified_by_source') for r in retained):
    print('NOT PROVEN: missing verified campaign IDs');sys.exit(2)
if '--require-expert-labels' in sys.argv and not all(r.get('expert_verified') for r in retained):
    print('NOT PROVEN: inherited/AI labels are not expert verification');sys.exit(2)
print('Campaign independence: NOT PROVEN. All labels independently expert verified: NO.')
