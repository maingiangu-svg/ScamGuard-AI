"""Inspect the actual deployed bundle. No fixed coefficients or preset verdicts."""
import json
import sys
from pathlib import Path
from predict import classify, load_bundle

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    bundle = load_bundle()
    report = json.loads((Path(__file__).parent / "models" / "split_ids.json").read_text())
    for key in ("sms_group_disjoint", "url_hostname_disjoint", "sms_url_hostname_disjoint"):
        if report.get(key) is not True:
            raise RuntimeError("Training split isolation failed: " + key)
    print(json.dumps(bundle["metadata"], ensure_ascii=False, indent=2))
    for text in ("Hey, are you free for lunch tomorrow?",
                 "Your account is suspended. Verify now http://bank-login.vip/verify"):
        result = classify(text=text)
        if not result["model_ready"]:
            raise RuntimeError("Production inference unavailable")
        print(json.dumps(result, ensure_ascii=False))
