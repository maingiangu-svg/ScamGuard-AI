# Extension 1.3.0: batched URL inference

Historical measurement. The user replaced automatic extension link scanning
with [manual context-menu checks](extension-context-menu.md) in version 2.0.0.
The bounded batch backend remains available; the extension no longer scans pages.

On pages with many links, 1.2.0/1.2.1 sent one URL per request and started Python,
imported the ML runtime, verified artifacts and loaded the model for every URL.
Same-site navigation also preceded later external message links in DOM order.

The extension now collects visible URLs for 40ms, deduplicates them and submits
up to 20 per request. External destinations precede same-site navigation in the
next batch; no required checks are skipped. One Python process verifies and
loads the unchanged URL head, then predicts the whole group together. Per-URL
scores remain separate and never replace the current-page badge. LOW results
retain the page's original appearance, without green outlines or risk tooltips.

## Measurement

Same machine, interpreter, active model, eight fixed public URL inputs, and three
repetitions of each strategy. Every repetition launches fresh subprocesses;
neither strategy benefits from a persistent loaded model. This measures local
inference including process startup, without HTTP/extension pacing.

| Strategy | Runs (seconds for 8 URLs) | Median |
|---|---|---|
| Original, one process per URL | 50.35, 47.49, 46.29 | 47.49 s |
| New, one process per group | 5.99, 5.68, 6.39 | 5.99 s |

The observed median speedup is **7.92x** (87.4% less time). All eight scores match
exactly in all repetitions: `[1, 0, 94, 59, 2, 1, 0, 2]`. This is a controlled
local measurement, not a guarantee for every website, device or queue depth.
Inputs: Facebook, YouTube, `qi.lv/F0i`, the previously reported Sunwin profile,
Google, GitHub, Wikipedia and Microsoft. No private message data were benchmarked.
Raw timings are in `.local-runtime/link-speed-comparison.json`.

## Bounds and compatibility

`POST /api/analyze-links` accepts `{urls: [...]}` with 1–20 canonical minimized
HTTP/HTTPS URLs. Query, fragment and credentials are rejected, as are oversized,
malformed and foreign-origin requests. Response rows are validated against exact
requested URL identities. A missing, incompatible or busy model returns 503;
errors never become LOW results. Inputs are not fetched as web destinations.

The endpoint shares existing rate limits, body limits, 15-second child timeout,
output cap and two-process admission with the other inference endpoints. No
security limit was raised. At most four extension batches are queued; successful
per-URL results remain cached for five minutes in worker memory. Batches retain
1.5-second pacing and 429 backoff. No persistent worker or dependency was added.

The Python entry reuses manifest-bound preprocessing/model loading; no model
weights, training labels, thresholds, calibration or holdouts changed. A stale
test expectation for the old active run was updated to the actual activated run,
while adding explicit checks for the former parent run, row count and ancestor
hash. Existing lineage/isolation/provenance assertions remain.

The packaging gate caught a dynamic script path causing Next's tracer to include
raw datasets. Complete literal script paths restored tracing boundaries, and a
clean build was checked to contain no `ml_model/data` before local startup.

Tests cover score/action parity, one verified load, invalid inputs, CORS, quotas,
shared admission, cache identity, malformed responses and mode-change races.
Browser tests use owned HTML in an isolated profile and a separate localhost API
to avoid competing with the user's active browser session.

## Verification

- 139 Python tests, 62 JavaScript unit tests, 21 API integration tests and three
  inference-lifecycle tests passed.
  Lint, TypeScript and the standalone production build passed. The existing API
  and security assertions remain; the batch endpoint was added to the CI runner.
- The isolated Chromium suite passed 15 groups. Five distinct visible URLs
  shared one request and completed in 4,968ms, including browser/API overhead.
  The external regression URL preceded same-site navigation in the payload.
- Facebook and wrapped YouTube LOW results had no extension outline, tooltip or
  added accessible description; the 59/94 warning colors and keyboard tooltip
  remained. Pending/outage, new messages, recycled href, removal, stop races,
  original attributes, minimized inputs and no destination fetching all passed.
- Fixture CLS remained 0, with no JavaScript page errors. Scores and weights were
  unchanged; active and packaged bundle hashes still matched
  `26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`.
- Source scripts and screenshot/evidence are under
  `.local-runtime/extension-v130/`. No native browser profile, user conversation,
  extension Reload or permission prompt was automated. Reload the unpacked
  extension and web tab to activate version 1.3.0.
- The default local service was restarted with the batch endpoint and checked
  again on port 3000 (Facebook 1/LOW, regression link 94/HIGH). The isolated test
  server was stopped. The ZIP's nine entries were verified against current
  extension source files. No remote deployment was performed.
