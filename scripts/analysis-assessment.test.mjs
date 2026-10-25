import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createAssessment, getRiskLevels, isMLAvailable } from '../src/lib/analysis-assessment.ts';

const ml = (score, extra = {}) => ({
  ml_risk_score: score, ml_label: 'SAFE', ml_confidence: 90,
  ml_top_signals: ['free', 'lunch'], model_ready: true, ...extra,
});

test('a low score has no threat evidence or absolute safety claim', () => {
  const result = createAssessment(ml(11), false);
  assert.equal(result.riskScore, 11);
  assert.deepEqual(result.reasons, []);
  assert.deepEqual(result.detectedPatterns, []);
  assert.doesNotMatch(result.summary, /nội dung an toàn\./i);
});

test('every valid ML score is preserved without a whitelist or external blend', () => {
  for (const score of [0, 11, 30, 35, 79, 80, 100]) {
    assert.equal(createAssessment(ml(score), true).riskScore, score);
  }
});

test('missing, invalid and failed predictions produce no assessment', () => {
  for (const model of [null, ml(null), ml(0, {model_ready: false}), ml(NaN), ml(101), ml(50, {ml_confidence: 0})]) {
    assert.equal(isMLAvailable(model), false);
    assert.equal(createAssessment(model, false), null);
  }
});

test('the entire review interval is described as uncertain', () => {
  for (const score of [30, 35, 40, 60, 70, 71, 79]) {
    const result = createAssessment(ml(score), true);
    assert.equal(result.riskLevel, 'MEDIUM');
    assert.doesNotMatch(result.summary, /< 30|an toàn\./i);
    assert.match(result.summary, /cần|nghi ngờ/i);
  }
});

test('high scores retain a suspected rather than verified threat category', () => {
  assert.equal(createAssessment(ml(99), false).scam_type, 'Suspected Smishing');
  assert.equal(createAssessment(ml(84), true).scam_type, 'Suspected URL / Message Risk');
});

test('independent URL review stays visible without inflating the primary SMS score', () => {
  const result = createAssessment(ml(10, {url_review_required: true}), true, 'en');
  assert.equal(result.riskScore, 10);
  assert.equal(result.riskLevel, 'MEDIUM');
  assert.match(result.summary, /URL/i);
  assert.ok(result.reasons.length > 0);
  assert.ok(result.urgent_actions.length > 0);
  assert.notEqual(result.scam_type, 'No Scam Indicators Detected');
});

test('URL review does not downgrade a high SMS score or invent a URL in text-only input', () => {
  assert.equal(createAssessment(ml(95, {url_review_required: true}), true).riskLevel, 'HIGH');
  assert.equal(createAssessment(ml(10, {url_review_required: true}), false).riskLevel, 'LOW');
});

for (const [score, riskLevel, threatLevel] of [
  [0, 'LOW', 'SAFE'], [20, 'LOW', 'SAFE'], [29, 'LOW', 'LOW'],
  [30, 'MEDIUM', 'MEDIUM'], [79, 'MEDIUM', 'MEDIUM'],
  [80, 'HIGH', 'HIGH'], [90, 'HIGH', 'HIGH'], [91, 'HIGH', 'CRITICAL'], [100, 'HIGH', 'CRITICAL'],
]) {
  test('consistent thresholds at score ' + score, () => {
    assert.deepEqual(getRiskLevels(score), {riskLevel, threatLevel});
  });
}
