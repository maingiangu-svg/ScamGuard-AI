import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';

const image = process.argv[2] ?? 'scamguard-ci';
const name = `scamguard-smoke-${process.pid}`;
const docker = (...args) => execFileSync('docker', args, {encoding: 'utf8', timeout: 30000, windowsHide: true}).trim();
const output = process.env.AUDIT_OUTPUT ?? 'docs/readiness-evidence/2026-10-26';
fs.mkdirSync(output, {recursive: true});
const evidence = {image, status: 'FAIL'};
try {
  evidence.user = docker('image', 'inspect', image, '--format', '{{.Config.User}}');
  assert.equal(evidence.user, '10001:10001');
  docker('run', '-d', '--name', name, '--read-only', '--tmpfs', '/tmp:rw,size=64m',
    '--tmpfs', '/app/.next/cache:rw,uid=10001,gid=10001,size=64m',
    '-e', 'RATE_LIMIT_TOTAL_PER_MINUTE=1000', '-p', '127.0.0.1:3110:8080', image);
  let response;
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      response = await fetch('http://127.0.0.1:3110/api/health', {signal: AbortSignal.timeout(1000)});
      if (response.ok) break;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  assert.equal(response?.status, 200);
  const started = performance.now();
  const prediction = await fetch('http://127.0.0.1:3110/api/analyze', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: 'https://example.com/'}),
    signal: AbortSignal.timeout(25000)});
  assert.equal(prediction.status, 200);
  const result = await prediction.json();
  assert.equal(result.ml_classifier.model_ready, true);
  assert.equal(result.ml_classifier.mode, 'hybrid_url_only');
  evidence.inferenceMs = Math.round(performance.now() - started);
  evidence.healthcheckExit = docker('exec', name, 'node', '-e',
    "fetch('http://127.0.0.1:8080/api/health').then(r=>process.exit(r.ok?0:1))");
  assert.equal(docker('exec', name, 'python', '-c', "from pathlib import Path; print(Path('/app/ml_model/data').exists())"), 'False');
  evidence.status = 'PASS';
} catch (error) {
  evidence.error = error.message;
  process.exitCode = 1;
} finally {
  try {fs.writeFileSync(`${output}/container.log`, docker('logs', name));} catch {}
  try {docker('rm', '-f', name);} catch {}
  fs.writeFileSync(`${output}/container-smoke.json`, JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify(evidence, null, 2));
}
