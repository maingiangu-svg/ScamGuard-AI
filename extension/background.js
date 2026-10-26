const AUTO_SCRIPT = 'scamguard-automatic';
const WEB_ORIGINS = ['http://*/*', 'https://*/*'];

function minimizedURL(value) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.origin === 'http://localhost:3000') throw new Error('Unsupported page');
  url.username = url.password = url.search = url.hash = '';
  return url.href;
}

async function applyMode(automatic) {
  if (automatic && !await chrome.permissions.contains({origins: WEB_ORIGINS})) {
    throw new Error('Cần cấp quyền truy cập trang web để bật tự quét.');
  }
  await chrome.scripting.unregisterContentScripts({ids: [AUTO_SCRIPT]}).catch(() => {});
  if (automatic) await chrome.scripting.registerContentScripts([{
    id: AUTO_SCRIPT, matches: WEB_ORIGINS, js: ['content.js'], css: ['overlay.css'], runAt: 'document_idle',
    persistAcrossSessions: true,
  }]);
  await chrome.storage.local.set({automatic});
  return {automatic};
}

let modeTransition = Promise.resolve();
function enqueueMode(action) {
  const result = modeTransition.then(action);
  modeTransition = result.catch(() => {});
  return result;
}
const pageChecks = new Map();
function checkTab(tab, action) {
  let url;
  try {url = minimizedURL(tab?.url);} catch {return Promise.reject(new Error('Trang này không hỗ trợ kiểm tra.'));}
  const key = `${tab.id}:${url}`;
  if (!pageChecks.has(key)) {
    const task = performTabCheck(tab, action).finally(() => pageChecks.delete(key));
    pageChecks.set(key, task);
  }
  return pageChecks.get(key);
}

async function performTabCheck(tab, action) {
  if (!tab) throw new Error('Không có trang đang mở để kiểm tra.');
  const url = minimizedURL(tab.url);
  try {
    const live = await chrome.tabs.sendMessage(tab.id, {action: 'PING'}).catch(() => null);
    if (live?.version !== chrome.runtime.getManifest().version) {
      await chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => {
        try {window.__scamguardInstalled?.cleanup?.();} catch {}
        delete window.__scamguardInstalled;
      }});
      await chrome.scripting.insertCSS({target: {tabId: tab.id}, files: ['overlay.css']});
      await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
    }
    return await chrome.tabs.sendMessage(tab.id, {action});
  } catch (error) {
    await showScanStatus(tab.id, url, {error: true});
    throw error;
  }
}

async function checkActiveTab(action) {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  return checkTab(tab, action);
}

async function setMode(automatic) {
  const settings = await enqueueMode(() => applyMode(automatic));
  // Registration affects future documents. Explicitly check the page that is
  // already open; do not keep the mode-transition queue waiting for inference.
  if (automatic) checkActiveTab('AUTO_PAGE').catch(() => {});
  return settings;
}

async function showScanStatus(tabId, url, data) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (minimizedURL(tab.url) !== url) return; // A late result belongs to the previous page.
    const score = data.riskScore ?? data.risk_score;
    const failed = data.error || !Number.isFinite(score) || score < 0 || score > 100;
    await Promise.all([
      chrome.action.setBadgeText({tabId, text: failed ? '!' : String(Math.round(score))}),
      chrome.action.setBadgeBackgroundColor({tabId, color: failed ? '#78716C' : score >= 80 ? '#DC2626' : score >= 30 ? '#D97706' : '#52525B'}),
      chrome.action.setTitle({tabId, title: (failed ? 'ScamGuard: chưa kiểm tra được. Hãy kiểm tra quyền extension và dịch vụ local.'
        : `ScamGuard: đã kiểm tra — ${Math.round(score)}/100. Kết quả không bảo đảm an toàn.`) + `\n${url}`}),
    ]);
  } catch { /* The tab may have closed or lost its temporary permission. */ }
}

async function handleMessage(message, sender) {
  if (sender.id !== chrome.runtime.id) throw new Error('Invalid sender');
  if (message.action === 'ANALYZE_URL') {
    if (!sender.tab || minimizedURL(sender.url) !== message.url) throw new Error('URL does not match sender');
    try {
      const response = await fetch('http://localhost:3000/api/analyze', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'omit', cache: 'no-store',
        body: JSON.stringify({url: message.url}), signal: AbortSignal.timeout(20000),
      });
      if (!response.ok) throw new Error(`Dịch vụ local trả lỗi ${response.status}.`);
      const data = await response.json();
      await showScanStatus(sender.tab.id, message.url, data);
      return data;
    } catch (error) {
      await showScanStatus(sender.tab.id, message.url, {error: true});
      throw error;
    }
  }
  if (sender.url !== chrome.runtime.getURL('popup.html')) throw new Error('Settings require extension popup');
  if (message.action === 'GET_SETTINGS') {
    const settings = await chrome.storage.local.get({automatic: false});
    if (settings.automatic) {
      const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
      try {minimizedURL(tab?.url);} catch {return {...settings, unsupportedPage: true};}
      if (message.ensure === true) checkTab(tab, 'AUTO_PAGE').catch(() => {});
    }
    return settings;
  }
  if (message.action === 'SET_MODE' && typeof message.automatic === 'boolean') return setMode(message.automatic);
  if (message.action === 'CHECK_ACTIVE_TAB') {
    return checkActiveTab('CHECK_PAGE');
  }
  throw new Error('Unsupported action');
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  handleMessage(message, sender).then(respond, error => respond({error: error.message}));
  return true;
});

async function restoreMode() {
  const settings = await enqueueMode(async () => {
    const {automatic = false} = await chrome.storage.local.get('automatic');
    return applyMode(automatic).catch(() => applyMode(false));
  });
  if (settings.automatic) checkActiveTab('AUTO_PAGE').catch(() => {});
  return settings;
}
chrome.runtime.onInstalled.addListener(restoreMode);
chrome.runtime.onStartup.addListener(restoreMode);
chrome.permissions.onRemoved.addListener(restoreMode);
chrome.tabs.onUpdated.addListener(async (tabId, change) => {
  if (!change.url && change.status !== 'complete') return;
  if (change.url) {
    try {
      const previous = await chrome.action.getTitle({tabId});
      if (!previous.endsWith('\n' + minimizedURL(change.url))) {
        await chrome.action.setBadgeText({tabId, text: ''});
      }
    } catch { await chrome.action.setBadgeText({tabId, text: ''}).catch(() => {}); }
  }
  const {automatic = false} = await chrome.storage.local.get('automatic');
  if (automatic) chrome.tabs.get(tabId).then(tab => checkTab(tab, 'AUTO_PAGE')).catch(() => {});
});
chrome.tabs.onActivated.addListener(async ({tabId}) => {
  const {automatic = false} = await chrome.storage.local.get('automatic');
  if (automatic) chrome.tabs.get(tabId).then(tab => checkTab(tab, 'AUTO_PAGE')).catch(() => {});
});
