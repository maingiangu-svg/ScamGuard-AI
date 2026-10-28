# URL accuracy target above 95%, 2026-10-27

User requests further supervised training with accuracy strictly above 95%.
This applies to URL classification, the branch studied in this conversation;
SMS weights are preserved. Accuracy means (TN + TP) / all labeled cases, not
precision, model confidence or a guarantee about website safety.

## Protocol fixed before the new run

- Preserve all earlier experiments, original labels, active model and checks.
- Use the checksum-pinned original good/bad URL source. Repair, deduplicate and
  quarantine conflicts using the existing shared preparation. Exclude every
  owner domain in the historical selected 50,000 URLs, repaired SMS/URL rows,
  earlier PhishVN experiments/audits, official seeds and known serving examples.
- Select additional source-labeled cases using SHA-256 URL order, at most ten
  URLs per ICANN owner domain. Assign new domains to training (hash modulo 5
  nonzero) or a fresh reserved test (modulo 5 zero), before fitting or scoring.
  Cap additions at 40,000 training URLs and the fresh test at 4,000 URLs, without
  selecting by model outputs or making labels. Retain the natural label mix of
  this capped/hash-sampled source subset and report the majority-class baseline.
  All extra labels are inherited source labels, not expert verification.
- Join additions to the existing 31,309 accepted training rows. Keep fresh test
  domains separate from every old and new fitting/calibration/selection domain.
  The fresh set is new for these model fits, drawn from the same historical
  source; it is not independent external or expert-verified population evidence.
- Compare exactly four candidate configurations against the existing estimator
  using three training-only owner-domain folds, fixed seed 42 and URL threshold
  0.50. Fit vocabulary, scaling and SVD inside each fold:
  1. Character 2–6 TF-IDF, 50,000 features, min_df=2, sublinear TF, plus the existing
     13 scaled numeric features; LogisticRegression C=1, liblinear, max_iter=1000.
  2. Same representation with LogisticRegression C=4.
  3. Existing 13 numeric features; ExtraTrees, 300 trees, min_samples_leaf=2,
     max_features=1.0, random_state=42, n_jobs=2.
  4. Existing 13 scaled numeric features plus character 3–5 TF-IDF (5,000 features,
     min_df=2, sublinear TF), then 64-component randomized SVD (five iterations,
     seed 42) on the character branch. HistGradientBoosting: max_iter=200,
     max_depth=6, min_samples_leaf=15, l2_regularization=1, early_stopping=False,
     random_state=42.
- Selection never reads either test's predictions. Preserve nonregression in
  training-only pooled FP/TP counts relative to the paired reference. Prefer
  candidates with accuracy >0.95 and both constraints satisfied; maximize accuracy,
  then F1, then minimize FP, then stable name order. If none meets the target,
  fit the best nonregressing candidate for research and report that failure.
- Freeze the selected estimator, fit final train-only three-outer/three-inner
  grouped sigmoid calibration, and retain its raw 0.50 alert threshold. Report
  selection bias in development calibration estimates. No resampling, overrides,
  threshold search, fabricated phishing examples or fitting the serving tests.
- Freeze weights before one fresh-test evaluation. Report accuracy, precision,
  recall, F1, balanced accuracy, confusion matrix and Wilson accuracy interval.
  Evaluate the old 9,935 URL tests once as a reused diagnostic, not as a new
  benchmark. Evaluate existing serving regressions separately. Do not activate
  an artifact that fails the target, nonregression, calibration or serving checks.
- Bind data/source/split/code/selection/calibration/evaluation hashes. Completed
  stages refuse reruns. Do not tune or try a second winner against these tests.

Model APIs follow official scikit-learn documentation for
[ExtraTreesClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesClassifier.html)
and [TruncatedSVD](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.TruncatedSVD.html).

## Commands

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
.\.venv\Scripts\python.exe ml_model\accuracy_target_training.py prepare
.\.venv\Scripts\python.exe ml_model\accuracy_target_training.py select
.\.venv\Scripts\python.exe ml_model\accuracy_target_training.py fit
.\.venv\Scripts\python.exe ml_model\accuracy_target_training.py evaluate
```

Local artifacts: `ml_model/data/prepared/accuracy95_2026-10-27/`.

## Data preparation and trace audit

The completed preparation added 40,000 URLs (26,773 source-good, 13,227
source-bad) to the prior 31,309 accepted URL training rows. Total URL fitting
rows: 71,309, with 51,034 source/seed label 0 and 20,275 label 1. The SMS head's
3,786 fitting rows and weights are preserved.

The fresh reserved set contains 4,000 URLs: 2,670 source-good and 1,330
source-bad, covering 3,764 ICANN owner domains. Its majority-class baseline is
66.75%. The 54,290 fitting owner domains have zero overlap with those test
domains. All 77,966 previously represented/excluded owner domains were blocked
before new-source sampling.

An additional trace audit independently compared all 40,000 added fitting rows
and 4,000 held-out rows with their original source record numbers, labels and
repaired URL strings. All matched; zero expert labels were created. It also
verified the pinned Public Suffix List and zero owner overlap with the earlier
50,000 selected URLs. Trace correctness does not independently verify the
semantic truth of inherited source labels or prove campaign independence.

Shared source preparation quarantined 5,158 malformed/conflicting records and
removed 41,760 duplicates before new-source selection. These are preparation
counts for the full 549,346-row source, not new training/test sample counts.

## Training-only model comparison

All configurations used exactly the same three owner-domain folds. These
results select a configuration; they are not an unbiased final accuracy estimate.

| Configuration | Accuracy | False alarms | Bad URLs detected | Eligible for target selection |
|---|---:|---:|---:|---|
| Refitted existing estimator | 91.84% | 1,090 | 15,545 | Reference |
| Wide character LR C=1 | 94.85% | 872 | 17,477 | No: below 95% |
| Wide character LR C=4 | 95.58% | 979 | 18,104 | Yes, selected |
| Numeric ExtraTrees | 82.81% | 4,912 | 12,927 | No |
| SVD + gradient boosting | 93.16% | 1,631 | 17,025 | No |

The selected C=4 configuration passed both fixed FP/TP nonregression constraints
and the strict accuracy >0.95 criterion using training-only predictions. Neither
fresh nor historical test scores were used to make this choice.

The exact seven source/dependency files used by the frozen training protocol
were archived under the run's `frozen_source/` directory with matching SHA-256
checksums, alongside all fitting rows, fold membership and selection predictions.

## Final result: observed fresh-test accuracy 95.375%

The selected wide-character LR C=4 model was fitted on all 71,309 URL training
rows. Nested group calibration and final fitting took 397.354 seconds. Source-label
Brier decreased from 0.035414 to 0.034326 and log loss from 0.131955 to 0.126481.
The calibration gate passed; development selection bias remains acknowledged.

The fitted weights were frozen before the first and only fresh-test scoring.
On 4,000 reserved source-labeled URLs, the candidate got 3,815 correct and 185
wrong, exceeding the strict observed-accuracy target of 95%.

| Fresh-test measure | Active baseline | Trained candidate |
|---|---:|---:|
| Accuracy | 89.33% | **95.38%** |
| Precision for source-bad URLs | 91.31% | 95.91% |
| Recall for source-bad URLs | 75.04% | 89.92% |
| F1 | 82.38% | 92.82% |
| Balanced accuracy | 85.74% | 94.01% |
| Correctly cleared source-good URLs | 2,575 | 2,619 |
| False alarms | 95 | 51 |
| Missed source-bad URLs | 332 | 134 |
| Detected source-bad URLs | 998 | 1,196 |

The 95% owner-domain cluster bootstrap interval for candidate accuracy is
**94.71%–96.00%** (1,000 resamples of 3,764 owner groups; seed 42). The row-wise
Wilson interval is 94.68%–95.98%. Both intervals include values below 95%: this
run establishes an observed source-label agreement above 95%, not a statistical
guarantee of population accuracy above 95%. Source-label errors, source shift
and cross-domain campaign overlap remain outside those sampling intervals.
There is no expert-verified or independent external evaluation in this run.

On the reused historical 9,935-case diagnostic, accuracy improved from 92.29%
to 96.02%, false alarms decreased from 160 to 131, and detected source-bad URLs
increased from 1,624 to 1,966. Precision was 93.75%, recall 88.16% and F1 90.87%.
That aggregate nonregression gate also passed. These historical scores were
not used to choose or refit another configuration.

## Serving decision: candidate remains unactivated

The existing `https://qi.lv/F0i` serving checks still fail: the candidate scores
the URL 27 and returns CLEAR, and does not request an independent URL review when
the URL accompanies ordinary lunch-message text. The active baseline scores the
same URL 94/BLOCK and requests URL review in mixed input. No new label was assigned
to this serving example and it was not inserted into fitting to force that result.

The long reported Sunwin profile URL scored 59, preserving the expected REVIEW
band. All 14 exact official service URLs checked scored below the URL review
threshold; ten are seen fitting seeds and four remain excluded owner domains.
These exact-URL checks do not establish that all content on those domains is safe.

**The observed >95% training objective was met on the reserved source-labeled
test, but serving quality gates were not all met. The active model was preserved.**
There is no activation command in this experimental runner. The candidate bundle,
its checksum manifest, fitting data, predictions and evidence remain available
locally for review. No deployment, external publication or active-weight change
was performed.

### SMS state audit correction

The frozen evaluation's `sms_head_byte_identical` field was computed after
candidate SMS inference. It reported false because scikit-learn's word TF-IDF
transformer updates its `_stop_words_id` runtime cache during prediction.
This was a QA false alarm, not a change to trained SMS weights.

A separately recorded audit loaded both saved bundles again, compared the
complete SMS states **before** inference and confirmed identical serialized
bytes (SHA-256 `4bcd9784c00bf2115a6c4da80b29070462cdfd041c17ede694f008a1c7171129`).
It isolated the only changed word-vectorizer attribute to `_stop_words_id` and
confirmed identical SMS prediction scores. The original frozen evaluation was
preserved; the correction is in `sms_state_audit.json`. Correcting this cache
check leaves activation blocked by the genuine `qi.lv/F0i` regression.

## Verification and artifacts

- 128 Python tests and 47 JavaScript unit tests passed. Lint, production build
  and TypeScript checks passed. The source-label accuracy boundary test caught
  an intentional `>=95%` mutation in a temporary copy; training code stayed frozen.
- The independent trace audit verified 44,000 added/reserved source records and
  zero fitting/test owner overlap. Frozen source snapshots match protocol hashes.
- Candidate bundle SHA-256:
  `cb64212f5bec259ac8ad62b3c701fd9119fb46cd50091a333f5e3800b6ca9e62`.
- Active parent SHA-256 (preserved):
  `6a0fd38b35570bff4b0ae56dd52a07747a6670d3dc2eceda304e1f10898314d0`.
- [Machine-readable results](accuracy95-training-2026-10-27.json) include model
  comparison, data/trace audit, calibration, fresh and historical confusion
  matrices, uncertainty intervals, serving regressions and the SMS cache audit.
- Local run: `ml_model/data/prepared/accuracy95_2026-10-27/`. Raw datasets and
  per-record exports remain local and gitignored; the shareable report contains
  aggregate metrics and already-public official URL checks.
