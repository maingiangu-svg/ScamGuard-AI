import assert from 'node:assert/strict';
import {test} from 'node:test';

const origin = process.env.TEST_APP_URL ?? 'http://127.0.0.1:3000';
const post = (route, body, type = 'application/json') => fetch(origin + route, {
  method: 'POST', headers: {'content-type': type}, body,
  signal: AbortSignal.timeout(25000),
});

test('both inference routes reject unsupported, malformed, and oversized bodies', async () => {
  for (const route of ['/api/analyze', '/api/ml-classify']) {
    for (const [body, type, status] of [
      ['{}', 'text/plain', 415], ['{', 'application/json', 400],
      [JSON.stringify({textInput: 'hello', ignored: 'a'.repeat(262144)}), 'application/json', 413],
    ]) {
      const response = await post(route, body, type);
      assert.equal(response.status, status, route);
      const result = await response.json();
      assert.ok(result.error);
      assert.equal(result.riskScore, undefined);
      assert.equal(result.ml_risk_score, undefined);
    }
  }
});

test('shared inference admission rejects excess work across both endpoints', async () => {
  const responses = await Promise.all(['/api/analyze', '/api/ml-classify', '/api/analyze'].map(
    route => post(route, JSON.stringify({url: 'https://example.com/'}))));
  assert.deepEqual(responses.map(r => r.status).sort(), [200, 200, 503]);
  const rejected = await responses.find(r => r.status === 503).json();
  assert.ok(rejected.error);
  assert.equal(rejected.riskScore, undefined);
  assert.equal((await post('/api/analyze', JSON.stringify({url: 'https://example.com/'}))).status, 200);
});

test('both endpoints reject foreign origins without wildcard CORS and disable caching', async () => {
  for (const route of ['/api/analyze', '/api/ml-classify']) {
    const response = await fetch(origin + route, {method: 'POST', headers: {
      'Content-Type': 'application/json', Origin: 'https://evil.example',
    }, body: JSON.stringify({url: 'https://example.com/'})});
    assert.equal(response.status, 403);
    assert.equal(response.headers.get('access-control-allow-origin'), null);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    const preflight = await fetch(origin + route, {method: 'OPTIONS', headers: {Origin: origin}});
    assert.equal(preflight.status, 204);
    assert.equal(preflight.headers.get('access-control-allow-origin'), origin);
  }
});
