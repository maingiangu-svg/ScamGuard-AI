import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {assessImage} from './image-security.mjs';

const report = (vulnerabilities = []) => ({ArtifactType: 'container_image',
  Metadata: {ImageID: 'sha256:fixture', OS: {Family: 'debian', Name: '13'}},
  Results: [{Class: 'os-pkgs', Target: 'fixture', Vulnerabilities: vulnerabilities,
    Packages: ['libbz2-1.0', 'libdb5.3t64', 'libffi8', 'liblzma5', 'libsqlite3-0',
      'libc6', 'libstdc++6', 'libgcc-s1', 'libgomp1', 'libssl3t64', 'libzstd1', 'zlib1g']
      .map(Name => ({Name, Version: '1.0'}))},
    {Class: 'lang-pkgs', Type: 'node-pkg', Packages: [{Name: 'fixture-node', Version: '1.0'}]},
    {Class: 'lang-pkgs', Type: 'python-pkg', Packages: [{Name: 'fixture-python', Version: '1.0'}]}]});

test('blocks high findings even without an upstream fixed version', () => {
  const verdict = assessImage(report([{VulnerabilityID: 'CVE-fixture', Severity: 'HIGH', Status: 'affected'}]));
  assert.equal(verdict.pass, false);
  assert.equal(verdict.high, 1);
  assert.equal(verdict.fixable, 0);
});

test('counts advisory identities separately from affected packages', () => {
  const verdict = assessImage(report([
    {VulnerabilityID: 'CVE-shared', Severity: 'CRITICAL'},
    {VulnerabilityID: 'CVE-shared', Severity: 'CRITICAL'},
    {VulnerabilityID: 'CVE-medium', Severity: 'MEDIUM'},
  ]));
  assert.equal(verdict.pass, false);
  assert.equal(verdict.critical, 2);
  assert.equal(verdict.uniqueHighCritical, 1);
});

test('missing scan evidence cannot become a clean verdict', () => {
  for (const value of [null, {}, {Results: []}, {...report(), ArtifactType: 'filesystem'}]) {
    assert.throws(() => assessImage(value), /image scan/i);
  }
  assert.equal(assessImage(report()).pass, true);
});

test('rejects incomplete native and language package inventories', () => {
  const missingLibrary = report();
  missingLibrary.Results[0].Packages.pop();
  assert.throws(() => assessImage(missingLibrary), /inventory/i);
  const missingPython = report();
  missingPython.Results.pop();
  assert.throws(() => assessImage(missingPython), /inventory/i);
  const emptyPython = report();
  emptyPython.Results[2].Packages = [];
  assert.throws(() => assessImage(emptyPython), /inventory/i);
});

test('the previous runtime image fails the new unsuppressed gate', () => {
  const previous = JSON.parse(readFileSync('docs/readiness-evidence/2026-10-26/container-scan-after.json', 'utf8'));
  const verdict = assessImage(previous);
  assert.equal(verdict.pass, false);
  assert.equal(verdict.high, 44);
  assert.equal(verdict.uniqueHighCritical, 8);
});
