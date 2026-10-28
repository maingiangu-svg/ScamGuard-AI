# Supervised SMS training with English ham additions — 2026-10-29

Completed run **`english-ham-20261029`** on **4,186 labeled training records**:
4,053 English and 133 Vietnamese, including the 62 newly admitted UCI source
negatives. Recomputed grouping produced 3,544 connected fitting groups.
The candidate is saved and **not activated**: historical nonregression failed.
The serving model and URL estimator remain unchanged.

## Method

Word/character TF-IDF logistic regression uses fixed `C=16` and NCSU weak-source
weight `0.5`, selected by the earlier training-only experiment. There is no new
configuration or threshold search. Weights are Vietnamese `3`, source-human
`2`, NCSU feed/AI-screened `0.5`, remaining labels including UCI ham `1`.
Counts by weight are 133 / 484 / 338 / 3,231.

Labels total 3,663 negative and 523 positive. Provenance is retained: 2,966
upstream ham/non-smishing-spam, 483 published two-researcher manual relabels,
334 AI semantic reviews, 338 NCSU feed/AI-screened positives, 62 UCI source-ham
proxies and three user scope/label decisions. No new expert labels were created.

Grouping preserves previous groups, source addition groups, templates, >=0.80
character similarity and public/private domain owners from all merged source
variants. Rows, fold assignments, code and hashes were frozen before fitting.
Three outer group folds estimate scores; each fit uses three inner group folds
for sigmoid calibration. The final SMS model is fitted on all 4,186 rows.
Thresholds remain SMS 0.65 and URL 0.5.

The fixed configuration was previously selected on overlapping training data.
These are **grouped OOF estimates with nested calibration under a reused fixed
configuration**, not an independent estimate of the entire selection process.
Different data/folds prevent attributing differences from the earlier run to
the 62 additions alone.

## Training-fold results

Raw SMS classification at 0.65 against recorded source/mixed labels:

| Cohort | Rows | Precision | Recall | F1 | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| English | 4,053 | 96.41% | 91.68% | 93.99% | 16 | 39 |
| Vietnamese | 133 | 80.36% | 83.33% | 81.82% | 11 | 9 |
| All | 4,186 | 94.62% | 90.82% | 92.68% | 27 | 48 |

All 62 new source-negative records were negative out of fold at 0.65 (0 FP).
These mostly personal conversations do not establish reliability on modern
banking, delivery, OTP or promotional messages. No heldout or unresolved record
was fitted, and no score is represented as expert-verified fraud accuracy.

Calibration passed: Brier 0.012899 → 0.012610; log-loss 0.048358 → 0.044054;
ten-bin ECE 0.012710 → 0.005729. These estimate the recorded label mixture.
Fitting after preparation took 15.639 seconds on this machine.

## Historical diagnostics and disposition

The frozen model was scored once on existing historical exports. No fitting,
label or threshold change followed those results.

| Cohort at 0.65 | Parent FP / FN | Candidate FP / FN |
| --- | ---: | ---: |
| English validation, 904 rows | 4 / 3 | 11 / 2 |
| Vietnamese validation, 41 rows | 2 / 1 | 2 / 2 |
| English test, 38 rows | 3 / 0 | 5 / 0 |

Nonregression fails at all existing raw diagnostic thresholds: 0.30, 0.65 and
0.80. At 0.30, English validation FP decreases 22 → 14, but Vietnamese validation
FN increases 0 → 1. These are raw SMS checks, not rounded full-application
actions or independent URL-review decisions. Historical cohorts are small,
reused diagnostics with limited group diversity, not a fresh benchmark.

The 95/96 new unlabeled validation/test candidates and the 3,003 individually
unlabeled campaign URLs remain unscored. Candidate flags are explicitly
`release_approved=false`, `historical_nonregression_pass=false` and
`all_policy_nonregression_pass=false`. Runtime inference rejects it without
producing a risk score. Current serving weights are retained.

## Artifacts and checks

Package: `ml_model/data/prepared/english_ham_training_2026-10-29/`.
Includes `candidate_bundle.pkl`, `candidate_manifest.json`, `protocol.json`,
fitting rows, folds, OOF predictions, `training_report.json`, `evaluation.json`,
`release_decision.json` and `verification_report.json`.

Candidate SHA-256:
`a5603e091ec4095f55b3b2ee37ab10f01dc0f45f028e014c9b4cd5edf822b113`.
Active bundle remains:
`26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`.

All **172 Python tests pass**. Verification checks labels, provenance, weights
and membership; zero outer-fold group overlap; valid inner folds; unchanged
serialized URL estimator state; changed SMS weights; rejection of the failed
candidate; and readiness of active SMS and URL inference. All protected hashes
match. No JavaScript/build changes were required for this offline training.

```powershell
.\.venv\Scripts\python.exe ml_model/english_ham_training.py verify
.\.venv\Scripts\python.exe ml_model/data/prepared/english_ham_training_2026-10-29/verify_artifact.py
```

Fitting refuses existing output directories. Historical evaluation creates its
marker exclusively and refuses repeats. Do not use these reused tests to tune
a follow-up configuration or deploy the rejected artifact. Contemporary
source-labeled negatives and an independently labeled benchmark remain gaps.
