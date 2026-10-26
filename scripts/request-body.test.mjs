import assert from 'node:assert/strict';
import {test} from 'node:test';
import {MAX_JSON_BYTES, readJSONBody} from '../src/lib/request-body.ts';

const request = (body, headers = {'content-type': 'application/json'}) =>
  new Request('http://localhost/api/analyze', {method: 'POST', body, headers});

test('valid JSON including Vietnamese is parsed without changing input', async () => {
  const body = {textInput: 'Xin chào, hãy kiểm tra tin nhắn này.'};
  assert.deepEqual(await readJSONBody(request(JSON.stringify(body))), {body});
});

test('both unsupported media types and malformed JSON fail before inference', async () => {
  assert.equal((await readJSONBody(request('{}', {'content-type': 'text/plain'}))).status, 415);
  assert.equal((await readJSONBody(request('{}', {'content-type': 'application/json-not-really'}))).status, 415);
  assert.equal((await readJSONBody(request('{'))).status, 400);
});

test('declared excessive size is refused without reading the stream', async () => {
  const result = await readJSONBody(request('{}', {
    'content-type': 'application/json', 'content-length': String(MAX_JSON_BYTES + 1),
  }));
  assert.equal(result.status, 413);
});

test('chunked oversized ignored fields cannot bypass the byte cap', async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    pull(controller) {controller.enqueue(new Uint8Array(65536).fill(32));},
    cancel() {cancelled = true;},
  });
  const req = new Request('http://localhost/api/analyze', {
    method: 'POST', body: stream, duplex: 'half', headers: {'content-type': 'application/json'},
  });
  assert.equal((await readJSONBody(req)).status, 413);
  assert.equal(cancelled, true);
});

test('the cap counts UTF-8 bytes rather than JavaScript characters', async () => {
  const body = JSON.stringify({textInput: 'a', ignored: '界'.repeat(Math.ceil(MAX_JSON_BYTES / 3))});
  assert.ok(body.length < MAX_JSON_BYTES);
  assert.equal((await readJSONBody(request(body))).status, 413);
});
