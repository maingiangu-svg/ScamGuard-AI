# ScamGuard AI

Local machine learning screening for suspicious messages and URLs.

The default web model is `processed-20261025`: word/character TF-IDF + Logistic
Regression for SMS, and lexical/character features + HistGradientBoosting for
URLs. SMS decisions use the text model; embedded URLs are scored separately.
No fusion model was trained for this fit.
The app makes no external AI calls and does not fetch submitted URLs.

The score is a model estimate, not proof of fraud or a calibrated probability.
Policy: <30 low risk, 30–79 review, >=80 high risk. Domain annotations never
bypass the classifier or modify its score. Missing/incompatible models return
HTTP 503 rather than an invented safe verdict.

## Setup

See [local training instructions](ml_model/README.md). From this directory:

    npm.cmd ci --ignore-scripts
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r ml_model\requirements.txt
    .\.venv\Scripts\python.exe ml_model\download_data.py

Place phishing_site_urls.csv in ml_model/data, then:

    .\scripts\start-local.ps1

Open http://localhost:3000. No external model API key is needed.
Pickled model files and raw datasets are not downloaded by git pull.
This checkout uses the fitted bundle in
`ml_model/data/prepared/processed_agent_fit_2026-10-25/`. `train.py` trains the
older fusion pipeline, not this selected model. See
[activation and real test data](docs/web-model-activation-2026-10-25.md).

## Evidence and limits

[Current fit report](ml_model/data/prepared/processed_agent_fit_2026-10-25/training_report.json)
records the 3,857 training SMS and 9,123 training URLs. Labels have mixed
provenance: source human annotations, source labels and reviewed AI labels;
they are not all expert-verified. Keyword-derived smishing labels were excluded.
The SMS threshold is 0.65; the URL threshold is 0.22. These binary decisions are
shown separately from the 30/80 alert policy. Scores are not calibrated.

The downloadable English test contains 39 held-out SmishX messages. Its 25
positive messages share one similarity group, so it cannot establish
generalization to new scam campaigns. Vietnamese results remain diagnostics.
The older fusion bundle and its historical reports are preserved; set
`SCAMGUARD_INFERENCE_MODE=legacy` before starting to explicitly select it.

Image analysis and roleplay are unavailable because no local OCR/dialogue model
has been trained. Sample scenarios are clearly labelled educational illustrations.
They are not live model evaluations. The extension warns only at the >=80 policy.

## Checks

    .\.venv\Scripts\python.exe -m unittest discover -s ml_model -v
    node --test scripts/analysis-assessment.test.mjs
    node --test scripts/analyze.integration.test.mjs
    npm.cmd run lint
    npm.cmd run build

Integration tests require the local app. Python startup is included in request
latency; the application makes no sub-4ms end-to-end performance claim.
