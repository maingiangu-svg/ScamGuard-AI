import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';

const origin = process.env.TEST_APP_URL ?? 'http://127.0.0.1:3000';
const manifest = JSON.parse(readFileSync('ml_model/models/hybrid_manifest.json', 'utf8'));
const modelId = manifest.head_model_ids?.url ?? manifest.training.run_id + ':url';
const post = (body, headers = {}, route = '/api/analyze-links') => fetch(origin + route, {
  method: 'POST', headers: {'Content-Type': 'application/json', ...headers}, body: JSON.stringify(body),
  signal: AbortSignal.timeout(25000),
});

test('batch API preserves single-URL scores, review levels and active model identity', async () => {
  const urls = ['https://www.facebook.com/', 'https://qi.lv/F0i',
    'https://uccle.monopinion.belgium.be/profiles/sunwinorgvc/badges'];
  const response = await post({urls});
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const {results} = await response.json();
  assert.equal(results.length, 3);
  for (let index = 0; index < urls.length; index++) {
    const old = await post({url: urls[index]}, {}, '/api/analyze');
    assert.equal(old.status, 200);
    const baseline = await old.json();
    assert.equal(results[index].url, urls[index]);
    assert.equal(results[index].riskScore, baseline.riskScore);
    assert.equal(results[index].riskLevel, baseline.riskLevel);
    assert.equal(results[index].model_id, modelId);
  }
});

test('batch API bounds work and rejects sensitive URL parts, wrong types and unsupported protocols', async () => {
  for (const body of [{urls: []}, {urls: Array(21).fill('https://example.com/')}, {urls: [12]},
    {urls: ['https://example.com/?secret=1']}, {urls: ['https://user:pass@example.com/']},
    {urls: ['javascript:alert(1)']}, {urls: ['https://example.com/#secret']}, {urls: ['https://']}]) {
    const response = await post(body);
    assert.equal(response.status, 400);
    assert.ok((await response.json()).error);
  }
  assert.equal((await post({}, {'Content-Type': 'text/plain'})).status, 415);
  assert.equal((await post({urls: ['https://example.com/'], ignored: 'a'.repeat(262144)})).status, 413);
});

test('batch API enforces origin restrictions and preflight without wildcard CORS', async () => {
  const response = await post({urls: ['https://example.com/']}, {Origin: 'https://evil.example'});
  assert.equal(response.status, 403);
  assert.equal(response.headers.get('access-control-allow-origin'), null);
  const extension = 'chrome-extension://lamffehgecaabedhleppfmgjcagamlih';
  const preflight = await fetch(origin + '/api/analyze-links', {method: 'OPTIONS', headers: {Origin: extension}});
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get('access-control-allow-origin'), extension);
});

test('batch inference shares existing admission limits and recovers after excess work', async () => {
  const responses = await Promise.all([
    post({urls: ['https://example.com/']}), post({url: 'https://example.com/'}, {}, '/api/analyze'),
    post({urls: ['https://example.com/']}),
  ]);
  assert.deepEqual(responses.map(response => response.status).sort(), [200, 200, 503]);
  const rejected = await responses.find(response => response.status === 503).json();
  assert.ok(rejected.error);
  assert.equal(rejected.results, undefined);
  assert.equal((await post({urls: ['https://example.com/']})).status, 200);
});
