"""
ScamShield Forensic AI — Stacking Meta-Learner Training Pipeline
================================================================
Implements:
  1. Base Model 1: Sublinear TF-IDF + Balanced Logistic Regression (Text Branch)
  2. Base Model 2: 13-D Information-Theoretic Features (StandardScaler) + Char n-grams + GBDT (URL Branch)
  3. Stacking Meta-Learner with Interaction Term:
       s_fused = sigma(beta_0 + beta_1 * p_text + beta_2 * p_url + beta_3 * p_text * p_url)
  4. 5-Fold Stratified Cross-Validation (Out-Of-Fold, leak-free within each fold)
  5. Multi-modal threat representation: Paired SMS corpus augmented with spear-phishing & legitimate URL sharing
  6. Comprehensive Ablation:
       - Text-only
       - URL-only
       - Max-Fusion Baseline: max(p_text, p_url)
       - Linear Meta-Learner: sigma(beta_0 + beta_1 * p_text + beta_2 * p_url)
       - Proposed Interaction Meta-Learner: sigma(beta_0 + beta_1 * p_text + beta_2 * p_url + beta_3 * p_text * p_url)
  7. Exports production artifacts (.pkl) and empirical metrics (metrics_meta.json)
"""

import os
import sys
import json
import time
import pickle
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, log_loss
)

warnings.filterwarnings("ignore")

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "ml_model" / "data"
MODELS_DIR = ROOT / "ml_model" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

sys.path.append(str(ROOT / "ml_model"))
from preprocess import extract_13_features, canonicalize_url, normalize_text


def compute_metrics(y_true, y_prob, threshold=0.5):
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob))
    }


def main():
    print("=" * 75)
    print("⚡ ScamGuard — Stacking Meta-Learner Training & 5-Fold CV")
    print("   Evaluating: Text, URL, Max-Fusion, Linear Meta, Interaction Meta")
    print("=" * 75)

    preprocessed_path = DATA_DIR / "smishing_preprocessed.csv"
    phishing_urls_path = DATA_DIR / "phishing_site_urls.csv"
    if not preprocessed_path.exists():
        raise FileNotFoundError(f"Missing {preprocessed_path}. Run preprocess.py first.")

    print(f"\n📂 Loading normalized smishing corpus: {preprocessed_path.name}...")
    df_smish = pd.read_csv(preprocessed_path)
    paired_orig = df_smish[df_smish["has_url"] == 1].copy()
    print(f"   Original paired multi-modal records: {len(paired_orig):,}")

    # Build augmented dataset for robust multi-modal threat modeling
    print("\n🛡️  Building robust multi-modal benchmark (including spear-phishing threat simulation)...")
    ham_texts = df_smish[(df_smish["has_url"] == 0) & (df_smish["label"] == 0)]["normalized_text"].dropna().sample(3000, random_state=42).tolist()

    aug_rows = []
    if phishing_urls_path.exists():
        print(f"   Loading external URL benchmarks from {phishing_urls_path.name}...")
        df_urls = pd.read_csv(phishing_urls_path)
        bad_urls = df_urls[df_urls["Label"] == "bad"]["URL"].dropna().sample(1500, random_state=42).tolist()
        good_urls = df_urls[df_urls["Label"] == "good"]["URL"].dropna().sample(1500, random_state=42).tolist()

        # Spear-phishing pairs: benign carrier message + malicious phishing URL
        for i in range(1500):
            aug_rows.append({
                "normalized_text": ham_texts[i] + " <url>",
                "extracted_url": canonicalize_url(bad_urls[i]),
                "label": 1
            })
        # Legitimate sharing pairs: benign carrier message + legitimate URL
        for i in range(1500):
            aug_rows.append({
                "normalized_text": ham_texts[1500 + i] + " <url>",
                "extracted_url": canonicalize_url(good_urls[i]),
                "label": 0
            })

    df_paired = pd.concat([paired_orig[["normalized_text", "extracted_url", "label"]], pd.DataFrame(aug_rows)], ignore_index=True)
    df_paired = df_paired.sample(frac=1.0, random_state=42).reset_index(drop=True)

    n_paired = len(df_paired)
    n_scam = int((df_paired["label"] == 1).sum())
    n_ham = int((df_paired["label"] == 0).sum())
    print(f"   Total evaluation corpus size: {n_paired:,} paired records")
    print(f"     • Malicious (Class 1): {n_scam:,} ({n_scam/n_paired*100:.1f}%)")
    print(f"     • Benign (Class 0):    {n_ham:,} ({n_ham/n_paired*100:.1f}%)")

    # Pre-extract 13-D handcrafted structural & lexical features for URLs
    print("\n🔍 Pre-computing 13-D handcrafted indicators for paired URLs...")
    t0 = time.time()
    feats_13_list = [extract_13_features(u) for u in df_paired["extracted_url"]]
    X_url_13 = np.array(feats_13_list, dtype=np.float32)
    print(f"   Extracted 13-D indicators for {n_paired:,} URLs in {time.time() - t0:.2f}s")

    texts = df_paired["normalized_text"].fillna("").values
    urls = df_paired["extracted_url"].fillna("").values
    y = df_paired["label"].values.astype(int)

    # Setup 5-Fold Stratified Cross-Validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    oof_p_text = np.zeros(n_paired, dtype=np.float32)
    oof_p_url = np.zeros(n_paired, dtype=np.float32)

    fold_metrics_text = []
    fold_metrics_url = []

    print("\n🚀 Commencing 5-Fold Stratified Cross-Validation (Leak-Free Protocol)...")
    for fold, (train_idx, val_idx) in enumerate(skf.split(texts, y), 1):
        t_fold = time.time()
        print(f"\n--- [Fold {fold}/5] (Train: {len(train_idx):,}, Val: {len(val_idx):,}) ---")

        # ── 1. Text Pipeline (Fit strictly on Train Fold) ──────────────────
        vec_text = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True)
        X_tr_text = vec_text.fit_transform(texts[train_idx])
        X_val_text = vec_text.transform(texts[val_idx])

        clf_text = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
        clf_text.fit(X_tr_text, y[train_idx])

        p_text_val = clf_text.predict_proba(X_val_text)[:, 1]
        oof_p_text[val_idx] = p_text_val
        m_text = compute_metrics(y[val_idx], p_text_val)
        fold_metrics_text.append(m_text)
        print(f"   [Text Branch] Acc: {m_text['accuracy']*100:.2f}% | F1: {m_text['f1']*100:.2f}% | AUC: {m_text['roc_auc']:.4f}")

        # ── 2. URL Pipeline (Fit strictly on Train Fold) ───────────────────
        scaler_url = StandardScaler()
        X_tr_13_scaled = scaler_url.fit_transform(X_url_13[train_idx])
        X_val_13_scaled = scaler_url.transform(X_url_13[val_idx])

        vec_url_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=1000)
        X_tr_char = vec_url_char.fit_transform(urls[train_idx]).toarray()
        X_val_char = vec_url_char.transform(urls[val_idx]).toarray()

        X_tr_url = np.hstack([X_tr_13_scaled, X_tr_char])
        X_val_url = np.hstack([X_val_13_scaled, X_val_char])

        clf_url = HistGradientBoostingClassifier(
            max_depth=4, max_iter=100, learning_rate=0.1, class_weight="balanced", random_state=42
        )
        clf_url.fit(X_tr_url, y[train_idx])

        p_url_val = clf_url.predict_proba(X_val_url)[:, 1]
        oof_p_url[val_idx] = p_url_val
        m_url = compute_metrics(y[val_idx], p_url_val)
        fold_metrics_url.append(m_url)
        print(f"   [URL Branch ] Acc: {m_url['accuracy']*100:.2f}% | F1: {m_url['f1']*100:.2f}% | AUC: {m_url['roc_auc']:.4f} (Fold elapsed: {time.time() - t_fold:.1f}s)")

    print("\n" + "=" * 75)
    print("📊 Evaluating Fusion Architectures on Out-Of-Fold (OOF) Predictions")
    print("=" * 75)

    # 1. Base Text Model Only
    m_base_text = compute_metrics(y, oof_p_text)

    # 2. Base URL Model Only
    m_base_url = compute_metrics(y, oof_p_url)

    # 3. Max Fusion Baseline: s = max(p_text, p_url)
    p_max_fusion = np.maximum(oof_p_text, oof_p_url)
    m_max_fusion = compute_metrics(y, p_max_fusion)

    # 4. Linear Meta-Learner (K-Fold cross-val on OOF features [p_text, p_url])
    oof_p_linear = np.zeros(n_paired, dtype=np.float32)
    X_meta_linear = np.column_stack([oof_p_text, oof_p_url])

    for tr_i, val_i in skf.split(X_meta_linear, y):
        meta_lin = LogisticRegression(C=1.0, random_state=42)
        meta_lin.fit(X_meta_linear[tr_i], y[tr_i])
        oof_p_linear[val_i] = meta_lin.predict_proba(X_meta_linear[val_i])[:, 1]
    m_linear_meta = compute_metrics(y, oof_p_linear)

    # 5. Proposed Interaction Meta-Learner: [p_text, p_url, p_text * p_url]
    interaction_term = oof_p_text * oof_p_url
    X_meta_interaction = np.column_stack([oof_p_text, oof_p_url, interaction_term])

    oof_p_interaction = np.zeros(n_paired, dtype=np.float32)
    for tr_i, val_i in skf.split(X_meta_interaction, y):
        meta_inter = LogisticRegression(C=1.0, random_state=42)
        meta_inter.fit(X_meta_interaction[tr_i], y[tr_i])
        oof_p_interaction[val_i] = meta_inter.predict_proba(X_meta_interaction[val_i])[:, 1]
    m_interaction_meta = compute_metrics(y, oof_p_interaction)

    # Fit final meta-learners on all OOF pairs to inspect global coefficients
    final_linear_meta = LogisticRegression(C=1.0, random_state=42).fit(X_meta_linear, y)
    final_inter_meta = LogisticRegression(C=1.0, random_state=42).fit(X_meta_interaction, y)

    b0_lin = float(final_linear_meta.intercept_[0])
    b1_lin = float(final_linear_meta.coef_[0][0])
    b2_lin = float(final_linear_meta.coef_[0][1])

    b0_int = float(final_inter_meta.intercept_[0])
    b1_int = float(final_inter_meta.coef_[0][0])
    b2_int = float(final_inter_meta.coef_[0][1])
    b3_int = float(final_inter_meta.coef_[0][2])

    print("\n📈 Learned Meta-Learner Formulations:")
    print(f"   • Linear Meta-Learner:")
    print(f"       s_fused = sigma({b0_lin:.3f} + {b1_lin:.3f}*p_text + {b2_lin:.3f}*p_url)")
    print(f"   • Proposed Interaction Meta-Learner (ScamGuard):")
    print(f"       s_fused = sigma({b0_int:.3f} + {b1_int:.3f}*p_text + {b2_int:.3f}*p_url + {b3_int:.3f}*(p_text*p_url))")

    print("\n📋 Comparative Performance Summary Table:")
    print("-" * 80)
    print(f"{'Method / Configuration':<36} | {'Accuracy':<8} | {'Precision':<9} | {'Recall':<7} | {'F1-Score':<8} | {'ROC-AUC':<7}")
    print("-" * 80)
    print(f"{'Base Model 1 (Text-only)':<36} | {m_base_text['accuracy']*100:6.2f}% | {m_base_text['precision']*100:7.2f}% | {m_base_text['recall']*100:6.2f}% | {m_base_text['f1']*100:7.2f}% | {m_base_text['roc_auc']:7.4f}")
    print(f"{'Base Model 2 (URL-only)':<36} | {m_base_url['accuracy']*100:6.2f}% | {m_base_url['precision']*100:7.2f}% | {m_base_url['recall']*100:6.2f}% | {m_base_url['f1']*100:7.2f}% | {m_base_url['roc_auc']:7.4f}")
    print(f"{'Max Fusion Baseline (Heuristic)':<36} | {m_max_fusion['accuracy']*100:6.2f}% | {m_max_fusion['precision']*100:7.2f}% | {m_max_fusion['recall']*100:6.2f}% | {m_max_fusion['f1']*100:7.2f}% | {m_max_fusion['roc_auc']:7.4f}")
    print(f"{'Linear Meta-Learner (No Interact)':<36} | {m_linear_meta['accuracy']*100:6.2f}% | {m_linear_meta['precision']*100:7.2f}% | {m_linear_meta['recall']*100:6.2f}% | {m_linear_meta['f1']*100:7.2f}% | {m_linear_meta['roc_auc']:7.4f}")
    print(f"{'ScamGuard (Interaction Meta-Learner)':<36} | {m_interaction_meta['accuracy']*100:6.2f}% | {m_interaction_meta['precision']*100:7.2f}% | {m_interaction_meta['recall']*100:6.2f}% | {m_interaction_meta['f1']*100:7.2f}% | {m_interaction_meta['roc_auc']:7.4f}")
    print("-" * 80)

    # ── Full Training on Complete Corpus for Production Deployment ──────────────
    print("\n💾 Training Final Production Models on Complete Dataset...")
    vec_text_full = TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True)
    X_text_full = vec_text_full.fit_transform(texts)
    clf_text_full = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    clf_text_full.fit(X_text_full, y)

    scaler_url_full = StandardScaler()
    X_13_scaled_full = scaler_url_full.fit_transform(X_url_13)

    vec_url_char_full = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=1000)
    X_char_full = vec_url_char_full.fit_transform(urls).toarray()

    X_url_full = np.hstack([X_13_scaled_full, X_char_full])
    clf_url_full = HistGradientBoostingClassifier(
        max_depth=4, max_iter=100, learning_rate=0.1, class_weight="balanced", random_state=42
    )
    clf_url_full.fit(X_url_full, y)

    artifacts = {
        "sms_classifier.pkl": clf_text_full,
        "tfidf_sms.pkl": vec_text_full,
        "url_classifier.pkl": clf_url_full,
        "tfidf_url.pkl": vec_url_char_full,
        "scaler_url.pkl": scaler_url_full,
        "meta_learner.pkl": final_inter_meta
    }

    for fname, obj in artifacts.items():
        with open(MODELS_DIR / fname, "wb") as f:
            pickle.dump(obj, f)
        print(f"   Saved {fname} ({os.path.getsize(MODELS_DIR / fname) / 1024:.1f} KB)")

    # Save comprehensive metrics JSON
    metrics_summary = {
        "evaluation_dataset": {
            "total_paired_records": int(n_paired),
            "smishing_count": int(n_scam),
            "benign_count": int(n_ham),
            "cv_folds": 5
        },
        "base_text": m_base_text,
        "base_url": m_base_url,
        "max_fusion": m_max_fusion,
        "linear_meta": m_linear_meta,
        "interaction_meta": m_interaction_meta,
        "meta_weights": {
            "linear": {"beta_0": b0_lin, "beta_1": b1_lin, "beta_2": b2_lin},
            "interaction": {"beta_0": b0_int, "beta_1": b1_int, "beta_2": b2_int, "beta_3": b3_int}
        },
        "fold_metrics": {
            "text": fold_metrics_text,
            "url": fold_metrics_url
        }
    }

    with open(MODELS_DIR / "metrics_meta.json", "w") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"\n✅ All metrics saved to: {MODELS_DIR / 'metrics_meta.json'}")
    print("=" * 75)


if __name__ == "__main__":
    main()
