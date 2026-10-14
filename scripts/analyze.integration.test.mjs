// Run against the local app without a Gemini key: node --test scripts/analyze.integration.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';

const origin = process.env.TEST_APP_URL ?? 'http://127.0.0.1:3000';
const headers = { 'Content-Type': 'application/json', 'x-real-ip': '127.0.0.2' };

async function analyze(body) {
  const response = await fetch(`${origin}/api/analyze`, {
    method: 'POST', headers, body: JSON.stringify(body), signal: AbortSignal.timeout(20000),
  });
  assert.equal(response.status, 200);
  return response.json();
}

test('ordinary SMS uses the ML score and has no fabricated threat evidence', async () => {
  const result = await analyze({ textInput: 'Hey, are you free for lunch tomorrow?' });
  assert.equal(result.ml_classifier.model_ready, true);
  assert.equal(result.ml_classifier.ml_label, 'SAFE');
  assert.equal(result.risk_score, 11);
  assert.equal(result.riskScore, result.ml_classifier.ml_risk_score);
  assert.equal(result.riskLevel, 'LOW');
  assert.equal(result.threat_level, 'SAFE');
  assert.equal(result.scam_detected, false);
  assert.equal(result.scam_type, 'No Scam Indicators Detected');
  assert.deepEqual(result.red_flags, []);
  assert.deepEqual(result.detectedPatterns, []);
  assert.deepEqual(result.psychological_tricks, []);
  assert.equal(result.web_intelligence.verified_live, false);
  assert.doesNotMatch(result.family_alert_card.headline, /verified|phishing|fraud alert/i);
});

test('spam SMS keeps the ML risk score and a message-specific threat category', async () => {
  const result = await analyze({ textInput: 'Congratulations! You won a FREE prize. Claim your cash reward now!' });
  assert.equal(result.risk_score, result.ml_classifier.ml_risk_score);
  assert.equal(result.risk_score, 99);
  assert.equal(result.riskLevel, 'HIGH');
  assert.equal(result.threat_level, 'CRITICAL');
  assert.equal(result.scam_detected, true);
  assert.equal(result.scam_type, 'Suspected Spam / Scam Message');
  assert.ok(result.red_flags.length > 0);
  assert.ok(result.red_flags.every(flag => !flag.official_link));
});

test('whitelisted URL remains safe', async () => {
  const result = await analyze({ url: 'https://www.google.com/search?q=weather' });
  assert.equal(result.risk_score, 0);
  assert.equal(result.threat_level, 'SAFE');
  assert.equal(result.scam_detected, false);
  assert.deepEqual(result.red_flags, []);
});

test('an image is not classified using the placeholder text when Gemini is unavailable', async () => {
  const form = new FormData();
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+XwS8AAAAASUVORK5CYII=', 'base64');
  form.set('image', new Blob([png], { type: 'image/png' }), 'test.png');
  const response = await fetch(`${origin}/api/analyze`, {
    method: 'POST', headers: { 'x-real-ip': '127.0.0.2' }, body: form,
    signal: AbortSignal.timeout(20000),
  });
  assert.equal(response.status, 503);
  const result = await response.json();
  assert.ok(result.error);
  assert.equal(result.risk_score, undefined);
});
