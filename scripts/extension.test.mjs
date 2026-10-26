import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

const content = readFileSync(new URL('../extension/content.js', import.meta.url), 'utf8');
const background = readFileSync(new URL('../extension/background.js', import.meta.url), 'utf8');

async function inspectPage(href, verdict = {riskScore: 95, riskLevel: 'HIGH'}) {
  const calls = [], banners = [];
  let contentListener;
  const pageWindow = {location: {href}};
  const document = {
    title: 'Welcome — private title', readyState: 'complete',
    getElementById: () => null,
    createElement: () => ({appendChild() {}, addEventListener() {}}),
    body: {prepend: banner => banners.push(banner)},
  };
  vm.runInNewContext(content, {
    document, window: pageWindow, URL, AbortController,
    setTimeout: () => 1, clearTimeout() {}, console: {warn() {}},
    chrome: {storage: {local: {get: async () => ({automatic: true})}}, runtime: {
      getManifest: () => ({version: '1.1.2'}),
      onMessage: {addListener: listener => {contentListener = listener;}},
      sendMessage: async message => {calls.push({body: {url: message.url}}); return typeof verdict === 'function' ? verdict() : verdict;},
    }},
    fetch: async (url, options) => {
      calls.push({url, body: JSON.parse(options.body)});
      return {ok: true, json: async () => verdict};
    },
  });
  await new Promise(resolve => setImmediate(resolve));
  const send = action => new Promise(resolve => contentListener({action}, {}, resolve));
  return {calls, banners, send, pageWindow};
}

test('page screening uses URL-only input and excludes title, credentials, query and fragment', async () => {
  const {calls, banners} = await inspectPage('https://user:password@evil.example/login?token=private#private');
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].body, {url: 'https://evil.example/login'});
  assert.equal(banners.length, 1);
});

test('a hostname beginning with the localhost exclusion still gets checked', async () => {
  assert.equal((await inspectPage('http://localhost:3000@evil.example/')).calls.length, 1);
  assert.equal((await inspectPage('http://localhost:30000/')).calls.length, 1);
});

test('the actual local app and non-web protocols are excluded', async () => {
  for (const url of ['http://localhost:3000/path', 'chrome://settings', 'about:blank', 'file:///private']) {
    assert.equal((await inspectPage(url)).calls.length, 0);
  }
});

test('low-risk and unavailable responses never create a high-risk banner', async () => {
  for (const result of [{riskScore: 10, riskLevel: 'LOW'}, {model_ready: false}]) {
    assert.equal((await inspectPage('https://example.com/', result)).banners.length, 0);
  }
});

test('automatic rechecks of the same URL are deduplicated; manual refresh still runs', async () => {
  const page = await inspectPage('https://example.com/', {riskScore: 12, riskLevel: 'LOW'});
  await page.send('AUTO_PAGE');
  await page.send('AUTO_PAGE');
  assert.equal(page.calls.length, 1);
  await page.send('CHECK_PAGE');
  assert.equal(page.calls.length, 2);
});

test('a late result for the previous URL cannot display a warning on the new page', async () => {
  let release;
  const waiting = new Promise(resolve => {release = resolve;});
  const page = await inspectPage('https://old.example/', () => waiting);
  page.pageWindow.location.href = 'https://new.example/';
  release({riskScore: 95, riskLevel: 'HIGH'});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(page.banners.length, 0);
});

function worker(options = {}) {
  const requests = [], registrations = [], injections = [], tabMessages = [], badges = [];
  let listener, updated, installed;
  let tabURL = 'https://evil.example/path?private=1';
  const titles = new Map();
  const id = 'lamffehgecaabedhleppfmgjcagamlih';
  const settings = {automatic: options.automatic ?? false};
  const event = {addListener() {}};
  vm.runInNewContext(background, {URL, AbortSignal, console, chrome: {
    runtime: {id, getURL: name => `chrome-extension://${id}/${name}`,
      getManifest: () => ({version: '1.1.2'}),
      onMessage: {addListener: callback => {listener = callback;}}, onInstalled: {addListener: callback => {installed = callback;}}, onStartup: event},
    storage: {local: {get: async () => settings, set: async value => Object.assign(settings, value)}},
    permissions: {contains: async () => true, onRemoved: event},
    action: {setBadgeText: async value => badges.push(value), setBadgeBackgroundColor: async () => {},
      setTitle: async value => titles.set(value.tabId, value.title), getTitle: async value => titles.get(value.tabId) ?? '',
      getBadgeText: async value => badges.findLast(badge => badge.tabId === value.tabId)?.text ?? ''},
    scripting: {insertCSS: async () => {}, executeScript: async value => {
      injections.push(value); if (options.executeScript) await options.executeScript(value);
    },
      unregisterContentScripts: async () => {}, registerContentScripts: async value => {
      registrations.push(value);
      if (options.register) await options.register();
    }},
    tabs: {onUpdated: {addListener: callback => {updated = callback;}}, onActivated: event,
      query: async () => [{id: 1, url: 'https://example.com/already-open?private=1'}],
      get: async () => ({id: 1, url: tabURL}),
      sendMessage: async (id, message) => {tabMessages.push({id, message});
        return message.action === 'PING' ? {version: options.liveContentVersion} : {riskScore: 12, riskLevel: 'LOW'};}},
  }, fetch: async (url, request) => {requests.push({url, body: JSON.parse(request.body)});
    return {ok: true, json: async () => options.verdict ?? ({riskScore: 95, riskLevel: 'HIGH'})};}});
  const send = (message, sender) => new Promise(resolve => listener(message, {id, ...sender}, resolve));
  const navigate = async url => {tabURL = url; await updated(1, {url});};
  return {requests, registrations, settings, injections, tabMessages, badges, send, navigate, restore: () => installed(),
    popup: {url: `chrome-extension://${id}/popup.html`}};
}

test('worker accepts only a minimized URL matching its browser-provided sender', async () => {
  const w = worker();
  const sender = {url: 'https://evil.example/path?private=1', tab: {id: 1, url: 'https://evil.example/path?private=1'}};
  assert.ok((await w.send({action: 'ANALYZE_URL', url: 'https://other.example/'}, sender)).error);
  assert.equal(w.requests.length, 0);
  assert.equal((await w.send({action: 'ANALYZE_URL', url: 'https://evil.example/path'}, sender)).riskScore, 95);
  assert.deepEqual(w.requests[0].body, {url: 'https://evil.example/path'});
  assert.equal(w.requests[0].url, 'http://localhost:3000/api/analyze');
});

test('automatic mode is opt-in and pages cannot change user settings', async () => {
  const w = worker();
  assert.equal(w.settings.automatic, false);
  const forged = await w.send({action: 'SET_MODE', automatic: true}, {url: 'https://evil.example/', tab: {id: 1}});
  assert.ok(forged.error);
  assert.equal(w.settings.automatic, false);
  await w.send({action: 'SET_MODE', automatic: true}, w.popup);
  assert.equal(w.settings.automatic, true);
  assert.equal(w.registrations.length, 1);
  await w.send({action: 'SET_MODE', automatic: false}, w.popup);
  assert.equal(w.settings.automatic, false);
});

test('a delayed enable cannot overwrite a later manual-mode choice', async () => {
  let release;
  const pending = new Promise(resolve => {release = resolve;});
  const w = worker({register: () => pending});
  const enabling = w.send({action: 'SET_MODE', automatic: true}, w.popup);
  await new Promise(resolve => setImmediate(resolve));
  const disabling = w.send({action: 'SET_MODE', automatic: false}, w.popup);
  release();
  await Promise.all([enabling, disabling]);
  assert.equal(w.settings.automatic, false);
});

test('enabling automatic mode checks the already-open active page without a manual click', async () => {
  const w = worker();
  const result = await w.send({action: 'SET_MODE', automatic: true}, w.popup);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(result.automatic, true);
  assert.equal(w.injections.filter(item => item.files?.includes('content.js')).length, 1);
  assert.equal(w.tabMessages.at(-1).message.action, 'AUTO_PAGE');
});

test('restoring an already-enabled extension checks the current page without toggling the radio', async () => {
  const w = worker({automatic: true});
  await w.restore();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(w.settings.automatic, true);
  assert.equal(w.tabMessages.at(-1)?.message.action, 'AUTO_PAGE');
});

test('opening automatic popup with no result repairs missing injection', async () => {
  const w = worker({automatic: true});
  await w.send({action: 'GET_SETTINGS', ensure: true}, w.popup);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(w.injections.filter(item => item.files?.includes('content.js')).length, 1);
});

test('overlapping automatic requests initialize a page only once', async () => {
  let release;
  const waiting = new Promise(resolve => {release = resolve;});
  const w = worker({automatic: true, executeScript: () => waiting});
  const first = w.send({action: 'GET_SETTINGS', ensure: true}, w.popup);
  const second = w.send({action: 'GET_SETTINGS', ensure: true}, w.popup);
  await new Promise(resolve => setImmediate(resolve));
  try {assert.equal(w.injections.length, 1);} finally {release();}
  await Promise.all([first, second]);
});

test('a completed low-score scan is visible in the extension badge', async () => {
  const w = worker({verdict: {riskScore: 12, riskLevel: 'LOW'}});
  await w.send({action: 'ANALYZE_URL', url: 'https://evil.example/path'},
    {url: 'https://evil.example/path?private=1', tab: {id: 1}});
  assert.equal(w.badges.length, 1);
  assert.equal(w.badges[0].tabId, 1);
  assert.equal(w.badges[0].text, '12');
});

test('query/fragment-only navigation preserves a result for the same minimized URL', async () => {
  const w = worker({verdict: {riskScore: 12, riskLevel: 'LOW'}});
  await w.send({action: 'ANALYZE_URL', url: 'https://evil.example/path'},
    {url: 'https://evil.example/path?private=1', tab: {id: 1}});
  await w.navigate('https://evil.example/path?private=2#new');
  assert.equal(w.badges.at(-1).text, '12');
  await w.navigate('https://evil.example/different');
  assert.equal(w.badges.at(-1).text, '');
});
