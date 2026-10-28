import assert from 'node:assert/strict';
import {test} from 'node:test';
import {parseLinkBatch, validLinkResults} from '../src/lib/link-batch.ts';

test('batch parsing bounds work and only accepts minimized absolute web URLs', () => {
  assert.deepEqual(parseLinkBatch({urls: ['https://example.com/', 'https://example.com/']}), ['https://example.com/']);
  for (const body of [null, {}, {urls: []}, {urls: Array(21).fill('https://example.com/')},
    {urls: ['https://example.com/?secret=1']}, {urls: ['https://user:pass@example.com/']},
    {urls: ['javascript:alert(1)']}, {urls: ['https://example.com/#private']},
    {urls: ['http://localhost:3000/']}, {urls: [12]}, {urls: ['https://example.com/' + 'a'.repeat(4096)]}]) {
    assert.equal(parseLinkBatch(body), null);
  }
});

test('batch output must match every requested URL exactly, with valid model scores', () => {
  const urls = ['https://example.com/'];
  const row = {url: urls[0], riskScore: 1, riskLevel: 'LOW', model_id: 'verified-model:url'};
  assert.equal(validLinkResults({model_ready: true, results: [row]}, urls), true);
  for (const output of [null, {}, {model_ready: false, results: [row]},
    {model_ready: true, results: []}, {model_ready: true, results: [row, row]},
    {model_ready: true, results: [{...row, url: 'https://other.example/'}]},
    {model_ready: true, results: [{...row, riskScore: 101}]},
    {model_ready: true, results: [{...row, riskLevel: 'SAFE'}]}]) {
    assert.equal(validLinkResults(output, urls), false);
  }
});
