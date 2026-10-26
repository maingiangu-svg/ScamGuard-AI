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
  const expectedScore = Number(evidence.manualResult.split('/')[0]);
  assert.ok(expectedScore >= 80 && expectedScore <= 100, 'The fixed local fixture must exercise a high-score warning');
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
  const alreadyOpen = await context.newPage();
  await alreadyOpen.goto('http://localhost:3105/test?already-open=1#private', {waitUntil: 'networkidle'});
  assert.equal(await alreadyOpen.evaluate(() => !!window.__scamguardInstalled), false);
  assert.equal(automaticRequests.length, 0);
  const existingTab = (await autoWorker.evaluate(() => chrome.tabs.query({})))
    .find(tab => tab.url?.includes('already-open=1'));
  assert.ok(existingTab);
  let autoPopup = await context.newPage();
  await autoPopup.goto(`chrome-extension://${evidence.extensionId}/popup.html`);
  await autoPopup.evaluate(async tabId => {
    await chrome.tabs.update(tabId, {active: true});
    document.querySelector('input[value="automatic"]').click();
  }, existingTab.id);
  await alreadyOpen.locator('#scamguard-alert-banner').waitFor({timeout: 25000});
  assert.deepEqual(automaticRequests, [{url: 'http://localhost:3105/test'}]);
  const activeBadge = await autoWorker.evaluate(tabId => chrome.action.getBadgeText({tabId}), existingTab.id);
  assert.equal(activeBadge, String(expectedScore));
  evidence.automaticAlreadyOpenPage = 'PASS';
  evidence.actualBadge = activeBadge;
  assert.equal((await autoWorker.evaluate(() => chrome.storage.local.get('automatic'))).automatic, true);
  assert.equal((await autoWorker.evaluate(() => chrome.scripting.getRegisteredContentScripts())).length, 1);
  const autoPage = await context.newPage();
  await autoPage.goto('http://localhost:3105/test?automatic=1#private', {waitUntil: 'networkidle'});
  await autoPage.locator('#scamguard-alert-banner').waitFor({timeout: 25000});
  assert.deepEqual(automaticRequests, [{url: 'http://localhost:3105/test'}, {url: 'http://localhost:3105/test'}]);
  evidence.automaticRequests = automaticRequests;
  await context.route('https://www.youtube.com/**', route => route.fulfill({
    status: 200, contentType: 'text/html', body: '<!doctype html><title>External-origin permission fixture</title><p>Owned synthetic page</p>',
  }));
  const external = await context.newPage();
  await external.goto('https://www.youtube.com/watch?private=fixture#private', {waitUntil: 'networkidle'});
  const externalTab = (await autoWorker.evaluate(() => chrome.tabs.query({})))
    .find(tab => tab.url?.startsWith('https://www.youtube.com/watch'));
  assert.ok(externalTab);
  await external.waitForFunction(() => !!document.documentElement, {timeout: 5000});
  let externalBadge;
  for (let attempt = 0; attempt < 100; attempt++) {
    externalBadge = await autoWorker.evaluate(tabId => chrome.action.getBadgeText({tabId}), externalTab.id);
    if (/^\d+$/.test(externalBadge)) break;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.match(externalBadge, /^\d+$/);
  assert.ok(automaticRequests.some(request => request.url === 'https://www.youtube.com/watch'));
  evidence.externalOriginAutomatic = {status: 'PASS', badge: externalBadge,
    pageFixture: 'HTTPS YouTube origin intercepted with owned HTML; no real YouTube content or browser profile used'};
  const beforeReload = automaticRequests.length;
  // Fault-inject a missing receiver while keeping automatic=true and the old
  // installation marker. runtime.reload() disables CLI-loaded fixture extensions
  // in this browser; this is receiver recovery, not a claimed native Reload test.
  await autoWorker.evaluate(async tabId => {
    await chrome.scripting.executeScript({target: {tabId}, func: () => window.__scamguardInstalled?.cleanup?.()});
    await chrome.action.setBadgeText({tabId, text: ''});
  }, externalTab.id);
  await autoPopup.evaluate(async tabId => {
    await chrome.tabs.update(tabId, {active: true});
    return chrome.runtime.sendMessage({action: 'GET_SETTINGS', ensure: true});
  }, externalTab.id);
  for (let attempt = 0; attempt < 100 && automaticRequests.length === beforeReload; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.ok(automaticRequests.length > beforeReload, 'An enabled extension must repair a missing page receiver without a manual scan');
  assert.equal((await autoPopup.evaluate(() => chrome.storage.local.get('automatic'))).automatic, true);
  evidence.missingReceiverRecovery = 'PASS';
  evidence.nativeRuntimeReloadTested = false;
  await autoPopup.bringToFront();
  await autoPopup.locator('input[value="manual"]').check();
  await autoPopup.locator('#status').filter({hasText: 'Đã chuyển sang quét thủ công'}).waitFor();
  assert.deepEqual(await autoPopup.evaluate(() => chrome.scripting.getRegisteredContentScripts()), []);
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
