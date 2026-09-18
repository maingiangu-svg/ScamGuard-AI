// content.js - ScamGuard AI Threat Detector Content Script

(function () {
  let isAnalyzing = false;

  function injectWarningBanner(messageText) {
    if (document.getElementById("scamguard-alert-banner")) {
      return;
    }

    const banner = document.createElement("div");
    banner.id = "scamguard-alert-banner";
    banner.className = "scamguard-banner-container";

    const textSpan = document.createElement("span");
    textSpan.className = "scamguard-banner-text";
    textSpan.textContent = messageText || "🔴 CẢNH BÁO: Trang web này có nguy cơ lừa đảo cao!";

    const closeBtn = document.createElement("button");
    closeBtn.id = "scamguard-banner-close-btn";
    closeBtn.className = "scamguard-banner-button";
    closeBtn.textContent = "Xác nhận / Đóng";
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

  async function analyzeCurrentPage() {
    if (isAnalyzing) return;

    const currentUrl = window.location.href;
    const currentTitle = document.title;

    if (
      !currentUrl ||
      currentUrl.startsWith("http://localhost:3000") ||
      currentUrl.startsWith("chrome://") ||
      currentUrl.startsWith("chrome-extension://") ||
      currentUrl.startsWith("about:")
    ) {
      return;
    }

    isAnalyzing = true;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch("http://localhost:3000/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: currentUrl,
          title: currentTitle,
          textInput: `URL: ${currentUrl}\nTitle: ${currentTitle}`,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        console.warn("[ScamGuard AI Extension] API request returned status:", response.status);
        return;
      }

      const data = await response.json();

      const score = data.riskScore ?? data.risk_score ?? 0;
      const level = data.riskLevel ?? data.threat_level ?? "";
      const scamDetected = data.scam_detected ?? false;

      const isHighRisk = level === "HIGH" || level === "CRITICAL" || score > 70 || scamDetected === true;

      if (isHighRisk) {
        const warningText = data.executive_summary
          ? `🔴 CẢNH BÁO: Trang web này có nguy cơ lừa đảo cao! (${data.scam_type || "Nghi vấn lừa đảo"})`
          : "🔴 CẢNH BÁO: Trang web này có nguy cơ lừa đảo cao!";
        injectWarningBanner(warningText);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        console.warn("[ScamGuard AI Extension] Network request timed out after 5 seconds.");
      } else {
        console.warn("[ScamGuard AI Extension] Unable to reach API at http://localhost:3000/api/analyze:", err.message);
      }
    } finally {
      isAnalyzing = false;
    }
  }

  if (document.readyState === "complete" || document.readyState === "interactive") {
    analyzeCurrentPage();
  } else {
    window.addEventListener("DOMContentLoaded", analyzeCurrentPage);
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message && (message.action === "ANALYZE_PAGE" || message.action === "CHECK_PAGE")) {
      analyzeCurrentPage();
    }
  });
})();
