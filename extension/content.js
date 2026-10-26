// content.js - ScamGuard AI Threat Detector Content Script

(function () {
  const version = chrome.runtime.getManifest().version;
  if (window.__scamguardInstalled?.version === version) return;
  window.__scamguardInstalled = {version};
  let inFlight = null;
  let lastURL = '', lastResult = null;

  function injectWarningBanner(messageText) {
    if (document.getElementById("scamguard-alert-banner")) {
      return;
    }

    const banner = document.createElement("div");
    banner.id = "scamguard-alert-banner";
    banner.className = "scamguard-banner-container";

    const textSpan = document.createElement("span");
    textSpan.className = "scamguard-banner-text";
    textSpan.textContent = messageText || "🔴 WARNING: This website poses a high risk of scam or phishing!";

    const closeBtn = document.createElement("button");
    closeBtn.id = "scamguard-banner-close-btn";
    closeBtn.className = "scamguard-banner-button";
    closeBtn.textContent = "Acknowledge / Dismiss";
    closeBtn.addEventListener("click", () => {
      const el = document.getElementById("scamguard-alert-banner");
      if (el) {
        el.remove();
      }
    });

    banner.appendChild(textSpan);
    banner.appendChild(closeBtn);

    if (document.body) {
      document.body.prepend(banner);
    } else if (document.documentElement) {
      document.documentElement.appendChild(banner);
    }
  }

  function currentPageURL() {
    let page;
    try { page = new URL(window.location.href); } catch { return null; }
    if (!["http:", "https:"].includes(page.protocol) || page.origin === "http://localhost:3000") return null;
    // Only the page URL is classified. Titles are not SMS, and URL credentials,
    // query tokens and fragments must not be collected by automatic screening.
    page.username = page.password = page.search = page.hash = "";
    return page.href;
  }

  function analyzeCurrentPage(force = false) {
    const url = currentPageURL();
    if (!url) return Promise.resolve();
    if (inFlight?.url === url) return inFlight.promise;
    if (!force && lastURL === url && lastResult) return Promise.resolve(lastResult);
    if (lastURL !== url) document.getElementById('scamguard-alert-banner')?.remove();
    const task = {url};
    task.promise = performAnalysis(url).then(data => {
      if (data && !data.error && currentPageURL() === url && Number.isFinite(data.riskScore ?? data.risk_score)) {
        lastURL = url; lastResult = data;
      }
      return data;
    }).finally(() => {if (inFlight === task) inFlight = null;});
    inFlight = task;
    return task.promise;
  }

  async function performAnalysis(url) {
    try {
      const data = await chrome.runtime.sendMessage({action: 'ANALYZE_URL', url});
      if (data.error) return data;
      if (currentPageURL() !== url) return data;

      const score = data.riskScore ?? data.risk_score ?? 0;
      const level = data.riskLevel ?? data.threat_level ?? "";
      const scamDetected = data.scam_detected ?? false;

      const isHighRisk = level === "HIGH" || level === "CRITICAL" || score >= 80 || scamDetected === true;

      if (isHighRisk) {
        const warningText = data.executive_summary
          ? `🔴 WARNING: High scam/phishing risk detected! (${data.scam_type || "Suspicious Activity"})`
          : "🔴 WARNING: This website poses a high risk of scam or phishing!";
        injectWarningBanner(warningText);
      }
      return data;
    } catch (err) {
      return {error: err.message};
    }
  }

  async function automaticCheck() {
    const {automatic = false} = await chrome.storage.local.get('automatic');
    if (automatic) return analyzeCurrentPage();
  }
  automaticCheck();
  const listener = (message, sender, respond) => {
    if (message?.action === 'PING') {respond({version}); return false;}
    if (message?.action === 'CHECK_PAGE' || message?.action === 'AUTO_PAGE') {
      (message.action === 'CHECK_PAGE' ? analyzeCurrentPage(true) : automaticCheck()).then(respond);
      return true;
    }
  };
  chrome.runtime.onMessage.addListener(listener);
  window.__scamguardInstalled.cleanup = () => chrome.runtime.onMessage.removeListener(listener);
})();
