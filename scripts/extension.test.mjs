import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {test} from 'node:test';

const content = readFileSync(new URL('../extension/content.js', import.meta.url), 'utf8');
const background = readFileSync(new URL('../extension/background.js', import.meta.url), 'utf8');

async function inspectPage(href, verdict = {riskScore: 95, riskLevel: 'HIGH'}) {
  const calls = [], banners = [];
  const document = {
    title: 'Welcome — private title', readyState: 'complete',
    getElementById: () => null,
    createElement: () => ({appendChild() {}, addEventListener() {}}),
    body: {prepend: banner => banners.push(banner)},
  };
  vm.runInNewContext(content, {
    document, window: {location: {href}}, URL, AbortController,
    setTimeout: () => 1, clearTimeout() {}, console: {warn() {}},
    chrome: {storage: {local: {get: async () => ({automatic: true})}}, runtime: {
      onMessage: {addListener() {}},
      sendMessage: async message => {calls.push({body: {url: message.url}}); return verdict;},
    }},
    fetch: async (url, options) => {
      calls.push({url, body: JSON.parse(options.body)});
      return {ok: true, json: async () => verdict};
    },
  });
  await new Promise(resolve => setImmediate(resolve));
  return {calls, banners};
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

function worker(options = {}) {
  const requests = [], registrations = [];
  let listener;
  const id = 'lamffehgecaabedhleppfmgjcagamlih';
  const settings = {automatic: false};
  const event = {addListener() {}};
  vm.runInNewContext(background, {URL, AbortSignal, console, chrome: {
    runtime: {id, getURL: name => `chrome-extension://${id}/${name}`,
      onMessage: {addListener: callback => {listener = callback;}}, onInstalled: event, onStartup: event},
    storage: {local: {get: async () => settings, set: async value => Object.assign(settings, value)}},
    permissions: {contains: async () => true, onRemoved: event},
    scripting: {unregisterContentScripts: async () => {}, registerContentScripts: async value => {
      registrations.push(value);
      if (options.register) await options.register();
    }},
    tabs: {onUpdated: event},
  }, fetch: async (url, options) => {requests.push({url, body: JSON.parse(options.body)});
    return {ok: true, json: async () => ({riskScore: 95, riskLevel: 'HIGH'})};}});
  const send = (message, sender) => new Promise(resolve => listener(message, {id, ...sender}, resolve));
  return {requests, registrations, settings, send, popup: {url: `chrome-extension://${id}/popup.html`}};
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
