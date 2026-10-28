# Train a conservative SMS confirmation model

User asks to train until false alarms do not increase. Use a supervised SMS
confirmation head with score min(existing SMS raw score, confirmation score).
At unchanged thresholds and routing, its score cannot create a new raw alert;
the unchanged URL head retains its independent review behavior. This does not
guarantee unchanged recall, so preserve the existing false-negative gates too.

- [x] Freeze 4,186 admitted labeled development rows, original 3,786 anchor-fit
  identities, source hashes, three grouped folds, code and finite search grid.
- [x] Compare confirmation C in {1,4}, NCSU source weight in {0,0.1,0.5},
  positive loss multiplier in {1,4,16,64}. Zero source weight excludes those
  rows from confirmation loss; retain their labels for calibration/evaluation.
  Never relabel them. All other provenance
  weights and SMS/URL thresholds stay fixed. Keep new legitimate data.
  Follow-up after the training-only first search failed eligibility: also
  select confirmation-only logit offsets {0,0.5,1,2,4}. This requires stronger
  negative evidence before vetoing an anchor alert; the application thresholds
  and raw score cap are unchanged. Reuse fitted features for offset trials.
  Second search had two Vietnamese outer-fold misses at 0.30 and was rejected
  before historical scoring. Final follow-up: require at least 0.05 confirmation
  margin on retained training-CV positives, C={0.05,1,4}, source={0,0.1,0.5},
  positive multiplier={4,16,64}, offset={0.5,1,2,4}; 108 logical trials with
  shared fitted features. Preserve every earlier rejected search and criterion.
  Third search still had one Vietnamese outer-fold miss at 0.30; no historical
  scoring was opened. Restrict confirmation to English gate probability >=0.99.
  Train that language gate on permitted training-language metadata inside each
  group fold; do not infer expert provenance. Uncertain language uses the anchor
  unchanged. Keep the same safety margin, grid and all FP/FN release criteria.
- [x] Use paired group CV with an anchor refitted only on original anchor
  fitting rows in each fold. Require no extra FP or FN per language at raw
  0.30/0.65/0.80. Prefer lowest total FP, then lowest total FN, then greatest
  margin above every retained positive threshold, deterministic grid order.
- [x] Estimate the entire selection/calibration process in three outer group
  folds. Fit a sigmoid on inner OOF logit scores, never in-sample scores.
  Freeze the final candidate after full training-only selection.
- [x] Evaluate the final frozen candidate once on reused historical cohorts.
  Never select a configuration or threshold from historical test predictions.
  Retain both FP and FN nonregression; do not lower release criteria.
- [x] Verify real serving action monotonicity, unchanged URL state, calibration,
  hashes, source labels and group splits; run regression tests and publish.

No classifier can promise zero false alarms on unseen real-world inputs.
The score bound guarantees no *additional* alerts relative to this pinned
parent at the same thresholds; measured recall remains dataset-dependent.
No fabricated expert labels, synthetic benchmark, raw URL verdicts or training
on heldout/quarantined cases. Preserve all previous experiments and active
artifacts until every required release check passes.

Completed: `sms-confirmation-english-20261029` is activated locally after all
grouped, calibration, raw-threshold and 983 full-action checks passed. Historical
FP/FN counts are unchanged at all existing raw and real application policies.
Three preceding development searches were rejected before historical scoring.
All 181 Python, 68 JavaScript and 23 HTTP checks pass, with lint/build. Parent
bytes and earlier snapshots are preserved; the released verifier resolves the
former parent pointer to those exact archives. No remote deployment.
See docs/conservative-sms-training-2026-10-29.md and .json.
