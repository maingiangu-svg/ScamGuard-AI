import assert from 'node:assert/strict';
import { test } from 'node:test';

// Run against an isolated app started with SCAMGUARD_MODEL_PATH pointing to a
// missing or invalid test artifact. Applies to the hybrid adapter by default;
// never rename or overwrite the real bundle.
const origin = process.env.TEST_APP_URL ?? 'http://127.0.0.1:3102';

for (const route of ['/api/analyze', '/api/ml-classify']) {
  test(`${route} returns unavailable without a fabricated risk score`, async () => {
    const response = await fetch(origin + route, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({textInput: 'Please verify your account https://example.com/'}),
      signal: AbortSignal.timeout(25000),
    });
    assert.equal(response.status, 503);
    const body = await response.json();
    assert.ok(body.error);
    for (const key of ['riskScore', 'risk_score', 'ml_risk_score', 'riskLevel']) {
      assert.equal(body[key], undefined);
    }
    assert.notEqual(body.model_ready, true);
    assert.doesNotMatch(JSON.stringify(body), /Traceback|FileNotFoundError|\.pkl|[A-Za-z]:\\/);
  });
}
