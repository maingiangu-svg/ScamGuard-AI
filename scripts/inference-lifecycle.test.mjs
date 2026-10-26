import assert from 'node:assert/strict';
import path from 'node:path';
import {test} from 'node:test';
import {runMLClassifier} from '../src/lib/ml-inference.ts';

async function withExecutable(executable, action) {
  const previous = process.env.PYTHON_EXECUTABLE;
  try {
    process.env.PYTHON_EXECUTABLE = executable;
    return await action();
  } finally {
    if (previous === undefined) delete process.env.PYTHON_EXECUTABLE;
    else process.env.PYTHON_EXECUTABLE = previous;
  }
}

const classify = () => runMLClassifier('Hello, are you free for lunch tomorrow?', '');

test('failed Python startup releases admission for later valid inference', async () => {
  const results = await withExecutable(path.resolve('.local-runtime/audit/missing-python.exe'),
    () => Promise.all([classify(), classify()]));
  assert.deepEqual(results, [null, null]);
  assert.equal((await classify()).model_ready, true);
});

test('nonzero child exit releases admission for later valid inference', async () => {
  // Node cannot execute the Python source; this produces a real child-process failure.
  const results = await withExecutable(process.execPath, () => Promise.all([classify(), classify()]));
  assert.deepEqual(results, [null, null]);
  assert.equal((await classify()).model_ready, true);
});

test('excess work is rejected without preventing recovery after completion', async () => {
  const results = await Promise.all([classify(), classify(), classify()]);
  assert.equal(results.filter(value => value?.model_ready).length, 2);
  assert.equal(results.filter(value => value === null).length, 1);
  assert.equal((await classify()).model_ready, true);
});
