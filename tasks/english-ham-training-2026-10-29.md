# Supervised SMS fitting with isolated English ham additions

- [x] Verify the immutable 62-row source-ham package, prior 4,124 training rows,
  positive expansion, parent serving bundle and historical diagnostics.
- [x] Recompute training groups with previous groups, all source variant domain
  owners, templates and >=0.80 character similarity. Freeze 4,186 rows, code,
  folds and source hashes before any fitting or historical scoring.
- [x] Fix C=16 and NCSU weak-source weight=0.5, selected in the previous
  training-only experiment. Do not tune again. Vietnamese weight=3, human-source
  weight=2, other labels including UCI source ham weight=1. Thresholds unchanged.
- [x] Fit three outer grouped folds with three inner grouped sigmoid calibration
  folds, then fit the final SMS raw/calibrated models on all labeled train rows.
  Keep the URL model state exactly unchanged and save an isolated candidate.
- [x] Evaluate historical diagnostics once, bind the report, preserve all old
  tests and new unlabeled pools; no further fitting after historical results.
- [x] Run regression tests, verify candidate and parent hashes, publish metrics
  and model disposition. Training alone does not approve deployment.

OOF estimates are source-label estimates, not expert-verified fraud accuracy.
Historical cohorts are reused diagnostics, not a fresh independent benchmark.
Release requires calibration plus per-language nonregression at all existing
raw diagnostic thresholds, then separate serving validation. Default candidate
release approval is false; do not bypass runtime release guards.

Completed: 4,186 rows, 3,544 groups. English grouped OOF precision 96.41%,
recall 91.68%, F1 93.99%; all 62 new source negatives classified negative at
0.65. Calibration passed. Historical gates at 0.30/0.65/0.80 failed; candidate
is saved and not approved for release. All 172 Python tests and artifact checks
passed. See docs/english-ham-training-2026-10-29.md and .json.
