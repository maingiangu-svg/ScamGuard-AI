# ScamGuard browser extension

Load this directory as an unpacked extension in Chrome/Edge, then start ScamGuard
at `http://localhost:3000`. Analysis uses that local service's `/api/analyze` endpoint.
The extension does not call the deployed Cloud Run service.

Open the extension popup to choose either mode:

- **Manual (default):** press the check button to screen the active HTTP/HTTPS tab.
  The extension uses `activeTab` and injects the checker for that action.
- **Automatic (opt-in):** choose automatic mode and approve the browser's optional
  access to HTTP/HTTPS sites. A registered content script screens visited pages.
  Switching back to manual unregisters automatic scripts and attempts to remove
  those optional grants. If the browser retains a grant, the popup explains how
  to revoke it in extension settings; automatic scanning stays off.

The mandatory localhost host permission lets the service worker call the local
API. Broad web access is optional. Only this extension's popup can change modes;
ordinary page messages cannot enable automatic scanning. The manifest's public
key fixes the unpacked ID to `lamffehgecaabedhleppfmgjcagamlih`, which the local
API explicitly allows. A separately distributed build with another ID needs a
corresponding `SCAMGUARD_ALLOWED_ORIGINS` entry.

Only the page URL's scheme, hostname, port and path are submitted. Page titles,
page body text, URL usernames/passwords, query strings and fragments are not
submitted. Paths can still contain personal information; this is data minimization,
not anonymization. The URL model evaluates the minimized URL, so a signal present
only in a query or fragment is outside this URL check in either mode.

The extension does not use a remote AI service. A banner appears for a HIGH or
CRITICAL verdict or score >=80, consistent with the app's existing alert policy.
An absent banner is not a safety guarantee: the model can miss threats, the API
can be unavailable, or browser local-network permissions can block the request.

The actual local app origin is excluded from automatic screening. Other origins
whose text begins with that origin are still checked. Request timeout is 20 seconds.

Run `npm.cmd test` from the project root for regression tests, including mode
switch races, sender validation, permission checks and URL minimization.

`scripts/extension-browser.mjs` installs the production manifest into isolated
Chromium and checks default manual mode, the real popup/service worker/API flow,
and rejection of automatic mode without host grants. A separately identified
fixture pregrants hosts to test automatic registration, warnings and disabling;
the production manifest is not changed. See the [readiness report](../docs/project-readiness-2026-10-26.md).

Before release, manually accept/deny the native optional-permission prompt in
each supported Chrome/Edge version and test manual checks on an external site
with `activeTab`. That native prompt and cross-browser/local-network settings
are not established by the automated fixture. A page already displaying a banner
may retain it until navigation after automatic scanning is disabled.
