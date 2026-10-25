"""Local model inference. A missing or incompatible bundle never produces a verdict."""
import json
import os
import pickle
import re
import sys
import time
from pathlib import Path

import numpy as np
import sklearn

from modeling import meta_features, pipeline_fingerprint
from preprocess import canonicalize_url, extract_urls, normalize_text


def load_bundle():
    path = Path(os.environ.get("SCAMGUARD_MODEL_PATH", Path(__file__).parent / "models" / "model_bundle.pkl"))
    with path.open("rb") as file:
        bundle = pickle.load(file)
    metadata = bundle["metadata"]
    if metadata["pipeline_fingerprint"] != pipeline_fingerprint():
        raise ValueError("Preprocessing/model version mismatch; retrain the bundle")
    if metadata["sklearn_version"] != sklearn.__version__:
        raise ValueError("Estimator runtime version mismatch")
    for key in ("text_model", "url_model", "meta_model"):
        if key not in bundle:
            raise ValueError("Incomplete model bundle")
    return bundle


def probability(model, rows):
    values = np.asarray(model.predict_proba(rows), dtype=float)[:, 1]
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Invalid model probabilities")
    return values


def positive_text_signals(model, text):
    if not hasattr(model, "named_steps"):
        return []
    vector = model.named_steps["tfidf"].transform([text])
    names = model.named_steps["tfidf"].get_feature_names_out()
    weights = model.named_steps["classifier"].coef_[0]
    positive = [(float(vector[0, i]) * weights[i], str(names[i])) for i in vector.nonzero()[1] if weights[i] > 0]
    return [name for _, name in sorted(positive, reverse=True)[:5]]


def classify(text="", url=""):
    started = time.perf_counter()
    unavailable = {"model_ready": False, "ml_risk_score": None, "ml_label": "UNAVAILABLE",
                   "ml_confidence": 0, "ml_top_signals": [], "action": "UNAVAILABLE"}
    try:
        if not isinstance(text, str) or not isinstance(url, str) or not (text.strip() or url.strip()):
            raise ValueError("Text or URL is required")
        masked, urls = extract_urls(text)
        if url.strip():
            urls = list(dict.fromkeys([canonicalize_url(url)] + urls))
        if len(urls) > 20:
            raise ValueError("Too many URLs")
        normalized = normalize_text(masked)
        has_text = bool(re.sub(r"<url>|[\W_]+", "", normalized))
        bundle = load_bundle()
        text_result = None
        url_result = None
        signals = []
        if has_text:
            pt = float(probability(bundle["text_model"], [normalized])[0])
            signals = positive_text_signals(bundle["text_model"], normalized)
            text_result = {"score": pt, "model_ready": True, "top_features": signals}
        if urls:
            scores = probability(bundle["url_model"], urls)
            pu = float(scores.max())
            url_result = {"score": pu, "model_ready": True, "top_features": [],
                          "urls": [{"url": u, "score": float(p)} for u, p in zip(urls, scores)]}
        if text_result is not None and url_result is not None:
            fused = float(probability(bundle["meta_model"], meta_features([pt], [pu]))[0])
            mode = "interaction_stacking"
        elif text_result is not None:
            fused, mode = pt, "text_only"
        elif url_result is not None:
            fused, mode = pu, "url_only"
        else:
            raise ValueError("No supported input")
        score = int(round(fused * 100))
        label, action = ("SCAM", "BLOCK") if score >= 80 else (
            ("SUSPICIOUS", "REVIEW") if score >= 30 else ("SAFE", "CLEAR"))
        metadata = bundle.get("metadata", {})
        coefficients = metadata.get("meta_coefficients")
        formula = None
        if coefficients and mode == "interaction_stacking":
            b0, b1, b2, b3 = coefficients
            formula = f"100 × σ({b0:.4f} + {b1:.4f}·p_text + {b2:.4f}·p_url + {b3:.4f}·p_text·p_url)"
        return {
            "model_ready": True, "ml_risk_score": score, "ml_label": label,
            "ml_confidence": round(max(fused, 1 - fused) * 100, 1),
            "ml_top_signals": signals, "action": action,
            "uncertainty": round(1 - 2 * abs(fused - 0.5), 4),
            "normalized_text": normalized, "extracted_url": urls[0] if urls else "",
            "text_result": text_result, "url_result": url_result,
            "inference_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": mode, "meta_formula": formula,
            "training": {key: metadata.get(key) for key in (
                "run_id", "method", "target", "text_training_samples", "url_training_samples",
                "paired_training_samples", "paired_holdout_samples", "synthetic_pairs",
                "probability_calibrated")},
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError, EOFError, RuntimeError, pickle.UnpicklingError):
        return {**unavailable, "error": "MODEL_UNAVAILABLE_OR_INCOMPATIBLE"}


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {"text": " ".join(sys.argv[1:])}
        result = classify(payload.get("text", ""), payload.get("url", ""))
    except (ValueError, TypeError, AttributeError):
        result = {"model_ready": False, "ml_risk_score": None, "ml_label": "UNAVAILABLE",
                  "ml_confidence": 0, "ml_top_signals": [], "error": "INVALID_INPUT"}
    print(json.dumps(result, ensure_ascii=False))
