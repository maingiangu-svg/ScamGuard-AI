# Link risk outlines, extension 1.3.0

Historical feature: automatic scanning was removed at the user's request in
2.0.0. See [context-menu checks](extension-context-menu.md) for the current flow.

User request: automatically assess links on all websites, including newly
received Facebook/Messenger links. Updated preference: keep low-risk links
unadorned; outline review/high-risk links yellow/red.

## Acceptance and scope

- Existing automatic-mode consent enables scanning of visible HTTP/HTTPS
  anchors on any supported top-level web page. Manual mode sends no link checks.
- Observe added anchors and href changes. Defer offscreen links until visible;
  never follow/click a destination to classify it. Plain text, browser internal
  pages, closed shadow roots and embedded frames are outside this version.
- LOW has no extension outline, tooltip or added accessible risk description;
  checking and caching continue. Yellow means MEDIUM, red HIGH/CRITICAL. Pending, unavailable,
  invalid or rate-limited checks stay grey. A low score is not a safety guarantee.
- Show the score and explanation on hover and keyboard focus, with a persistent
  accessible description. Outlines and fixed tooltips do not change page layout.
- Send only a minimized URL (scheme/host/port/path), without credentials, query,
  fragment, link text, page body or messages. Decode recognized Facebook link
  wrappers and Google/YouTube wrappers locally before minimization; malformed
  wrappers must not receive a LOW verdict. Other redirects are not resolved.
- Link scores never replace the current-page badge. Reject link requests from
  unconsented, stale, non-web or non-top-level senders and malformed targets.
- Serialize link inference globally, pace unique requests, bound queued work and
  cache successful scores for five minutes in worker memory only. No persistent
  browsing history. Show errors without inventing low scores.
- On disable/revocation/cleanup remove outlines, descriptions, observers and
  queued DOM work; ignore late results. Preserve original page attributes/links.

## Implementation and checks

Use native browser APIs and existing MV3 message passing; no new dependencies.
`extension/links.js` owns DOM discovery, outlines and tooltip. `content.js` owns
mode lifecycle. `background.js` authorizes and queues `ANALYZE_LINKS {urls}` (up
to 20). `POST /api/analyze-links` validates minimized URLs, CORS, shared quota and
the existing two-process inference admission. It runs `predict_links.py`, which
loads the same manifest-verified URL head once and predicts the batch together.
The response is `{results: [{url, riskScore, riskLevel, model_id}]}` or `{error}`.
Single-link worker messages remain compatible. Existing page screening stays.

Visible links coalesce for 40ms. External destinations take priority over same-site
navigation. No required link checks are skipped. The global 1.5s pacing applies
to batches; at most four batches are queued. No persistent Python worker, new
dependency or increase to existing backend admission/quota limits is needed.

Style follows existing plain JavaScript, semicolons and two-space indentation:
`if (!enabled || !anchor.isConnected) return;`.

Build order: request authorization/queue tests and implementation; DOM lifecycle
and UI; isolated-browser checks with synthetic documents and real local model.

Commands: `npm.cmd test`, `npm.cmd run lint`, `npm.cmd run check:types`,
`npm.cmd run build`, `node scripts/extension-browser.mjs`, and
`node scripts/extension-links-browser.mjs` (Playwright runtime already installed
under `.local-runtime/audit/node-tools`; set `PLAYWRIGHT_BROWSERS_PATH` to
`.local-runtime/browsers`). Tests must cover colors, new/recycled/hidden links,
wrappers/minimization, outage, deduplication, disable races, keyboard tooltips,
no destination fetching and zero layout shift on the owned fixture.

Always preserve existing assertions, labels/model artifacts, permissions defaults
and unrelated changes. No new dependency, training, remote deployment or native
browser-profile access is needed. Revisit scope before changing these boundaries.

References: [Chrome messaging](https://developer.chrome.com/docs/extensions/develop/concepts/messaging),
[IntersectionObserver](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API),
[MutationObserver](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver/observe).

## Initial 1.2.0 verification, 2026-10-27

- 58 Node tests passed, including consent/sender checks, bounded serial work,
  duplicate and expired cache, throttling, invalid results, original banner
  behavior and a delayed popup-settings regression. A temporary mutation that
  removed automatic-mode consent was caught; production sources were untouched.
- Lint, TypeScript checks and the production build passed. The local standalone
  service was restarted after rebuilding; health and real URL inference were
  checked again. No remote deployment was performed.
- Both installed-extension Chromium suites passed. The existing suite retained
  manual/automatic, permissions, badge and receiver-repair assertions. The new
  suite passed 14 groups including fresh messages, href replacement, removal,
  outage and disable during in-flight inference. Run these suites sequentially:
  they share the local server's two-inference admission limit.
- Real local URL model: Facebook homepage 1 (green), reported Sunwin profile
  59 (yellow), `qi.lv/F0i` 94 (red). Facebook's wrapped YouTube destination scored
  0. The actual active bundle remained SHA-256
  `26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`.
- Owned fixture: CLS 0, unchanged anchor bounding box/href/title, preserved
  accessible description, no JavaScript page errors, no destination requests,
  no message text or secret query in API bodies. Fault injections for outage and
  delayed responses are identified separately from the real-model color checks.
- Browser profiles were isolated. Optional permissions were pregranted only in
  the identified fixture manifest. Native Chrome/Edge permission dialogs and
  the user's installed extension Reload were not automated. Reload and grant
  automatic mode in the real browser to activate the local update.

## Version 1.3.0

LOW links now keep their original appearance, including on hover and keyboard
focus. The model still checks and caches them. Batched inference and external
link priority are verified in the [performance report](extension-performance-2026-10-27.md).
