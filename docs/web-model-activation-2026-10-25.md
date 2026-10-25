# Web activation, 2026-10-25

The user authorized switching the web to the fitted processed models. The default
Python entry point is now `ml_model/predict_processed.py`, run ID
`processed-20261025`. It loads the fit from
`ml_model/data/prepared/processed_agent_fit_2026-10-25/trained_agent_models.pkl`
and verifies SHA-256
`a69b0afc4b2f3b6f997c86a8fd18488282ccb391a5040e8616129062f35099d2`
before unpickling. Frozen helper checksums, estimator runtime and thresholds
are checked too. Neither the old bundle nor frozen experiment outputs changed.

This fit uses 3,857 SMS and 9,123 URLs. SMS labels have mixed provenance, including
497 source-human training rows; this is not an entirely expert-verified corpus.
The original `production_compatible: false` flag describes incompatibility with
the old inference contract. The new adapter explicitly supports the processed
contract; this flag is not rewritten to imply validated production accuracy.

SMS inference preserves the exact frozen `round2_experiment.text_input`
preprocessing, including URLs. URL inference uses `external_training.url_input`,
including HTTP/HTTPS collapsing. SMS with links uses the SMS score for its
decision, while reporting URL scores separately. URL-only inputs use the URL
model. There is no newly trained paired fusion, so the old fusion is not reused.
The URL target includes source-reported abuse, beyond credential phishing.

The learned binary labels use the frozen thresholds: SMS 0.65, URL 0.22. The UI
shows this decision separately from the existing alert bands (<30, 30–79, >=80).
Scores are rounded model outputs, not calibrated probabilities. Compare test
labels against `model_prediction_label`, computed from the unrounded output.
Missing/corrupt/incompatible artifacts return HTTP 503; there is no silent
fallback to the old model or invented safe label.

## Real held-out test

Open `http://127.0.0.1:3000`. Downloads:

- `/test-data/sms-test-39.txt`: messages to copy into the UI.
- `/test-data/sms-test-39.csv`: messages, IDs, binary labels and provenance.
- `/test-data/sms-test-39.json`: the same records as JSON.
- `/test-data/sms-test-39-answers.csv`: frozen selected-model predictions and errors.

These are the 39 actual English test messages reserved by the SmishX experiment,
not the earlier 12 authored examples. None was used to fit this model or choose
its threshold. Source: [SmishX](https://github.com/yizhu-joy/SmishX), commit
`116a8c827741e0572563f678d25ed04306b1e3ff`, `data/dataset.csv`, SHA-256
`8d65e373b17477c34e8f1c619e6f59d249e8fca21276cabdd03a55d11a469285`.
The authors report manual labeling by two researchers with disagreement
resolution; this project has not independently verified expert qualifications.
Source `legitimate`/`spam` map to 0 and eligible `smishing` to 1. Scope conflicts
and ambiguous language records were quarantined before selection.

The test has 25 positive and 14 negative messages in 11 similarity groups.
**All 25 positives are in one group.** The saved result is TP24/FN1/FP1/TN13;
this narrow test is not evidence of robust accuracy across independent scam
campaigns. Do not train on these files or tune after reading the answer key.
Vietnamese historic tests remain separate diagnostics. See
`smishx-training-2026-10-25.md` for all results, including regressions.

API parity checks compare deployed scores to frozen outputs; they are deployment
verification, not a new model-selection or unbiased evaluation experiment.
Activation evidence is stored under
`ml_model/data/prepared/web_activation_2026-10-25/`.

Verification completed: 46 Python tests, 14 assessment tests and 10 live API
integration tests passed, including missing-model HTTP 503. Inverting the new
binary threshold made the adapter tests fail; the original source was restored
and its five tests passed again. Lint and the full Next.js build passed. A real
Edge browser submitted a message and displayed this run ID, threshold 0.65 and
3,857 training SMS without a runtime exception. All 39 API scores and labels
matched the frozen predictions exactly; the downloaded CSV matched every held-out
record. The initial sandboxed build could not create standalone directories;
the build succeeded with the required filesystem access, without code changes.

## Local start and rollback

Use `scripts/start-local.ps1` for development. For a built app, use
`npm.cmd run build` followed by `npm.cmd run start -- --hostname 127.0.0.1`.
Python is resolved from `.venv`; no external AI API is required. Submitted URLs
are not fetched. To explicitly restore the older bundle, set
`$env:SCAMGUARD_INFERENCE_MODE='legacy'` before restarting. Clear that environment
variable to use the processed model again. An invalid `SCAMGUARD_MODEL_PATH`
deliberately makes the model unavailable and must not silently trigger rollback.
