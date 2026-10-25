"""Shared, deterministic preprocessing for training and inference. No network access."""
import hashlib
import ipaddress
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
PIPELINE_VERSION = "2.0"
URL_RE = re.compile(
    r"https?://[^\s<>\"{}]+|www\.[^\s<>\"{}]+|"
    r"(?<![@\w])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"(?:com|vn|net|org|info|biz|vip|top|xyz|site|online|work|ly|co|uk|in|io|me|edu|gov)"
    r"\b(?:[/:?][^\s<>\"{}]*)?", re.I
)
BRANDS = {
    "vietcombank": ["vietcombank.com.vn", "vcbdigibank.com.vn"],
    "facebook": ["facebook.com", "fb.com"], "shopee": ["shopee.vn", "shopee.com"],
    "vneid": ["vneid.gov.vn"], "momo": ["momo.vn"], "zalo": ["zalo.me", "zalo.vn"],
    "telegram": ["telegram.org", "t.me"], "binance": ["binance.com"],
    "apple": ["apple.com"], "netflix": ["netflix.com"], "solana": ["solana.com"],
}
KEYWORDS = ("login", "verify", "secure", "update", "bank", "otp", "confirm", "account",
            "password", "pay", "claim", "win", "prize", "free", "urgent", "alert",
            "task", "invest", "earn", "commission", "transfer", "apk")
RISK_TLDS = (".vip", ".top", ".xyz", ".site", ".info", ".biz", ".click", ".link", ".online", ".work")
TRUST_TLDS = (".gov.vn", ".edu.vn", ".com.vn", ".gov", ".edu", ".org")


def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def canonicalize_url(url):
    if not isinstance(url, str) or not url.strip():
        return ""
    url = url.strip()
    if re.search(r"[\s\x00-\x1f\x7f]", url):
        raise ValueError("Invalid URL characters")
    if not re.match(r"^https?://", url, re.I):
        if re.match(r"^[a-z][a-z0-9+.-]*:", url, re.I) and not re.match(r"^[^/:]+\.\w+:\d+(?:/|$)", url):
            raise ValueError("Only HTTP and HTTPS URLs are supported")
        url = "http://" + url.removeprefix("//")
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("Invalid HTTP URL")
    host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    if ":" in host:
        ipaddress.IPv6Address(host)
        host = "[" + host + "]"
    port = parts.port
    netloc = host
    if port and (parts.scheme.lower(), port) not in (("http", 80), ("https", 443)):
        netloc += ":" + str(port)
    if "@" in parts.netloc:
        netloc = parts.netloc.rsplit("@", 1)[0] + "@" + netloc
    return urlunsplit((parts.scheme.lower(), netloc, parts.path, parts.query, ""))


def extract_urls(text):
    urls = []
    def mask(match):
        raw = match.group().rstrip(".,;:!?)'\"")
        try:
            url = canonicalize_url(raw)
        except (ValueError, UnicodeError):
            return match.group()
        if url not in urls:
            urls.append(url)
        return "<URL>" + match.group()[len(raw):]
    return URL_RE.sub(mask, text), urls


def extract_raw_url(text):
    masked, urls = extract_urls(text)
    return masked, urls[0] if urls else ""


def normalize_text(text):
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"(?<!\w)(?:\+84|0)\d{9,10}\b", "<phone>", text)
    text = re.sub(r"\$\s*\d[\d,.]*|\b\d[\d,.]*\s*(?:vnđ|vnd|usd|triệu|trieu|đ|k)\b", "<money>", text)
    text = re.sub(r"(\b(?:otp|code|mã)\s*[:=]?\s*)\d{4,8}\b", r"\1<otp>", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_13_features(url):
    if not url:
        return [0.0] * 13
    url = canonicalize_url(url)
    parts = urlsplit(url)
    host = parts.hostname
    try:
        ipaddress.ip_address(host)
        has_ip = 1.0
    except ValueError:
        has_ip = 0.0
    counts = Counter(host)
    entropy = -sum((n / len(host)) * math.log2(n / len(host)) for n in counts.values())
    brand_spoof = any(
        brand in host and not any(host == official or host.endswith("." + official) for official in domains)
        for brand, domains in BRANDS.items()
    )
    return [
        float(len(url)), float(len(host)), float(len(parts.path) + len(parts.query)),
        float(sum(k in url.lower() for k in KEYWORDS)),
        float(host.endswith(RISK_TLDS)), float(host.endswith(TRUST_TLDS)),
        sum(c.isdigit() for c in url) / len(url),
        sum(c in "-_@!~&=?%" for c in url) / len(url),
        float(host.count("-")), float(max(0, host.count(".") - 1)), has_ip,
        float(brand_spoof), entropy,
    ]


def clean_messages(frame):
    frame = frame[["raw_text", "label"]].copy()
    initial = len(frame)
    frame = frame.dropna()
    frame["label"] = pd.to_numeric(frame["label"], errors="raise")
    if not frame["label"].isin([0, 1]).all():
        raise ValueError("Labels must be explicitly 0 or 1")
    frame["label"] = frame["label"].astype(int)
    prepared = [extract_urls(str(t)) for t in frame.raw_text]
    frame["normalized_text"] = [normalize_text(t) for t, _ in prepared]
    frame["urls_json"] = [json.dumps(u, ensure_ascii=False) for _, u in prepared]
    frame = frame[frame.normalized_text.ne("")].copy()
    frame["dedup_key"] = frame.normalized_text + "|" + frame.urls_json
    conflicts = frame.groupby("dedup_key").label.nunique()
    conflicts = set(conflicts[conflicts > 1].index)
    frame = frame[~frame.dedup_key.isin(conflicts)]
    before = len(frame)
    frame = frame.drop_duplicates("dedup_key").reset_index(drop=True)
    frame["has_url"] = frame.urls_json.ne("[]").astype(int)
    return frame, {
        "raw_rows": initial, "clean_rows": len(frame),
        "conflicting_groups_removed": len(conflicts), "duplicates_removed": before - len(frame),
        "paired_records": int(frame.has_url.sum()),
        "labels": {str(k): int(v) for k, v in frame.label.value_counts().items()},
    }


def run_pipeline():
    source = DATA_DIR / "smishing_combined.csv"
    frame = pd.read_csv(source).rename(columns={"message": "raw_text", "smishing label": "label"})
    cleaned, audit = clean_messages(frame)
    cleaned.to_csv(DATA_DIR / "smishing_preprocessed.csv", index=False)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    run_pipeline()
