"""Reversible dataset repairs. Source labels never become expert annotations."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from zipfile import ZipFile

import pandas as pd

from preprocess import canonicalize_url, extract_urls, normalize_text

UCI_URL = 'https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip'
UCI_SHA256 = '1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3'
REFERENCE_PATH = Path(__file__).parent / 'data/reference/uci_sms_spam_collection.zip'


def read_spam_reference(path=REFERENCE_PATH, expected_sha256=UCI_SHA256):
    """Read full original messages, including quotes/commas lost by the local CSV."""
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('UCI reference checksum mismatch')
    with ZipFile(path) as archive:
        lines = archive.read('SMSSpamCollection').decode('utf-8').split('\n')
    rows = []
    for record, line in enumerate(lines, 1):
        if not line.strip():
            continue
        label, text = line.rstrip('\r').split('\t', 1)
        if label not in ('ham', 'spam'):
            raise ValueError('Unknown UCI label')
        rows.append({'raw_text': text, 'label': int(label == 'spam'),
                     'original_label': label, 'source_record': record,
                     'label_provenance': 'source_spam_ham_not_verified_smishing'})
    return pd.DataFrame(rows)


def repair_url(value):
    """Repair explicit defanging/path spaces only; never guess or fetch a host."""
    if not isinstance(value, str) or not value.strip():
        return '', 'empty_url'
    value = value.strip()
    if re.search(r'[\x00-\x1f\x7f-\x9f]', value):
        return '', 'control_characters'
    if re.search(r'\s(?:Trojan\b|Win32/|MSIL/|PUP\.|HTTP/\d|https?://)', value, re.I) or '<' in value or '>' in value:
        return '', 'embedded_metadata_or_redaction'
    if re.search(r'\s+[a-z0-9.-]+\.[a-z]{2,}(?::\d+)?/', value, re.I):
        return '', 'multiple_address_candidates'
    actions = []
    if re.match(r'^hxxps?://', value, re.I):
        value = re.sub(r'^hxxp', 'http', value, flags=re.I)
        actions.append('refang_scheme')
    # urlsplit treats [.] as broken IPv6, so refang only the authority before parsing.
    match = re.match(r'^(?P<prefix>[a-z][a-z0-9+.-]*://)?(?P<host>[^/?#]+)(?P<tail>.*)$', value, re.I)
    if match and '[.]' in match['host']:
        value = (match['prefix'] or '') + match['host'].replace('[.]', '.') + match['tail']
        actions.append('refang_host')
    try:
        candidate = value if re.match(r'^[a-z][a-z0-9+.-]*://', value, re.I) else 'http://' + value
        parts = urlsplit(candidate)
        if re.search(r'\s', parts.netloc) or parts.netloc.endswith(':'):
            return '', 'ambiguous_hostname_or_port'
        if re.search(r'\s', parts.query + parts.fragment):
            return '', 'ambiguous_whitespace_in_query_or_fragment'
        if any(' ' in part for part in (parts.path, parts.query, parts.fragment)):
            value = urlunsplit((parts.scheme, parts.netloc, parts.path.replace(' ', '%20'),
                                parts.query.replace(' ', '%20'), parts.fragment.replace(' ', '%20')))
            actions.append('encode_literal_spaces')
        result = canonicalize_url(value)
        # Quarantine obvious non-host garbage; never infer the intended hostname.
        host = urlsplit(result).hostname
        if not host or not re.search(r'[a-z0-9]', host, re.I) or any(char in host for char in "\\'\"<>"):
            return '', 'invalid_hostname'
        return result, '+'.join(actions) or 'canonicalized'
    except (ValueError, UnicodeError) as error:
        return '', 'invalid_url: ' + str(error)


def _partition(frame, keys, issues):
    usable = issues.eq('')
    label_counts = frame.loc[usable].groupby(keys[usable]).label.nunique()
    conflicts = set(label_counts[label_counts > 1].index)
    conflicting = usable & keys.isin(conflicts)
    issues = issues.copy()
    issues.loc[conflicting] = 'conflicting_target_labels'
    accepted = frame.loc[issues.eq('')].copy()
    duplicates = keys.loc[accepted.index].duplicated()
    accepted = accepted.loc[~duplicates].copy()
    accepted['label'] = accepted.label.astype(int)
    review = frame.loc[issues.ne('')].copy()
    review['issues'] = issues.loc[review.index]
    review['proposed_label'] = None
    review['review_status'] = 'pending'
    review['reviewer'] = None
    review['evidence'] = None
    return accepted.reset_index(drop=True), review.reset_index(drop=True), {
        'raw_rows': len(frame), 'candidate_rows': len(accepted), 'quarantined_rows': len(review),
        'conflicting_groups': len(conflicts), 'conflicting_rows': int(conflicting.sum()),
        'duplicates_removed': int(duplicates.sum())}


def prepare_sms(source, provenance='weak_keyword_derived'):
    frame = source.rename(columns={'message': 'raw_text', 'smishing label': 'label'}).copy()
    if 'source_record' not in frame:
        frame['source_record'] = range(1, len(frame) + 1)
    if 'original_label' not in frame:
        frame['original_label'] = frame.label
    frame['label'] = pd.to_numeric(frame.label, errors='coerce')
    frame['label_provenance'] = provenance
    frame['raw_text'] = frame.raw_text.fillna('').astype(str)
    prepared = frame.raw_text.map(extract_urls)
    frame['normalized_text'] = prepared.map(lambda value: normalize_text(value[0]))
    frame['urls_json'] = prepared.map(lambda value: json.dumps(value[1], ensure_ascii=False))
    frame['dedup_key'] = frame.normalized_text + '|' + frame.urls_json
    frame['has_url'] = frame.urls_json.ne('[]').astype(int)
    issues = pd.Series('', index=frame.index)
    issues.loc[~frame.label.isin([0, 1])] = 'missing_or_invalid_target_label'
    issues.loc[frame.normalized_text.eq('')] = 'empty_content'
    return _partition(frame, frame.dedup_key, issues)


def prepare_urls(source):
    frame = source.copy()
    frame['source_record'] = range(1, len(frame) + 1)
    frame['original_label'] = frame.Label
    frame['label'] = frame.Label.fillna('').str.strip().str.lower().map({'good': 0, 'bad': 1})
    results = frame.URL.map(repair_url)
    frame['url'] = results.map(lambda value: value[0])
    frame['repair_action'] = results.map(lambda value: value[1])
    frame['label_provenance'] = 'inherited_url_source_not_expert_verified'
    frame['host'] = frame.url.map(lambda value: urlsplit(value).hostname if value else '')
    issues = pd.Series('', index=frame.index)
    issues.loc[frame.label.isna()] = 'missing_or_invalid_target_label'
    issues.loc[frame.url.eq('')] = frame.loc[frame.url.eq(''), 'repair_action']
    accepted, review, audit = _partition(frame, frame.url, issues)
    audit['repaired_source_rows'] = int(results.map(lambda value: bool(value[0]) and value[1] != 'canonicalized').sum())
    return accepted, review, audit
