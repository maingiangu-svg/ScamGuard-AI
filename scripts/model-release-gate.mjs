import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';

// Test a declared rejection using a valid, unchanged serving bundle. This is
// an API guard fixture, never an approval of a research candidate's accuracy.
const root = process.cwd();
const source = path.join(root, '.next/standalone');
const fixture = path.join(root, '.local-runtime/model-release-checks', String(Date.now()));
const output = path.resolve(process.env.AUDIT_OUTPUT ?? 'ml_model/data/prepared/english_sms_selection_2026-10-28');
const hash = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const liveModel = path.join(root, 'ml_model/models/hybrid_bundle.pkl');
const liveManifest = path.join(root, 'ml_model/models/hybrid_manifest.json');
const before = {model: hash(liveModel), manifest: hash(liveManifest)};
assert.ok(fs.existsSync(path.join(source, 'server.js')), 'Run the production build first');
assert.equal(fs.existsSync(path.join(source, 'ml_model/data')), false, 'Training data must not be packaged');
assert.equal(hash(path.join(source, 'ml_model/predict_hybrid.py')), hash(path.join(root, 'ml_model/predict_hybrid.py')));
fs.cpSync(source, fixture, {recursive: true, errorOnExist: true, force: false});
const fixtureManifest = path.join(fixture, 'ml_model/models/hybrid_manifest.json');
const original = fs.readFileSync(fixtureManifest, 'utf8');
const manifest = JSON.parse(original);
assert.equal(hash(path.join(fixture, 'ml_model/models/hybrid_bundle.pkl')), before.model);

const reservation = net.createServer();
await new Promise(resolve => reservation.listen(0, '127.0.0.1', resolve));
const port = reservation.address().port;
await new Promise(resolve => reservation.close(resolve));
const log = fs.openSync(path.join(fixture, 'server.log'), 'w');
const server = spawn(process.execPath, ['server.js'], {
  cwd: fixture, windowsHide: true,
  env: {...process.env, HOSTNAME: '127.0.0.1', PORT: String(port),
    SCAMGUARD_INFERENCE_MODE: 'hybrid',
    SCAMGUARD_MODEL_PATH: path.join(fixture, 'ml_model/models/hybrid_bundle.pkl'),
    PYTHON_EXECUTABLE: path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'),
    OMP_NUM_THREADS: '1', OPENBLAS_NUM_THREADS: '1',
    RATE_LIMIT_TOTAL_PER_MINUTE: '1000', RATE_LIMIT_PER_MINUTE: '1000'},
  stdio: ['ignore', log, log],
});
fs.closeSync(log);
let startError;
server.on('error', error => { startError = error; });
const checks = [];

async function post(route, body, expected, phase) {
  const response = await fetch(`http://127.0.0.1:${port}${route}`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body), signal: AbortSignal.timeout(25000),
  });
  const value = await response.json();
  assert.equal(response.status, expected, `${phase} ${route}: ${JSON.stringify(value)}`);
  if (expected === 503) {
    for (const key of ['riskScore', 'risk_score', 'ml_risk_score', 'riskLevel']) assert.equal(value[key], undefined);
    assert.notEqual(value.model_ready, true);
    assert.doesNotMatch(JSON.stringify(value), /Traceback|\.pkl|[A-Za-z]:\\/);
  } else {
    assert.equal(value.model_ready, true);
  }
  checks.push({phase, route, status: response.status});
}

async function checkHealth(expected, phase) {
  const response = await fetch(`http://127.0.0.1:${port}/api/health`, {signal: AbortSignal.timeout(5000)});
  const value = await response.json();
  assert.equal(response.status, expected, `${phase} health`);
  assert.equal(value.status, expected === 200 ? 'ok' : 'unavailable');
  checks.push({phase, route: '/api/health', status: response.status});
}

try {
  let ready = false;
  let readinessError = '';
  for (let attempt = 0; attempt < 60; attempt++) {
    if (startError) throw startError;
    if (server.exitCode !== null) throw new Error('Fixture server exited; inspect its server.log');
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/health`, {signal: AbortSignal.timeout(1000)});
      if (response.ok) { ready = true; break; }
      readinessError = `HTTP ${response.status}`;
    } catch (error) { readinessError = `${error.message}: ${error.cause?.message ?? ''}`; }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  assert.ok(ready, `Fixture server did not become ready: ${readinessError}`);
  const body = {textInput: 'Hello, can we meet for lunch tomorrow?'};
  await checkHealth(200, 'legacy_control');
  await post('/api/ml-classify', body, 200, 'legacy_control');
  fs.writeFileSync(fixtureManifest, JSON.stringify({...manifest, historical_nonregression_pass: false}));
  await checkHealth(503, 'rejected');
  await post('/api/analyze', body, 503, 'rejected');
  await post('/api/ml-classify', body, 503, 'rejected');
  await post('/api/analyze-links', {urls: ['https://example.com/']}, 503, 'rejected');
  fs.writeFileSync(fixtureManifest, JSON.stringify({...manifest, historical_nonregression_pass: 'true'}));
  await checkHealth(503, 'invalid_approval_type');
  await post('/api/ml-classify', body, 503, 'invalid_approval_type');
  fs.writeFileSync(fixtureManifest, JSON.stringify({...manifest, historical_nonregression_pass: true}));
  await checkHealth(200, 'passed_control');
  await post('/api/ml-classify', body, 200, 'passed_control');
  assert.equal(hash(liveModel), before.model);
  assert.equal(hash(liveManifest), before.manifest);
  fs.mkdirSync(output, {recursive: true});
  const evidence = {checks, fixture_bundle_sha256: before.model,
    serving_code_sha256: hash(path.join(root, 'ml_model/predict_hybrid.py')),
    verification_script_sha256: hash(new URL(import.meta.url)),
    live_artifacts_unchanged: true, experimental_candidate_approved: false, fixture};
  fs.writeFileSync(path.join(output, 'api_release_gate_check.json'), JSON.stringify(evidence, null, 2) + '\n');
  console.log(JSON.stringify(evidence));
} finally {
  fs.writeFileSync(fixtureManifest, original);
  if (server.pid && server.exitCode === null) server.kill();
}
