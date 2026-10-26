// content.js - ScamGuard AI Threat Detector Content Script

(function () {
  if (window.__scamguardInstalled) return;
  window.__scamguardInstalled = true;
  let inFlight = null;

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

  function analyzeCurrentPage() {
    if (!inFlight) inFlight = performAnalysis().finally(() => {inFlight = null;});
    return inFlight;
  }

  async function performAnalysis() {

    let page;
    try { page = new URL(window.location.href); } catch { return; }
    if (!["http:", "https:"].includes(page.protocol) || page.origin === "http://localhost:3000") return;
    // Only the page URL is classified. Titles are not SMS, and URL credentials,
    // query tokens and fragments must not be collected by automatic screening.
    page.username = page.password = page.search = page.hash = "";

    try {
      const data = await chrome.runtime.sendMessage({action: 'ANALYZE_URL', url: page.href});
      if (data.error) return data;

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
  chrome.runtime.onMessage.addListener((message, sender, respond) => {
    if (message?.action === 'CHECK_PAGE' || message?.action === 'AUTO_PAGE') {
      (message.action === 'CHECK_PAGE' ? analyzeCurrentPage() : automaticCheck()).then(respond);
      return true;
    }
  });
})();
