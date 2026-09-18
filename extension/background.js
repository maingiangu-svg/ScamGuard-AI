// background.js - Service Worker for ScamGuard AI Threat Detector

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === "complete" &&
    tab.url &&
    (tab.url.startsWith("http://") || tab.url.startsWith("https://")) &&
    !tab.url.startsWith("http://localhost:3000")
  ) {
    chrome.tabs.sendMessage(tabId, { action: "ANALYZE_PAGE", url: tab.url, title: tab.title }).catch((err) => {
      // Content script may not be ready or injected yet; silently handle
    });
  }
});
