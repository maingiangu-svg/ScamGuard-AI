# Local ML corrections, 23 October 2026

The active system uses a complete model_bundle.pkl trained by train.py, which
delegates to train_meta_fusion.py. Legacy individual pickle files are not loaded.

## Changes and their purpose

- Removed the external generative-model SDK and its runtime calls. Text/URL scores
  always use trained local estimators, including the 30–79 review interval.
- Removed whitelist clearance and brand-score adjustments. Domain information is
  displayed separately and an unknown domain is never labelled legitimate.
- Replaced mismatched train/inference feature extraction with shared preprocessing
  and saved estimator pipelines. Source fingerprints normalize CRLF/LF for portability.
- NFC preserves composed Vietnamese words. URL handling preserves path case, parses
  hostnames correctly and evaluates all recognized URLs rather than the first one.
- Invalid labels fail training; conflicting normalized records are quarantined.
- Restored the public smishing source through a pinned revision and checksum.
  The upstream label process is keyword-based and research-use terms are retained.
- Removed synthetic pairing. Text OOF uses only SMS training, with an untouched
  grouped holdout. External URL training excludes every SMS hostname.
- Missing, failed, stale or incomplete bundles return unavailable, never safe.
- Dashboard coefficients, training counts and timing come from the loaded bundle
  and actual execution. Educational examples are explicitly labelled as presets.
- Replaced historical research assertions with current measured holdout results.
- Development and production use the supported Webpack builder because local Turbopack repeatedly
  failed to start its PostCSS worker. Type checks and lint checks remain enabled.
  Removed build-time Google font requests; the existing system-font CSS is retained.

## Verified

- 13 Python regression tests pass.
- 14 assessment tests pass, and a deliberate change to the 80-point boundary was
  caught by the tests before the original source was restored.
- 8 API integration tests pass. The review-interval check exercises both text-only
  and paired input with actual scores in 30–79, using the trained local models.
- Both scoring endpoints also pass isolated missing-model and corrupt-model
  integration checks: HTTP 503, no fabricated verdict and no internal path disclosure.
- The verification CLI runs in Windows PowerShell with UTF-8 output.
- TypeScript, ESLint and the production build pass.
- Development and production desktop and 390px mobile browser checks pass without runtime exceptions or
  external AI requests. Mobile has no horizontal overflow.
- Split checks confirm disjoint SMS groups, external URL hostnames and SMS/URL
  training hostnames. Current counts and metrics are in training_report.json.

## Remaining research/product limits

This fixes implementation and reporting defects; it does not create independent
expert labels or prove novelty. The source labels are weak supervision, scores
are uncalibrated, and the 30/80 policy is not claimed optimal. Hostname grouping
does not prove registrable-domain, temporal or campaign independence. Vietnamese
and expert-labelled external test sets are still needed.

Images return HTTP 415 and dialogue evaluation returns 501. Their controls are
disabled because no suitable local OCR/dialogue model has been installed/trained.
No heuristic result is presented as a trained dialogue model.

The Docker runtime definition includes Python dependencies and the trained bundle;
the Cloud Run script no longer requires an external model key. The Docker image
was not built here because Docker Engine is not running. Nothing was deployed to
a cloud service.
