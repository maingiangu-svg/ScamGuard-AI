// Run with isolated Playwright installed under .local-runtime/audit/node-tools.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const origin = process.env.TEST_APP_URL ?? 'http://127.0.0.1:3101';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(origin).hostname), 'Audit only a local test server');
const toolsRoot = path.resolve(process.env.AUDIT_NODE_TOOLS ?? '.local-runtime/audit/node-tools');
const {chromium} = await import(pathToFileURL(path.join(toolsRoot, 'node_modules/playwright/index.mjs')));
const output = path.resolve(process.env.AUDIT_OUTPUT ?? 'docs/audit-evidence/2026-10-26');
await fs.mkdir(output, {recursive: true});
const browser = await chromium.launch({
  executablePath: process.env.AUDIT_BROWSER_PATH ?? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true,
});
const report = {browser: browser.version(), origin, errors: [], failedRequests: [], externalRequests: [], widths: []};
try {
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const page = await context.newPage();
  page.on('pageerror', error => report.errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') report.errors.push(message.text());
  });
  page.on('requestfailed', request => report.failedRequests.push({url: request.url(), error: request.failure()?.errorText}));
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.protocol.startsWith('http') && url.origin !== new URL(origin).origin) {
      report.externalRequests.push(url.origin);
      return route.abort();
    }
    return route.continue();
  });
  const response = await page.goto(origin, {waitUntil: 'networkidle'});
  assert.equal(response.status(), 200);
  report.headers = await response.allHeaders();
  assert.match(report.headers['content-security-policy'], /script-src.*'nonce-/);
  assert.match(report.headers['cache-control'], /no-store/);
  const nonces = await page.locator('script').evaluateAll(scripts => scripts.map(script => script.nonce));
  assert.ok(nonces.length > 0 && nonces.every(Boolean));
  const secondResponse = await context.request.get(origin);
  assert.notEqual(secondResponse.headers()['content-security-policy'], report.headers['content-security-policy']);
  for (const width of [320, 390, 768, 1024, 1440]) {
    await page.setViewportSize({width, height: 1000});
    const size = await page.evaluate(() => ({viewport: innerWidth, content: document.documentElement.scrollWidth}));
    report.widths.push({width, ...size});
    assert.ok(size.content <= size.viewport, `Horizontal overflow at ${width}px`);
    if (width === 390 || width === 1440) {
      await page.screenshot({path: path.join(output, `browser-${width}-after.png`), fullPage: true});
    }
  }
  report.viewport = await page.locator('meta[name="viewport"]').getAttribute('content');
  assert.doesNotMatch(report.viewport, /maximum-scale=1(?:,|$)|user-scalable=no/);
  const sample = page.getByRole('button', {name: /Fake Solana investment/});
  await sample.focus();
  await page.keyboard.press('Enter');
  assert.ok(await page.getByRole('button', {name: 'Download PDF', exact: true}).isVisible());
  await page.getByRole('button', {name: 'VI', exact: true}).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Tải báo cáo PDF', exact: true}).click();
  const pdf = await download;
  const pdfPath = path.join(output, 'browser-sample-report.pdf');
  await pdf.saveAs(pdfPath);
  const pdfBytes = await fs.readFile(pdfPath);
  assert.equal(pdfBytes.subarray(0, 5).toString(), '%PDF-');
  assert.ok(pdfBytes.length > 10000);
  report.pdf = {status: 'PASS', bytes: pdfBytes.length, file: 'browser-sample-report.pdf', language: 'vi'};
  await page.getByRole('button', {name: 'EN', exact: true}).click();
  // Only synthetic text is submitted. No saved browser profile or user content is used.
  await page.getByRole('textbox').fill('Hello, are you free for lunch tomorrow?');
  const apiResponse = page.waitForResponse(r => r.url() === origin + '/api/analyze' && r.request().method() === 'POST');
  const started = performance.now();
  await page.getByRole('button', {name: 'Check content', exact: true}).click();
  const api = await apiResponse;
  report.apiDurationMs = Math.round(performance.now() - started);
  assert.equal(api.status(), 200);
  const result = await api.json();
  assert.equal(result.ml_classifier.model_ready, true);
  assert.equal(result.web_intelligence.verified_live, false);
  report.model = {mode: result.ml_classifier.mode, riskScore: result.riskScore, riskLevel: result.riskLevel};
  await page.screenshot({path: path.join(output, 'browser-result-after.png'), fullPage: true});
  await page.getByRole('button', {name: 'VI', exact: true}).click();
  assert.ok(await page.getByRole('button', {name: 'Kiểm tra nội dung', exact: true}).isVisible());
  report.languageToggle = 'PASS';
  report.htmlLanguageAfterVietnameseToggle = await page.locator('html').getAttribute('lang');
  assert.equal(report.htmlLanguageAfterVietnameseToggle, 'vi');
  await page.getByRole('button', {name: 'Đã hiểu', exact: true}).click();
  await page.reload({waitUntil: 'networkidle'});
  assert.equal(await page.getByRole('button', {name: 'Đã hiểu', exact: true}).count(), 0);
  assert.equal(await page.locator('html').getAttribute('lang'), 'vi');
  report.preferencePersistence = 'PASS';
  assert.deepEqual(report.externalRequests, []);
  assert.deepEqual(report.errors, []);
  assert.deepEqual(report.failedRequests, []);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.message;
  process.exitCode = 1;
} finally {
  await fs.writeFile(path.join(output, 'browser-audit.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify(report, null, 2));
}
