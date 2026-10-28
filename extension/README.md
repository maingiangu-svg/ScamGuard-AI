# ScamGuard extension 2.0.0

Load this directory as an unpacked Chrome/Edge extension. Keep the local ScamGuard
service running at http://localhost:3000. Checks use its existing /api/analyze
endpoint and the active local SMS/URL models; no remote AI service is called.

## Use

- Right-click an HTTP/HTTPS link, then choose **ScamGuard AI → Kiểm tra liên kết này**.
- Highlight the part of a message you want checked, right-click, then choose
  **ScamGuard AI → Kiểm tra tin nhắn đã chọn**.
- Or open the toolbar popup and press **Kiểm tra trang hiện tại**.

The context actions immediately open a small result window with a pending state,
then show the model score, risk level and explanation, or an unavailable/error
state. A low score is not a guarantee of safety. Messages with risky embedded
URLs retain their own primary SMS score and show the independent URL warning.

There is no automatic page/link scanning, DOM observer, page banner or colored
link outline. Merely loading a page, receiving a link or opening its native
right-click menu does not call the API. Choosing the ScamGuard action does.

## Data and permissions

For a link, submit only scheme/host/port/path. Credentials, query and fragments
are stripped after locally decoding recognized Facebook, Google and YouTube
redirect wrappers. Other redirects are not followed and query-only signals are
outside a link check. Submitted destinations are never fetched.

For a message, send exactly the selected text, including any URLs the user chose.
No surrounding chat, page title, sender identity or page body is collected.
Empty selections or selections over 20,000 characters are rejected, not truncated.
The local API can evaluate only the content actually provided.

Results use trusted extension session memory, with at most ten summaries and
ten-minute viewing expiry. Selected message text is never stored; a result
window URL contains only a random result ID. No persistent browsing history is
written. Summaries may remain in bounded session memory until another check or
the browser session ends; expired summaries are not returned to the interface.

Permissions are activeTab, localhost host access, storage and contextMenus.
Scripting is retained only to unregister the former automatic content script
during migration; the extension never registers or injects a new script.
Broad optional web-host access has been removed. Only this extension's popup can
request a current-page check or retrieve a result. Page messages and legacy scan
actions cannot initiate checks. The unpacked ID remains
lamffehgecaabedhleppfmgjcagamlih, already included in the local API allowlist.

## Upgrade

Reload ScamGuard at edge://extensions or chrome://extensions, then reload any web
tabs that still have old outlines. The popup must show **Phiên bản 2.0.0**.
Installation/update/startup turns the former automatic setting off, unregisters
its persistent content script and creates the context menus. Existing models,
thresholds and backend endpoints are unchanged.

## Verification

Run npm.cmd test, npm.cmd run lint and npm.cmd run check:types from the root.
node scripts/extension-browser.mjs loads an isolated browser profile, invokes the
registered native-menu handler using owned fixture click data, and checks real
local inference, result windows, explicit current-page checks, privacy and errors.

Native Chrome/Edge OS-menu item selection and the user's Reload are not
automated. Confirm the two menu entries after reloading the real extension.
The historical automatic-scanning tests were replaced because that behavior was
explicitly removed; sender validation, minimized input, model errors, private
selection handling and concurrent-result isolation remain covered.

See [manual workflow specification](../docs/extension-context-menu.md).
