"""Bounded URL inference: verify/load once, predict the whole batch together."""
import json
import sys
import time
from urllib.parse import urlsplit

from predict import probability
from predict_hybrid import load_bundle
from preprocess import canonicalize_url


def classify_links(urls):
    unavailable = {'model_ready': False, 'error': 'LINK_MODEL_UNAVAILABLE_OR_INVALID_INPUT'}
    started = time.perf_counter()
    try:
        if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
            return unavailable
        for url in urls:
            if not isinstance(url, str) or len(url) > 4096:
                return unavailable
            parts = urlsplit(url)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
                return unavailable
        bundle = load_bundle()  # Includes the original manifest/code/checksum gates.
        head = bundle['url']
        values = probability(head['model'], [canonicalize_url(url) for url in urls])
        results = []
        for url, value in zip(urls, values):
            score = int(round(float(value) * 100))
            level = 'HIGH' if score >= 80 else 'MEDIUM' if value >= head['threshold'] else 'LOW'
            results.append({'url': url, 'riskScore': score, 'riskLevel': level, 'model_id': head['model_id']})
        return {'model_ready': True, 'results': results,
                'inference_ms': round((time.perf_counter() - started) * 1000, 2)}
    except Exception:
        # Do not return model paths or input details on artifact/runtime failures.
        return unavailable


if __name__ == '__main__':
    try:
        payload = json.loads(sys.stdin.read())
        result = classify_links(payload.get('urls'))
    except (ValueError, TypeError, AttributeError):
        result = {'model_ready': False, 'error': 'INVALID_INPUT'}
    print(json.dumps(result, ensure_ascii=False))
