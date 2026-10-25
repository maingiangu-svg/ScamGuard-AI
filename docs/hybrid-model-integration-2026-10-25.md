# Hybrid SMS and URL integration — 2026-10-25

## Contract

Use the frozen processed SMS estimator (3,857 training messages, threshold
0.65) and the URL estimator from bundle `20261025T152344Z` (40,004 training
URLs, reference classification threshold 0.50). Preserve each estimator's
training preprocessing and unrounded decision score. These are independently
supervised branches, not a newly trained ensemble.

For substantive text, the SMS score remains the primary score. For URL-only
input, the maximum score across the supplied URLs is the primary URL score.
For text containing URLs, a positive URL classification additionally requires
URL review, even when the SMS score is low. This changes the review action,
not the SMS score or SMS binary prediction. The existing 30/80 display bands
remain; independent URL review raises a low-band result to review.

Do not average incompatible scores or reuse the old meta-learner with a
different SMS estimator. URL-only input must not run the SMS model. Preserve
every extracted URL, case-sensitive paths and independent branch metadata.

## Artifacts and provenance

Package the existing fitted SMS and URL estimators into
`ml_model/models/hybrid_bundle.pkl`, with a checksum/provenance manifest beside
it. The package operation performs no fitting, threshold selection, or test
evaluation. Runtime verifies the artifact and frozen helper checksums before
unpickling. Helper hashes normalize CRLF to LF for Windows/Linux checkouts.
Include both files in Git and the Docker runtime. Missing, corrupt
or incompatible artifacts return unavailable (HTTP 503), without fallback.

SMS labels have mixed source-human, source and AI-reviewed provenance; they
are not entirely expert verified. URL labels are upstream good/bad source
labels, not independently expert verified. Retain source artifact hashes,
training counts, label scope and calibration status in the manifest/API.

## Acceptance and verification

- Pure SMS predictions match the frozen processed SMS estimator exactly.
- URL-only predictions match the selected bundle URL estimator exactly.
- Neutral text cannot hide a URL that the URL estimator flags for review.
- Multiple explicit/embedded URLs are all scored, with no forced whitelist.
- No model or source artifact is retrained or overwritten.
- UI shows branch-specific scores, the source of the primary score, and a
  visible URL-review warning. It never claims live website verification.
- Python unit tests cover routing, preprocessing, URL review and corrupt
  artifacts. Node/API tests cover assessment severity and response parity.
- Run `python -m unittest discover -s ml_model -p "test_*.py"`,
  `node --experimental-strip-types --test scripts/analysis-assessment.test.mjs`,
  `node --test scripts/analyze.integration.test.mjs`, `npm.cmd run lint`, and
  `npm.cmd run build`, using the local `.venv` Python and `TEST_APP_URL` for
  live API tests. Inspect the result in an isolated local browser.

## Evidence boundary

This integrates model capabilities and preserves independent decisions. It
does not establish improved accuracy, calibrated probabilities, or a new
learned fusion result. Independent URL review can increase review volume;
measure that tradeoff on new shared, labeled, training-disjoint evaluation
data before claiming a performance improvement. Historical held-out datasets
and selections remain frozen. No URLs are fetched.

## Verification completed

- 56 Python, 16 assessment, 10 production API and 2 unavailable-model API tests
  passed. The packaged heads exactly matched their source scores on smoke
  inputs. Missing-model tests used a separate server and never renamed models.
- Inverting the URL-review comparison in an in-memory module made two tests
  fail. The repository source was never mutated by this check.
- Lint passed. The production build, TypeScript and static generation passed
  on a checksum-verified source snapshot under `.local-runtime/`; the ordinary
  root build was blocked by an existing locked `.next/local-server.stderr.log`.
  `.local-runtime/` is excluded from lint and Docker as generated local output.
- Real Edge UI checks showed URL-only 89/100 and a mixed message with SMS
  12/100 plus URL 89/100, a visible independent-review warning and amber REVIEW
  state. No app runtime exceptions or failed local responses were recorded.
- Source model artifacts and six pre-existing local paper/document files were
  preserved. No new overall accuracy or calibrated probability is claimed.
