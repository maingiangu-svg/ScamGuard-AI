"""Web adapter for the checksum-pinned SMS/URL models fitted on processed data."""
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
from external_training import url_input
from predict import probability
from preprocess import canonicalize_url, extract_urls
from round2_experiment import text_input

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "data/prepared/processed_agent_fit_2026-10-25/trained_agent_models.pkl"
EXPECTED_SHA256 = "a69b0afc4b2f3b6f997c86a8fd18488282ccb391a5040e8616129062f35099d2"
SELECTION = ROOT / "data/prepared/smishx_training_2026-10-25/selection_frozen.json"
RUN_ID = "processed-20261025"


def load_processed_bundle():
    path = Path(os.environ.get("SCAMGUARD_MODEL_PATH", MODEL))
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Processed model checksum mismatch")
    frozen = json.loads(SELECTION.read_text(encoding="utf-8"))
    for name, expected in frozen["code_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen training/preprocessing code changed")
    bundle = pickle.loads(content)
    if bundle["sklearn_version"] != sklearn.__version__:
        raise ValueError("Estimator runtime version mismatch")
    if bundle["artifact_type"] != "processed_supervised_models" or bundle["paired_fusion_trained"]:
        raise ValueError("Unsupported processed model contract")
    if bundle["sms"]["threshold"] != .65 or bundle["url"]["threshold"] != .22:
        raise ValueError("Frozen decision threshold mismatch")
    return bundle


def text_signals(model, text):
    if not hasattr(model, "named_steps"):
        return []
    features = model.named_steps["features"]
    vector = features.transform([text])
    names = features.get_feature_names_out()
    weights = model.named_steps["classifier"].coef_[0]
    ranked = sorted(((float(vector[0, i]) * weights[i], str(names[i]))
                     for i in vector.nonzero()[1] if weights[i] > 0), reverse=True)
    return [name for _, name in ranked[:5]]


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
        bundle = load_processed_bundle()
        normalized = text_input(text)
        text_result, url_result, signals = None, None, []
        if has_text:
            pt = float(probability(bundle["sms"]["model"], [normalized])[0])
            signals = text_signals(bundle["sms"]["model"], normalized)
            text_result = {"score": pt, "model_ready": True, "top_features": signals,
                           "threshold": bundle["sms"]["threshold"]}
        if links:
            values = probability(bundle["url"]["model"], [url_input(u) for u in links])
            pu = float(values.max())
            url_result = {"score": pu, "model_ready": True, "top_features": [],
                          "threshold": bundle["url"]["threshold"],
                          "target": "source_reported_abuse_or_phishing_vs_benign",
                          "urls": [{"url": u, "score": float(p)} for u, p in zip(links, values)]}
        # Selection chose the SMS text model. No learned fusion exists for this fit.
        if text_result is not None:
            raw_score, branch, mode = pt, "sms", "processed_text"
        elif url_result is not None:
            raw_score, branch, mode = pu, "url", "processed_url_only"
        else:
            raise ValueError("No supported input")
        threshold = bundle[branch]["threshold"]
        score = int(round(raw_score * 100))
        label, action = ("SCAM", "BLOCK") if score >= 80 else (
            ("SUSPICIOUS", "REVIEW") if score >= 30 else ("SAFE", "CLEAR"))
        return {"model_ready": True, "ml_risk_score": score, "ml_label": label, "action": action,
                "ml_confidence": round(max(raw_score, 1 - raw_score) * 100, 1), "ml_top_signals": signals,
                "uncertainty": round(1 - 2 * abs(raw_score - .5), 4),
                "normalized_text": normalized, "extracted_url": links[0] if links else "",
                "text_result": text_result, "url_result": url_result,
                "mode": mode, "meta_formula": None, "inference_ms": round((time.perf_counter() - started) * 1000, 2),
                "model_prediction_label": int(raw_score >= threshold), "decision_threshold": threshold,
                "decision_branch": branch,
                "training": {"run_id": RUN_ID, "method": "Processed supervised SMS LR and URL HistGB; separate branches",
                             "target": "SMS project smishing scope; URL source-reported abuse/phishing scope",
                             "text_training_samples": 3857, "url_training_samples": 9123,
                             "source_human_sms_samples": 497, "paired_training_samples": 0,
                             "synthetic_pairs": 0, "probability_calibrated": False}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, RuntimeError, pickle.UnpicklingError):
        return {**unavailable, "error": "MODEL_UNAVAILABLE_OR_INCOMPATIBLE"}


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        result = classify(payload.get("text", ""), payload.get("url", ""))
    except (ValueError, TypeError, AttributeError):
        result = {"model_ready": False, "ml_risk_score": None, "ml_label": "UNAVAILABLE", "ml_confidence": 0,
                  "ml_top_signals": [], "error": "INVALID_INPUT"}
    print(json.dumps(result, ensure_ascii=False))
