# Extension 2.0.0: checks requested by the user

The user replaces automatic link scanning with right-click actions. Remove all
automatic page/link scanning, DOM observers/outlines and automatic-mode controls.
Keep the toolbar button for checking the current page explicitly.

Two native context actions under ScamGuard AI: check an HTTP/HTTPS link, or check
the selected message text. Use Chrome's browser-provided linkUrl/selectionText;
no DOM collection. Show pending/result/error in an extension window immediately.
Only the selected message (at most 20,000 characters, reject rather than truncate)
or a minimized URL is sent to the existing local API. Never fetch destinations.
Decode existing recognized Facebook/Google/YouTube wrappers before minimization.

Permissions: activeTab, localhost host access, storage, contextMenus. Scripting is
retained only to unregister legacy automatic content scripts during migration;
no new script registration/injection or broad optional host access remains.
Initialize on install/update/startup, force automatic=false, remove old registered
scanner and recreate menus without duplicates. Reload old web tabs to clear old
injected DOM styling.

Store at most 10 result summaries in trusted extension session storage, with
ten-minute viewing expiry, never message text or persistent browsing history.
Expired summaries remain bounded in memory until another check or session end.
Result IDs prevent
concurrent/out-of-order checks from overwriting each other's view. Only this
extension's popup may request current-page checks or read results. Legacy page
messages and forged menu commands cannot initiate analysis.

Reuse the current URL/SMS models and alert policies. Scores are not guarantees.
Preserve low SMS score plus an independent risky-URL warning. Errors must not
show a cached safe verdict. Render every input/result as text, without HTML.

Verification: update obsolete automatic-scanning tests because the feature is
explicitly removed; retain input minimization, sender validation, invalid/model
failure handling, privacy and race coverage in the replacement manual flow.
`npm.cmd test`, `npm.cmd run lint`, `npm.cmd run check:types`,
`node scripts/extension-browser.mjs`. Native OS menu selection is not automated:
test menu registration and invoke its registered handler in an isolated Chromium
profile, then exercise real local inference and result windows. Never attach a
personal browser profile or read real messages.

References: [contextMenus](https://developer.chrome.com/docs/extensions/reference/api/contextMenus),
[windows](https://developer.chrome.com/docs/extensions/reference/api/windows),
[session storage](https://developer.chrome.com/docs/extensions/reference/api/storage).

## Verification, 2026-10-27

- 65 Node tests passed, including 31 manual-extension cases. Lint, TypeScript
  and git diff whitespace checks passed. Existing automatic-workflow cases were
  replaced because the user explicitly removed that feature; no tests were
  skipped. A temporary mutation removing the trusted popup-path guard was caught.
- Isolated Chromium verified all three menu IDs actually exist through Chrome's
  contextMenus.update API, no broad web grants remain, no scripts are registered,
  and startup/page load/new links/right-click alone produce zero analysis calls.
- The registered menu handler exercised real local high/low URL inference,
  selected-text-only requests, independent embedded-URL warnings, current-page
  checks, result windows and keyboard close. All 13 browser check groups passed,
  without JavaScript page errors or destination fetching. A deliberate 503
  response displayed an error without a score. Selected text was absent from
  session storage and result URLs.
- The literal-URL message test compares the displayed primary score with the
  API's actual text head. Its URL placeholder can change the SMS score compared
  with a message that contains no URL; no assertion assumes they are identical.
- Native OS menu-item selection and the user's extension Reload were not
  automated. Screenshots and evidence are under .local-runtime/extension-v200/.
  The six-file ZIP was checked against current extension sources and contains
  no automatic scanner. Backend, model weights and training data were unchanged.
