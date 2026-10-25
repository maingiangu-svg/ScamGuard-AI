"""Package two existing supervised heads; never fit, tune or evaluate a model."""
import hashlib
import json
import pickle
from pathlib import Path

from predict import load_bundle as load_url_bundle
from predict_processed import MODEL as SMS_SOURCE, EXPECTED_SHA256, load_processed_bundle

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "models/hybrid_bundle.pkl"
URL_SOURCE = ROOT / "models/model_bundle.pkl"
URL_SHA256 = "7c6a0da47fe331976f36f76798a581dcaed7440f884230bac7a74a10cba906c4"


def package():
    active_manifest = ROOT / 'models/hybrid_manifest.json'
    if OUTPUT == ROOT / 'models/hybrid_bundle.pkl' and active_manifest.exists():
        active = json.loads(active_manifest.read_text(encoding='utf-8'))
        if active['training']['run_id'].startswith('hybrid-isolated-'):
            raise ValueError('Refusing to overwrite the repaired model with historical fitted heads')
    sources = {"sms": (SMS_SOURCE, EXPECTED_SHA256), "url": (URL_SOURCE, URL_SHA256)}
    for source, expected in sources.values():
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError("Selected source model checksum mismatch")
    sms, url = load_processed_bundle(), load_url_bundle()
    if url["metadata"]["run_id"] != "20261025T152344Z":
        raise ValueError("Unexpected URL training run")
    training = {"run_id": "hybrid-20261025", "method": "Independent supervised SMS and URL branches; no learned fusion",
                "text_training_samples": 3857, "url_training_samples": 40004,
                "source_human_sms_samples": 497, "paired_training_samples": 0, "synthetic_pairs": 0,
                "probability_calibrated": False,
                "target": "SMS project smishing scope; URL upstream good/bad scope",
                "text_label_provenance": "mixed source-human, source and AI review; not entirely expert verified",
                "url_label_provenance": "upstream good/bad source labels; not independently expert verified"}
    bundle = {"artifact_type": "routed_supervised_models", "sklearn_version": sms["sklearn_version"],
              "sms": dict(sms["sms"], model_id="processed-20261025:sms"),
              "url": {"model": url["url_model"], "threshold": .5, "model_id": "20261025T152344Z:url"},
              "training": training, "paired_fusion_trained": False}
    content = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
    manifest = {"bundle_sha256": hashlib.sha256(content).hexdigest(),
                "source_sha256": {key: expected for key, (_, expected) in sources.items()},
                "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in
                                ("preprocess.py", "modeling.py", "round2_experiment.py", "audit_vi_holdout.py")},
                "code_hash_normalization": "CRLF to LF for Windows/Linux parity",
                "training": training, "fitted_rows": 0, "test_evaluation_performed": False,
                "threshold_provenance": {"sms": "frozen validation-selected 0.65",
                                         "url": "existing bundle holdout reference 0.50; not retuned"}}
    OUTPUT.write_bytes(content)
    OUTPUT.with_name("hybrid_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bundle": str(OUTPUT), "bytes": len(content), "sha256": manifest["bundle_sha256"],
                      "fitted_rows": 0}))


if __name__ == "__main__":
    package()
