# SMS release without additional false alarms — 2026-10-29

**Activated locally:** `sms-confirmation-english-20261029`.
Every existing raw-threshold, grouped-CV and full-application nonregression
check passed. False-positive and false-negative counts on the evaluated
cohorts are **unchanged**. The previous model is archived for recovery.
There was no remote deployment.

## Result and scope

The supervised workflow uses 4,186 admitted labeled records: 4,053 English and
133 Vietnamese, in 3,544 connected groups. The original 3,786-row SMS model is
the fixed anchor. The new confirmation classifier trains on 3,848 rows,
including the 62 added UCI legitimate messages. Selection assigns the 338 NCSU
feed/AI-screened positives zero confirmation-loss weight; their labels remain
in language fitting, calibration and evaluation. No labels were changed or
promoted to expert verification, and no heldout/quarantined row was fitted.

The new SMS score is the minimum of the original score and a supervised
confirmation score. Confirmation applies only when a binary language classifier
trained on permitted language metadata outputs an English score >=0.99;
uncertain language retains the original score. This language score is not an
expert language judgment. The raw SMS score cannot exceed the pinned anchor
for the same input. SMS/URL thresholds, rounding, URL-only routing and independent
URL review remain unchanged. All learned URL estimator state is preserved.

This cap also preserves the anchor's detection ceiling: it cannot add positive
decisions at a fixed raw threshold. The measured outcome is stable alert/miss
counts plus improved probability calibration, rather than a demonstrated
reduction in false alarms or increased detection of novel scams.

## Training-only selection

Three development searches were rejected before historical scoring: the first
had no eligible final configuration, and the next two introduced Vietnamese
outer-fold misses at raw 0.30. Their code snapshots, tables and rejection
records remain in separate prepared directories. The final search added the
English language gate and retained every FP/FN acceptance criterion.

The final grid has 108 logical configurations: C={0.05,1,4}, weak-source
weight={0,0.1,0.5}, positive-loss multiplier={4,16,64}, and confirmation-only
logit offset={0.5,1,2,4}. The offset is an intercept adjustment selected on train
OOF predictions; application thresholds never change. Eligible configurations
must preserve each language's FP/FN at raw 0.30/0.65/0.80 and retain at least
0.05 confirmation margin on existing positive decisions. Selection then
minimizes FP, minimizes FN and prefers the largest retained-positive margin.

Three outer group folds estimate the full selection/calibration process; each
uses three inner group folds. The anchor is refitted only on its original
training identities inside every fold. The language model is also fitted
inside each training fold. A sigmoid learns from inner OOF logit scores of the
combined model. Classifier-fitting and calibration predictions are separated,
following the [scikit-learn calibration guidance](https://scikit-learn.org/stable/modules/calibration.html).

Every outer fold and the final selection chose C=0.05, weak-source weight=0,
positive-loss multiplier=4, confirmation offset=0.5. English grouped OOF at 0.65
has precision 98.03%, recall 63.75% and F1 77.26%, equal to its paired anchor.
At 0.30, English recall is 96.80%. Vietnamese and English FP/FN are unchanged
at all three thresholds. These are mixed-source-label estimates after an
adaptive development process, not a fresh independent accuracy benchmark.

Probability calibration passed: Brier **0.025427 → 0.020858**, log-loss
**0.111247 → 0.069955**, ten-bin ECE **0.057337 → 0.009753**. The estimate targets
the recorded label mixture; it is separate from the capped raw alert score.
On fitting data, the English gate activates for 246 records and lowers one raw
score. Those are in-sample activity counts, not an accuracy result.

## Frozen historical checks

Only the final model was evaluated on historical cohorts during this task.
These cohorts were used by earlier experiments and remain reused regression
diagnostics. The new 95/96 unlabeled validation/test candidates and 3,003
individually unlabeled campaign URLs remain unscored.

Raw SMS classification at 0.65:

| Cohort | Rows | Parent FP / FN | Released FP / FN |
| --- | ---: | ---: | ---: |
| English validation | 904 | 4 / 3 | **4 / 3** |
| Vietnamese validation | 41 | 2 / 1 | **2 / 1** |
| English historical test | 38 | 3 / 0 | **3 / 0** |

All raw 0.30/0.65/0.80 gates passed. Running actual inference on all **983**
historical inputs also verified rounded scores and independent URL review:

| Cohort | REVIEW-or-BLOCK FP / FN, old = new | BLOCK FP / FN, old = new |
| --- | ---: | ---: |
| English validation | 45 / 0 | 3 / 5 |
| Vietnamese validation | 13 / 0 | 1 / 6 |
| English historical test | 10 / 0 | 1 / 7 |

The application review counts include the unchanged independent URL branch;
they differ from SMS-only raw-threshold diagnostics. No score-bound violation
was observed. The composite SMS head has no single linear top-token attribution;
model identity, raw score, calibrated source estimate and provenance remain
available.

## Activation and verification

All **181 Python tests**, **68 JavaScript tests**, lint and production build
passed. There were **17 isolated HTTP checks** covering the parent, approved
candidate and rejection of unapproved metadata; **six additional HTTP checks**
confirmed the activated model in the synchronized standalone package.
The active-model test now verifies the new release and retains the original
URL/calibration lineage assertions, plus all four release gates and inherited
URL source bindings. No quality assertion was suppressed.

Active bundle SHA-256:
`1688e9e0960fb9320cac0e4ff2f4e98b705cb5f8db11a8a47cbcdcedda78c8f1`.
Parent bundle SHA-256:
`26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`.

Local package: `ml_model/data/prepared/conservative_sms_english_gate_2026-10-29/`.
It contains frozen code, folds, OOF scores, selections, calibration and historical
reports, `release_manifest.json`, `release_decision.json`, runtime checks, and
the exact `parent_bundle.pkl` / `parent_manifest.json` backups. Current serving
files are `ml_model/models/hybrid_bundle.pkl` and `hybrid_manifest.json`.

```powershell
.\.venv\Scripts\python.exe ml_model/data/prepared/conservative_sms_english_gate_2026-10-29/release_artifact.py verify
```

The release verifier checks every protected input and resolves only the two
former live-model paths to their exact parent archives. Historical experiment
verifiers remain bound to the earlier live pointer; their data/code snapshots
were preserved. The approved manifest binds release evidence and serving-code
hashes. All release flags are true, including full-application nonregression;
unapproved metadata continues to return 503 without a verdict.
