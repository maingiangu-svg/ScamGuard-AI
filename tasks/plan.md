# Vietnamese SMS data readiness — 2026-10-27

User authorized all proposed data improvements and asked for questions while work continues.
The user has no private SMS to contribute. Work uses existing licensed sources and
public source evidence; no messages are sent to third parties.

## Ordered work

1. Audit the 2,991-message Vietnamese source against recorded historical roles,
   active fitting data, normalized content, templates, similarity and ICANN/PSL domains.
   Preserve source labels, original train/test roles and old quarantine decisions.
2. Prepare separate blind three-class annotation and public-message intake workflows.
   Legitimate, spam/promotion and scam are labels; unknown is an unresolved state.
   Two independent human reviews and evidence are required for a human benchmark.
3. Run an isolated supervised training experiment using eligible recorded training
   labels only. Freeze protocol and membership before fitting. Historical evaluation
   is diagnostic; no historical row is renamed a new independent test.
4. Verify the workflow with leakage, identity, annotation and evaluation tests;
   run existing project checks; deliver local datasets and a public aggregate report.

## Constraints and open dependencies

- Preserve all current uncommitted changes and deployed model artifacts.
- Reuse existing offline domain, similarity, preprocessing and model helpers.
- Dataset exports and annotation identities remain in gitignored prepared/.
- No expert signatures, campaign IDs, new real messages or rights are fabricated.
- A fresh 300–500 real-message benchmark requires qualifying source records and
  actual independent human decisions. Pending inputs remain explicitly pending.
- Ask the user about reviewers and label scope asynchronously; continue independent work.

## Verification

Focused Python tests must fail before implementation and pass after it. Preparation
must reconcile every source row, preserve source hashes, refuse overwriting completed
packages and show actual eligibility counts. Training must reject held-out/quarantined
rows. Evaluation must refuse incomplete review, mixed groups and repeat test use.
Existing Python/JavaScript tests, lint, typecheck and production build stay enforced.
