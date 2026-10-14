"""
ScamShield Forensic AI — ML Training Pipeline
Trains two lightweight classifiers:
  1. SMS/Text Scam Classifier  (TF-IDF + Logistic Regression)
  2. URL Phishing Classifier   (Feature Engineering + Gradient Boosting)

Usage:
  python ml_model/train.py

Output (4 .pkl files in ml_model/models/):
  sms_classifier.pkl
  url_classifier.pkl
  tfidf_sms.pkl
  tfidf_url.pkl
  metrics.json   (accuracy, F1, AUC for paper)
"""

import os
import sys
import json
import time
import pickle
import warnings
import re
import math
from pathlib import Path

warnings.filterwarnings("ignore")

# ─── Auto-install dependencies if missing ────────────────────────────────────
def install(package):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

required = {"scikit-learn": "sklearn", "pandas": "pandas", "numpy": "numpy"}
for pkg, module in required.items():
    try:
        __import__(module)
    except ImportError:
        print(f"  📦 Installing {pkg}...")
        install(pkg)

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    precision_score, recall_score, classification_report
)
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import FunctionTransformer
from joblib import parallel_backend

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent   # scamshield-forensic/
DATA_DIR    = ROOT / "ml_model" / "data"
MODELS_DIR  = ROOT / "ml_model" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║      ScamShield Forensic AI — ML Training Pipeline          ║
║      TF-IDF + Logistic Regression | Gradient Boosting       ║
╚══════════════════════════════════════════════════════════════╝
"""

# ─── Colour helpers ──────────────────────────────────────────────────────────
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
R  = "\033[91m"   # red
B  = "\033[94m"   # blue
W  = "\033[0m"    # reset
BOLD = "\033[1m"

def ok(msg):  print(f"  {G}✓{W}  {msg}")
def info(msg): print(f"  {B}ℹ{W}  {msg}")
def warn(msg): print(f"  {Y}⚠{W}  {msg}")
def err(msg):  print(f"  {R}✗{W}  {msg}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

def load_sms_data() -> pd.DataFrame:
    """Load SMS spam dataset. Supports multiple filenames and encodings."""
    candidates = [
        DATA_DIR / "spam.csv",
        DATA_DIR / "SMSSpamCollection",
        DATA_DIR / "SMSSpamCollection.csv",
        DATA_DIR / "sms_spam.csv",
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            # Try CSV with multiple separator / encoding combos
            for enc in ("latin-1", "utf-8", "cp1252"):
                try:
                    # Standard Kaggle "spam.csv": columns v1=label, v2=text
                    df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
                    if "v1" in df.columns and "v2" in df.columns:
                        df = df[["v1", "v2"]].rename(columns={"v1": "label", "v2": "text"})
                        df = df.dropna()
                        ok(f"Loaded SMS data from {path.name}: {len(df):,} rows")
                        return df

                    # Tab-separated format (SMSSpamCollection)
                    df = pd.read_csv(path, sep="\t", header=None,
                                     names=["label", "text"], encoding=enc, on_bad_lines="skip")
                    df = df.dropna()
                    ok(f"Loaded SMS data from {path.name}: {len(df):,} rows")
                    return df
                except Exception:
                    continue
        except Exception as e:
            warn(f"Could not read {path.name}: {e}")
            continue

    # ── Fallback: create a realistic synthetic dataset ──────────────────────
    warn("SMS data file not found in ml_model/data/. Generating synthetic training set…")
    spam_msgs = [
        "URGENT: Your bank account has been suspended. Verify now: http://vcb-verify.vip/otp",
        "Congratulations! You won $5,000. Click to claim: bit.ly/win5000",
        "Your OTP is 847291. Do NOT share with anyone. Transaction: -15,000,000 VND",
        "FREE prize! Reply WIN to claim your reward. Limited time!",
        "ALERT: Suspicious login detected. Confirm identity: http://secure-login.vip",
        "You have been selected for a 20% commission task. Transfer money now!",
        "VCB: Your account will be closed. Click http://vietcombank-verify.info to reactivate",
        "Police: Your ID needs level-2 upgrade. Install app: http://vneid-update.apk-site.vip",
        "Make 0.065 SOL/hour guaranteed. Connect wallet: hashrate-accesscenter.com",
        "Earn 30% daily! Our BO platform guarantees 100% loss protection. Deposit now!",
        "Congratulations winner! Claim your prize by providing bank details immediately",
        "Your parcel is held. Pay customs: http://postoffice-payment.vip/fee",
        "IMPORTANT: Your account shows unusual activity. Call 1800-FAKE to verify",
        "Send money urgently! Emergency situation. Western Union accepted.",
        "Investment opportunity: 500% returns guaranteed. No risk. Join now!",
    ] * 40  # repeat to get more samples

    ham_msgs = [
        "Hey, are you free for lunch tomorrow?",
        "Meeting confirmed at 3pm in conference room B",
        "Your order #12345 has been shipped. Track at shopee.vn",
        "Hi, just checking in to see how your project is going",
        "Reminder: Your appointment is scheduled for Monday at 9AM",
        "Thanks for your payment. Receipt attached.",
        "Can you send me the updated report when you get a chance?",
        "Happy birthday! Hope you have a wonderful day!",
        "The team meeting is rescheduled to 2PM",
        "Your subscription renewal is due next month",
        "Dinner tonight? I found a great new restaurant",
        "Please review the document and send comments by Friday",
        "Your flight is confirmed. Check-in opens 24 hours before departure",
        "The project deadline has been extended to next week",
        "Good morning! Don't forget about the presentation today",
    ] * 40

    texts  = spam_msgs + ham_msgs
    labels = ["spam"] * len(spam_msgs) + ["ham"] * len(ham_msgs)
    df = pd.DataFrame({"label": labels, "text": texts})
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    ok(f"Generated synthetic SMS dataset: {len(df):,} samples")
    return df


def load_url_data() -> pd.DataFrame:
    """Load phishing URL dataset."""
    candidates = [
        DATA_DIR / "phishing_site_urls.csv",
        DATA_DIR / "phishing_urls.csv",
        DATA_DIR / "urls.csv",
        DATA_DIR / "malicious_phish.csv",
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            for enc in ("utf-8", "latin-1"):
                try:
                    df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
                    # Kaggle phishing_site_urls.csv: columns URL, Label
                    if "URL" in df.columns and "Label" in df.columns:
                        df = df[["URL", "Label"]].rename(columns={"URL": "url", "Label": "label"})
                        # Labels: "bad"/"good" or "phishing"/"benign"
                        df = df.dropna()
                        ok(f"Loaded URL data from {path.name}: {len(df):,} rows")
                        return df
                    # malicious_phish.csv format: url, type
                    if "url" in df.columns and "type" in df.columns:
                        df = df[["url", "type"]].rename(columns={"type": "label"})
                        df = df.dropna()
                        ok(f"Loaded URL data from {path.name}: {len(df):,} rows")
                        return df
                except Exception:
                    continue
        except Exception as e:
            warn(f"Could not read {path.name}: {e}")

    warn("URL data file not found. Generating synthetic URL dataset…")
    phishing = [
        "http://vietcombank-login.vip/verify-otp",
        "http://shopee-task-earn.top/commission",
        "https://hashrate-accesscenter.com/solana-miner",
        "http://vneid-gov.apk-download.site/vneid.apk",
        "http://bo-trading-vip.net/trade",
        "https://bit.ly/win-prize-claim",
        "http://secure-bank-verify.info/otp",
        "https://facebook-login-verify.com/auth",
        "http://vcb-reactivate.net/account",
        "https://netflix-billing-update.vip/payment",
        "http://amazon-prize-winner.com/claim",
        "https://paypal-secure-verify.net/confirm",
    ] * 80
    legit = [
        "https://www.google.com/search?q=weather",
        "https://shopee.vn/product/12345",
        "https://github.com/torvalds/linux",
        "https://www.vietcombank.com.vn/personal",
        "https://docs.python.org/3/library/",
        "https://www.youtube.com/watch?v=abc",
        "https://stackoverflow.com/questions/12345",
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://vneid.gov.vn/register",
        "https://facebook.com/groups/techvietnam",
    ] * 96
    urls   = phishing + legit
    labels = (["bad"] * len(phishing)) + (["good"] * len(legit))
    df = pd.DataFrame({"url": urls, "label": labels})
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    ok(f"Generated synthetic URL dataset: {len(df):,} samples")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURE ENGINEERING — URL
# ══════════════════════════════════════════════════════════════════════════════

def extract_url_features(url: str) -> list:
    """
    Hand-crafted features for URL phishing detection.
    Returns a fixed-length numeric feature vector.
    """
    try:
        url = str(url)
        # Basic length features
        url_len      = len(url)
        domain_part  = re.sub(r"https?://", "", url).split("/")[0]
        domain_len   = len(domain_part)
        path_len     = max(0, len(url) - len(domain_part) - 8)

        # Suspicious keywords
        sus_keywords = ["login", "verify", "secure", "update", "bank", "otp",
                        "confirm", "account", "password", "pay", "claim",
                        "win", "prize", "free", "urgent", "alert", "task",
                        "invest", "earn", "commission", "transfer", "apk"]
        keyword_count = sum(1 for kw in sus_keywords if kw in url.lower())

        # TLD analysis
        tld_suspicious = int(any(url.lower().endswith(t)
                                 for t in [".vip", ".top", ".xyz", ".site",
                                           ".info", ".biz", ".click", ".link"]))
        tld_trusted    = int(any(domain_part.lower().endswith(t)
                                 for t in [".gov.vn", ".edu.vn", ".com.vn",
                                           ".gov", ".edu", ".org"]))

        # Digit / special-char ratios
        digit_ratio   = sum(c.isdigit() for c in url) / max(url_len, 1)
        special_ratio = sum(c in "-_@!~" for c in url) / max(url_len, 1)

        # Hyphen count (many hyphens → suspicious)
        hyphen_count  = url.count("-")

        # Subdomain depth
        subdomain_depth = max(0, len(domain_part.split(".")) - 2)

        # IP address in domain?
        has_ip = int(bool(re.match(r"\d{1,3}(\.\d{1,3}){3}", domain_part)))

        # Presence of brand names in suspicious context
        brands = ["vietcombank", "vcb", "shopee", "solana", "vneid",
                  "facebook", "paypal", "amazon", "netflix", "telegram"]
        brand_in_domain = int(any(b in domain_part.lower() for b in brands))

        # Shannon entropy of the domain (high entropy → random = suspicious)
        freq = {}
        for c in domain_part.lower():
            freq[c] = freq.get(c, 0) + 1
        entropy = -sum((v / len(domain_part)) * math.log2(v / len(domain_part))
                       for v in freq.values()) if domain_part else 0

        return [
            url_len, domain_len, path_len,
            keyword_count, tld_suspicious, tld_trusted,
            digit_ratio, special_ratio, hyphen_count,
            subdomain_depth, has_ip, brand_in_domain, entropy,
        ]
    except Exception:
        return [0] * 13


def build_url_feature_matrix(urls):
    return np.array([extract_url_features(u) for u in urls])


# ══════════════════════════════════════════════════════════════════════════════
# 3. TRAINING
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_model(model, X, y):
    """Fit once per fold, fitting TF-IDF only on that fold's training data."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    with parallel_backend("threading"):
        scores = cross_validate(
            model, X, y, cv=cv, scoring=["accuracy", "f1", "roc_auc"],
            n_jobs=4, error_score="raise", verbose=2,
        )
    acc_scores, f1_scores, auc_scores = (
        scores["test_accuracy"], scores["test_f1"], scores["test_roc_auc"]
    )
    for i, (a, f, r) in enumerate(zip(acc_scores, f1_scores, auc_scores), 1):
        print(f"     Fold {i}/5: Accuracy={a:.3f}  F1={f:.3f}  AUC-ROC={r:.3f}")
    return acc_scores, f1_scores, auc_scores


def train_sms_model(df: pd.DataFrame):
    """TF-IDF + Logistic Regression for SMS / text classification."""
    print(f"\n  {BOLD}🏋️  Training SMS Text Classifier…{W}")

    # Normalise labels
    df["label"] = df["label"].str.lower().str.strip()
    label_map   = {"spam": 1, "ham": 0,
                   "phishing": 1, "benign": 0,
                   "bad": 1, "good": 0,
                   "scam": 1, "legit": 0}
    df["label_enc"] = df["label"].map(label_map).fillna(0).astype(int)

    X = df["text"].fillna("").values
    y = df["label_enc"].values

    tfidf = TfidfVectorizer(
        max_features=10_000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
    )
    clf = LogisticRegression(max_iter=1000, C=5.0, solver="lbfgs",
                             class_weight="balanced", random_state=42)

    model = Pipeline([("tfidf", tfidf), ("classifier", clf)])
    acc_scores, f1_scores, auc_scores = evaluate_model(model, X, y)
    model.fit(X, y)   # final fit on full data

    metrics = {
        "sms_accuracy": float(acc_scores.mean()),
        "sms_f1"      : float(f1_scores.mean()),
        "sms_auc"     : float(auc_scores.mean()),
        "sms_samples" : int(len(df)),
    }
    print(f"\n  {G}📊 SMS Model — Accuracy: {acc_scores.mean():.3f} | F1: {f1_scores.mean():.3f} | AUC: {auc_scores.mean():.3f}{W}")
    return tfidf, clf, metrics


def train_url_model(df: pd.DataFrame):
    """Feature engineering + Gradient Boosting for URL phishing detection."""
    print(f"\n  {BOLD}🏋️  Training URL Phishing Classifier…{W}")

    df["label"] = df["label"].str.lower().str.strip()
    label_map   = {"bad": 1, "phishing": 1, "malicious": 1, "defacement": 1,
                   "good": 0, "benign": 0, "legitimate": 0}
    df["label_enc"] = df["label"].map(label_map).fillna(0).astype(int)

    # Subsample large datasets to keep training fast
    if len(df) > 50_000:
        df = df.sample(50_000, random_state=42)
        info(f"Subsampled URL dataset to 50,000 rows for speed")

    urls = df["url"].fillna("").values
    y    = df["label_enc"].values

    # Also use TF-IDF on URL characters as second view
    tfidf_url = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                                max_features=5000, sublinear_tf=True)
    features = FeatureUnion([
        ("numeric", FunctionTransformer(build_url_feature_matrix)),
        ("tfidf", tfidf_url),
    ])

    clf = GradientBoostingClassifier(
        n_estimators=100, max_depth=4,
        learning_rate=0.1, random_state=42,
        subsample=0.8,
    )

    model = Pipeline([("features", features), ("classifier", clf)])
    acc_scores, f1_scores, auc_scores = evaluate_model(model, urls, y)
    info("Fitting final URL model on the selected training data…")
    model.fit(urls, y)
    tfidf_url = model.named_steps["features"].transformer_list[1][1]

    metrics = {
        "url_accuracy": float(acc_scores.mean()),
        "url_f1"      : float(f1_scores.mean()),
        "url_auc"     : float(auc_scores.mean()),
        "url_samples" : int(len(df)),
    }
    print(f"\n  {G}📊 URL Model — Accuracy: {acc_scores.mean():.3f} | F1: {f1_scores.mean():.3f} | AUC: {auc_scores.mean():.3f}{W}")
    return tfidf_url, clf, metrics


# ══════════════════════════════════════════════════════════════════════════════
# 4. SAVE / LOAD UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def save_model(obj, filename: str):
    path = MODELS_DIR / filename
    with open(path, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    ok(f"Saved  →  {path}")


def save_metrics(metrics: dict):
    path = MODELS_DIR / "metrics.json"
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    ok(f"Saved metrics  →  {path}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print(BANNER)
    t0 = time.time()

    # ── Load datasets ──────────────────────────────────────────────────────
    print(f"\n{BOLD}📂  Loading Datasets{W}")
    print("  ─" * 30)
    sms_df = load_sms_data()
    url_df = load_url_data()

    # ── Train SMS classifier ──────────────────────────────────────────────
    print("\n" + "─" * 65)
    tfidf_sms, clf_sms, sms_metrics = train_sms_model(sms_df)

    # ── Train URL classifier ──────────────────────────────────────────────
    print("\n" + "─" * 65)
    tfidf_url, clf_url, url_metrics = train_url_model(url_df)

    # ── Save all artefacts ────────────────────────────────────────────────
    print(f"\n{BOLD}💾  Saving Models{W}")
    print("  ─" * 30)
    save_model(tfidf_sms, "tfidf_sms.pkl")
    save_model(clf_sms,   "sms_classifier.pkl")
    save_model(tfidf_url, "tfidf_url.pkl")
    save_model(clf_url,   "url_classifier.pkl")

    all_metrics = {**sms_metrics, **url_metrics, "training_time_seconds": round(time.time() - t0, 1)}
    save_metrics(all_metrics)

    # ── Final summary ─────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"""
{G}{'═'*65}
  ✅  TRAINING COMPLETE!
{'═'*65}{W}
  SMS Model  → Accuracy: {sms_metrics['sms_accuracy']:.1%}  |  F1: {sms_metrics['sms_f1']:.3f}  |  AUC: {sms_metrics['sms_auc']:.3f}
  URL Model  → Accuracy: {url_metrics['url_accuracy']:.1%}  |  F1: {url_metrics['url_f1']:.3f}  |  AUC: {url_metrics['url_auc']:.3f}

  {G}4 model files saved to:  ml_model/models/{W}
    ✅ sms_classifier.pkl
    ✅ url_classifier.pkl
    ✅ tfidf_sms.pkl
    ✅ tfidf_url.pkl
    ✅ metrics.json

  ⏱  Total training time: {elapsed:.1f} seconds

  {B}👉 Next step:{W}
     Run the dev server:  npm run dev
     The ML pre-classifier is now live at /api/ml-classify
""")


if __name__ == "__main__":
    main()
