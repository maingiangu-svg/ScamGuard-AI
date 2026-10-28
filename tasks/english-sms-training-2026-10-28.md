# Supervised English SMS training — 2026-10-28

User requests training after the English data expansion. Train a new SMS head
using the exact current 3,786 fit rows plus the 338 admitted additions (4,124
total). Retain all 133 Vietnamese fit rows and the complete frozen URL head.
Preserve labels and their weak/source/manual/user provenance.

- [x] Bind source and parent hashes; reject unlabelled, heldout or quarantined
  rows; recompute connected training groups before cross-validation.
- [x] Fit the same SMS estimator and sample-weight policy; keep threshold .65.
  Use three outer and three inner group folds for source-label calibration.
  Do not tune hyperparameters or thresholds using historical tests.
- [x] Freeze and save a compatible candidate bundle/manifest and fitted rows.
  Verify the URL head is preserved and inference can consume the candidate.
- [x] Evaluate historical SMS validation/test once as reused diagnostics,
  including English/Vietnamese, false alarms and missed positives. Do not
  score or fit the new unlabeled test/validation or URL-review pools.
- [x] Run focused/full Python checks; publish model paths, measured results
  and limitations. Keep the active model unless a separately justified local
  activation meets the existing serving checks; no remote deployment.

Calibration passes only if outer-fold source-label Brier and log-loss do not
worsen. Historical nonregression checks require no additional FP or FN on each
English/Vietnamese validation cohort and the 38-case English test. These are
diagnostic gates, not a new independent benchmark. Failed gates do not authorize
retuning on the observed test or relabeling uncertain records.

Completed: candidate trained on 4,124 SMS / 3,530 groups, including 338 added
English examples. English OOF precision 95.97%, recall 91.47%, F1 93.67%.
Calibration passed; historical nonregression failed (English validation FP
4 to 8, historical test FP 3 to 5), so no activation. URL learned parameter
values and active artifacts are unchanged. All 157 Python tests and five local
inference smoke checks passed. Evidence: docs/english-sms-training-2026-10-28.md.
