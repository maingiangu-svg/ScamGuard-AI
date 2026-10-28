# URL supervised training round 2, 2026-10-27

User requested additional training after the official-URL candidate failed.
This is a separate run; preserve the prior run and active model. Retain the
31,299 accepted source-labeled URL training rows and 10 first-party URL seeds.
No historical validation/test/quarantined row or excluded owner domain enters
fitting, calibration or model/threshold selection. No new labels are fabricated.
The SMS head, URL preprocessing and fixed alert threshold 0.50 stay unchanged.

## Protocol frozen before model comparison

1. Verify the earlier run's bound data and the unchanged active parent.
2. Make one deterministic 3-fold stratified split by existing owner-domain
   repair groups on training rows only. Save exact fold membership before fitting.
3. Refit the existing URL estimator as a reference in each fold. Compare exactly
   three sparse URL pipelines: existing 13 numeric URL features plus character
   TF-IDF (3–5 characters, 20,000 features, minimum document frequency 2,
   sublinear TF), and LogisticRegression with C = 1, 4 or 16, solver liblinear,
   max_iter 1000, seed 42. Each row has ordinary weight 1. Fit vocabulary, numeric
   scaling and classifier inside each training fold; no full-data feature cache.
4. Choose only from candidates whose pooled out-of-fold false positives do not
   exceed the reference and whose true positives do not fall below it. Among
   eligible candidates maximize F1, then minimize false positives, then use stable
   configuration-name order. If none qualifies, retain a fitted research candidate
   but block activation. Selection metrics are development estimates, not an
   unbiased final performance estimate.
5. Freeze the chosen configuration and selection checksum. Reuse the existing
   train-only 3-outer/3-inner grouped sigmoid calibration protocol and fit a final
   URL candidate on all accepted training rows. Require Brier and log loss not to
   increase against raw scores on the outer folds. Because the configuration was
   chosen on the same development corpus, these calibration estimates also have
   selection bias; do not call them a new independent benchmark.
6. Freeze candidate weights before one evaluation on the historical 9,935-case
   URL diagnostic. It is reused and has already been inspected in earlier runs.
   It never selects between the three configurations or changes thresholds.
   Preserve the release criteria: no additional false positives and no loss of
   true positives against the active baseline. If any gate fails, preserve the
   active model. No retries/retuning against this historical test.
7. Bind input, split, selection, code, calibration and evaluation checksums;
   preserve parent artifacts and label provenance. Exact official-seed scores
   are seen-example checks, not general safety guarantees or test accuracy.

The sparse estimator accepts sparse inputs as documented by
[scikit-learn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html).
Non-overlapping group folds follow
[StratifiedGroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html).

## Commands

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
.\.venv\Scripts\python.exe ml_model\url_model_selection.py select
.\.venv\Scripts\python.exe ml_model\url_model_selection.py fit
.\.venv\Scripts\python.exe ml_model\url_model_selection.py evaluate
```

Do not activate this completed candidate: the additional serving-regression
checks below failed, even though the aggregate historical diagnostic passed.

Local artifacts: `ml_model/data/prepared/url_training_round2_2026-10-27/`.

## Completed training-only selection

All four estimators used the same 31,309 accepted training rows and exact same
three disjoint owner-domain folds. No historical test prediction was read by
the selection stage.

| Configuration | False positives | Missed bad URLs | Detected bad URLs | F1 | Eligible |
|---|---:|---:|---:|---:|---|
| Existing estimator refitted in folds | 351 | 1,423 | 5,625 | 86.38% | Reference |
| Sparse C=1 | 302 | 1,287 | 5,761 | 87.88% | Yes, selected |
| Sparse C=4 | 399 | 946 | 6,102 | 90.07% | No: more false alarms |
| Sparse C=16 | 499 | 803 | 6,245 | 90.56% | No: more false alarms |

The higher F1 candidates were excluded by the predeclared false-alarm constraint.
The selected C=1 reduces 49 false alarms and detects 136 additional bad URLs
versus the paired reference on these development folds. Selection on these
predictions means these numbers are not an unbiased independent accuracy claim.

## Final fit and historical diagnostic

The selected sparse C=1 URL head was refitted on all 31,309 accepted training
rows with ordinary row weight 1. No new labels or duplicate records were added
in round 2. The SMS head is byte-identical to its active parent. Final nested
group calibration/fitting took 80.791 seconds. Source-label Brier decreased from
0.040702 to 0.036723 and log loss from 0.152143 to 0.127971; the train-only
calibration gate passed. Selection bias remains possible because selection and
calibration estimates share the development corpus.

After freezing the winner and fitted bundle, one comparison was run on the
9,935-case historical URL diagnostic. These tests were reused from prior runs;
the results are not a fresh independent benchmark or real-world safety rate.

| Measure | Active baseline | Round 2 candidate |
|---|---:|---:|
| Legitimate URLs correctly cleared | 7,545 | 7,611 |
| False alarms | 160 | 94 |
| Bad URLs missed | 606 | 472 |
| Bad URLs detected | 1,624 | 1,758 |
| Precision | 91.03% | 94.92% |
| Recall | 72.83% | 78.83% |
| F1 | 80.92% | 86.13% |

The original aggregate false-alarm/detection gate passed. There were 66 fewer
false alarms and 134 additional bad URLs detected, with the threshold fixed at
0.50. No second configuration was selected or retuned after this evaluation.

## Serving regression: candidate not activated

The existing API tests also require `https://qi.lv/F0i` to trigger a high-risk
URL alert and require an independent URL review when it accompanies ordinary
SMS text. A check using the actual frozen candidate through `predict_hybrid`
confirmed both regressions:

| Existing case | Active baseline | Round 2 candidate |
|---|---|---|
| URL-only `https://qi.lv/F0i` | 94, BLOCK | 30, CLEAR |
| Ordinary lunch message plus that URL | REVIEW; URL review required | CLEAR; URL review not required |

The URL-only alert uses the raw 0.50 URL threshold; a rounded score of 30 can
therefore still be CLEAR. This is unchanged policy, not a threshold adjustment.
The candidate remains a research artifact. **No activation was performed.**
The serving bundle/manifest remain the original active version. No existing
assertion was removed or weakened to accept the new model. The example was not
given a new training label or added to fitting to force the old outcome.

## Exact official URL checks

All 14 checked official URLs were below the URL review threshold in the round 2
candidate. Ten are seen training seeds; four remain excluded owner domains
(`google.com`, `microsoft.com`, `apple.com`, `wikipedia.org`). These checks do not
label all paths, posts, redirects or downloads on a domain as safe.

| Service URL | Active score | Candidate score |
|---|---:|---:|
| YouTube homepage | 39 | 0 |
| Facebook homepage | 25 | 1 |
| Zalo PC | 75 | 23 |
| Shopee homepage | 48 | 15 |
| Tiki homepage | 47 | 8 |
| Vietcombank homepage | 78 | 20 |
| BIDV homepage | 9 | 18 |
| MoMo homepage | 64 | 8 |
| DVC procedure-category URL | 1 | 0 |
| VnExpress homepage | 22 | 5 |

Scores are rounded model alert scores, not calibrated fraud probabilities or
guarantees. A score rounded to zero does not establish that a URL is risk-free.

## Evidence

- Candidate bundle SHA-256:
  `4eed2fb808c06fcdeb7381d0f59996348552e9d058707943ac86b48fa745a268`.
- Active parent bundle SHA-256:
  `6a0fd38b35570bff4b0ae56dd52a07747a6670d3dc2eceda304e1f10898314d0`.
- [Machine-readable results](url-training-round2-2026-10-27.json) include selection,
  calibration, historical evaluation, exact URL scores and serving regressions.
- Frozen local artifacts include exact fit rows, fold membership, each
  configuration's out-of-fold predictions, the selection freeze, final weights,
  calibration predictions and reports. Original data and the prior run remain
  unchanged.
- 123 Python tests and 47 JavaScript unit tests passed, as did lint, production
  build and TypeScript checks. Five new Python tests check sparse learning,
  training-role/group isolation, strict selection gates, evidence tampering
  and activation rejection. An inverted selection gate was caught in a temporary
  source copy; frozen training code was preserved.
- Three inference-lifecycle tests and all 17 API integration tests passed using
  the unchanged active serving model. The round 2 candidate was checked
  separately and failed the two existing `qi.lv/F0i` behaviors described above;
  the passing active-model tests do not certify the candidate for serving.
