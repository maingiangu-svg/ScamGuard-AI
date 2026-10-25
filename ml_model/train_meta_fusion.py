"""Reproducible local training. Real embedded links only; no synthetic pairing.

An untouched SMS holdout evaluates fusion. Text OOF is generated only inside
SMS training. The URL estimator is trained on a separate URL corpus, excluding
ALL hostnames in the SMS corpus, so its scores on SMS are externally held out.
"""
import hashlib
import json
import os
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, log_loss
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from modeling import text_model, url_model, meta_features, pipeline_fingerprint, url_scores
from preprocess import DATA_DIR, clean_messages
from data_quality import REFERENCE_PATH, UCI_URL, UCI_SHA256, prepare_urls, read_spam_reference

MODELS_DIR = Path(__file__).resolve().parent / "models"


def message_groups(frame):
    """Connected components prevent shared text or any shared hostname crossing folds."""
    parent = list(range(len(frame)))
    seen = {}
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, row in enumerate(frame.itertuples()):
        keys = ["text:" + row.normalized_text]
        keys += ["host:" + urlsplit(u).hostname for u in json.loads(row.urls_json)]
        for key in keys:
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    return np.array([find(i) for i in range(len(frame))])


def holdout_split(y, groups):
    train, test = next(StratifiedGroupKFold(5, shuffle=True, random_state=42).split(y, y, groups))
    if len(np.unique(y[train])) != 2 or len(np.unique(y[test])) != 2:
        raise ValueError("Both classes are required in grouped train and holdout")
    return train, test


def compute_metrics(y, probabilities):
    probabilities = np.asarray(probabilities, dtype=float)
    pred = probabilities >= 0.5
    return {
        "samples": len(y), "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probabilities)) if len(np.unique(y)) == 2 else None,
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
    }


def clean_urls(path, excluded_hosts):
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)[["URL", "Label"]]
    if not raw.Label.str.strip().str.lower().isin(["good", "bad"]).all():
        raise ValueError("Unknown URL labels; refusing to map them to benign")
    cleaned, _, audit = prepare_urls(raw)
    cleaned = cleaned[~cleaned.host.isin(excluded_hosts)].reset_index(drop=True)
    cleaned.attrs['data_quality_audit'] = audit
    return cleaned, audit['conflicting_groups']


def main():
    started = time.perf_counter()
    MODELS_DIR.mkdir(exist_ok=True)
    sms_path = DATA_DIR / "smishing_combined.csv"
    if sms_path.exists():
        raw = pd.read_csv(sms_path).rename(columns={"message": "raw_text", "smishing label": "label"})
        target = "smishing (upstream keyword-derived labels, not expert ground truth)"
        source_manifest = DATA_DIR / "smishing_source.json"
        source_metadata = json.loads(source_manifest.read_text(encoding="utf-8-sig")) if source_manifest.exists() else None
    else:
        sms_path = REFERENCE_PATH
        raw = read_spam_reference(sms_path)
        target = "UCI SMS spam/ham proxy; not validated smishing ground truth"
        source_metadata = {"source_url": UCI_URL, "sha256": UCI_SHA256,
                           "label_note": "Original UCI spam/ham labels; not expert-verified smishing labels.",
                           "license": "CC BY 4.0"}
    sms, audit = clean_messages(raw)
    sms.to_csv(DATA_DIR / "smishing_preprocessed.csv", index=False)
    texts = sms.normalized_text.to_numpy()
    y = sms.label.to_numpy()
    links = [json.loads(u) for u in sms.urls_json]
    groups = message_groups(sms)
    train, test = holdout_split(y, groups)
    print(f"SMS clean={len(sms)}, train={len(train)}, holdout={len(test)}, paired={int(sms.has_url.sum())}", flush=True)

    # No URL from an SMS hostname can occur in the external URL training corpus.
    sms_hosts = {urlsplit(u).hostname for row in links for u in row}
    url_path = DATA_DIR / "phishing_site_urls.csv"
    urls, conflicts = clean_urls(url_path, sms_hosts)
    url_data_audit = urls.attrs['data_quality_audit']
    if len(urls) > 50000:
        _, indices = train_test_split(np.arange(len(urls)), test_size=50000,
                                     stratify=urls.label, random_state=42)
        urls = urls.iloc[indices].reset_index(drop=True)
    urls.to_csv(DATA_DIR / 'urls_preprocessed.csv', index=False)
    uy = urls.label.to_numpy()
    utrain, utest = holdout_split(uy, urls.host.to_numpy())
    print(f"URL selected={len(urls)}, train={len(utrain)}, holdout={len(utest)}; fitting...", flush=True)
    model_url = url_model().fit(urls.url.iloc[utrain].to_numpy(), uy[utrain])
    url_metrics = compute_metrics(uy[utest], model_url.predict_proba(urls.url.iloc[utest].to_numpy())[:, 1])
    sms_url_scores = url_scores(model_url, links)

    # Inner OOF never sees any outer-holdout labels, text or vocabulary.
    oof_text = np.zeros(len(train))
    folds = StratifiedGroupKFold(5, shuffle=True, random_state=42)
    for fold, (fit_i, val_i) in enumerate(folds.split(texts[train], y[train], groups[train]), 1):
        fold_model = text_model().fit(texts[train[fit_i]], y[train[fit_i]])
        oof_text[val_i] = fold_model.predict_proba(texts[train[val_i]])[:, 1]
        print(f"Text OOF fold {fold}/5 complete", flush=True)
    model_text = text_model().fit(texts[train], y[train])
    test_text = model_text.predict_proba(texts[test])[:, 1]
    paired_train = sms.has_url.iloc[train].to_numpy().astype(bool)
    paired_test = sms.has_url.iloc[test].to_numpy().astype(bool)
    if len(np.unique(y[train][paired_train])) != 2:
        raise ValueError("Insufficient real paired SMS from both classes to train fusion")
    linear = LogisticRegression(C=1, max_iter=1000, random_state=42).fit(
        meta_features(oof_text[paired_train], sms_url_scores[train][paired_train], False),
        y[train][paired_train])
    meta = LogisticRegression(C=1, max_iter=1000, random_state=42).fit(
        meta_features(oof_text[paired_train], sms_url_scores[train][paired_train]),
        y[train][paired_train])
    pt = test_text[paired_test]
    pu = sms_url_scores[test][paired_test]
    py = y[test][paired_test]
    metrics = {
        "evaluation": "Untouched grouped holdouts; inner text OOF only on SMS training; external URL training excludes all SMS hostnames",
        "text_holdout": compute_metrics(y[test], test_text),
        "url_holdout": url_metrics,
        "paired_holdout": {
            "text_only": compute_metrics(py, pt), "url_only": compute_metrics(py, pu),
            "max_fusion": compute_metrics(py, np.maximum(pt, pu)),
            "linear_meta": compute_metrics(py, linear.predict_proba(meta_features(pt, pu, False))[:, 1]),
            "interaction_meta": compute_metrics(py, meta.predict_proba(meta_features(pt, pu))[:, 1]),
        },
    }
    metadata = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "pipeline_fingerprint": pipeline_fingerprint(), "sklearn_version": sklearn.__version__,
        "method": "Text LR + URL HistGB + logistic interaction stacking",
        "target": target, "synthetic_pairs": 0, "data_audit": audit,
        "url_data_audit": url_data_audit,
        "data_quality_sha256": hashlib.sha256((Path(__file__).parent / 'data_quality.py').read_bytes()).hexdigest(),
        "training_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "text_training_samples": len(train), "url_training_samples": len(utrain),
        "paired_training_samples": int(paired_train.sum()),
        "paired_holdout_samples": int(paired_test.sum()), "url_conflicting_groups_removed": conflicts,
        "thresholds": {"review": 30, "high": 80, "selection": "Fixed review policy, not claimed optimal or calibrated"},
        "probability_calibrated": False,
        "meta_coefficients": [float(meta.intercept_[0])] + meta.coef_[0].tolist(),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [sms_path, url_path]},
        "source": source_metadata,
        "training_seconds": round(time.perf_counter() - started, 2),
    }
    # Keep held-out rows OUT of deployed models so reported validation stays attributable.
    bundle = {"metadata": metadata, "text_model": model_text, "url_model": model_url, "meta_model": meta}
    temporary = MODELS_DIR / "model_bundle.tmp"
    with temporary.open("wb") as file:
        pickle.dump(bundle, file, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temporary, MODELS_DIR / "model_bundle.pkl")
    (MODELS_DIR / "training_report.json").write_text(json.dumps({"metadata": metadata, "metrics": metrics}, indent=2), encoding="utf-8")
    split_ids = {
        "sms_train": train.tolist(), "sms_holdout": test.tolist(),
        "url_train": utrain.tolist(), "url_holdout": utest.tolist(),
        "sms_group_disjoint": not bool(set(groups[train]) & set(groups[test])),
        "url_hostname_disjoint": not bool(set(urls.host.iloc[utrain]) & set(urls.host.iloc[utest])),
        "sms_url_hostname_disjoint": not bool(sms_hosts & set(urls.host.iloc[utrain])),
    }
    (MODELS_DIR / "split_ids.json").write_text(json.dumps(split_ids), encoding="utf-8")
    print(json.dumps(metrics, indent=2), flush=True)
    print(f"Saved complete model bundle, run {metadata['run_id']}", flush=True)


if __name__ == "__main__":
    main()
