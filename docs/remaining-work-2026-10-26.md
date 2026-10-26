# Remaining release work

User scope, 2026-10-26: defer OCR and roleplay; complete container security,
extension permissions, independent Vietnamese evaluation and score calibration.
User requests continuous execution and questions only for material decisions;
routine spec/plan approvals are not separate stopping points for this task.

| Module | Responsibility | Dependency |
| --- | --- | --- |
| runtime-security | Remove unnecessary vulnerable OS components; preserve package inventory and scan all High/Critical findings | existing inference |
| extension-consent | Verify real browser permission acceptance/denial and manual activeTab without pregrants | existing extension/local API |
| supervised-evaluation | Validate real reviewer records, isolate benchmark groups, bind predictions and calibration to provenance | existing model, human labels |

Order: runtime-security, extension-consent, supervised-evaluation. No OCR,
dialogue, unrelated paper edits or automatic production deployment.

Commands: `npm.cmd test`, `npm.cmd run lint`, `npm.cmd run check:types`,
`npm.cmd run build`, `.venv/Scripts/python.exe -m unittest discover -s ml_model -v`.
Runtime checks use owned local servers/browser profiles and owned Docker smoke
containers; detailed evidence goes under `.local-runtime/completion/`.

Success criteria:

1. Runtime builds, runs both SMS and URL as an unprivileged user/read-only root,
   retains the package inventory for shipped OS libraries, and image Trivy scan
   reports zero unignored High/Critical findings. Add a reproducible CI gate.
2. Extension uses its production manifest and actual optional permission prompt;
   acceptance, denial, manual activeTab and subsequent disabling are observed.
   Do not relabel a pregranted fixture as real consent.
3. New Vietnamese benchmark is bound to source/license, task scope, input hashes,
   independent reviewer evidence and split/group exclusion. Reused historical
   diagnostics and the 811 train candidates never become a new untouched test.
4. Calibration fits only eligible labeled calibration data, not train/test leaks;
   evaluation reports sample support and calibration metrics. Unverified labels
   remain unverified. No automatic expert signature or unconditional safety claim.
5. Existing tests and model/preprocessing integrity checks remain effective.

The current dataset/source search found broader spam/scam labels and synthetic
corpora; those are not silently promoted to expert-verified project smishing
labels. Two actual reviewers or a qualified source review record are requested.
This human dependency must remain explicit until evidence exists.

## Predeclared calibration experiment

User authorized AI review with uncertain advertising quarantined, and approved
SMISHX-0704 label 1 as a user decision. Do not overwrite source records or call
these expert labels. Exclude unknown cases and their entire repair groups from
the candidate's train data. Hold validation/test files fixed and outside fitting.

Fit sigmoid CalibratedClassifierCV with ensemble=False, three stratified group
folds, seed42, and the existing estimator hyperparameters/weights. Assess it by
three outer stratified group folds with three inner calibration folds. The raw
estimator and calibrated estimate use the same trained base in each comparison.
Candidate gate requires both Brier score and log-loss no worse than raw scores
for both branches on outer held-out predictions. Never tune on the old test set.
Record group-bootstrap uncertainty and label provenance. Passing this train-only
gate supports only a source-label estimate, not a new expert Vietnamese benchmark
or a general population fraud probability. Existing 30/80 alert policy and raw
branch decision thresholds remain separate from the calibrated estimate.
