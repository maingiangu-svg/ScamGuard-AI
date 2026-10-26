# URL alert policy correction — 2026-10-26

The reported `https://www.facebook.com/` returns raw score
`0.3478950622608507`, rounded to 35/100, from the active supervised URL head.
Its binary label is 0 at the existing 0.50 threshold. Python, the assessment
adapter and the web verdict nevertheless applied the SMS review band starting
at 30 points. This produced a suspicious-content alert alongside a negative URL
classification. No score arithmetic error was found.

## Correction

- Hybrid URL-only review now uses the URL head's raw detection threshold.
  Scores and model weights are preserved. Raw 0.4999 remains below threshold even
  though its displayed score rounds to 50/100.
- Assessments consume the inference action. The API derives threat level and
  `scam_detected` from that assessment, and the UI uses those API conclusions.
  The URL branch bars compare raw scores, avoiding a second rounding error.
- Below-threshold URLs are described as unverified, without invented red flags.
  The UI states that model scores are uncalibrated and are not fraud probabilities.
- SMS keeps its existing early-review band. Positive URLs still independently
  require review in mixed SMS/URL input. Existing high-risk alerts are preserved.

## Retrospective impact, not a new benchmark

Calculated from the existing frozen `url_test_predictions.jsonl` under
`ml_model/data/prepared/repaired_training_2026-10-26-icann/`.
The 9,935 rows contain 7,705 source-labeled good URLs and 2,230 source-labeled bad
URLs. Labels are inherited and **not independently expert verified**. These
holdouts have been used previously; this comparison does not establish external
validity and was not used to tune a new threshold.

| URL alert rule | TN | FP | FN | TP | False-positive rate | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Previous: rounded score >=30 | 7,241 | 464 | 364 | 1,866 | 6.02% | 83.68% |
| Corrected: raw score >=0.50 | 7,570 | 135 | 616 | 1,614 | 1.75% | 72.38% |

This removes 329 false alarms but also removes alerts for 252 source-labeled bad
URLs in the former early-review band. It is a policy consistency correction,
**not an improvement in model discrimination or a production safety claim**.
The inherited 0.50 URL threshold was not selected on a URL validation set.
Selecting a different sensitivity/false-alarm balance requires a separately
labeled validation set and independent evaluation, not tuning on these test rows
or on the reported Facebook example.

## Model sensitivity remains a limitation

The active estimator uses 13 numeric URL features plus character TF-IDF with
histogram gradient boosting. Scores are 35 for `https://www.facebook.com/`,
6 for `https://facebook.com/`, and 44 for `https://www.google.com/`.
All 32,777 accepted training URL strings have the `http` scheme; among them,
2,294/24,974 source-labeled good URLs and 880/7,803 source-labeled bad URLs have
a leading `www.` hostname. The available representation and training coverage
therefore deserve a separate robustness evaluation. These statistics alone do
not identify the contribution of each individual feature to the reported score.

Different hostnames need not serve the same content. Removing `www.`, forcing
brand scores down, or declaring official-looking URLs safe would conceal this
limitation. No URL rewriting, whitelist override, relabeling, model fitting,
calibration, or test-data reuse for training is part of this correction.

## Regression verification

Python tests cover raw URL thresholds, score preservation, mixed-input review,
high-risk URLs, and unavailable model behavior. Assessment/API tests cover the
reported Facebook/Google inputs and agreement between both endpoints.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s ml_model -p 'test_*.py'
node --experimental-strip-types --test scripts/analysis-assessment.test.mjs
# With the app running on localhost:3000:
node --test scripts/analyze.integration.test.mjs
npm.cmd run lint
npm.cmd run build
```
