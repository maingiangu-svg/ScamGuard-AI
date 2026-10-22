"""
ScamShield Forensic AI — ML Prediction Module
==============================================
Loads trained .pkl models and runs fast inference using the
5-stage Preprocessing Pipeline and Interaction Stacking Meta-Learner:
  s_fused = sigma(beta_0 + beta_1 * p_text + beta_2 * p_url + beta_3 * (p_text * p_url))
Used by Next.js API routes (/api/ml-classify and /api/analyze).
"""

import sys
import json
import pickle
import re
import math
import os
import warnings
from pathlib import Path
import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "ml_model" / "models"

sys.path.append(str(ROOT / "ml_model"))
try:
    from preprocess import extract_raw_url, normalize_text, canonicalize_url, extract_13_features
except ImportError:
    # Fallback inline if import path differs
    def extract_raw_url(text): return text, ""
    def normalize_text(text): return text.lower().strip()
    def canonicalize_url(url): return url.strip()
    def extract_13_features(url): return [0.0] * 13

_cache = {}

def _load(name):
    if name not in _cache:
        path = MODELS_DIR / name
        if not path.exists():
            return None
        with open(path, "rb") as f:
            _cache[name] = pickle.load(f)
    return _cache[name]


def classify_text(norm_text: str) -> dict:
    tfidf = _load("tfidf_sms.pkl")
    clf   = _load("sms_classifier.pkl")
    if tfidf is None or clf is None:
        return {"score": 0.5, "label": "unknown", "confidence": 0, "top_features": [], "model_ready": False}

    vec = tfidf.transform([norm_text])
    proba = clf.predict_proba(vec)[0]
    score = float(proba[1])
    label = "scam" if score >= 0.5 else "safe"

    top_features = []
    try:
        feature_names = tfidf.get_feature_names_out()
        coefs = clf.coef_[0]
        nz = vec.nonzero()[1]
        top = sorted(nz, key=lambda i: abs(coefs[i]) * vec[0, i], reverse=True)[:5]
        top_features = [str(feature_names[i]) for i in top]
    except Exception:
        pass

    return {
        "score": round(score, 4),
        "label": label,
        "confidence": round(max(score, 1 - score) * 100, 1),
        "top_features": top_features,
        "model_ready": True,
    }


def classify_url(canon_url: str) -> dict:
    scaler = _load("scaler_url.pkl")
    tfidf  = _load("tfidf_url.pkl")
    clf    = _load("url_classifier.pkl")
    if clf is None:
        return {"score": 0.5, "label": "unknown", "confidence": 0, "top_features": [], "model_ready": False}

    try:
        f13 = np.array([extract_13_features(canon_url)], dtype=np.float32)
        if scaler is not None:
            f13_scaled = scaler.transform(f13)
        else:
            f13_scaled = f13

        if tfidf is not None:
            f_char = tfidf.transform([canon_url]).toarray()
            X_u = np.hstack([f13_scaled, f_char])
        else:
            X_u = f13_scaled

        proba = clf.predict_proba(X_u)[0]
        score = float(proba[1])
    except Exception:
        score = 0.5

    label = "phishing" if score >= 0.5 else "safe"

    # Top URL signals
    signals = []
    f = extract_13_features(canon_url)
    labels_map = [
        ("URL length", f[0], 75),
        ("Suspicious keyword count", f[3], 1),
        ("Suspicious TLD", f[4], 0.5),
        ("Hyphen count", f[8], 2),
        ("Subdomain depth", f[9], 2),
        ("Has IP address", f[10], 0.5),
        ("Brand spoofing flag", f[11], 0.5),
        ("Domain entropy", f[12], 3.8),
    ]
    for name, val, threshold in labels_map:
        if val >= threshold:
            signals.append(f"{name}: {round(val, 2)}")

    return {
        "score": round(score, 4),
        "label": label,
        "confidence": round(max(score, 1 - score) * 100, 1),
        "top_features": signals[:4],
        "model_ready": True,
    }


def classify(text: str = "", url: str = "") -> dict:
    raw_text = text or ""
    explicit_url = url or ""

    # Preprocessing & URL extraction
    masked_txt, embedded_url = extract_raw_url(raw_text)
    norm_txt = normalize_text(masked_txt)
    target_url = canonicalize_url(explicit_url or embedded_url)

    text_result = classify_text(norm_txt) if norm_txt.strip() else None
    url_result  = classify_url(target_url)  if target_url.strip()  else None

    meta_clf = _load("meta_learner.pkl")

    if text_result and url_result and text_result["model_ready"] and url_result["model_ready"]:
        p_t = text_result["score"]
        p_u = url_result["score"]
        if meta_clf is not None:
            # Interaction Meta-Learner: [p_t, p_u, p_t * p_u]
            X_meta = np.array([[p_t, p_u, p_t * p_u]], dtype=np.float32)
            fused_score = float(meta_clf.predict_proba(X_meta)[0, 1])
        else:
            # Fallback formulation
            fused_score = 1.0 / (1.0 + np.exp(-(-4.072 + 8.785 * p_t + 0.099 * p_u + 3.158 * p_t * p_u)))
    elif text_result and text_result["model_ready"]:
        fused_score = text_result["score"]
    elif url_result and url_result["model_ready"]:
        fused_score = url_result["score"]
    else:
        fused_score = 0.0

    fused_score = round(float(fused_score), 4)
    ml_risk_score = int(round(fused_score * 100))
    uncertainty = round(1.0 - 2.0 * abs(fused_score - 0.5), 3)

    if fused_score >= 0.80:
        ml_label = "SCAM"
        action = "BLOCK"
    elif fused_score >= 0.30:
        ml_label = "SUSPICIOUS"
        action = "ESCALATE_VLM"
    else:
        ml_label = "SAFE"
        action = "CLEAR"

    all_features = []
    if text_result:
        all_features.extend(text_result.get("top_features", []))
    if url_result:
        all_features.extend(url_result.get("top_features", []))

    return {
        "ml_risk_score": ml_risk_score,
        "ml_label": ml_label,
        "action": action,
        "uncertainty": uncertainty,
        "ml_confidence": round(max(fused_score, 1 - fused_score) * 100, 1),
        "ml_top_signals": list(dict.fromkeys(all_features))[:5],
        "normalized_text": norm_txt,
        "extracted_url": target_url,
        "text_result": text_result,
        "url_result": url_result,
        "model_ready": (text_result or url_result) is not None,
    }


if __name__ == "__main__":
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
        if sys.argv[1].startswith("http"):
            url, text = sys.argv[1], ""
    else:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    result = classify(text=text, url=url)
    print(json.dumps(result, ensure_ascii=False))
