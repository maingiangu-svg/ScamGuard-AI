# ScamGuard AI

Local machine learning screening for suspicious messages and URLs.

The default web model is `group-calibrated-20261026`: word/character TF-IDF + Logistic
Regression for SMS, and lexical/character features + HistGradientBoosting for
URLs. SMS decisions use the text model; embedded URLs are scored separately.
Both heads were refitted after quarantining unresolved review groups and isolating
connected domains and message groups. Train-only nested group folds fit separate
sigmoid estimates for source labels. No fusion model was trained for this fit.
The app makes no external AI calls and does not fetch submitted URLs.

The 0–100 alert score is not proof of fraud or a calibrated probability.
A separate calibrated estimate is conditional on the source labels; it is not
an expert-verified real-world probability that a message or website is fraudulent.
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

[Current completion report](docs/completion-results-2026-10-26.md) records 3,786 training
SMS and 31,299 training URLs, after excluding groups containing 807 unresolved
review candidates. The [parent repair report](docs/data-repair-2026-10-26.json)
records the prior 3,800/32,777 fit. Labels retain source human, inherited source,
AI review and user-decision provenance; they are not all expert verified.
Known reference conflicts are quarantined, without inventing corrected labels.
The SMS threshold is 0.65; the URL threshold is 0.50. These binary decisions are
shown separately from the 30/80 alert policy and the new source-label estimate.
Calibration improved train-only out-of-group Brier/log loss for both heads;
on the reused historical URL test, Brier slightly worsened (0.05906 to 0.05972).
No new independent Vietnamese benchmark or expert labels were created.

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
They are not live model evaluations. Extension 1.1.2 displays a score badge after
successful checks at any score; its warning banner still uses the >=80 policy.

## Checks

    .\.venv\Scripts\python.exe -m unittest discover -s ml_model -v
    npm.cmd test
    npm.cmd run test:inference
    npm.cmd run test:api
    npm.cmd run lint
    npm.cmd run build

Integration tests require the local app. Python startup is included in request
latency; the application makes no sub-4ms end-to-end performance claim.

See the [project audit and remaining limitations](docs/project-audit-2026-10-26.md)
for Trivy, Lighthouse, ASVS review, 140 passing tests and train-only cleanlab
results from the initial audit. The follow-up [five-step readiness report](docs/project-readiness-2026-10-26.md)
records the security, CI, expert-review preparation and browser/PDF work, current
verification results, and remaining environment checks.

The [extension instructions](extension/README.md) explain the user's choice of
manual checks (default) or optional automatic screening. The [expert-review
protocol](docs/ml-expert-review-protocol.md) keeps the 811 train-review candidates
separate from a future independent Vietnamese benchmark.

## Production configuration

`SCAMGUARD_ALLOWED_ORIGINS` is a comma-separated exact browser-origin allowlist.
The default includes localhost:3000, the current Cloud Run URL and the unpacked
extension ID. Set it explicitly for a new domain or extension ID. API responses
are not cached; root HTML uses a fresh CSP script nonce and private/no-store.

`SCAMGUARD_TRUSTED_PROXY_HOPS=0` ignores forwarded client IP headers by default.
Only configure trusted hops after verifying the proxy topology and header
rewriting. `RATE_LIMIT_TOTAL_PER_MINUTE` (default 60) limits both inference
endpoints together per process; `RATE_LIMIT_PER_MINUTE` (default 10) also limits
recognized clients. This is an in-memory safeguard: replicas and restarts do
not share a durable quota. A public deployment needing a global quota needs
an edge/distributed limiter with an explicit operating budget.

`GET /api/health` checks the current hybrid artifact against its checksum
manifest. Real inference is verified separately by integration/container smoke
tests. The health endpoint alone does not prove prediction quality or Python
runtime compatibility.

The pinned GitHub Actions workflow runs lint, tests, standalone build, API,
browser, installed-extension, dependency audits and Docker smoke checks on Linux.
For a local full integration run after `npm run build`, install the locked tools
in `tools/audit` (or set `AUDIT_NODE_TOOLS`), install Playwright Chromium, and run
`node scripts/ci-integration.mjs` with `TEST_EXTENSION=1`. It owns test servers on
ports 3000 and 3101–3103; these ports must be free.

After a successful image smoke check, `scripts/deploy-cloud-run.sh` accepts
`GCP_PROJECT_ID`, optional `GCP_REGION` and `GCP_SERVICE`. Its HTTP startup and
liveness probes follow [Cloud Run's documented probe configuration](https://docs.cloud.google.com/run/docs/configuring/healthchecks).
Review the project/service before running it: this command publishes an
unauthenticated service and may incur cloud costs. Preparing this script has
not deployed the workspace changes.
