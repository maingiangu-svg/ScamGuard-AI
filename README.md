# ScamGuard AI

Local machine learning screening for suspicious messages and URLs.

The default web model is `hybrid-isolated-20261026-icann`: word/character TF-IDF + Logistic
Regression for SMS, and lexical/character features + HistGradientBoosting for
URLs. SMS decisions use the text model; embedded URLs are scored separately.
Both heads were refitted after quarantining known label conflicts and isolating
connected domains and message groups. No fusion model was trained for this fit.
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
The default hybrid bundle and its checksum manifest are versioned in
`ml_model/models/`; raw training datasets are not downloaded by git pull.
`train.py` trains the historical fusion pipeline. The current repair and fitting
commands are documented in [data repair and evidence](docs/data-repair-2026-10-26.md).

## Evidence and limits

[Current repair report](docs/data-repair-2026-10-26.json) records 3,800 training
SMS and 32,777 training URLs. Labels retain source human, inherited source,
AI review and user-decision provenance; they are not all expert verified.
Known reference conflicts are quarantined, without inventing corrected labels.
The SMS threshold is 0.65; the URL threshold is 0.50. These binary decisions are
shown separately from the 30/80 alert policy. Scores are not calibrated.

The repaired historical test contains 38 SmishX messages and 9,935 source-labeled
URLs. The 24 positive SMS share one source similarity group. Both ICANN owner
domains and PSL domains including private suffixes are disjoint across retained
train/validation/test, as are the checked text/group proxies. Campaign IDs are
missing, so campaign independence remains unproven. These are reused diagnostics,
not a new untouched benchmark. Vietnamese results remain diagnostics.
The older fusion bundle and its historical reports are preserved; set
`SCAMGUARD_INFERENCE_MODE=legacy` before starting to explicitly select it.
Historical modes do not inherit the repaired bundle's split-isolation evidence.

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
