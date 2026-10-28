import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const tools = path.resolve(process.env.AUDIT_NODE_TOOLS ?? '.local-runtime/audit/node-tools');
const {chromium} = await import(pathToFileURL(path.join(tools, 'node_modules/playwright/index.mjs')));
const output = process.env.AUDIT_OUTPUT ?? '.local-runtime/extension-v200';
await fs.mkdir(output, {recursive: true});
const extension = await fs.mkdtemp(path.resolve('.local-runtime/context-extension-'));
await fs.cp('extension', extension, {recursive: true});
const apiOrigin = process.env.TEST_APP_URL ?? 'http://localhost:3000';
if (apiOrigin !== 'http://localhost:3000') {
  const file = path.join(extension, 'background.js');
  await fs.writeFile(file, (await fs.readFile(file, 'utf8')).replaceAll('http://localhost:3000/api/analyze', apiOrigin + '/api/analyze'));
}
const profile = await fs.mkdtemp(path.resolve('.local-runtime/context-profile-'));
const sourceURL = 'http://localhost:3115/inbox?PRIVATE_SENTINEL=1#secret';
const server = http.createServer((request, response) => {
  response.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'});
  response.end('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Owned context fixture</title><body><h1>Owned messages</h1><p>PRIVATE_BODY_SENTINEL</p><a id="link" href="https://qi.lv/F0i?private=1#secret">Link trong tin nhắn</a><p id="message">Hello, are you free for lunch tomorrow?</p></body></html>');
});
await new Promise(resolve => server.listen(3115, '127.0.0.1', resolve));
const evidence = {status: 'FAIL', apiOrigin, requests: [], destinationRequests: [], errors: [],
  nativeMenuSelectionAutomated: false,
  fixture: 'Native menu registration covered by unit tests; invoke its registered worker handler with owned click data. Real Chrome result windows and local API; no private profile.'};
let context;
try {
  context = await chromium.launchPersistentContext(profile, {channel: 'chromium', headless: true,
    viewport: {width: 420, height: 640}, args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]});
  const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  const id = new URL(worker.url()).host;
  assert.equal(id, 'lamffehgecaabedhleppfmgjcagamlih');
  context.on('page', page => page.on('pageerror', error => evidence.errors.push(error.message)));
  context.on('request', request => {
    if (request.url() === apiOrigin + '/api/analyze' && request.method() === 'POST') evidence.requests.push(JSON.parse(request.postData()));
  });
  await context.route('https://**/*', route => {evidence.destinationRequests.push(route.request().url()); return route.abort();});
  const page = await context.newPage();
  await page.goto(sourceURL, {waitUntil: 'networkidle'});
  evidence.registeredMenuIds = await worker.evaluate(async () => {
    const ids = ['scamguard-root', 'scamguard-link', 'scamguard-selection'];
    for (const id of ids) await chrome.contextMenus.update(id, {enabled: true});
    return ids;
  });
  const grants = await worker.evaluate(() => chrome.permissions.getAll());
  assert.ok(!grants.origins.some(origin => origin === 'http://*/*' || origin === 'https://*/*'));
  assert.deepEqual(await worker.evaluate(() => chrome.scripting.getRegisteredContentScripts()), []);
  assert.equal((await worker.evaluate(() => chrome.storage.local.get('automatic'))).automatic, false);
  await page.evaluate(() => {const a = document.createElement('a'); a.href = 'https://new-link.example/'; a.textContent = 'New message link'; document.body.append(a);});
  await page.locator('#link').click({button: 'right'});
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1000);
  assert.equal(evidence.requests.length, 0, 'Load, mutations and right-click alone must not analyze anything');
  const tab = (await worker.evaluate(() => chrome.tabs.query({}))).find(tab => tab.url === sourceURL);
  assert.ok(tab);

  async function menu(info) {
    const opened = context.waitForEvent('page');
    const completed = worker.evaluate(({info, tab}) => handleMenuClick(info, tab), {info: {...info, pageUrl: sourceURL}, tab});
    const view = await opened;
    await view.waitForURL('**/popup.html?check=*');
    const job = await completed;
    await view.waitForFunction(status => document.getElementById('status').textContent.includes(status),
      job.status === 'done' ? 'Đã kiểm tra' : 'Chưa kiểm tra');
    return {view, job};
  }
  const high = await menu({menuItemId: 'scamguard-link', linkUrl: 'https://qi.lv/F0i?private=1#secret'});
  assert.equal(high.job.score, 94); assert.equal(high.job.level, 'HIGH');
  assert.equal(await high.view.locator('#score').innerText(), '94/100');
  assert.equal(await high.view.locator('#target').innerText(), 'https://qi.lv/F0i');
  await high.view.screenshot({path: path.join(output, 'right-click-link.png')});
  await high.view.locator('#close').focus();
  const closed = high.view.waitForEvent('close');
  await high.view.keyboard.press('Enter').catch(error => {if (!high.view.isClosed()) throw error;});
  await closed;

  const low = await menu({menuItemId: 'scamguard-link', linkUrl: 'https://www.facebook.com/'});
  assert.equal(low.job.score, 1); assert.equal(low.job.level, 'LOW');
  assert.equal(await low.view.locator('#level').innerText(), 'Rủi ro thấp');
  await low.view.close();

  const selectedText = await page.locator('#message').innerText();
  const message = await menu({menuItemId: 'scamguard-selection', selectionText: selectedText});
  assert.ok(message.job.score < 30); assert.equal(message.job.kind, 'message');
  assert.deepEqual(evidence.requests.at(-1), {text: selectedText, language: 'vi'});
  await message.view.screenshot({path: path.join(output, 'selected-message.png')});
  const memory = await worker.evaluate(() => chrome.storage.session.get(null));
  assert.ok(!JSON.stringify(memory).includes(selectedText));
  await message.view.close();

  const mixedText = selectedText + ' https://qi.lv/F0i';
  const mixedResponse = context.waitForEvent('response', {predicate: response => response.url() === apiOrigin + '/api/analyze'
    && response.request().method() === 'POST' && JSON.parse(response.request().postData()).text === mixedText});
  const mixed = await menu({menuItemId: 'scamguard-selection', selectionText: mixedText});
  const baseline = await (await mixedResponse).json();
  // Literal URLs produce a URL placeholder in the SMS input. Preserve that
  // actual text-head score rather than assuming it equals a URL-free message.
  assert.equal(mixed.job.score, Math.round(baseline.ml_classifier.text_result.score * 100));
  assert.equal(mixed.job.level, baseline.riskLevel); assert.equal(mixed.job.urlScore, 94);
  assert.match(await mixed.view.locator('#url-note').innerText(), /94\/100/);
  await mixed.view.close();

  const popup = await context.newPage();
  await popup.goto(`chrome-extension://${id}/popup.html`);
  assert.match(await popup.locator('#version').innerText(), /2\.0\.0/);
  assert.equal(await popup.locator('input[name="mode"]').count(), 0);
  const beforePopup = evidence.requests.length;
  const denied = await popup.evaluate(() => chrome.runtime.sendMessage({action: 'ANALYZE_LINKS', urls: ['https://forged.example/']}));
  assert.ok(denied.error); assert.equal(evidence.requests.length, beforePopup);
  await popup.evaluate(async tabId => {await chrome.tabs.update(tabId, {active: true}); document.getElementById('check').click();}, tab.id);
  await popup.waitForFunction(() => document.getElementById('kind').textContent.includes('Trang bạn yêu cầu')
    && /\/100$/.test(document.getElementById('score').textContent), null, {timeout: 25000});
  assert.deepEqual(evidence.requests.at(-1), {url: 'http://localhost:3115/inbox', language: 'vi'});
  await popup.screenshot({path: path.join(output, 'manual-popup.png')});

  await context.route(apiOrigin + '/api/analyze', route => route.fulfill({status: 503, json: {error: 'Owned outage fixture'}}));
  const failed = await menu({menuItemId: 'scamguard-link', linkUrl: 'https://unavailable.example/'});
  assert.equal(failed.job.status, 'error'); assert.equal(await failed.view.locator('#score').innerText(), '');
  assert.equal(await failed.view.locator('#level').innerText(), '');
  await failed.view.close();
  assert.equal(await page.locator('[data-scamguard-risk]').count(), 0);
  assert.ok(evidence.requests.every(body => !JSON.stringify(body).includes('PRIVATE_BODY_SENTINEL') && !JSON.stringify(body).includes('PRIVATE_SENTINEL')));
  assert.deepEqual(evidence.destinationRequests, []); assert.deepEqual(evidence.errors, []);
  evidence.checks = ['no automatic scan', 'native-handler link flow', 'real high/low scores', 'selected text only',
    'independent URL warning', 'separate result windows', 'keyboard close', 'manual current page', 'rejected legacy messages',
    'outage without safe score', 'no stored message text', 'no destination fetch', 'no page outlines'];
  evidence.status = 'PASS';
} catch (error) {
  evidence.error = error.stack; process.exitCode = 1;
} finally {
  if (context) await context.close();
  await new Promise(resolve => server.close(resolve));
  await fs.writeFile(path.join(output, 'context-browser.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
}
