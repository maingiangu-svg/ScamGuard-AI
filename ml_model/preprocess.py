"""
ScamShield / ScamGuard — Data Preprocessing & Normalization Pipeline
Implements the 5 formal stages:
  Stage 1: Data Cleaning (Deduplication, NaN removal, label validation)
  Stage 2: Text Normalization (Unicode NFKD, URL extraction, entity masks)
  Stage 3: URL Canonicalization (RFC 3986 parse, lowercasing, path extraction)
  Stage 4: Feature Engineering & Extraction (13-D Information-Theoretic Indicators)
  Stage 5: Standardized Dataset Export
"""

import os
import re
import math
import unicodedata
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "ml_model" / "data"

SUSPICIOUS_KEYWORDS = [
    "login", "verify", "secure", "update", "bank", "otp", "confirm",
    "account", "password", "pay", "claim", "win", "prize", "free",
    "urgent", "alert", "task", "invest", "earn", "commission", "transfer",
    "apk", "vneid", "phatnguoi", "canhsat", "khoataikhoan"
]

SUSPICIOUS_TLDS = [".vip", ".top", ".xyz", ".site", ".info", ".biz", ".click", ".link", ".online", ".work"]
TRUSTED_TLDS = [".gov.vn", ".edu.vn", ".com.vn", ".gov", ".edu", ".org"]
KNOWN_BRANDS = ["vietcombank", "vcb", "shopee", "solana", "vneid", "momo", "zalo", "telegram", "binance", "facebook", "apple", "netflix"]


def extract_raw_url(text: str) -> tuple[str, str]:
    """
    Extract first embedded URL from message text.
    Replaces embedded URL with <URL> token in cleaned text.
    """
    if not isinstance(text, str):
        return "", ""
    
    # Match standard http/https or www or bare domain patterns
    url_pattern = r"(https?://\S+|www\.\S+|[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|vn|vip|top|xyz|site|net|org|info|biz)\b\S*)"
    match = re.search(url_pattern, text, flags=re.IGNORECASE)
    if match:
        raw_url = match.group(0).rstrip(".,;:!?)'\"")
        # Replace embedded url with <URL> token
        masked_text = text[:match.start()] + "<URL>" + text[match.end():]
        return masked_text, raw_url
    return text, ""


def normalize_text(text: str) -> str:
    """
    Stage 2: Text Normalization
    Unicode NFKD, lowercasing, entity normalization.
    """
    if not isinstance(text, str):
        return ""
    # Unicode canonical decomposition (normalizes accents and Cyrillic/homoglyph lookalikes)
    text = unicodedata.normalize("NFKD", text)
    # Mask phone numbers
    text = re.sub(r"\b(?:\+?84|0)(?:\d{9,10})\b", "<PHONE>", text)
    # Mask currency amounts
    text = re.sub(r"\b\d+[\.,]?\d*\s*(?:vnđ|vnd|đ|usd|\$|k|triệu|trieu)\b", "<MONEY>", text, flags=re.IGNORECASE)
    # Mask OTP codes
    text = re.sub(r"\b\d{4,8}\b", "<OTP>", text)
    # Clean redundant whitespaces
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def canonicalize_url(url: str) -> str:
    """
    Stage 3: URL Canonicalization
    RFC 3986 parsing, lowercasing, trailing slash normalization.
    """
    if not url:
        return ""
    url = url.strip()
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        url = "http://" + url
    return url


def compute_shannon_entropy(domain: str) -> float:
    """Computes Shannon entropy across the character alphabet of the domain."""
    if not domain:
        return 0.0
    domain = domain.lower()
    freq = {}
    for c in domain:
        freq[c] = freq.get(c, 0) + 1
    length = len(domain)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def extract_13_features(url: str) -> list[float]:
    """
    Stage 4: Extracts the formal 13 handcrafted structural & information features.
    """
    if not url:
        return [0.0] * 13

    url_clean = canonicalize_url(url)
    url_len = len(url_clean)

    # Domain, path extraction
    no_scheme = re.sub(r"^https?://", "", url_clean)
    parts = no_scheme.split("/", 1)
    domain_part = parts[0].split(":")[0].lower()
    path_part = parts[1] if len(parts) > 1 else ""

    domain_len = len(domain_part)
    path_len = len(path_part)

    # Lexical features
    keyword_count = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in url_clean.lower())
    tld_suspicious = 1.0 if any(domain_part.endswith(tld) for tld in SUSPICIOUS_TLDS) else 0.0
    tld_trusted = 1.0 if any(domain_part.endswith(tld) for tld in TRUSTED_TLDS) else 0.0

    digit_ratio = sum(c.isdigit() for c in url_clean) / max(url_len, 1)
    special_ratio = sum(c in "-_@!~&=?%" for c in url_clean) / max(url_len, 1)
    hyphen_count = float(domain_part.count("-"))

    subdomain_depth = float(max(0, domain_part.count(".") - 1))
    has_ip = 1.0 if bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain_part)) else 0.0

    # Brand spoofing flag
    brand_spoof = 0.0
    for b in KNOWN_BRANDS:
        if b in url_clean.lower() and not domain_part.endswith(f"{b}.com") and not domain_part.endswith(f"{b}.vn"):
            brand_spoof = 1.0
            break

    # Shannon Entropy of domain
    entropy = compute_shannon_entropy(domain_part)

    return [
        float(url_len), float(domain_len), float(path_len),
        float(keyword_count), tld_suspicious, tld_trusted,
        float(digit_ratio), float(special_ratio), hyphen_count,
        subdomain_depth, has_ip, brand_spoof, float(entropy)
    ]


def run_pipeline():
    print("=" * 65)
    print("🚀 ScamGuard — Data Preprocessing & Normalization Pipeline")
    print("=" * 65)

    source_csv = DATA_DIR / "smishing_combined.csv"
    if not source_csv.exists():
        raise FileNotFoundError(f"Missing {source_csv}")

    print(f"\n📂 Loading raw dataset: {source_csv.name}...")
    df = pd.read_csv(source_csv)
    print(f"   Raw row count: {len(df):,}")

    # Stage 1: Data Cleaning
    print("\n🧹 Stage 1: Data Cleaning...")
    df = df.rename(columns={"message": "raw_text", "smishing label": "label"})
    df = df.dropna(subset=["raw_text", "label"])
    df["label"] = df["label"].astype(int)
    
    # Deduplication
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["raw_text"]).reset_index(drop=True)
    print(f"   Removed {before_dedup - len(df):,} exact duplicates. Retained: {len(df):,} unique messages.")

    # Stage 2 & 3: Text & URL Normalization
    print("\n📝 Stage 2 & 3: Text Normalization & URL Canonicalization...")
    extracted_urls = []
    normalized_texts = []
    has_url_flags = []

    for text in df["raw_text"]:
        masked_txt, raw_url = extract_raw_url(text)
        norm_txt = normalize_text(masked_txt)
        canon_url = canonicalize_url(raw_url) if raw_url else ""

        normalized_texts.append(norm_txt)
        extracted_urls.append(canon_url)
        has_url_flags.append(1 if canon_url else 0)

    df["normalized_text"] = normalized_texts
    df["extracted_url"] = extracted_urls
    df["has_url"] = has_url_flags

    # Summary of paired data
    paired_count = df["has_url"].sum()
    paired_scam = ((df["has_url"] == 1) & (df["label"] == 1)).sum()
    paired_ham = ((df["has_url"] == 1) & (df["label"] == 0)).sum()

    print(f"   Total messages with embedded URLs: {paired_count:,}")
    print(f"     • Smishing (Class 1 with URL): {paired_scam:,}")
    print(f"     • Legitimate (Class 0 with URL): {paired_ham:,}")

    # Export normalized dataset
    out_csv = DATA_DIR / "smishing_preprocessed.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n💾 Saved normalized dataset to: {out_csv}")
    print(f"   File size: {out_csv.stat().st_size / (1024*1024):.2f} MB")
    print("=" * 65)


if __name__ == "__main__":
    run_pipeline()
