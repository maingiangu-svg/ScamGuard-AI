"""Prepare traceable candidate datasets and review queues without training models."""
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from data_quality import REFERENCE_PATH, UCI_URL, prepare_sms, prepare_urls, read_spam_reference, repair_url
from preprocess import DATA_DIR, canonicalize_url, clean_messages

OUTPUT = DATA_DIR / 'prepared'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(frame, filename, source_path, checksum):
    frame = frame.copy()
    frame['source_file'] = source_path.relative_to(DATA_DIR).as_posix()
    frame['source_sha256'] = checksum
    path = OUTPUT / filename
    if path.suffix == '.jsonl':
        frame.to_json(path, orient='records', lines=True, force_ascii=False)
    else:
        frame.to_csv(path, index=False, encoding='utf-8-sig')


def recovery_log(local, reference):
    """Match complete lexical content to the original; do not use fuzzy guesses."""
    def tokens(text):
        return tuple(re.findall('[a-z0-9]+', text.casefold()))
    lookup = defaultdict(list)
    for row in reference.itertuples():
        lookup[(row.original_label, tokens(row.raw_text))].append(row)
    extras = [column for column in local if column.startswith('Unnamed:')]
    log = []
    for index, row in local[local[extras].ne('').any(axis=1)].iterrows():
        fragments = [row[column] for column in ['v2'] + extras if row[column] != '']
        matches = lookup[(row.v1, tokens(','.join(fragments)))]
        parts = [matches] if len({match.raw_text for match in matches}) == 1 else []
        if not parts and '\r' in row.v2:
            first, marker = row.v2.split('\r', 1)
            second_label = marker.strip('"')
            if second_label in ('ham', 'spam'):
                first_matches = lookup[(row.v1, tokens(first))]
                second_matches = lookup[(second_label, tokens(','.join(fragments[1:])))]
                if (len({item.raw_text for item in first_matches}) == 1
                        and len({item.raw_text for item in second_matches}) == 1
                        and any(b.source_record == a.source_record + 1
                                for a in first_matches for b in second_matches)):
                    parts = [first_matches, second_matches]
        log.append({'source_record': index + 1, 'original': row.to_dict(),
                    'status': 'matched_to_original_reference' if parts else 'unresolved',
                    'matching_method': 'exact_ascii_word_and_number_sequence_with_same_source_label',
                    'reference_records': [[item.source_record for item in matches] for matches in parts],
                    'restored_messages': [matches[0].raw_text for matches in parts],
                    'reference_sha256': sha256(REFERENCE_PATH)})
    return log


def main():
    OUTPUT.mkdir(exist_ok=True)
    paths = [DATA_DIR / name for name in ('smishing_combined.csv', 'spam.csv', 'phishing_site_urls.csv')]
    before = {path.name: sha256(path) for path in paths}
    bundle = DATA_DIR.parent / 'models/model_bundle.pkl'
    bundle_hash = sha256(bundle) if bundle.exists() else None
    report = {'created_at': datetime.now(timezone(timedelta(hours=7))).isoformat(),
              'source_sha256': before, 'automatic_label_changes': 0,
              'expert_verified_labels_added': 0, 'model_retrained': False}
    report['preparation_code_sha256'] = sha256(Path(__file__))
    report['data_quality_code_sha256'] = sha256(Path(__file__).with_name('data_quality.py'))

    # 1. Recover fallback SMS content from the checksum-pinned, authoritative source.
    reference = read_spam_reference()
    local = pd.read_csv(paths[1], dtype=str, keep_default_na=False, encoding='latin-1')
    repairs = recovery_log(local, reference)
    with (OUTPUT / 'spam_content_repairs.jsonl').open('w', encoding='utf-8') as stream:
        for entry in repairs:
            stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
    export(reference, 'spam_restored_full.csv', REFERENCE_PATH, sha256(REFERENCE_PATH))
    fallback, fallback_review, fallback_audit = prepare_sms(
        reference, provenance='source_spam_ham_not_verified_smishing')
    export(fallback, 'spam_training_candidates.csv', REFERENCE_PATH, sha256(REFERENCE_PATH))
    export(fallback_review, 'spam_quarantine.jsonl', REFERENCE_PATH, sha256(REFERENCE_PATH))
    report['spam_recovery'] = {
        'local_records': len(local), 'official_reference_records': len(reference),
        'affected_local_records': len(repairs),
        'matched_local_records': sum(entry['status'] != 'unresolved' for entry in repairs),
        'merged_local_records': sum(len(entry['restored_messages']) > 1 for entry in repairs),
        'reference_url': UCI_URL, 'reference_sha256': sha256(REFERENCE_PATH),
        'cleaning': fallback_audit}

    # 2. Keep primary weak labels and missing auxiliary values intact; quarantine conflicts.
    source = pd.read_csv(paths[0], dtype=str, keep_default_na=False)
    sms, sms_review, sms_audit = prepare_sms(source)
    export(sms, 'smishing_training_candidates.csv', paths[0], before[paths[0].name])
    export(sms_review, 'smishing_quarantine.jsonl', paths[0], before[paths[0].name])
    auxiliary = source['spam label'].str.strip()
    auxiliary_review = source.loc[~auxiliary.isin(['0', '1'])].copy()
    auxiliary_review['source_record'] = auxiliary_review.index + 1
    auxiliary_review['review_status'] = 'pending_source_verification_not_training_target'
    auxiliary_review['proposed_label'] = None
    auxiliary_review['reviewer'] = None
    auxiliary_review['evidence'] = None
    export(auxiliary_review, 'auxiliary_label_review.jsonl', paths[0], before[paths[0].name])
    report['smishing'] = {**sms_audit, 'label_provenance': 'weak_keyword_derived',
                          'missing_auxiliary_labels_preserved': int(auxiliary.eq('').sum()),
                          'nonbinary_auxiliary_labels_preserved': int((~auxiliary.isin(['', '0', '1'])).sum())}

    # 3. Repair explicit URL representations and quarantine invalid or conflicting records.
    urls_source = pd.read_csv(paths[2], dtype=str, keep_default_na=False)
    urls, url_review, url_audit = prepare_urls(urls_source)
    export(urls, 'url_training_candidates.csv', paths[2], before[paths[2].name])
    export(url_review, 'url_quarantine.jsonl', paths[2], before[paths[2].name])
    url_repairs = urls.loc[urls.repair_action.ne('canonicalized')]
    export(url_repairs, 'url_format_repairs.jsonl', paths[2], before[paths[2].name])
    report['urls'] = {**url_audit, 'retained_repaired_unique_urls': len(url_repairs),
                      'quarantine_reasons': url_review.issues.value_counts().to_dict(),
                      'repair_actions': url_repairs.repair_action.value_counts().to_dict()}

    # 4. A reproducible content-review sample, NOT an independent evaluation/test set.
    sample = pd.concat([group.sample(n=min(100, len(group)), random_state=42)
                        for _, group in sms.groupby('label')]).sort_values('source_record')
    sample = sample[['source_record', 'raw_text', 'original_label', 'label_provenance']].copy()
    sample['review_status'] = 'pending'
    for column in ('proposed_label', 'reviewer', 'evidence'):
        sample[column] = None
    export(sample, 'sms_label_review_sample.jsonl', paths[0], before[paths[0].name])
    export(sample, 'sms_label_review_sample.csv', paths[0], before[paths[0].name])
    report['content_review_sample'] = {'rows': len(sample), 'sampling_seed': 42,
                                      'per_label': 100, 'completed_expert_reviews': 0,
                                      'purpose': 'label_quality_audit_not_independent_test'}

    # Real-data verification: accounting, parser idempotence, source and model preservation.
    for audit in (sms_audit, fallback_audit, url_audit):
        assert audit['raw_rows'] == audit['candidate_rows'] + audit['quarantined_rows'] + audit['duplicates_removed']
    assert not sms.dedup_key.duplicated().any() and not urls.url.duplicated().any()
    expected_sms, _ = clean_messages(source.rename(columns={'message': 'raw_text', 'smishing label': 'label'}))
    assert sms.dedup_key.tolist() == expected_sms.dedup_key.tolist()
    assert sms.label.tolist() == expected_sms.label.tolist()
    check_urls = pd.DataFrame({'url': urls_source.URL.map(lambda value: repair_url(value)[0]),
                               'label': urls_source.Label.str.strip().str.lower()})
    check_urls = check_urls[check_urls.url.ne('') & check_urls.label.isin(['good', 'bad'])]
    check_conflicts = check_urls.groupby('url').label.nunique()
    assert not urls.url.isin(check_conflicts[check_conflicts > 1].index).any()
    assert all(canonicalize_url(url) == url for url in urls.url)
    assert before == {path.name: sha256(path) for path in paths}
    assert bundle_hash == (sha256(bundle) if bundle.exists() else None)
    report['verification'] = {'row_accounting': True, 'candidate_keys_unique': True,
                               'conflicting_labels_excluded_by_independent_recheck': True,
                               'url_canonicalization_idempotent': True,
                               'original_sources_unchanged': True, 'deployed_model_unchanged': True}
    report['training_decision'] = 'Candidate datasets prepared; no retraining because independent expert-labelled evaluation data is not available.'
    (OUTPUT / 'preparation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    # User-facing preview includes actual before/after values, rendered as literal text.
    display_date = datetime.fromisoformat(report['created_at']).strftime('%d/%m/%Y')
    preview = [f'# Dữ liệu sau xử lý — {display_date}', '',
               'Đã sửa nội dung/định dạng, chưa kiểm định lại toàn bộ nhãn. Không có nhãn mới do chuyên gia xác minh.', '',
               '## SMS: trước và sau phục hồi từ UCI', '']
    examples = repairs[:4] + [entry for entry in repairs if len(entry['restored_messages']) > 1]
    for entry in examples:
        preview += [f"### Bản ghi CSV cũ {entry['source_record']}", '', 'Trước (các cột nguyên gốc):', '']
        preview += ['    ' + json.dumps(entry['original'], ensure_ascii=False), '', 'Sau (nội dung từ UCI):', '']
        for message in entry['restored_messages']:
            preview += ['    ' + message.replace('\n', '\n    '), '']
    preview += ['## URL: ví dụ sửa định dạng', '', '| Bản ghi nguồn | Trước | Sau | Thao tác |', '|---:|---|---|---|']
    for row in url_repairs.head(8).itertuples():
        preview.append(f'| {row.source_record} | `{row.URL.replace("|", "%7C")}` | `{row.url.replace("|", "%7C")}` | {row.repair_action} |')
    preview += ['', '## Số liệu', '', '```json', json.dumps(report, ensure_ascii=False, indent=2), '```', '',
                '## Cách dùng các tệp', '',
                '- spam_restored_full.csv: bản SMS UCI đầy đủ, 5.574 tin. Nhãn vẫn là spam/ham, không phải smishing đã kiểm định.',
                '- smishing_training_candidates.csv: SMS đã loại trùng/mâu thuẫn, giữ nguyên nguồn gốc nhãn yếu.',
                '- spam_training_candidates.csv: bản UCI đã làm sạch, dùng dự phòng cho bài toán spam/ham.',
                '- url_training_candidates.csv: URL đã sửa biểu diễn rõ ràng và loại trùng/mâu thuẫn.',
                '- Các tệp quarantine.jsonl: cách ly, chưa dùng huấn luyện.',
                '- auxiliary_label_review.jsonl: ô nhãn spam phụ còn thiếu/khác định dạng; không tự điền.',
                '- sms_label_review_sample.jsonl: 200 mẫu chờ người rà soát; không dùng để tuyên bố độ chính xác hay lỗi nhãn.',
                '', 'Mỗi bản ghi xuất có source_file, source_record và source_sha256 để truy về nguồn. Các CSV là tệp dữ liệu máy học, không phải nhãn chuyên gia.']
    (OUTPUT / 'XEM_DU_LIEU_SAU_SUA.md').write_text('\n'.join(preview), encoding='utf-8')
    preview_rows = []
    for entry in examples:
        for text in entry['restored_messages']:
            preview_rows.append({'source_file': 'spam.csv', 'source_record': entry['source_record'],
                                 'before': json.dumps(entry['original'], ensure_ascii=False),
                                 'after': text, 'original_label': entry['original']['v1'],
                                 'action': 'restore_original_UCI_content', 'expert_verified': False})
    for row in url_repairs.head(8).itertuples():
        preview_rows.append({'source_file': 'phishing_site_urls.csv', 'source_record': row.source_record,
                             'before': row.URL, 'after': row.url, 'original_label': row.Label,
                             'action': row.repair_action, 'expert_verified': False})
    pd.DataFrame(preview_rows).to_csv(OUTPUT / 'du_lieu_mau_truoc_sau.csv', index=False, encoding='utf-8-sig')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
