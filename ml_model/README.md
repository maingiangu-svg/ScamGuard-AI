# Local training and inference

The web defaults to `predict_hybrid.py`: `url-ensemble-20261027`. The SMS head is
preserved (3,786 training messages, threshold 0.65). The URL head combines frozen
lexical/character models through a supervised residual gate: 71,309 raw-model
training URLs plus 3,000 separate calibration-fit URLs, with review threshold 0.50.
The checksum-pinned `models/hybrid_bundle.pkl` and `hybrid_manifest.json` ship
with the app. SMS stays the primary score when text is present; URL positives
independently require link review. Alert scores are not averaged or recalibrated.
The separate `calibrated_probability` estimates source label 1 using disjoint-owner
temperature calibration for URLs and the inherited grouped sigmoid SMS model;
it is not an expert-verified fraud probability. See
[current protocol, results and local activation](../docs/url-regression-repair-2026-10-27.md).
Missing or incompatible artifacts fail closed. See
`../docs/hybrid-model-integration-2026-10-25.md` for routing, provenance and limits.

`python ml_model/package_hybrid.py` is the historical packager for older heads;
it does not reproduce the current residual ensemble. Preserve the
manifest and bundle together. Set `SCAMGUARD_INFERENCE_MODE=legacy` to explicitly
use `predict.py`, or `processed` for the previous local processed adapter (its
research artifacts must exist locally). Unset the variable for hybrid mode.
`SCAMGUARD_MODEL_PATH` overrides the selected adapter's artifact path; a missing
or incompatible override causes HTTP 503 and never a silent fallback.

The older fusion pipeline is `train_meta_fusion.py`; `train.py` delegates to it.
Its bundle remains available through `SCAMGUARD_INFERENCE_MODE=legacy`.
Descriptions below of isolated experiments preserving the app refer to their
original execution, before the separately authorized web activation.

## Activated URL regression repair, 2026-10-27

`repair_url_ensemble.py` learned a global parent-confidence cutoff of 0.80 from
71,299 audited source-label OOF/unseen-owner score pairs, preserving ten accepted
official URL fitting seeds. `finalize_url_repair.py` recorded a temperature
calibration revision after sigmoid failed its validation log-loss gate. No serving
test URL or held-out official-domain label was used to learn the gate.

The final model scored 95.175% accuracy on 4,000 newly reserved URLs, restored
`qi.lv/F0i` to 94/BLOCK, preserved independent mixed-input URL review, cleared all
14 exact official URL checks and passed all 17 API checks in a production standalone
package. It was activated locally with a verified backup; no remote deployment
was performed. These are source-label results, not expert-verified safety guarantees.
Earlier unactivated studies below describe historical candidates, not the current
active version. Full evidence is in the linked current report above.

## Official service URL training, 2026-10-27

`official_domain_training.py` fitted an isolated URL candidate using the active
model's exact accepted fit rows plus 10 first-party URL seeds from
`data/official_domain_seeds.json`. Four proposed owner domains remain excluded
because they belong to historical test/quarantine groups. Labels retain AI
evidence-review provenance and are not expert-verified safety certificates.

The candidate passed train-only grouped source-label calibration but failed the
predeclared historical-test release gate: four more false alarms and thirteen
more missed bad URLs. **It was not activated; the default model is preserved.**
See [protocol, results and artifacts](../docs/official-domain-training-2026-10-27.md).
The completed run refuses refitting or repeated historical-test evaluation.

Round 2 (`url_model_selection.py`) compared three sparse supervised URL heads
using training-only owner-domain folds and selected C=1 without consulting the
historical tests. On the later single historical diagnostic, false alarms fell
from 160 to 94 and detected bad URLs increased from 1,624 to 1,758. However, the
existing `qi.lv/F0i` serving cases regressed from BLOCK/REVIEW to CLEAR, so this
candidate also remains **unactivated**. The active model is unchanged. See
[round 2 protocol, selection and regressions](../docs/url-training-round2-2026-10-27.md).

The subsequent `accuracy_target_training.py` experiment added 40,000 traceable
source-labeled URLs, fitting 71,309 URL rows total, and reserved 4,000 new
owner-disjoint URLs before model selection. Training-only grouped comparison
selected a 50,000-feature character LR C=4 model. Its one fresh evaluation achieved
**95.375% observed accuracy** (precision 95.91%, recall 89.92%); the owner-domain
bootstrap 95% interval is 94.71%–96.00%. These are source-label agreements, not
expert-verified population guarantees. The `qi.lv/F0i` serving regressions persist,
so the candidate remains **unactivated** and the default model is unchanged.
See [95% target protocol and complete evidence](../docs/accuracy95-training-2026-10-27.md).

## Repairing and reviewing existing data

Run `python ml_model/prepare_data.py` before reviewing the old datasets. This
does not retrain models or overwrite the source CSV files. It writes traceable
candidate datasets, quarantine queues, a 200-message stratified label-review
sample and `data/prepared/XEM_DU_LIEU_SAU_SUA.md` with actual before/after examples.
Generated files remain local and Git-ignored.

After the Vietnamese AI review exists, run the additional holdout audit:

    .\.venv\Scripts\python.exe ml_model\audit_vi_holdout.py

It separates unresolved labels and compares all reviewed messages with the old
SMS corpus, restored UCI messages and the provider's training split. It groups
masked templates, shared hostnames and character-ngram cosine matches >=0.90.
Outputs are in `data/prepared/review_2026-10-25/holdout_audit/`; start with
`KET_QUA_TACH_VA_NHOM.md`. Reference overlap blocks the entire connected group.
Groups containing unresolved or conflicting labels also remain outside the
reserved holdout candidates. Original labels, review decisions and model files
remain unchanged. Similarity flags do not automatically change any label.
This is a conservative lexical audit, not proof of campaign independence.
Provider test records remain reserved for evaluation: no training partition is
created, and AI review does not promote any row to expert-verified ground truth.

For the separately authorized exploratory AI-label training run:

    .\.venv\Scripts\python.exe ml_model\run_review_experiment.py --allow-ai-labels

The explicit flag permits reviewed AI labels only in this isolated experiment;
it does not change the original automatic-training restrictions. The script
requires the fixed training-review sample and authored notes in the review
directory's `experiment/` folder. It uses the existing text estimator, freezes a
more conservative 0.80 similarity screen before fitting, and writes the model,
per-message predictions, error cases and `KET_QUA_THU_NGHIEM.md` into that folder.
It never places provider test records in training or replaces deployed bundles.
Metrics are agreement with AI proposals, not verified real-world accuracy;
review the false alarms under the app's 30/80 policy as well as binary metrics.
The separate 30-message human annotation sample remains pending until actual
user/independent labels are recorded. Preserve `human_verification.json` answers
and never overwrite an existing annotation sample when rerunning preparation.

The next isolated study is `round2_experiment.py`, with separate `prepare`,
`select`, and `test` phases, each requiring `--allow-ai-labels`. Its authored
notes and outputs are under `data/prepared/review_2026-10-25/round2/`; start with
`KET_QUA_TOAN_BO.md`. The completed study reviewed 500 additional Vietnamese
messages, fitted 458 reviewed messages, selected on 66 validation messages and
evaluated 70 new test messages once. Model and threshold checksums are frozen
before test annotation and prediction; completed selection/test phases reject
reruns. The earlier 288-message diagnostic set is not used for this selection.

Audit grouping now recognizes explicit URLs wrapped in dataset brackets such
as `[http://example.com]`, so wrappers cannot hide a shared hostname. Original
text and production inference preprocessing remain unchanged. Group conflicts
found after the initial sample selection block affected records rather than
moving seen examples to a new partition. The training guard also rejects any
record explicitly marked validation, test or `do_not_train`, even if it came
from a provider file originally named `train.csv`.

Two account-rental messages were assigned project label 1 by the user after
selection was frozen. They are recorded in the latest reviewed dataset and a
separate decision file, not retrofitted into the model's 458-row fit manifest.
The final study still lacks a complete independently human-verified test set;
public evidence supporting two annotations does not imply expert verification.

The fallback source is now the original UCI SMS Spam Collection archive at
`data/reference/uci_sms_spam_collection.zip`, with pinned SHA-256
`1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3`.
Obtain it from https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip
if absent. The UCI dataset is attributed to Almeida and Hidalgo, DOI
10.24432/C5CC84, CC BY 4.0. Its complete original messages replace the malformed
local `spam.csv` as the fallback; spam/ham is still a proxy, not verified smishing.

Training uses the shared dataset URL repairs: refang explicit hxxp/hxxps and
host [.] representations, encode literal spaces in paths, then quarantine
invalid/ambiguous URLs and conflicting labels before deduplication. No URL is
fetched. Inference preprocessing remains unchanged; deployed bundles are not
replaced by data preparation. Repair-code hashes and URL audit counts are saved
in reports from future training runs.
Whitespace in queries/fragments, embedded malware/HTTP annotations, redactions,
and quotes in hostnames are quarantined rather than interpreted as URL content.

Missing auxiliary spam labels stay missing. Smishing labels are not copied into
the spam column. A repair to text/URL formatting never promotes inherited or
keyword-derived labels to expert verification. Review proposals remain pending
until their evidence and reviewer are recorded. The review sample is for a label
audit and is not an independent evaluation set. Do not report an error rate before
completing human review, or retrain/deploy as a verified improvement without a
separate reliable evaluation set.

From the project root on Windows:

    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r ml_model\requirements.txt
    .\.venv\Scripts\python.exe ml_model\download_data.py
    $env:OMP_NUM_THREADS = '2'
    $env:OPENBLAS_NUM_THREADS = '1'
    .\.venv\Scripts\python.exe -u ml_model\train.py
    .\.venv\Scripts\python.exe -m unittest discover -s ml_model -v
    .\.venv\Scripts\python.exe ml_model\verify_internal.py

Place phishing_site_urls.csv (columns URL,Label; good/bad) in ml_model/data first.
The existing copy contains 549,346 rows. Its SHA-256 is saved in training_report.json.

Training validates binary labels, canonicalizes URLs, masks entities, preserves
Vietnamese NFC words, quarantines conflicting normalized records and removes
duplicates. All URLs in a message are extracted; a group connects identical
normalized text and any shared hostname.

An untouched grouped SMS holdout is split before fitting. Inner 5-fold grouped
text OOF is restricted to the SMS training partition. The URL estimator is trained
on a separate URL corpus with every SMS hostname excluded, and has its own grouped
holdout. No synthetic text–URL pairs are generated. The meta-learner is fitted
only on real paired SMS in SMS training. Deployed models retain the test exclusions.

The Combined Labeled Smishing Dataset assigns its smishing labels using keyword
rules. These are weak labels, not expert-verified ground truth. See
data/smishing_source.json and data/smishing_source_README.md for provenance and
research-use terms. An SMS label does not independently establish its URL's label.

Outputs:

- models/model_bundle.pkl: the complete fitted pipelines and meta-learner.
- models/training_report.json: data hashes, run ID, fitted coefficients and holdout metrics.
- models/split_ids.json: reproducible split indices and isolation checks.

The bundle includes a hash of preprocessing/model definitions and the sklearn
version. Missing, corrupted or incompatible bundles return unavailable, never a
safe score. Rerun training after changing preprocessing or estimator definitions.
Never load pickle artifacts from an untrusted source.

Inference is fully local for every score. SMS retains the <30 low, 30–79 review,
>=80 high-risk policy. In the default hybrid adapter, URL-only input requires
review when its raw URL score meets the URL head's 0.50 threshold; >=80 rounded
points remains high risk. An independently positive URL still requires review
when SMS is present, without changing the SMS score. Both API endpoints and the
web verdict consume the inference action rather than reapplying SMS thresholds.
Legacy and processed adapters retain their historical policies. Scores are not
calibrated probabilities; a below-threshold result does not verify a website.
URL annotations cannot alter scores. See
`../docs/url-alert-policy-fix-2026-10-26.md` for the measured false-alarm/recall tradeoff.
Images and dialogue evaluation are unavailable until suitable local models exist.

    npm.cmd ci --ignore-scripts
    .\scripts\start-local.ps1

With the app running:

    node --test scripts/analysis-assessment.test.mjs scripts/analyze.integration.test.mjs
    npm.cmd run lint
    npm.cmd run build

The API starts Python per request. Its latency includes imports and model loading.
The dashboard reports measured Python inference time; it does not claim <4ms endpoint latency.

## External supervised training, 2026-10-25

The isolated experiment in `external_training.py` and `external_experiment.py`
has completed using Mendeley SMS Phishing Dataset v1 (5,971 original messages)
and PhishVN dataset version 4 / release v3.1.0 (53,116 original URLs). It also
retains eligible previously reviewed training messages. Original labels,
source checksums, review provenance, ambiguous records and group exclusions
are exported separately. No keyword rule creates a new smishing label.

See `../docs/external-data-training-2026-10-25.md` for sources, counts, actual
holdout results and limitations. The complete local artifacts are in
`data/prepared/external_training_2026-10-25/`: `final_report.json`,
`verification_report.json`, `selection_frozen.json`, `research_bundle.pkl`,
and CSV/JSONL train, validation, test, quarantine and prediction exports.
These generated datasets and model artifacts are intentionally gitignored.

Source SMS labels do not imply expert verification. An AI semantic review
covered 240 source messages; unresolved cases and the remaining 438 unreviewed
source-smishing messages are quarantined. PhishVN training positives are
gold-tier feed-listed abuse, a broader target than credential phishing.
Bronze records and silver positives are quarantined. Labels inferred from
scenario keywords are never training targets or features. URL inference uses
recomputed lexical features and collapses HTTP/HTTPS to one scheme to remove
the documented collection artifact.

Groups use the pinned Public Suffix List, text templates and character
similarity. Every domain represented by the published 200-case human audit is
reserved from both training corpora. Its 81 evidence-supported phishing versus
legitimate cases form a separate human-label URL evaluation. This is an
authors' published audit, not an independent verification by this project and
not a claim of verified expert qualifications. The source-labeled URL test,
AI/source-labeled SMS test and reused Vietnamese diagnostic are reported
separately. Fusion uses actual SMS links and grouped out-of-fold text scores;
validation selected the text model for SMS decisions.

Once all pinned source files and review annotations are present, the experiment
stages are:

    .\.venv\Scripts\python.exe ml_model\external_experiment.py prepare --allow-ai-labels
    .\.venv\Scripts\python.exe ml_model\external_experiment.py select --allow-ai-labels
    .\.venv\Scripts\python.exe ml_model\external_experiment.py test --allow-ai-labels

Selection and test have already completed in this checkout. They reject reruns
to prevent tuning against the same test. Frozen checksums cover inputs, code and
the research bundle. A changed experiment needs a separate output directory
and a new evaluation plan; do not erase the freeze to retest.

To try the fitted candidate without changing the app:

    .\.venv\Scripts\python.exe ml_model\external_experiment.py predict --allow-ai-labels --text "Me oi con can chuyen tien gap, dung goi con"

This bundle is explicitly incompatible with the production inference contract.
The app's models are preserved. The URL and Vietnamese false-positive results
do not support promoting this candidate to production. Scores are model outputs,
not calibrated real-world probabilities. MIMICS-3500 contributed zero records:
no official public data file with verified provenance and reuse terms was found.

Access-route correction, 2026-10-25: the user identified the official GVIS page
at https://gvis.unileon.es/datasets-mimics-3500/. It provides MIMICS-3500 upon
email request to gvis@unileon.es, from an institutional account; students must
have their supervisor submit the request. Include institution, project summary
and research objectives. The page states no response deadline or specific reuse
license. No request has been sent and no MIMICS records have been acquired.
The original frozen training reports remain unchanged; see the updated access
section in `../docs/external-data-training-2026-10-25.md`.

## SmishX English SMS expansion

`smishx_training.py` completes an isolated follow-up to the frozen external
experiment, without editing its code or outputs. It screens the multilingual
SmishX source against English language and project label scope, retains the
authors' manual label provenance, blocks old holdout groups, merges consistent
duplicates and fits a new SMS text model. Ambiguous scope or label conflicts
are quarantined rather than converted into new AI training labels. IMC's
AI-labeled messages and MIMICS-3500 are not fitted.

Artifacts are in `data/prepared/smishx_training_2026-10-25/`.
See `../docs/smishx-training-2026-10-25.md` for corrected language counts,
train/validation/test usage, results and regressions on reused diagnostics.
The new 39-message English holdout is small; historical tests are diagnostics.
The original app bundle is preserved. The later web activation uses the selected
model through a dedicated adapter. Completed selection and test stages reject reruns.

    .\.venv\Scripts\python.exe ml_model\smishx_training.py predict --allow-mixed-labels --text "Hello, can we meet at 3 tomorrow?"

## English SMS training candidate, 2026-10-28

`english_sms_training.py` fitted `english-sms-20261028` on the active 3,786 SMS
fit rows plus 338 admitted English additions. It preserves all 133 Vietnamese
rows, the fixed SMS threshold and the complete URL head. Nested grouped OOF
English precision/recall/F1 were 95.97%/91.47%/93.67% against source labels.
Sigmoid calibration passed, but historical English false alarms increased.
The candidate is saved under `data/prepared/english_sms_training_2026-10-28/`
and is **not activated**. The current serving model remains unchanged.
See [protocol, results and artifacts](../docs/english-sms-training-2026-10-28.md).

## Training-only SMS selection and release guards, 2026-10-28

`english_sms_selection.py` adds nested-group selection over eight fixed
regularization/weak-source-weight configurations. English nested OOF F1 rose
from 93.67% to 94.89%, but the selected candidate still failed historical
nonregression and remains unactivated. Rejected release flags now block serving
and health readiness; legacy manifests retain compatibility. The health hash
cache invalidates when the expected checksum or bundle path changes.
`model_state.py` compares learned values without mistaking NumPy padding for
changed weights. See [results and verification](../docs/english-sms-selection-2026-10-28.md).

## SMS training with admitted English ham, 2026-10-29

`english_ham_training.py` fits the prior training-only configuration on 4,186
labeled rows, including 62 newly isolated UCI negatives, with regrouping and
grouped sigmoid calibration. English grouped OOF F1 is 93.99%; these source-label
estimates use a previously selected configuration. Historical nonregression
failed, so the saved candidate is explicitly rejected and serving weights remain
unchanged. All 172 Python tests pass. See [training artifacts and checks](../docs/english-ham-training-2026-10-29.md).

## Conservative English SMS release, 2026-10-29

The active local run is `sms-confirmation-english-20261029`. A supervised English
confirmation head can lower the pinned parent's raw score; uncertain language
keeps the parent score. URL inference and all application thresholds are
unchanged. Grouped CV, historical thresholds and all 983 real serving decisions
preserve FP/FN counts. Sigmoid calibration improves grouped Brier/log-loss.
All 181 Python, 68 JavaScript and 23 HTTP checks pass, with lint/build.
Parent bytes are archived in `data/prepared/conservative_sms_english_gate_2026-10-29/`.
Use its `release_artifact.py verify` for parent-aware integrity verification.
See [release protocol, metrics and limits](../docs/conservative-sms-training-2026-10-29.md).
