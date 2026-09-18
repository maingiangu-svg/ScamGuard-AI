# TASK SPEC: Chrome Extension for ScamGuard AI

## Objective
Build a lightweight Manifest V3 Chrome Extension that inspects the current active tab URL/content, calls the local ScamGuard AI API (`http://localhost:3000/api/analyze`), and dynamically injects a red warning banner if a scam risk is detected.

## Target Directory
`extension/`

## Step-by-Step Execution Plan

### Task 1: Initialize Manifest V3
- File: `extension/manifest.json`
- Requirements:
  - `manifest_version`: 3
  - `name`: "ScamGuard AI Threat Detector"
  - `version`: "1.0.0"
  - `permissions`: ["activeTab", "scripting"]
  - `host_permissions`: ["<all_urls>"]
  - `background`: `{ "service_worker": "background.js" }`
  - `content_scripts`: Match `<all_urls>` with `content.js` and `overlay.css`

### Task 2: Background Listener
- File: `extension/background.js`
- Requirements:
  - Listen to `chrome.tabs.onUpdated`.
  - Trigger message to `content.js` when `status === 'complete'`.

### Task 3: Content Script & Injector
- File: `extension/content.js`
- Requirements:
  - Extract `window.location.href` and `document.title`.
  - Send `POST` request to `http://localhost:3000/api/analyze` with payload `{ url, title }`.
  - Parse response. If `riskLevel === 'HIGH'` or `riskScore > 70`:
    - Inject a top-fixed banner `#scamguard-alert-banner`.
    - Render warning text: "🔴 CẢNH BÁO: Trang web này có nguy cơ lừa đảo cao!"
    - Add a "Xác nhận / Đóng" dismiss button.

### Task 4: Styling
- File: `extension/overlay.css`
- Requirements:
  - Fixed position at top: 0, left: 0, width: 100%.
  - High `z-index: 9999999`.
  - Bright red background with bold white typography and high contrast.

## Definition of Done
- All 4 files are created inside `extension/`.
- Zero files outside `extension/` are modified.
- Extension loads cleanly in Chrome (`chrome://extensions` via "Load unpacked").