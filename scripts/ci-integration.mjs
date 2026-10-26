import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const output = process.env.AUDIT_OUTPUT ?? 'docs/readiness-evidence/2026-10-26';
fs.mkdirSync(output, {recursive: true});
fs.cpSync('.next/static', '.next/standalone/.next/static', {recursive: true});
fs.cpSync('public', '.next/standalone/public', {recursive: true});
assert.equal(fs.existsSync('.next/standalone/ml_model/data'), false, 'Training data must not be packaged');
const python = process.env.PYTHON_EXECUTABLE ?? path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const children = [];

async function start(port, overrides = {}) {
  const log = fs.openSync(path.join(output, `server-${port}.log`), 'w');
  const child = spawn(process.execPath, ['.next/standalone/server.js'], {cwd: root, windowsHide: true,
    env: {...process.env, HOSTNAME: '127.0.0.1', PORT: String(port), PYTHON_EXECUTABLE: python,
      RATE_LIMIT_TOTAL_PER_MINUTE: '1000', RATE_LIMIT_PER_MINUTE: '1000',
      SCAMGUARD_ALLOWED_ORIGINS: 'http://127.0.0.1:3101,http://localhost:3000,chrome-extension://lamffehgecaabedhleppfmgjcagamlih',
      ...overrides}, stdio: ['ignore', log, log]});
  fs.closeSync(log);
  children.push(child);
  for (let attempt = 0; attempt < 60; attempt++) {
    if (child.exitCode !== null) throw new Error(`Test server ${port} exited; see its log`);
    try {
      const response = await fetch(`http://127.0.0.1:${port}/`, {signal: AbortSignal.timeout(1000)});
      if (response.ok) return;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`Test server ${port} did not become ready`);
}

async function run(args, env = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, {windowsHide: true, stdio: 'inherit',
      env: {...process.env, AUDIT_OUTPUT: output, ...env}});
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolve() : reject(new Error(`${args.join(' ')} exited ${code}`)));
  });
}

try {
  await start(3101);
  await run(['--test', '--test-concurrency=1', 'scripts/analyze.integration.test.mjs', 'scripts/api-security.integration.test.mjs'],
    {TEST_APP_URL: 'http://127.0.0.1:3101'});
  await start(3102, {SCAMGUARD_MODEL_PATH: path.join(root, '.local-runtime/missing-ci-model.pkl')});
  await run(['--test', 'scripts/model-unavailable.integration.test.mjs'], {TEST_APP_URL: 'http://127.0.0.1:3102'});
  await start(3103, {RATE_LIMIT_TOTAL_PER_MINUTE: '2'});
  const statuses = [];
  for (let i = 0; i < 3; i++) {
    const response = await fetch(`http://127.0.0.1:3103/api/${i % 2 ? 'ml-classify' : 'analyze'}`, {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Forwarded-For': `198.51.100.${i + 1}`}, body: '{}'});
    statuses.push(response.status);
    if (i === 2) assert.ok(Number(response.headers.get('retry-after')) > 0);
  }
  assert.deepEqual(statuses, [400, 400, 429]);
  console.log('PASS: shared quota cannot be bypassed by rotating forwarding headers.');
  await run(['scripts/browser-audit.mjs'], {TEST_APP_URL: 'http://127.0.0.1:3101'});
  if (process.env.TEST_EXTENSION === '1') {
    await start(3000);
    await run(['scripts/extension-browser.mjs']);
  }
} finally {
  for (const child of children) if (child.exitCode === null) child.kill();
}
