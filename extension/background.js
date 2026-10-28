const WEB_ORIGINS = ['http://*/*', 'https://*/*'];
let writes = Promise.resolve();

function minimizedURL(value) {
  if (typeof value !== 'string' || value.length > 4096) throw new Error('Liên kết không hợp lệ hoặc quá dài.');
  let url = new URL(value);
  for (let depth = 0; depth < 4; depth++) {
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Chỉ hỗ trợ liên kết HTTP/HTTPS.');
    const facebook = /(^|\.)facebook\.com$/.test(url.hostname) && url.pathname === '/l.php';
    const google = /(^|\.)google\.com$/.test(url.hostname) && url.pathname === '/url';
    const youtube = /(^|\.)youtube\.com$/.test(url.hostname) && url.pathname === '/redirect';
    if (!facebook && !google && !youtube) {
      url.username = url.password = url.search = url.hash = '';
      return url.href;
    }
    const target = url.searchParams.get(facebook ? 'u' : 'q') || (google && url.searchParams.get('url'));
    if (!target || !/^https?:\/\//i.test(target)) throw new Error('Không đọc được đích chuyển tiếp của link.');
    url = new URL(target);
  }
  throw new Error('Liên kết có quá nhiều lớp chuyển tiếp.');
}

function saveResult(job, latest = false) {
  const task = writes.then(async () => {
    const state = await chrome.storage.session.get({checks: {}, lastCheckId: null});
    const checks = {...state.checks, [job.id]: job};
    const retained = Object.values(checks).filter(item => item.expires > Date.now())
      .sort((a, b) => a.created - b.created).slice(-10);
    await chrome.storage.session.set({checks: Object.fromEntries(retained.map(item => [item.id, item])),
      lastCheckId: latest ? job.id : state.lastCheckId});
  });
  writes = task.catch(() => {});
  return task;
}

async function getResult(id) {
  await writes;
  const state = await chrome.storage.session.get({checks: {}, lastCheckId: null});
  const job = state.checks[id ?? state.lastCheckId];
  return job?.expires > Date.now() ? job : null;
}

async function runCheck(kind, input, openWindow = false) {
  let job = {id: crypto.randomUUID(), kind, status: 'pending', created: Date.now(), expires: Date.now() + 600000};
  await saveResult(job, true);
  if (openWindow) await chrome.windows.create({url: chrome.runtime.getURL('popup.html') + '?check=' + encodeURIComponent(job.id),
    type: 'popup', width: 440, height: 600});
  try {
    const body = await input();
    if (kind === 'message' && (typeof body.text !== 'string' || !body.text.trim() || body.text.length > 20000)) {
      throw new Error('Hãy bôi đen phần tin nhắn cần kiểm tra, tối đa 20.000 ký tự.');
    }
    if (body.url) {job.target = body.url; await saveResult(job);}
    const response = await fetch('http://localhost:3000/api/analyze', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, credentials: 'omit', cache: 'no-store',
      body: JSON.stringify({...body, language: 'vi'}), signal: AbortSignal.timeout(20000),
    });
    if (!response.ok) throw new Error('Dịch vụ local trả lỗi ' + response.status + '. Hãy kiểm tra localhost:3000 và thử lại.');
    const data = await response.json();
    if (data?.ml_classifier?.model_ready !== true || !Number.isInteger(data.riskScore) || data.riskScore < 0
      || data.riskScore > 100 || !['LOW', 'MEDIUM', 'HIGH'].includes(data.riskLevel)) {
      throw new Error('Mô hình chưa trả kết quả hợp lệ.');
    }
    const urlScore = data.ml_classifier.url_review_required ? data.ml_classifier.url_score : undefined;
    if (urlScore !== undefined && (!Number.isInteger(urlScore) || urlScore < 0 || urlScore > 100)) {
      throw new Error('Chưa có kết quả hợp lệ cho link trong tin nhắn.');
    }
    job = {...job, status: 'done', score: data.riskScore, level: data.riskLevel,
      summary: typeof data.summary === 'string' ? data.summary : '',
      ...(urlScore === undefined ? {} : {urlScore})};
  } catch (error) {
    job = {...job, status: 'error', error: error.message || 'Chưa kiểm tra được. Hãy thử lại sau.'};
  }
  await saveResult(job);
  return job;
}

async function handleMenuClick(info, tab) {
  const kind = info.menuItemId === 'scamguard-link' ? 'link'
    : info.menuItemId === 'scamguard-selection' ? 'message' : null;
  if (!kind) return;
  return runCheck(kind, () => {
    const source = new URL(info.frameUrl || info.pageUrl || tab?.url);
    if (!['http:', 'https:'].includes(source.protocol)) throw new Error('Trang này không hỗ trợ kiểm tra.');
    return kind === 'link' ? {url: minimizedURL(info.linkUrl)} : {text: info.selectionText};
  }, true);
}

async function handleMessage(message, sender) {
  let page;
  try {page = new URL(sender.url);} catch {throw new Error('Invalid sender');}
  if (sender.id !== chrome.runtime.id || page.protocol !== 'chrome-extension:' || page.host !== chrome.runtime.id
    || page.pathname !== '/popup.html') throw new Error('Chỉ giao diện ScamGuard được phép dùng thao tác này.');
  if (message.action === 'GET_RESULT') return getResult(typeof message.id === 'string' ? message.id : undefined);
  if (message.action === 'CHECK_ACTIVE_TAB') return runCheck('page', async () => {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    return {url: minimizedURL(tab?.url)};
  });
  throw new Error('Unsupported action');
}

async function initialize() {
  // Migration only: future documents must not run the old automatic scanner.
  await chrome.scripting.unregisterContentScripts({ids: ['scamguard-automatic']}).catch(() => {});
  await chrome.storage.local.set({automatic: false});
  await chrome.storage.session.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});
  await chrome.contextMenus.removeAll();
  const create = value => new Promise((resolve, reject) => {
    chrome.contextMenus.create(value, () => {
      const error = chrome.runtime.lastError;
      if (error) reject(new Error(error.message)); else resolve();
    });
  });
  await create({id: 'scamguard-root', title: 'ScamGuard AI', contexts: ['link', 'selection'], documentUrlPatterns: WEB_ORIGINS});
  await create({id: 'scamguard-link', parentId: 'scamguard-root', title: 'Kiểm tra liên kết này', contexts: ['link'],
    documentUrlPatterns: WEB_ORIGINS, targetUrlPatterns: WEB_ORIGINS});
  await create({id: 'scamguard-selection', parentId: 'scamguard-root', title: 'Kiểm tra tin nhắn đã chọn', contexts: ['selection'],
    documentUrlPatterns: WEB_ORIGINS});
  const tabs = await chrome.tabs.query({});
  await Promise.allSettled(tabs.map(tab => chrome.action.setBadgeText({tabId: tab.id, text: ''})));
}

chrome.contextMenus.onClicked.addListener(handleMenuClick);
chrome.runtime.onInstalled.addListener(initialize);
chrome.runtime.onStartup.addListener(initialize);
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  handleMessage(message, sender).then(respond, error => respond({error: error.message}));
  return true;
});
