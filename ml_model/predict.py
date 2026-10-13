"""
ScamShield Forensic AI — ML Prediction Module
==============================================
Loads trained .pkl models and runs fast inference.
Used by the Next.js /api/ml-classify endpoint via Python subprocess.

Usage (standalone test):
  python ml_model/predict.py "Free prize click now http://scam-site.vip"

Usage (from API route — JSON input/output):
  echo '{"text":"...","url":"..."}' | python ml_model/predict.py
"""

import sys
import json
import pickle
import re
import math
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

MODELS_DIR = Path(__file__).parent / "models"

# ─── Load models once at module level ────────────────────────────────────────
_cache = {}

def _load(name):
    if name not in _cache:
        path = MODELS_DIR / name
        if not path.exists():
            return None
        with open(path, "rb") as f:
            _cache[name] = pickle.load(f)
    return _cache[name]


# ─── URL feature extraction (mirrors train.py) ───────────────────────────────
def extract_url_features(url: str) -> list:
    try:
        url = str(url)
        url_len      = len(url)
        domain_part  = re.sub(r"https?://", "", url).split("/")[0]
        domain_len   = len(domain_part)
        path_len     = max(0, len(url) - len(domain_part) - 8)

        sus_keywords = ["login", "verify", "secure", "update", "bank", "otp",
                        "confirm", "account", "password", "pay", "claim",
                        "win", "prize", "free", "urgent", "alert", "task",
                        "invest", "earn", "commission", "transfer", "apk"]
        keyword_count    = sum(1 for kw in sus_keywords if kw in url.lower())
        tld_suspicious   = int(any(url.lower().endswith(t)
                                   for t in [".vip", ".top", ".xyz", ".site",
                                             ".info", ".biz", ".click", ".link"]))
        tld_trusted      = int(any(domain_part.lower().endswith(t)
                                   for t in [".gov.vn", ".edu.vn", ".com.vn",
                                             ".gov", ".edu", ".org"]))
        digit_ratio      = sum(c.isdigit() for c in url) / max(url_len, 1)
        special_ratio    = sum(c in "-_@!~" for c in url) / max(url_len, 1)
        hyphen_count     = url.count("-")
        subdomain_depth  = max(0, len(domain_part.split(".")) - 2)
        has_ip           = int(bool(re.match(r"\d{1,3}(\.\d{1,3}){3}", domain_part)))
        brands           = ["vietcombank", "vcb", "shopee", "solana", "vneid",
                            "facebook", "paypal", "amazon", "netflix", "telegram"]
        brand_in_domain  = int(any(b in domain_part.lower() for b in brands))

        freq = {}
        for c in domain_part.lower():
            freq[c] = freq.get(c, 0) + 1
        entropy = (-sum((v / len(domain_part)) * math.log2(v / len(domain_part))
                        for v in freq.values())
                   if domain_part else 0)

        return [url_len, domain_len, path_len,
                keyword_count, tld_suspicious, tld_trusted,
                digit_ratio, special_ratio, hyphen_count,
                subdomain_depth, has_ip, brand_in_domain, entropy]
    except Exception:
        return [0] * 13


# ─── Classify SMS / text ─────────────────────────────────────────────────────
def classify_text(text: str) -> dict:
    tfidf = _load("tfidf_sms.pkl")
    clf   = _load("sms_classifier.pkl")
    if tfidf is None or clf is None:
        return {"score": 0.5, "label": "unknown", "confidence": 0,
                "top_features": [], "model_ready": False}

    vec   = tfidf.transform([text])
    proba = clf.predict_proba(vec)[0]
    score = float(proba[1])   # P(spam/scam)
    label = "scam" if score >= 0.5 else "safe"

    # Extract top contributing features
    feature_names = tfidf.get_feature_names_out()
    try:
        coefs = clf.coef_[0]
        nz    = vec.nonzero()[1]
        top   = sorted(nz, key=lambda i: abs(coefs[i]) * vec[0, i], reverse=True)[:5]
        top_features = [str(feature_names[i]) for i in top]
    except Exception:
        top_features = []

    return {
        "score"       : round(score, 4),
        "label"       : label,
        "confidence"  : round(max(score, 1 - score) * 100, 1),
        "top_features": top_features,
        "model_ready" : True,
    }


# ─── Classify URL ─────────────────────────────────────────────────────────────
def classify_url(url: str) -> dict:
    tfidf = _load("tfidf_url.pkl")
    clf   = _load("url_classifier.pkl")
    if tfidf is None or clf is None:
        return {"score": 0.5, "label": "unknown", "confidence": 0,
                "top_features": [], "model_ready": False}

    import numpy as np
    try:
        import scipy.sparse as sp
        feats  = np.array(extract_url_features(url)).reshape(1, -1)
        chars  = tfidf.transform([url])
        X      = sp.hstack([sp.csr_matrix(feats), chars])

        # Try predict_proba with dense first (GradientBoosting)
        try:
            proba = clf.predict_proba(X.toarray())[0]
        except Exception:
            proba = clf.predict_proba(X)[0]
    except Exception:
        proba = [0.5, 0.5]

    score = float(proba[1])
    label = "phishing" if score >= 0.5 else "safe"

    # Top URL signals as human-readable strings
    signals = []
    f = extract_url_features(url)
    labels_map = [
        ("URL length", f[0], 80),
        ("Suspicious keyword count", f[3], 2),
        ("Suspicious TLD", f[4], 0.5),
        ("Brand in domain", f[11], 0.5),
        ("Hyphen count", f[8], 3),
        ("Subdomain depth", f[9], 2),
        ("Domain entropy", f[12], 3.5),
    ]
    for name, val, threshold in labels_map:
        if val >= threshold:
            signals.append(f"{name}: {round(val, 2)}")

    return {
        "score"       : round(score, 4),
        "label"       : label,
        "confidence"  : round(max(score, 1 - score) * 100, 1),
        "top_features": signals[:4],
        "model_ready" : True,
    }


# ─── Combined classifier ─────────────────────────────────────────────────────
def classify(text: str = "", url: str = "") -> dict:
    text_result = classify_text(text) if text.strip() else None
    url_result  = classify_url(url)   if url.strip()  else None

    if text_result and url_result and text_result["model_ready"] and url_result["model_ready"]:
        fused_score = 0.45 * text_result["score"] + 0.55 * url_result["score"]
    elif text_result and text_result["model_ready"]:
        fused_score = text_result["score"]
    elif url_result and url_result["model_ready"]:
        fused_score = url_result["score"]
    else:
        fused_score = 0.0

    fused_score  = round(fused_score, 4)
    ml_risk_score = int(fused_score * 100)
    ml_label      = "SCAM" if fused_score >= 0.6 else ("SUSPICIOUS" if fused_score >= 0.35 else "SAFE")

    all_features = []
    if text_result:
        all_features.extend(text_result.get("top_features", []))
    if url_result:
        all_features.extend(url_result.get("top_features", []))

    return {
        "ml_risk_score" : ml_risk_score,
        "ml_label"      : ml_label,
        "ml_confidence" : round(max(fused_score, 1 - fused_score) * 100, 1),
        "ml_top_signals": list(dict.fromkeys(all_features))[:5],  # dedupe
        "text_result"   : text_result,
        "url_result"    : url_result,
        "model_ready"   : (text_result or url_result) is not None,
    }


# ─── CLI entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Accept JSON from stdin (for API use) OR single string arg (for quick test)
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        try:
            payload = json.loads(raw)
            text = payload.get("text", "")
            url  = payload.get("url", "")
        except json.JSONDecodeError:
            text, url = raw, ""
    elif len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        url  = ""
        # detect if arg looks like a URL
        if sys.argv[1].startswith("http"):
            url, text = sys.argv[1], ""
    else:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    result = classify(text=text, url=url)
    print(json.dumps(result, ensure_ascii=False))
