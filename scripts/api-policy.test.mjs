import assert from 'node:assert/strict';
import {test} from 'node:test';
import {getClientIp, rateLimit} from '../src/lib/rate-limit.ts';
import {apiHeaders, allowedOrigin} from '../src/lib/api-policy.ts';

test('forwarding headers are ignored unless proxy hops are explicitly trusted', () => {
  const req = new Request('https://app.example/api/analyze', {headers: {
    'x-forwarded-for': '198.51.100.1, 203.0.113.2', 'x-real-ip': '198.51.100.9',
  }});
  assert.equal(getClientIp(req, 0), 'anonymous');
  assert.equal(getClientIp(req, 1), '203.0.113.2');
  assert.equal(getClientIp(req, 2), '198.51.100.1');
  assert.equal(getClientIp(req, 3), 'anonymous');
  assert.equal(getClientIp(new Request(req.url, {headers: {'x-forwarded-for': 'not-an-ip'}}), 1), 'anonymous');
});

test('bounded buckets reject new identities without evicting an exhausted identity', () => {
  const now = Number.MAX_SAFE_INTEGER - 10000000;
  assert.equal(rateLimit('test-a', 1, now, 3).ok, true);
  assert.equal(rateLimit('test-b', 1, now, 3).ok, true);
  assert.equal(rateLimit('test-c', 1, now, 3).ok, true);
  assert.equal(rateLimit('test-d', 1, now, 3).ok, false);
  assert.equal(rateLimit('test-a', 1, now, 3).ok, false);
  assert.equal(rateLimit('test-d', 1, now + 60000, 3).ok, true);
});

test('origin policy accepts same-origin and explicit allowlist, rejecting lookalikes', () => {
  const request = origin => new Request('https://app.example/api/analyze', {headers: {origin}});
  assert.equal(allowedOrigin(request('https://app.example'), ['https://app.example']), true);
  assert.equal(allowedOrigin(new Request('http://attacker.example/api/analyze', {
    headers: {host: 'attacker.example', origin: 'http://attacker.example'},
  }), []), false);
  assert.equal(allowedOrigin(request('https://other.example'), ['https://other.example']), true);
  for (const origin of ['null', 'https://app.example.evil.test', 'https://other.example/path']) {
    assert.equal(allowedOrigin(request(origin), ['https://other.example']), false);
  }
  assert.equal(allowedOrigin(new Request('https://app.example/api/analyze'), []), true);
  const extensionOrigin = 'chrome-extension://lamffehgecaabedhleppfmgjcagamlih';
  assert.equal(allowedOrigin(request(extensionOrigin), [extensionOrigin]), true);
  assert.equal(allowedOrigin(request(extensionOrigin), []), false);
  assert.equal(allowedOrigin(new Request('http://localhost:3101/api/analyze', {
    headers: {host: '127.0.0.1:3101', origin: 'http://127.0.0.1:3101'},
  }), ['http://127.0.0.1:3101']), true);
});

test('API responses disable caching and never grant wildcard CORS', () => {
  const req = new Request('http://localhost:3000/api/analyze', {headers: {origin: 'http://localhost:3000'}});
  const headers = apiHeaders(req);
  assert.equal(headers['Cache-Control'], 'no-store');
  assert.equal(headers['Access-Control-Allow-Origin'], 'http://localhost:3000');
  assert.match(headers.Vary, /Origin/);
  const denied = apiHeaders(new Request(req.url, {headers: {origin: 'https://evil.test'}}));
  assert.equal(denied['Access-Control-Allow-Origin'], undefined);
});
