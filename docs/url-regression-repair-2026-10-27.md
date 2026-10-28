# Supervised URL regression repair, 2026-10-27

User authorized resolving the remaining URL-model regressions. Preserve the
new character model's broad improvement and learn when to retain strong evidence
from the existing URL model. No benchmark URL is fitted, no hostname lookup
overrides a prediction, and SMS scores/policy remain unchanged.

## Protocol before fitting the repair

- Freeze the existing 31,299-row URL head and the 71,309-row character head.
- Fit a single global residual gate using genuine out-of-sample base scores:
  use the original parent URL head's nested-group OOF scores for its 31,299 fit
  rows; for the 40,000 newly added owner domains use the frozen parent head's
  predictions, because those owners were never fitted by that head. Use the
  character head's frozen training-group OOF scores for the same 71,299 cases.
  Exact case membership, labels, row groups and score ranges must match.
- The ten first-party fitting seeds are excluded from the source-label OOF
  performance table. Their label-0 training sanity constraint forbids introducing
  a positive alert for any accepted seed currently cleared by the character head.
  The four excluded/held-out official owner domains are never gate constraints.
- Test exactly these parent-confidence cutoffs: 0.50, 0.60, 0.70, 0.80, 0.85,
  0.90, 0.95, 0.975, 0.99, 1.01 (disabled). A cutoff is learned once from labels.
  Above the fitted cutoff the ensemble retains the larger trained URL score;
  below it the character head supplies the score. This is a supervised learned
  gate between URL models, not a text–URL fusion or a domain allowlist.
- Require development accuracy >95%, FP no greater than the parent reference,
  and TP no lower than the character reference; require no new positive alert on
  the ten accepted fitting seeds. Among eligible cutoffs maximize TP, then accuracy,
  then use the larger cutoff to break ties. These are fitting/selection estimates,
  not independent performance estimates. Never choose a cutoff from serving tests.
- Before fitting, reserve new source-owner groups outside all previous fits,
  tests, calibration and published audit domains. Hash-assign and cap ten URLs per
  owner: 3,000 calibration-fit URLs, 3,000 calibration-validation URLs and 4,000
  fresh test URLs. Repair, quarantine and retain original source labels/provenance.
  Old 4,000-case and 9,935-case tests remain excluded and diagnostic-only.
- Freeze the learned gate. Fit sigmoid calibration on the new calibration-fit
  groups only, wrapping the fitted ensemble in FrozenEstimator. Require Brier
  and log loss not to worsen on the disjoint calibration-validation groups.
  Calibration does not change the raw alert score or fixed URL threshold 0.50.
- Freeze weights before a single fresh-test evaluation. Require fresh accuracy
  >95%, historical FP/TP nonregression versus the active model, and all existing
  serving checks, including high-risk `qi.lv/F0i`, independent mixed-input URL
  review, official URL clearance and long-URL review. Preserve trained SMS state
  by comparing it before inference to avoid TF-IDF runtime-cache false alarms.
- Activation also requires bound evidence/checksums, unchanged parent, complete
  API checks against the candidate, and a backup of existing local artifacts.
  No remote deployment is authorized or performed by this experiment.

Already fitted classifiers can be calibrated on disjoint data using
[FrozenEstimator with CalibratedClassifierCV](https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html).

## Commands

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
.\.venv\Scripts\python.exe ml_model\repair_url_ensemble.py prepare
.\.venv\Scripts\python.exe ml_model\repair_url_ensemble.py fit
.\.venv\Scripts\python.exe ml_model\repair_url_ensemble.py evaluate
```

Artifacts: `ml_model/data/prepared/url_regression_repair_2026-10-27/`.

## Calibration revision before the fresh test

The raw residual gate was learned once at 0.80. Its development source-label
accuracy was 95.56%, with 1,057 FP and 18,163 TP. The ten accepted fitting seeds
were kept clear. The source OOF/reference mixture had 1,227 FP; the character
reference had 18,104 TP. Lower cutoffs failed the predefined false-alarm or seed
constraints. No serving-test score selected the cutoff.

Sigmoid calibration on the 3,000 calibration-fit groups reduced validation Brier
slightly but increased log loss, so it was rejected. Before any new test was
scored, temperature calibration was fitted on the same calibration-fit groups
and selected using the designated 3,000-case calibration-validation set:

| Validation measure | Raw ensemble | Selected temperature calibration |
|---|---:|---:|
| Brier | 0.036285 | 0.035890 |
| Log loss | 0.133180 | 0.130602 |

Both original calibration quality requirements passed. Validation metrics have
method-selection bias because two calibration families were considered; they
are not independent final estimates. The raw heads and learned gate were not
refitted, and raw alert scores stayed unchanged. The failed sigmoid artifact and
report remain intact. `finalize_url_repair.py` creates the separately bound final
revision at `data/prepared/url_regression_repair_final_2026-10-27/`.

```powershell
.\.venv\Scripts\python.exe ml_model\finalize_url_repair.py fit
.\.venv\Scripts\python.exe ml_model\finalize_url_repair.py evaluate
# Activation additionally requires a successful, checksum-bound candidate API run:
.\.venv\Scripts\python.exe ml_model\finalize_url_repair.py activate
```

## Completed results

The fresh 4,000-case source-label test covers 3,740 new owner domains. It was
reserved before fitting and scored once after the gate and calibration were
frozen. Calibration fitting, calibration validation and both raw-model fitting
owner sets are disjoint from these test owners.

| Fresh-test measure | Previous active model | Character candidate | Activated ensemble |
|---|---:|---:|---:|
| Accuracy | 89.18% | 95.10% | **95.18%** |
| Precision | 93.26% | 96.13% | 95.99% |
| Recall | 71.69% | 88.40% | 88.79% |
| F1 | 81.07% | 92.10% | 92.25% |
| False alarms | 67 | 46 | 48 |
| Missed source-bad URLs | 366 | 150 | 145 |
| Detected source-bad URLs | 927 | 1,143 | 1,148 |

Observed accuracy is 3,807 / 4,000 = 95.175%. Its owner-cluster bootstrap 95%
interval is **94.47%–95.80%** (1,000 resamples, seed 42). The interval includes
values below 95%; this is observed agreement with inherited source labels, not
a guarantee that population or expert-verified real-world accuracy exceeds 95%.
Campaign independence and source-label correctness are not established.

The residual guard trades two additional false alarms for five recovered bad
URLs versus the character-only model on this fresh set. It is not claimed to
improve every metric on every dataset. On the previously used 4,000-case set,
accuracy was 95.33% versus 95.38% character-only; false alarms rose from 51 to 59
while missed bad URLs fell from 134 to 128. On the reused 9,935-case diagnostic,
accuracy was 95.99%, with 140 FP and 1,972 TP, versus the old active model's
160 FP and 1,624 TP. The existing aggregate release gates passed.

## Serving regression resolved

The exact `qi.lv/F0i` URL and its owner domain are absent from both raw heads'
fitting records, gate fitting and calibration. Production prediction code contains
no hostname-specific rule. The source-label-trained global residual gate restores
the original model's complementary strong evidence:

| Existing case | Character-only candidate | Activated ensemble |
|---|---|---|
| `https://qi.lv/F0i` | 27, CLEAR | **94, BLOCK** |
| Ordinary lunch SMS plus that URL | CLEAR; no URL review | **REVIEW; URL review required** |
| Long reported Sunwin profile URL | 59, REVIEW | 59, REVIEW |
| Bare `https://facebook.com/` | CLEAR | CLEAR |

All 14 exact official URL checks remain below the review threshold. Examples:
YouTube 0, Facebook 1, Vietcombank 15, MoMo 7. Rounded zero is not a safety guarantee;
the model does not certify all content, paths or redirect targets on a domain.
The SMS state was compared before prediction and remained byte-identical to its
parent, avoiding the earlier `_stop_words_id` runtime-cache false alarm.

## Verification and local activation

- 136 Python tests, 47 JavaScript unit tests, 17 candidate API integration tests
  and 3 post-activation inference-lifecycle tests passed: **203 checks total**.
  Lint, production build and TypeScript checks passed. No test was removed or
  skipped. A deliberately removed benign-seed constraint was detected by a new
  test in a temporary source copy; the actual frozen source was preserved.
- The API harness can read `TEST_MODEL_MANIFEST` to check an isolated candidate
  server without changing active artifacts. The SMS model-ID assertion now checks
  the manifest's explicit per-head identity, preserving the inherited SMS version.
  All original alert, score, CORS, admission and input assertions remain enforced.
- A production standalone server loaded the actual candidate bundle and passed
  all 17 API checks before activation. Training data were absent from its package.
  Exact model, manifest and verification-script hashes bind the API evidence.
- A separate audit traced all 10,000 new calibration/validation/test rows back
  to original source URLs and labels and confirmed zero cross-role owner overlap,
  zero overlap with previous tests and no regression-domain fitting. No expert
  labels were fabricated. Frozen source snapshots were archived with checksums.
- The candidate was installed into local `ml_model/models/hybrid_bundle.pkl`
  and `hybrid_manifest.json`. Real default `predict_hybrid.classify` then verified
  the new run ID and expected scores; active and packaged artifacts match.
- Active run: `url-ensemble-20261027`. Bundle SHA-256:
  `26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`.
- Previous active pair is backed up under
  `data/prepared/url_regression_repair_final_2026-10-27/previous_active/`.
  Activation was local; the remote deployment was not changed.
- [Machine-readable evidence](url-regression-repair-2026-10-27.json) contains
  calibration-family results, OOF gate selection, all confusion matrices,
  official URL scores, serving checks, API verification and activation hashes.
