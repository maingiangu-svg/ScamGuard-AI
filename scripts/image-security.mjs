import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

export function assessImage(report) {
  if (report?.ArtifactType !== 'container_image' || !report.Metadata?.ImageID
      || !report.Metadata?.OS?.Family || !Array.isArray(report.Results)
      || !report.Results.some(result => result.Class === 'os-pkgs')) {
    throw new Error('A completed container image scan with OS inventory is required.');
  }
  const findings = report.Results.flatMap(result => result.Vulnerabilities ?? [])
    .filter(finding => ['HIGH', 'CRITICAL'].includes(finding.Severity));
  const identified = pkg => typeof pkg.Name === 'string' && !!pkg.Name
    && typeof pkg.Version === 'string' && !!pkg.Version;
  const packages = new Set(report.Results.filter(result => result.Class === 'os-pkgs')
    .flatMap(result => result.Packages ?? []).filter(identified).map(pkg => pkg.Name));
  if (findings.length === 0 && (!['libbz2-1.0', 'libdb5.3t64', 'libffi8', 'liblzma5', 'libsqlite3-0',
    'libc6', 'libstdc++6', 'libgcc-s1', 'libgomp1', 'libssl3t64', 'libzstd1', 'zlib1g'].every(name => packages.has(name))
      || !['node-pkg', 'python-pkg'].every(type => report.Results.some(result => result.Type === type
        && Array.isArray(result.Packages) && result.Packages.length > 0 && result.Packages.every(identified))))) {
    throw new Error('Runtime library and Node/Python package inventory is incomplete.');
  }
  return {pass: findings.length === 0, image: report.Metadata.ImageID,
    high: findings.filter(finding => finding.Severity === 'HIGH').length,
    critical: findings.filter(finding => finding.Severity === 'CRITICAL').length,
    uniqueHighCritical: new Set(findings.map(finding => finding.VulnerabilityID)).size,
    fixable: findings.filter(finding => !!finding.FixedVersion).length};
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const result = assessImage(JSON.parse(readFileSync(process.argv[2], 'utf8')));
    console.log(JSON.stringify(result, null, 2));
    if (!result.pass) process.exitCode = 1;
  } catch (error) {console.error(error.message); process.exitCode = 1;}
}
