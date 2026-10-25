"""Retrieve the public research dataset at an immutable revision and verify bytes."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent / "data"
COMMIT = "3bf9983df4b187ee9b54a671e4b5bc5f0d48b3fc"
SOURCE = f"https://raw.githubusercontent.com/shaghayegh-hp/Smishing_Dataset/{COMMIT}/Combined-Labeled-Dataset.csv"
EXPECTED_SHA256 = "4dc1311965acb80b9b97536db5afdbe874a1e2175143d3b145e32caf9bb81a8d"


def main():
    ROOT.mkdir(exist_ok=True)
    target = ROOT / "smishing_combined.csv"
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != EXPECTED_SHA256:
        with urlopen(SOURCE, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
            raise ValueError("Source checksum mismatch; original file left unchanged")
        target.write_bytes(data)
    manifest = {
        "repository": "https://github.com/shaghayegh-hp/Smishing_Dataset",
        "commit": COMMIT, "source_url": SOURCE, "local_file": target.name,
        "sha256": EXPECTED_SHA256,
        "label_note": "Upstream smishing labels are assigned by keyword rules, not independent expert review.",
        "usage_note": "Upstream permits academic/research use. No broader commercial license asserted.",
    }
    (ROOT / "smishing_source.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Verified {target.name}: SHA-256 {EXPECTED_SHA256}")


if __name__ == "__main__":
    main()
