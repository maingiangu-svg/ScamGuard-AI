import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const tools = path.resolve(process.env.AUDIT_NODE_TOOLS ?? '.local-runtime/audit/node-tools');
const {chromium} = await import(pathToFileURL(path.join(tools, 'node_modules/playwright/index.mjs')));
const output = process.env.AUDIT_OUTPUT ?? 'docs/readiness-evidence/2026-10-26';
await fs.mkdir('.local-runtime/readiness', {recursive: true});
await fs.mkdir(output, {recursive: true});
const profile = await fs.mkdtemp(path.resolve('.local-runtime/readiness/extension-profile-'));
const extension = path.resolve('extension');
const server = http.createServer((request, response) => {
  response.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'});
  response.end('<!doctype html><html><head><title>Private test title</title></head><body><h1>Extension test page</h1></body></html>');
});
await new Promise(resolve => server.listen(3105, resolve));
const evidence = {status: 'FAIL', network: [], automaticPermissionPromptTested: false};
let context;
let popup;
try {
  context = await chromium.launchPersistentContext(profile, {channel: 'chromium', headless: true,
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]});
  const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  evidence.extensionId = new URL(worker.url()).host;
  assert.equal(evidence.extensionId, 'lamffehgecaabedhleppfmgjcagamlih');
  const settings = await worker.evaluate(() => chrome.storage.local.get({automatic: false}));
  assert.equal(settings.automatic, false);
  assert.deepEqual(await worker.evaluate(() => chrome.scripting.getRegisteredContentScripts()), []);
  context.on('request', request => {
    if (request.url() === 'http://localhost:3000/api/analyze') evidence.network.push(JSON.parse(request.postData()));
  });
  const page = await context.newPage();
  await page.goto('http://localhost:3105/test?private=1#private', {waitUntil: 'networkidle'});
  assert.equal(await page.evaluate(() => !!window.__scamguardInstalled), false);
  assert.equal(evidence.network.length, 0);
  const tabs = await worker.evaluate(() => chrome.tabs.query({}));
  const tab = tabs.find(tab => tab.url?.startsWith('http://localhost:3105/'));
  assert.ok(tab);
  popup = await context.newPage();
  await popup.goto(`chrome-extension://${evidence.extensionId}/popup.html`);
  assert.equal(await popup.locator('input[value="manual"]').isChecked(), true);
  // Bring the web tab forward before invoking the installed popup's real click handler.
  // localhost access is a declared host permission; no browser-profile grant is fabricated.
  await popup.evaluate(async tabId => {
    await chrome.tabs.update(tabId, {active: true});
    document.getElementById('check').click();
  }, tab.id);
  await popup.locator('#status').filter({hasText: /\/100/}).waitFor({timeout: 25000});
  assert.equal(evidence.network.length, 1);
  assert.deepEqual(evidence.network[0], {url: 'http://localhost:3105/test'});
  evidence.manualResult = await popup.locator('#status').innerText();
  await popup.screenshot({path: path.join(output, 'extension-popup.png')});
  // Lack of automatic host permission must not silently turn on collection.
  const denied = await popup.evaluate(() => chrome.runtime.sendMessage({action: 'SET_MODE', automatic: true}));
  assert.ok(denied.error);
  assert.equal((await worker.evaluate(() => chrome.storage.local.get('automatic'))).automatic, false);
  evidence.manualMode = 'PASS';
  evidence.automaticPermissionGuard = 'PASS';
  await context.close();
  context = undefined;
  // Test the post-consent state with an explicit fixture manifest. Application
  // scripts are unchanged; only optional host grants are preinstalled for this test.
  const fixture = await fs.mkdtemp(path.resolve('.local-runtime/readiness/extension-auto-fixture-'));
  await fs.cp(extension, fixture, {recursive: true});
  const manifestBytes = await fs.readFile(path.join(extension, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  manifest.host_permissions = [...new Set([...manifest.host_permissions, ...manifest.optional_host_permissions])];
  await fs.writeFile(path.join(fixture, 'manifest.json'), JSON.stringify(manifest, null, 2));
  evidence.automaticFixture = {productionManifestSha256: createHash('sha256').update(manifestBytes).digest('hex'),
    difference: 'Optional http/https host permissions pregranted in fixture manifest; source scripts unchanged'};
  const autoProfile = await fs.mkdtemp(path.resolve('.local-runtime/readiness/extension-auto-profile-'));
  context = await chromium.launchPersistentContext(autoProfile, {channel: 'chromium', headless: true,
    args: [`--disable-extensions-except=${fixture}`, `--load-extension=${fixture}`]});
  const autoWorker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  const automaticRequests = [];
  context.on('request', request => {
    if (request.url() === 'http://localhost:3000/api/analyze') automaticRequests.push(JSON.parse(request.postData()));
  });
  const autoPopup = await context.newPage();
  await autoPopup.goto(`chrome-extension://${evidence.extensionId}/popup.html`);
  await autoPopup.locator('input[value="automatic"]').check();
  await autoPopup.locator('#status').filter({hasText: 'Đã bật tự quét'}).waitFor();
  assert.equal((await autoWorker.evaluate(() => chrome.storage.local.get('automatic'))).automatic, true);
  assert.equal((await autoWorker.evaluate(() => chrome.scripting.getRegisteredContentScripts())).length, 1);
  const autoPage = await context.newPage();
  await autoPage.goto('http://localhost:3105/test?automatic=1#private', {waitUntil: 'networkidle'});
  await autoPage.locator('#scamguard-alert-banner').waitFor({timeout: 25000});
  assert.deepEqual(automaticRequests, [{url: 'http://localhost:3105/test'}]);
  evidence.automaticRequests = automaticRequests;
  await autoPopup.bringToFront();
  await autoPopup.locator('input[value="manual"]').check();
  await autoPopup.locator('#status').filter({hasText: 'Đã chuyển sang quét thủ công'}).waitFor();
  assert.deepEqual(await autoWorker.evaluate(() => chrome.scripting.getRegisteredContentScripts()), []);
  const disabledPage = await context.newPage();
  await disabledPage.goto('http://localhost:3105/manual-again', {waitUntil: 'networkidle'});
  assert.equal(await disabledPage.evaluate(() => !!window.__scamguardInstalled), false);
  evidence.automaticModeAfterConsent = 'PASS';
  evidence.disableAutomatic = 'PASS';
  evidence.status = 'PASS';
} catch (error) {
  evidence.error = error.message;
  if (popup) evidence.popupStatus = await popup.locator('#status').innerText().catch(() => 'unavailable');
  process.exitCode = 1;
} finally {
  if (context) await context.close();
  await new Promise(resolve => server.close(resolve));
  await fs.writeFile(path.join(output, 'extension-browser.json'), JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
}
