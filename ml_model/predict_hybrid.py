"""Independent supervised SMS and URL heads; manifest-bound weights, no score fusion."""
import hashlib
import json
import os
import pickle
import re
import sys
import time
from pathlib import Path

import sklearn

from audit_vi_holdout import audit_url_text
from predict import probability
from predict_processed import text_signals
from preprocess import canonicalize_url, extract_urls
from round2_experiment import text_input

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models/hybrid_bundle.pkl"
MANIFEST = ROOT / "models/hybrid_manifest.json"


def load_bundle():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    content = Path(os.environ.get("SCAMGUARD_MODEL_PATH", MODEL)).read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Hybrid model checksum mismatch")
    for name, expected in manifest["code_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError("Hybrid preprocessing checksum mismatch")
    bundle = pickle.loads(content)
    if bundle["artifact_type"] != "routed_supervised_models" or bundle["paired_fusion_trained"]:
        raise ValueError("Unsupported hybrid model contract")
    if bundle["sklearn_version"] != sklearn.__version__:
        raise ValueError("Estimator runtime version mismatch")
    if bundle["sms"]["threshold"] != .65 or bundle["url"]["threshold"] != .5:
        raise ValueError("Hybrid threshold mismatch")
    return bundle


def classify(text="", url=""):
    started = time.perf_counter()
    unavailable = {"model_ready": False, "ml_risk_score": None, "ml_label": "UNAVAILABLE",
                   "ml_confidence": 0, "ml_top_signals": [], "action": "UNAVAILABLE"}
    try:
        if not isinstance(text, str) or not isinstance(url, str) or not (text.strip() or url.strip()):
            raise ValueError("Text or URL required")
        if len(text) > 20000 or len(url) > 4096:
            raise ValueError("Input too long")
        masked, links = extract_urls(audit_url_text(text))
        if url.strip():
            links = list(dict.fromkeys([canonicalize_url(url)] + links))
        if len(links) > 20:
            raise ValueError("Too many URLs")
        has_text = bool(re.sub(r"<url>|[\W_]+", "", masked, flags=re.I))
        bundle = load_bundle()
        normalized = text_input(text)
        text_result, url_result, signals = None, None, []
        selected_url = ""
        if has_text:
            head = bundle["sms"]
            pt = float(probability(head["model"], [normalized])[0])
            signals = text_signals(head["model"], normalized)
            text_result = {"score": pt, "model_ready": True, "top_features": signals,
                           "threshold": head["threshold"], "model_id": head["model_id"]}
        if links:
            head = bundle["url"]
            # Keep the exact URL preprocessing used to train this URL head.
            values = probability(head["model"], links)
            pu = float(values.max())
            selected_url = links[int(values.argmax())]
            url_result = {"score": pu, "model_ready": True, "top_features": [],
                          "threshold": head["threshold"], "model_id": head["model_id"],
                          "target": "upstream_good_bad_url_source_labels",
                          "urls": [{"url": u, "score": float(p)} for u, p in zip(links, values)]}
        if text_result is not None:
            raw_score, branch, mode = pt, "sms", "hybrid_text"
        elif url_result is not None:
            raw_score, branch, mode = pu, "url", "hybrid_url_only"
        else:
            raise ValueError("No supported input")
        # Independent URL review never changes the SMS score/binary prediction.
        url_review = text_result is not None and url_result is not None and pu >= bundle["url"]["threshold"]
        score = int(round(raw_score * 100))
        label, action = ("SCAM", "BLOCK") if score >= 80 else (
            ("SUSPICIOUS", "REVIEW") if score >= 30 or url_review else ("SAFE", "CLEAR"))
        return {"model_ready": True, "ml_risk_score": score, "ml_label": label, "action": action,
                "ml_confidence": round(max(raw_score, 1 - raw_score) * 100, 1), "ml_top_signals": signals,
                "uncertainty": round(1 - 2 * abs(raw_score - .5), 4),
                "normalized_text": normalized, "extracted_url": selected_url,
                "text_result": text_result, "url_result": url_result, "url_review_required": bool(url_review),
                "mode": mode, "meta_formula": None, "inference_ms": round((time.perf_counter() - started) * 1000, 2),
                "model_prediction_label": int(raw_score >= bundle[branch]["threshold"]),
                "decision_threshold": bundle[branch]["threshold"], "decision_branch": branch,
                "training": bundle["training"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, RuntimeError, pickle.UnpicklingError):
        return {**unavailable, "error": "MODEL_UNAVAILABLE_OR_INCOMPATIBLE"}


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        result = classify(payload.get("text", ""), payload.get("url", ""))
    except (ValueError, TypeError, AttributeError):
        result = {"model_ready": False, "ml_risk_score": None, "ml_label": "UNAVAILABLE",
                  "ml_confidence": 0, "ml_top_signals": [], "error": "INVALID_INPUT"}
    print(json.dumps(result, ensure_ascii=False))
