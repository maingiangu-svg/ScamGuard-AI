# SKILL: Chrome Extension Validation & Debugging

## Purpose
Ensure all Chrome Extension code built for ScamGuard AI adheres strictly to Manifest V3 standards and handles API errors gracefully.

## Execution Rules
1. **Manifest V3 Verification:**
   - Verify `manifest_version` is `3`.
   - Ensure NO inline JavaScript is used in HTML or injected scripts.
   - Confirm `host_permissions` properly allow `http://localhost:3000/*` and target Web URLs.

2. **API Resilience:**
   - Always wrap `fetch('http://localhost:3000/api/analyze')` inside a `try...catch` block.
   - If the local API is unreachable, log a clear warning in the browser console instead of throwing an unhandled exception.
   - Handle timeout scenarios (set a default timeout of 5 seconds for network requests).

3. **DOM Injection Safety:**
   - Before injecting `#scamguard-alert-banner`, check if `document.getElementById('scamguard-alert-banner')` already exists to prevent duplicate banner injections on DOM changes.