"""
ScamShield Forensic AI — Internal Verification & Stress-Testing Suite
For internal team verification only (not shown to advisor).

Tests:
  1. Automated Benchmark on 6 Hard Edge-Cases (Clean vs Messy, Phishing vs Benign)
  2. Side-by-side comparison of fusion mechanisms:
       - Max-Fusion Baseline (Heuristic)
       - Linear Meta-Learner
       - Interaction Meta-Learner (Proposed ScamGuard)
  3. Interactive mode for testing custom SMS/URLs
"""

import sys
import pickle
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent
MODELS_DIR = ROOT / "ml_model" / "models"

sys.path.append(str(ROOT / "ml_model"))
from preprocess import extract_raw_url, normalize_text, canonicalize_url, extract_13_features

# Color codes
G = "\033[92m"
Y = "\033[93m"
R = "\033[91m"
B = "\033[94m"
C = "\033[96m"
M = "\033[95m"
W = "\033[0m"
BOLD = "\033[1m"


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class ScamGuardVerifier:
    def __init__(self):
        print(f"{BOLD}{B}📦 Loading ScamGuard production models...{W}")
        with open(MODELS_DIR / "sms_classifier.pkl", "rb") as f:
            self.clf_text = pickle.load(f)
        with open(MODELS_DIR / "tfidf_sms.pkl", "rb") as f:
            self.vec_text = pickle.load(f)
        with open(MODELS_DIR / "url_classifier.pkl", "rb") as f:
            self.clf_url = pickle.load(f)
        with open(MODELS_DIR / "tfidf_url.pkl", "rb") as f:
            self.vec_url = pickle.load(f)
        with open(MODELS_DIR / "scaler_url.pkl", "rb") as f:
            self.scaler_url = pickle.load(f)
        with open(MODELS_DIR / "meta_learner.pkl", "rb") as f:
            self.meta_learner = pickle.load(f)

        # Meta coefficients
        self.b0 = float(self.meta_learner.intercept_[0])
        self.b1 = float(self.meta_learner.coef_[0][0])
        self.b2 = float(self.meta_learner.coef_[0][1])
        self.b3 = float(self.meta_learner.coef_[0][2])

        # Linear baseline coefficients
        self.b0_lin = -4.816
        self.b1_lin = 6.128
        self.b2_lin = 5.293

        print(f"{G}✓ Models loaded successfully.{W}")
        print(f"   Formula: s_fused = σ({self.b0:.3f} + {self.b1:.3f}*p_text + {self.b2:.3f}*p_url + {self.b3:.3f}*(p_text*p_url))\n")

    def analyze(self, raw_input: str) -> dict:
        # Step 1: Preprocessing & Canonicalization
        masked_txt, raw_url = extract_raw_url(raw_input)
        norm_txt = normalize_text(masked_txt)
        canon_url = canonicalize_url(raw_url) if raw_url else ""

        # Step 2: Text Branch
        X_txt = self.vec_text.transform([norm_txt])
        p_text = float(self.clf_text.predict_proba(X_txt)[0, 1])

        # Step 3: URL Branch (if URL exists)
        if canon_url:
            f13 = np.array([extract_13_features(canon_url)], dtype=np.float32)
            f13_scaled = self.scaler_url.transform(f13)
            f_char = self.vec_url.transform([canon_url]).toarray()
            X_u = np.hstack([f13_scaled, f_char])
            p_url = float(self.clf_url.predict_proba(X_u)[0, 1])

            # Fusion 1: Max Fusion
            s_max = max(p_text, p_url)

            # Fusion 2: Linear Meta
            z_lin = self.b0_lin + self.b1_lin * p_text + self.b2_lin * p_url
            s_lin = float(sigmoid(z_lin))

            # Fusion 3: Interaction Meta
            z_int = self.b0 + self.b1 * p_text + self.b2 * p_url + self.b3 * (p_text * p_url)
            s_int = float(sigmoid(z_int))
        else:
            p_url = None
            s_max = p_text
            s_lin = p_text
            s_int = p_text

        # Uncertainty on proposed model
        score_pct = s_int * 100.0
        uncertainty = 1.0 - 2.0 * abs(s_int - 0.5)

        if score_pct < 30.0:
            verdict = "BENIGN (Clear)"
            color = G
        elif score_pct < 80.0:
            verdict = "ESCALATE (VLM Cognitive Triage)"
            color = Y
        else:
            verdict = "MALICIOUS (Blocked)"
            color = R

        return {
            "raw": raw_input,
            "normalized_text": norm_txt,
            "extracted_url": canon_url,
            "p_text": p_text,
            "p_url": p_url,
            "s_max": s_max,
            "s_lin": s_lin,
            "s_int": s_int,
            "score_pct": score_pct,
            "uncertainty": uncertainty,
            "verdict": verdict,
            "color": color
        }


def run_benchmark():
    verifier = ScamGuardVerifier()

    test_cases = [
        {
            "category": "🚨 Phishing Scam (Vietcombank Fake OTP)",
            "text": "[VCB Digibank] Tai khoan cua quy khach bi tam khoa do vi pham dich vu. Vui long dang nhap http://vietcombank-security.vip/vcb de xac minh OTP ngay.",
            "ground_truth": "MALICIOUS"
        },
        {
            "category": "🚨 Phishing Scam (Government VNeID Impersonation)",
            "text": "Bo Cong An thong bao: Ho so VNeID muc 2 cua ban chua hoan tat. Truy cap http://dichvucong-vneid.top/app.apk de cap nhat truoc 24h tranh phat.",
            "ground_truth": "MALICIOUS"
        },
        {
            "category": "✅ Legitimate Bank Notification (With Official URL)",
            "text": "Vietcombank thong bao: So du TK 001100234567 thay doi -500,000 VND luc 14:30. Chi tiet xem tai https://vietcombank.com.vn hoac goi 1900545413.",
            "ground_truth": "BENIGN"
        },
        {
            "category": "✅ Legitimate Friendly SMS (Informal with raw link)",
            "text": "Toi gui lai cau bai tap ve nha va slide buoi truoc nhe, xem o https://drive.google.com/file/d/123456/view",
            "ground_truth": "BENIGN"
        },
        {
            "category": "⚠️ Borderline / Ambiguous Promo (Escalation Candidate)",
            "text": "Tri an khach hang than thiet: Nhan ma giam gia 50k khi dat hang tai shop hom nay. Chi tiet tai http://bit.ly/deal39k",
            "ground_truth": "BORDERLINE"
        },
        {
            "category": "💬 Text-Only Normal Scam (No URL Fallback Test)",
            "text": "Ban da trung thuong xe SH 150i tu chuong trinh tri an khach hang. Soan tin NHAN GUI 8777 de lam thu tuc nhan giai.",
            "ground_truth": "MALICIOUS"
        }
    ]

    print("=" * 80)
    print(f"{BOLD}🧪 INTERNAL VERIFICATION SUITE — 6 REAL-WORLD TEST CASES{W}")
    print("=" * 80)

    for i, tc in enumerate(test_cases, 1):
        res = verifier.analyze(tc["text"])
        print(f"\n{BOLD}[Case {i}] {tc['category']}{W}")
        print(f"  Input: \"{tc['text'][:85]}...\"")
        print(f"  • Extracted URL : {res['extracted_url'] or '(None - URL Fallback)'}")
        print(f"  • Normalized Txt: {res['normalized_text']}")
        print(f"  • Branch Scores : p_text = {res['p_text']*100:5.1f}% | p_url = {'N/A' if res['p_url'] is None else f'{res['p_url']*100:5.1f}%'}")
        
        # Compare fusion methods
        p_u_str = "N/A" if res['p_url'] is None else f"{res['p_url']*100:4.1f}%"
        print(f"  • {C}Fusion Comparison:{W}")
        print(f"      1. Max-Fusion       : {res['s_max']*100:5.1f}%")
        print(f"      2. Linear Meta      : {res['s_lin']*100:5.1f}%")
        print(f"      3. Interaction Meta : {BOLD}{res['s_int']*100:5.1f}%{W}  (ScamGuard Proposed)")
        print(f"  • Uncertainty Metric: {res['uncertainty']:.3f}")
        print(f"  • Final Decision    : {res['color']}{BOLD}{res['verdict']}{W} (GT: {tc['ground_truth']})")

    print("\n" + "=" * 80)
    print("🎯 Verification Completed successfully.")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        verifier = ScamGuardVerifier()
        print(f"{BOLD}💬 Interactive ScamGuard Shell. Type your SMS and press Enter (or 'exit' to quit):{W}\n")
        while True:
            try:
                line = input("SMS> ").strip()
                if not line or line.lower() in ("exit", "quit"):
                    break
                r = verifier.analyze(line)
                print(f"  Normalized  : {r['normalized_text']}")
                print(f"  URL         : {r['extracted_url'] or '(None)'}")
                print(f"  p_text      : {r['p_text']*100:.1f}%")
                if r['p_url'] is not None:
                    print(f"  p_url       : {r['p_url']*100:.1f}%")
                print(f"  Fused Score : {r['s_int']*100:.1f}% (Max-Fusion: {r['s_max']*100:.1f}%)")
                print(f"  Verdict     : {r['color']}{r['verdict']}{W}\n")
            except (KeyboardInterrupt, EOFError):
                break
    else:
        run_benchmark()
