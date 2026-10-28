# Reduce English SMS false alarms through training-only selection

User asks to continue improving the project after the first SMS candidate
failed historical nonregression. Keep every earlier experiment frozen.

- [x] Pin the 4,124 admitted training rows and current serving parent. Compare
  C in {0.25, 1, 4, 16} and new weak-source weight in {1, 0.5}; keep features,
  Vietnamese/source-human weights, class balancing and thresholds unchanged.
- [x] Implement group-based selection with tests: among configurations whose
  English and Vietnamese TP do not decrease and FP do not increase versus
  C=1/weak-weight=1 on the same inner folds, minimize total FP, maximize TP,
  then minimize review-policy FP. Resolve ties by smaller C, then smaller
  weak-source weight. The baseline is always feasible.
- [x] Estimate the entire selection/calibration procedure using three outer
  group folds. Select the final configuration using three-fold CV on all train
  rows, then fit final sigmoid calibration and raw estimator. Freeze weights
  and selected configuration before inspecting historical diagnostic results.
- [x] Check historical nonregression once with the existing criteria; preserve
  the 95/96 unlabeled heldout candidates and blocked URL pool without scoring.
- [x] Verify model loading, unchanged URL state and current regression checks;
  run full Python checks and publish artifacts, results and disposition.

No score/threshold/label change is chosen from historical tests. Calibration
must not worsen outer-fold Brier/log-loss. Activation requires all previous
per-cohort nonregression and serving gates; failed gates keep active weights.
No remote deployment. Nested OOF is a procedure estimate, final training-CV
scores are selection estimates, and reused historical tests are diagnostics.

- [x] Harden serving against explicitly failed/nonboolean release decisions;
  synchronize health gate checks and invalidate cached hash on identity change.
- [x] Verify structured NumPy padding does not cause a false changed-model
  result; preserve exact comparisons of learned values and RNG state.

Completed: nested selection chose C=16/new weak-source weight=0.5. English
nested OOF FP/FN improved 18/40 to 14/33; historical gates still failed, so
active weights are unchanged. Runtime release checks and health are now
enforced. All 166 Python, 68 JavaScript and 10 HTTP checks pass, with lint and
production build. Evidence: docs/english-sms-selection-2026-10-28.md and .json.
