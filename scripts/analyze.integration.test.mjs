import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync(process.env.TEST_MODEL_MANIFEST ??
  new URL('../ml_model/models/hybrid_manifest.json', import.meta.url), 'utf8'));

const origin = process.env.TEST_APP_URL ?? 'http://127.0.0.1:3000';
let requestId = 0;
async function post(route, body) {
  return fetch(origin + route, {
    method: 'POST', headers: {'Content-Type':'application/json', 'x-forwarded-for': '198.18.0.' + (++requestId)},
    body: JSON.stringify(body), signal: AbortSignal.timeout(25000),
  });
}
async function analyze(body) {
  const response = await post('/api/analyze', body);
  assert.equal(response.status, 200, await response.clone().text());
  const result = await response.json();
  assert.equal(result.ml_classifier.model_ready, true);
  assert.equal(result.riskScore, result.ml_classifier.ml_risk_score);
  assert.equal(result.web_intelligence.verified_live, false);
  assert.equal(result.ml_classifier.training.run_id, manifest.training.run_id);
  assert.equal(result.ml_classifier.training.text_training_samples, manifest.training.text_training_samples);
  assert.equal(result.ml_classifier.training.url_training_samples, manifest.training.url_training_samples);
  assert.equal(result.ml_classifier.training.registered_domain_isolation, true);
  assert.equal(result.ml_classifier.training.campaign_independence_proven, false);
  assert.equal(result.ml_classifier.training.paired_training_samples, 0);
  assert.equal(result.ml_classifier.calibration_status, 'source_label_calibrated');
  assert.ok(Number.isFinite(result.ml_classifier.calibrated_probability));
  assert.ok(result.ml_classifier.calibrated_probability >= 0 && result.ml_classifier.calibrated_probability <= 1);
  assert.equal(result.ml_classifier.calibrated_probability_expert_verified, false);
  return result;
}

test('ordinary text is evaluated locally with no invented threat evidence', async () => {
  const result = await analyze({textInput:'Hey, are you free for lunch tomorrow?'});
  assert.equal(result.riskLevel, 'LOW');
  assert.deepEqual(result.red_flags, []);
  assert.deepEqual(result.detectedPatterns, []);
});

test('review scores and binary labels use distinct declared thresholds', async () => {
  const result = await analyze({textInput:'Tuyển cộng tác viên chốt đơn tại nhà, lương 2 triệu/ngày. Đóng trước 500.000đ để kích hoạt tài khoản và nhận hoa hồng.'});
  assert.ok(result.riskScore >= 30 && result.riskScore < 80);
  assert.equal(result.riskLevel, 'MEDIUM');
  assert.equal(result.ml_classifier.action, 'REVIEW');
  assert.equal(result.ml_classifier.mode, 'hybrid_text');
  assert.equal(result.ml_classifier.decision_threshold, 0.65);
  assert.equal(result.ml_classifier.model_prediction_label, Number(result.ml_classifier.text_result.score >= .65));
});

test('an official URL does not bypass SMS; no untrained fusion is applied', async () => {
  const result = await analyze({textInput:'Congratulations! You won a FREE prize. Send bank details now. https://www.google.com/'});
  assert.equal(result.ml_classifier.mode, 'hybrid_text');
  assert.ok(result.ml_classifier.text_result);
  assert.ok(result.ml_classifier.url_result);
  assert.ok(result.ml_classifier.training.run_id);
  assert.equal(result.riskScore, Math.round(result.ml_classifier.text_result.score * 100));
  assert.equal(result.ml_classifier.meta_formula, null);
  assert.notEqual(result.summary, 'Verified legitimate website belonging to Google.');
});

test('a URL-only request is scored by the URL estimator, with no forced whitelist score', async () => {
  const result = await analyze({url:'https://www.google.com/search?q=weather'});
  assert.equal(result.ml_classifier.mode, 'hybrid_url_only');
  assert.equal(result.riskScore, Math.round(result.ml_classifier.url_result.score * 100));
  assert.equal(result.ml_classifier.decision_threshold, 0.5);
  assert.equal(result.ml_classifier.model_prediction_label, Number(result.ml_classifier.url_result.score >= .5));
});

test('spaces and line breaks before the reported URL never activate the SMS branch', async () => {
  const url = 'https://uccle.monopinion.belgium.be/profiles/sunwinorgvc/badges';
  const baseline = await analyze({url});
  for (const textInput of [url, ' ' + url, '\n\t' + url + ' \r\n', '(' + url + ')']) {
    const result = await analyze({textInput, language: 'vi'});
    assert.equal(result.ml_classifier.mode, 'hybrid_url_only');
    assert.equal(result.ml_classifier.decision_branch, 'url');
    assert.equal(result.ml_classifier.text_result, null);
    assert.equal(result.ml_classifier.text_score, null);
    assert.equal(result.riskScore, baseline.riskScore);
    assert.equal(result.ml_classifier.url_result.score, baseline.ml_classifier.url_result.score);
    assert.equal(result.ml_classifier.url_review_required, false);
    assert.equal(result.riskLevel, 'MEDIUM');
    assert.doesNotMatch(result.summary, /SMS/);
  }
});

test('the complete sunwin.org.vc domain is scored identically through both endpoints and input fields', async () => {
  const url = 'http://sunwin.org.vc';
  const baseline = await analyze({url});
  for (const textInput of ['sunwin.org.vc', ' sunwin.org.vc \n']) {
    const result = await analyze({textInput});
    assert.equal(result.ml_classifier.decision_branch, 'url');
    assert.equal(result.ml_classifier.text_result, null);
    assert.equal(result.web_intelligence.domain, 'sunwin.org.vc');
    assert.equal(result.ml_classifier.extracted_url, url);
    assert.equal(result.ml_classifier.url_result.urls.length, 1);
    assert.equal(result.ml_classifier.url_result.urls[0].url, url);
    assert.equal(result.riskScore, baseline.riskScore);
    const response = await post('/api/ml-classify', {textInput});
    assert.equal(response.status, 200);
    const prediction = await response.json();
    assert.equal(prediction.decision_branch, 'url');
    assert.equal(prediction.extracted_url, url);
    assert.equal(prediction.ml_risk_score, baseline.riskScore);
  }
});

test('reported Facebook and Google URLs preserve model scores without a contradictory alert', async () => {
  for (const url of ['https://www.facebook.com/', 'https://facebook.com/', 'https://www.google.com/']) {
    const result = await analyze({textInput: url});
    assert.equal(result.ml_classifier.decision_branch, 'url');
    assert.ok(result.ml_classifier.url_result.score < result.ml_classifier.decision_threshold);
    assert.equal(result.ml_classifier.model_prediction_label, 0);
    assert.equal(result.ml_classifier.action, 'CLEAR');
    assert.equal(result.riskLevel, 'LOW');
    assert.equal(result.threat_level, 'LOW');
    assert.equal(result.scam_detected, false);
    assert.deepEqual(result.red_flags, []);
    assert.deepEqual(result.urgent_actions, []);
    const classifier = await post('/api/ml-classify', {url});
    assert.equal(classifier.status, 200);
    const prediction = await classifier.json();
    assert.equal(prediction.action, 'CLEAR');
    assert.equal(prediction.ml_risk_score, result.riskScore);
  }
});

test('reported suspicious link uses the repaired URL head with the declared alert policy', async () => {
  const result = await analyze({textInput:'https://qi.lv/F0i'});
  assert.equal(result.ml_classifier.text_result, null);
  assert.equal(result.ml_classifier.url_result.model_id, manifest.head_model_ids?.url ?? manifest.training.run_id + ':url');
  assert.equal(result.riskScore, Math.round(result.ml_classifier.url_result.score * 100));
  assert.ok(result.riskScore >= 80);
  assert.equal(result.riskLevel, 'HIGH');
});

test('a risky link independently requires review when the message is below the review band', async () => {
  const result = await analyze({textInput:'Hey, are you free for lunch tomorrow?', url:'https://qi.lv/F0i'});
  assert.equal(result.ml_classifier.text_result.model_id, manifest.head_model_ids?.sms ?? manifest.training.run_id + ':sms');
  assert.ok(result.riskScore < 30);
  assert.equal(result.riskScore, Math.round(result.ml_classifier.text_result.score * 100));
  assert.equal(result.ml_classifier.model_prediction_label, 0);
  assert.equal(result.ml_classifier.url_review_required, true);
  assert.equal(result.ml_classifier.action, 'REVIEW');
  assert.equal(result.riskLevel, 'MEDIUM');
  assert.equal(result.threat_level, 'MEDIUM');
  assert.ok(result.red_flags.length);
  assert.match(result.summary, /URL/);
  assert.equal(result.ml_classifier.meta_formula, null);
});

test('all embedded URLs are included in the returned branch scores', async () => {
  const result = await analyze({textInput:'Check https://www.google.com/ and http://bank-login.vip/verify'});
  assert.equal(result.ml_classifier.url_result.urls.length, 2);
});

test('both endpoints reject malformed and excessive input', async () => {
  for (const route of ['/api/analyze', '/api/ml-classify']) {
    for (const body of [{textInput:7}, {textInput:'a'.repeat(20001)}, {url:'file:///secret'}, {}]) {
      assert.equal((await post(route, body)).status, 400);
    }
  }
});

test('incomplete URL inputs return a useful validation error without a risk score', async () => {
  for (const route of ['/api/analyze', '/api/ml-classify']) {
    for (const body of [
      {textInput:'https://', language:'vi'}, {textInput:' \nHTTPS:// ', language:'vi'},
      {textInput:'https:/', language:'vi'}, {textInput:'www.', language:'vi'},
      {url:'https://', language:'en'},
    ]) {
      const response = await post(route, body);
      assert.equal(response.status, 400);
      const result = await response.json();
      assert.match(result.error, body.language === 'vi' ? /URL.*tên miền/ : /URL.*hostname/);
      for (const key of ['riskScore', 'risk_score', 'ml_risk_score', 'ml_classifier']) {
        assert.equal(result[key], undefined);
      }
    }
  }
});

test('image analysis is explicitly unsupported without a local OCR model', async () => {
  const form = new FormData();
  form.set('image', new Blob(['image'], {type:'image/png'}), 'test.png');
  const response = await fetch(origin + '/api/analyze', {method:'POST', body:form});
  assert.equal(response.status, 415);
  assert.equal((await response.json()).risk_score, undefined);
});

test('roleplay does not substitute keyword heuristics or an external model', async () => {
  assert.equal((await post('/api/roleplay', {userMessage:'I refuse to share my OTP'})).status, 501);
});
