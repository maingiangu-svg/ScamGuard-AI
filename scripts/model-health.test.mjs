import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {test} from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const require = createRequire(import.meta.url);
const source = readFileSync(new URL('../src/app/api/health/route.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: {module: ts.ModuleKind.CommonJS, esModuleInterop: true},
}).outputText;

function fixture() {
  const bundle = Buffer.from('unchanged approved weights');
  const expected = createHash('sha256').update(bundle).digest('hex');
  const state = {manifest: {bundle_sha256: expected}, bundleReads: 0};
  const compiledModule = {exports: {}};
  vm.runInNewContext(compiled, {module: compiledModule, exports: compiledModule.exports,
    process: {cwd: () => '/test-app', env: {}}, Date: {now: () => 1000000},
    require: name => {
      if (name === 'next/server') return {NextResponse: {json: (body, options) => ({body, ...options})}};
      if (name === 'fs' || name === 'node:fs') return {readFileSync: file => {
        if (file.endsWith('hybrid_manifest.json')) return JSON.stringify(state.manifest);
        state.bundleReads++;
        return bundle;
      }};
      return require(name);
    },
  });
  return {state, expected, get: compiledModule.exports.GET};
}

test('declared rejection is visible immediately even when the bundle hash is cached', async () => {
  for (const key of ['historical_nonregression_pass', 'all_policy_nonregression_pass', 'release_approved']) {
    for (const value of [false, null, 'true', 1]) {
      const {state, get} = fixture();
      assert.equal((await get()).status, 200);
      state.manifest[key] = value;
      assert.equal((await get()).status, 503, `${key}=${value}`);
      state.manifest[key] = true;
      assert.equal((await get()).status, 200);
      assert.equal(state.bundleReads, 1, 'Flag checks must not force repeated bundle hashing');
    }
  }
});

test('a changed expected checksum invalidates the health hash cache', async () => {
  const {state, expected, get} = fixture();
  assert.equal((await get()).status, 200);
  assert.equal((await get()).status, 200);
  assert.equal(state.bundleReads, 1);
  state.manifest.bundle_sha256 = '0'.repeat(64);
  assert.equal((await get()).status, 503);
  state.manifest.bundle_sha256 = expected;
  assert.equal((await get()).status, 200);
  assert.equal(state.bundleReads, 3);
});

test('malformed manifest state cannot reuse an earlier healthy result', async () => {
  for (const invalid of [null, [], 'invalid']) {
    const {state, expected, get} = fixture();
    assert.equal((await get()).status, 200);
    state.manifest = invalid;
    const rejected = await get();
    assert.equal(rejected.status, 503);
    assert.equal(rejected.body.status, 'unavailable');
    state.manifest = {bundle_sha256: expected};
    assert.equal((await get()).status, 200);
  }
});
