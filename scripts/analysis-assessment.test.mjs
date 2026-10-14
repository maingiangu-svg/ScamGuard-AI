import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createAssessment, getRiskLevels, isMLAvailable } from '../src/lib/analysis-assessment.ts';

const ml = (score, extra = {}) => ({
  ml_risk_score: score, ml_label: 'SAFE', ml_confidence: 90,
  ml_top_signals: ['free', 'lunch'], model_ready: true, ...extra,
});

test('ML alone supplies the score, safe category and no threat evidence', () => {
  const result = createAssessment(null, ml(11), false);
  assert.equal(result.riskScore, 11);
  assert.equal(result.riskLevel, 'LOW');
  assert.equal(result.scam_type, 'No Scam Indicators Detected');
  assert.deepEqual(result.reasons, []);
  assert.deepEqual(result.detectedPatterns, []);
});

test('a valid zero ML score is used', () => {
  assert.equal(createAssessment(null, ml(0), false).riskScore, 0);
});

test('Gemini and ML are blended only when both are available', () => {
  const result = createAssessment({ riskScore: 30, riskLevel: 'LOW' }, ml(80), false);
  assert.equal(result.riskScore, 50);
  assert.equal(result.riskLevel, 'MEDIUM');
  assert.equal(result.scam_type, 'Suspicious Content');
});

test('Gemini alone works and its risk label is derived from its numeric score', () => {
  const result = createAssessment({ riskScore: 49, riskLevel: 'HIGH', summary: 'Cần xác minh thêm.' }, null, false);
  assert.equal(result.riskScore, 49);
  assert.equal(result.riskLevel, 'MEDIUM');
  assert.equal(result.scam_type, 'Suspicious Content');
});

test('an invalid Gemini score falls back to available ML', () => {
  for (const score of [NaN, -1, 101, '75']) {
    assert.equal(createAssessment({ riskScore: score }, ml(11), false).riskScore, 11);
  }
});

test('missing or unloaded models do not produce a safe verdict', () => {
  for (const model of [null, ml(0, { model_ready: false }), ml(0, { ml_confidence: 0 }), ml(NaN)]) {
    assert.equal(isMLAvailable(model), false);
    assert.equal(createAssessment(null, model, false), null);
  }
});

test('high risk categories distinguish messages from URLs without inventing impersonation', () => {
  assert.equal(createAssessment(null, ml(99), false).scam_type, 'Suspected Spam / Scam Message');
  assert.equal(createAssessment(null, ml(84), true).scam_type, 'Suspected URL Phishing');
});

for (const [score, riskLevel, threatLevel] of [
  [0, 'LOW', 'SAFE'], [20, 'LOW', 'SAFE'], [21, 'LOW', 'LOW'], [40, 'LOW', 'LOW'],
  [41, 'MEDIUM', 'MEDIUM'], [70, 'MEDIUM', 'MEDIUM'], [71, 'HIGH', 'HIGH'],
  [90, 'HIGH', 'HIGH'], [91, 'HIGH', 'CRITICAL'], [100, 'HIGH', 'CRITICAL'],
]) {
  test(`score ${score} maps to consistent risk and threat levels`, () => {
    assert.deepEqual(getRiskLevels(score), { riskLevel, threatLevel });
  });
}
