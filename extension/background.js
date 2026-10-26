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
function setMode(automatic) { return enqueueMode(() => applyMode(automatic)); }

async function handleMessage(message, sender) {
  if (sender.id !== chrome.runtime.id) throw new Error('Invalid sender');
  if (message.action === 'ANALYZE_URL') {
    if (!sender.tab || minimizedURL(sender.url) !== message.url) throw new Error('URL does not match sender');
    const response = await fetch('http://localhost:3000/api/analyze', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'omit', cache: 'no-store',
      body: JSON.stringify({url: message.url}), signal: AbortSignal.timeout(20000),
    });
    if (!response.ok) throw new Error(`Dịch vụ local trả lỗi ${response.status}.`);
    return response.json();
  }
  if (sender.url !== chrome.runtime.getURL('popup.html')) throw new Error('Settings require extension popup');
  if (message.action === 'GET_SETTINGS') return chrome.storage.local.get({automatic: false});
  if (message.action === 'SET_MODE' && typeof message.automatic === 'boolean') return setMode(message.automatic);
  if (message.action === 'CHECK_ACTIVE_TAB') {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    minimizedURL(tab.url);
    await chrome.scripting.insertCSS({target: {tabId: tab.id}, files: ['overlay.css']});
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['content.js']});
    return chrome.tabs.sendMessage(tab.id, {action: 'CHECK_PAGE'});
  }
  throw new Error('Unsupported action');
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  handleMessage(message, sender).then(respond, error => respond({error: error.message}));
  return true;
});

async function restoreMode() {
  return enqueueMode(async () => {
    const {automatic = false} = await chrome.storage.local.get('automatic');
    await applyMode(automatic).catch(() => applyMode(false));
  });
}
chrome.runtime.onInstalled.addListener(restoreMode);
chrome.runtime.onStartup.addListener(restoreMode);
chrome.permissions.onRemoved.addListener(restoreMode);
chrome.tabs.onUpdated.addListener(async (tabId, change) => {
  if (!change.url) return;
  const {automatic = false} = await chrome.storage.local.get('automatic');
  if (automatic) chrome.tabs.sendMessage(tabId, {action: 'AUTO_PAGE'}).catch(() => {});
});
