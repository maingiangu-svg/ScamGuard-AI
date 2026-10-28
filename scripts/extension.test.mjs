import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

const source = readFileSync(new URL('../extension/background.js', import.meta.url), 'utf8');
const manifest = JSON.parse(readFileSync(new URL('../extension/manifest.json', import.meta.url), 'utf8'));
const senderURL = 'https://chat.example/inbox?private=1';
const linkInfo = {menuItemId: 'scamguard-link', pageUrl: senderURL, linkUrl: 'https://example.com/shared?token=private#secret'};
const selectionInfo = {menuItemId: 'scamguard-selection', pageUrl: senderURL, selectionText: 'Are you free for lunch tomorrow?'};

function worker(options = {}) {
  const requests = [], windows = [], menus = [], registrations = [], listeners = {};
  const session = {}, local = {automatic: true};
  let sequence = 0, now = 1000;
  const event = name => ({addListener(callback) {listeners[name] = callback;}});
  const storage = values => ({get: async key => typeof key === 'object' ? {...key, ...values} : {[key]: structuredClone(values[key])},
    set: async value => Object.assign(values, structuredClone(value)), setAccessLevel: async () => {}});
  const id = 'lamffehgecaabedhleppfmgjcagamlih';
  const context = {URL, AbortSignal, console, Date: class extends Date {static now() {return now;}},
    crypto: {randomUUID: () => 'job-' + (++sequence)}, setTimeout,
    chrome: {runtime: {id, getURL: file => `chrome-extension://${id}/${file}`,
      getManifest: () => manifest, onInstalled: event('installed'), onStartup: event('startup'), onMessage: event('message')},
    storage: {local: storage(local), session: storage(session)},
    contextMenus: {removeAll: async () => {menus.length = 0;}, create: (value, callback) => {menus.push(value); callback?.(); return value.id;},
      onClicked: event('context')},
    scripting: {unregisterContentScripts: async value => registrations.push(value)},
    action: {setBadgeText: async () => {}},
    tabs: {query: async () => [{id: 1, url: options.tabURL ?? senderURL}], onUpdated: event('updated'), onActivated: event('activated')},
    windows: {create: async value => {windows.push(value); return {id: windows.length};}}},
    fetch: async (url, request) => {
      const body = JSON.parse(request.body); requests.push({url, body, credentials: request.credentials, cache: request.cache});
      if (options.fetch) return options.fetch(body);
      return {ok: options.status === undefined || options.status === 200, status: options.status ?? 200,
        json: async () => options.result ?? {riskScore: 12, riskLevel: 'LOW', summary: 'Owned test result', ml_classifier: {model_ready: true}}};
    }};
  vm.runInNewContext(source, context);
  const ui = {id, url: `chrome-extension://${id}/popup.html`};
  const send = (message, sender = ui) => new Promise(resolve => listeners.message(message, sender, resolve));
  const menu = info => listeners.context(info, {id: 1, url: senderURL});
  return {requests, windows, menus, registrations, listeners, session, local, ui, send, menu,
    initialize: () => listeners.installed(), advance: ms => {now += ms;}};
}

test('manifest adds context menus and removes broad optional access and content scripts', () => {
  assert.ok(manifest.permissions.includes('contextMenus'));
  assert.ok(manifest.permissions.includes('activeTab'));
  assert.deepEqual(manifest.host_permissions, ['http://localhost/*']);
  assert.equal(manifest.optional_host_permissions, undefined);
  assert.equal(manifest.content_scripts, undefined);
});

test('install migrates automatic mode off and unregisters the old scanner without analysis', async () => {
  const w = worker(); await w.initialize();
  assert.equal(w.local.automatic, false);
  assert.ok(w.registrations.some(value => value.ids.includes('scamguard-automatic')));
  assert.equal(w.requests.length, 0);
});

test('menus are limited to web link and selected-text contexts without private text in titles', async () => {
  const w = worker(); await w.initialize();
  const link = w.menus.find(value => value.id === 'scamguard-link');
  const text = w.menus.find(value => value.id === 'scamguard-selection');
  assert.deepEqual(Array.from(link.contexts), ['link']);
  assert.deepEqual(Array.from(text.contexts), ['selection']);
  assert.ok(w.menus.every(value => value.documentUrlPatterns.includes('https://*/*') && !value.title.includes('%s')));
});

test('reinitialization recreates menus without duplicates or automatic event handlers', async () => {
  const w = worker(); await w.initialize(); await w.initialize();
  assert.equal(new Set(w.menus.map(menu => menu.id)).size, w.menus.length);
  assert.equal(w.menus.length, 3);
  assert.equal(w.listeners.updated, undefined);
  assert.equal(w.listeners.activated, undefined);
  assert.equal(w.requests.length, 0);
});

test('right-click link submits only its minimized destination and opens an extension result window', async () => {
  const w = worker(); const job = await w.menu(linkInfo);
  assert.equal(job.status, 'done');
  assert.deepEqual(w.requests[0].body, {url: 'https://example.com/shared', language: 'vi'});
  assert.equal(w.requests[0].url, 'http://localhost:3000/api/analyze');
  assert.equal(w.requests[0].credentials, 'omit'); assert.equal(w.requests[0].cache, 'no-store');
  assert.match(w.windows[0].url, /^chrome-extension:\/\/lamffehgecaabedhleppfmgjcagamlih\/popup.html\?check=/);
  assert.equal(w.windows[0].type, 'popup');
});

test('recognized redirect wrappers are decoded locally before stripping private URL parts', async () => {
  for (const linkUrl of ['https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.com%2Flogin%3Fsecret%3D1',
    'https://www.google.com/url?q=https%3A%2F%2Fexample.com%2Flogin',
    'https://www.youtube.com/redirect?q=https%3A%2F%2Fexample.com%2Flogin']) {
    const w = worker(); await w.menu({...linkInfo, linkUrl});
    assert.equal(w.requests[0].body.url, 'https://example.com/login');
  }
});

test('credentials are removed from link checks', async () => {
  const w = worker(); await w.menu({...linkInfo, linkUrl: 'https://user:password@example.com/path?secret=1#private'});
  assert.equal(w.requests[0].body.url, 'https://example.com/path');
});

test('lookalike wrapper hosts are checked themselves instead of a forged target', async () => {
  const w = worker(); await w.menu({...linkInfo, linkUrl: 'https://l.facebook.com.evil.example/l.php?u=https://good.example/'});
  assert.equal(w.requests[0].body.url, 'https://l.facebook.com.evil.example/l.php');
});

test('selected message is submitted exactly, without collecting surrounding page content', async () => {
  const w = worker(); await w.menu({...selectionInfo, selectionText: '  Đoạn tin nhắn được chọn\nhttps://example.com/?selected=1  '});
  assert.deepEqual(w.requests[0].body, {text: '  Đoạn tin nhắn được chọn\nhttps://example.com/?selected=1  ', language: 'vi'});
});

test('empty selected text never produces a request or a safe verdict', async () => {
  const w = worker(); const job = await w.menu({...selectionInfo, selectionText: ' \n '});
  assert.equal(job.status, 'error'); assert.equal(job.score, undefined); assert.equal(w.requests.length, 0);
});

test('oversized selections are rejected rather than silently truncated', async () => {
  const w = worker(); const job = await w.menu({...selectionInfo, selectionText: 'a'.repeat(20001)});
  assert.equal(job.status, 'error'); assert.equal(w.requests.length, 0);
});

test('missing or non-string selected text is rejected', async () => {
  for (const selectionText of [undefined, 12, {}]) {
    const w = worker(); assert.equal((await w.menu({...selectionInfo, selectionText})).status, 'error');
    assert.equal(w.requests.length, 0);
  }
});

test('non-web link protocols cannot initiate classification', async () => {
  for (const linkUrl of ['javascript:alert(1)', 'file:///private', 'mailto:private@example.com', 'data:text/html,private']) {
    const w = worker(); assert.equal((await w.menu({...linkInfo, linkUrl})).status, 'error');
    assert.equal(w.requests.length, 0);
  }
});

test('malformed, oversized or invalid wrapped URLs cannot become low-risk results', async () => {
  for (const linkUrl of ['https://', 'https://example.com/' + 'x'.repeat(4096),
    'https://l.facebook.com/l.php?u=javascript%3Aalert(1)', 'https://l.facebook.com/l.php']) {
    const w = worker(); assert.equal((await w.menu({...linkInfo, linkUrl})).status, 'error');
    assert.equal(w.requests.length, 0);
  }
});

test('context actions on restricted browser documents are rejected', async () => {
  const w = worker(); assert.equal((await w.menu({...linkInfo, pageUrl: 'chrome://settings'})).status, 'error');
  assert.equal(w.requests.length, 0);
});

test('unknown native menu IDs do not trigger any action', async () => {
  const w = worker(); await w.menu({...linkInfo, menuItemId: 'forged'});
  assert.equal(w.requests.length, 0); assert.equal(w.windows.length, 0);
});

test('toolbar button checks the browser-provided active URL without content injection', async () => {
  const w = worker(); const job = await w.send({action: 'CHECK_ACTIVE_TAB'});
  assert.equal(job.status, 'done'); assert.equal(w.requests[0].body.url, 'https://chat.example/inbox');
  assert.equal(w.windows.length, 0);
});

test('popup cannot override the active URL with an arbitrary message field', async () => {
  const w = worker(); await w.send({action: 'CHECK_ACTIVE_TAB', url: 'https://forged.example/'});
  assert.equal(w.requests[0].body.url, 'https://chat.example/inbox');
});

test('non-web active tabs return an error instead of calling the model', async () => {
  const w = worker({tabURL: 'edge://extensions'}); assert.equal((await w.send({action: 'CHECK_ACTIVE_TAB'})).status, 'error');
  assert.equal(w.requests.length, 0);
});

test('ordinary pages cannot request analysis or inspect private result summaries', async () => {
  const w = worker();
  for (const action of ['CHECK_ACTIVE_TAB', 'GET_RESULT']) assert.ok((await w.send({action}, {id: w.ui.id, url: senderURL, tab: {id: 1}})).error);
  assert.equal(w.requests.length, 0);
});

test('foreign extension IDs and popup lookalike paths are rejected', async () => {
  const w = worker();
  for (const sender of [{id: 'foreign', url: w.ui.url}, {...w.ui, url: w.ui.url + '/forged'}]) {
    assert.ok((await w.send({action: 'CHECK_ACTIVE_TAB'}, sender)).error);
  }
  assert.equal(w.requests.length, 0);
});

test('legacy scanning and forged context commands cannot start analysis through messaging', async () => {
  const w = worker();
  for (const action of ['ANALYZE_URL', 'ANALYZE_LINK', 'ANALYZE_LINKS', 'SET_MODE', 'CHECK_SELECTION', 'CONTEXT_MENU']) {
    assert.ok((await w.send({action, automatic: true, url: 'https://example.com/', text: 'private'})).error);
  }
  assert.equal(w.requests.length, 0);
});

test('HTTP failure never produces a score', async () => {
  const w = worker({status: 503}); const job = await w.menu(linkInfo);
  assert.equal(job.status, 'error'); assert.equal(job.score, undefined);
});

test('network and malformed JSON failures leave an explicit error result', async () => {
  for (const fetch of [async () => {throw new Error('offline');}, async () => ({ok: true, json: async () => {throw new Error('bad JSON');}})]) {
    const w = worker({fetch}); assert.equal((await w.menu(linkInfo)).status, 'error');
  }
});

test('an unavailable or missing model cannot be presented as low risk', async () => {
  for (const result of [{model_ready: false}, {riskScore: 0, riskLevel: 'LOW', ml_classifier: {model_ready: false}},
    {riskScore: 0, riskLevel: 'LOW'}]) {
    const w = worker({result}); assert.equal((await w.menu(linkInfo)).status, 'error');
  }
});

test('invalid scores and unknown risk levels never enter a successful result', async () => {
  for (const [riskScore, riskLevel] of [[-1, 'LOW'], [101, 'LOW'], [NaN, 'LOW'], ['0', 'LOW'], [0, 'SAFE']]) {
    const w = worker({result: {riskScore, riskLevel, ml_classifier: {model_ready: true}}});
    assert.equal((await w.menu(linkInfo)).status, 'error');
  }
});

test('low, review and high scores are preserved without forced whitelist values', async () => {
  for (const [riskScore, riskLevel] of [[1, 'LOW'], [59, 'MEDIUM'], [94, 'HIGH']]) {
    const w = worker({result: {riskScore, riskLevel, ml_classifier: {model_ready: true}}});
    const job = await w.menu(linkInfo); assert.equal(job.score, riskScore); assert.equal(job.level, riskLevel);
  }
});

test('risky embedded URL stays visible without inflating a low message score', async () => {
  const w = worker({result: {riskScore: 2, riskLevel: 'MEDIUM', summary: 'Independent URL review',
    ml_classifier: {model_ready: true, url_review_required: true, url_score: 94}}});
  const job = await w.menu(selectionInfo);
  assert.equal(job.score, 2); assert.equal(job.level, 'MEDIUM'); assert.equal(job.urlScore, 94);
});

test('raw selected messages are not stored in session or local storage or result URLs', async () => {
  const w = worker(); const privateText = 'PRIVATE_MESSAGE_SENTINEL_123';
  await w.menu({...selectionInfo, selectionText: privateText});
  assert.ok(!JSON.stringify({session: w.session, local: w.local, windows: w.windows}).includes(privateText));
});

test('result IDs preserve independent checks when responses arrive out of order', async () => {
  let release;
  const held = new Promise(resolve => {release = resolve;});
  const w = worker({fetch: async body => {
    if (body.url) await held;
    return {ok: true, json: async () => ({riskScore: body.url ? 94 : 2, riskLevel: body.url ? 'HIGH' : 'LOW', ml_classifier: {model_ready: true}})};
  }});
  const first = w.menu(linkInfo);
  await new Promise(resolve => setImmediate(resolve));
  const second = await w.menu(selectionInfo); release(); const old = await first;
  assert.notEqual(old.id, second.id);
  assert.equal((await w.send({action: 'GET_RESULT', id: old.id})).score, 94);
  assert.equal((await w.send({action: 'GET_RESULT', id: second.id})).score, 2);
});

test('stored summaries are bounded and expired results are unavailable', async () => {
  const w = worker(); const first = await w.menu(linkInfo);
  for (let index = 0; index < 12; index++) await w.menu(linkInfo);
  assert.ok(Object.keys(w.session.checks ?? {}).length <= 10);
  w.advance(600001);
  assert.equal(await w.send({action: 'GET_RESULT', id: first.id}), null);
});
