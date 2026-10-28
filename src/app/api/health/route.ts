import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {NextResponse} from 'next/server';

export const runtime = 'nodejs';
let checkedAt = 0;
let ready = false;
let checkedBundleIdentity = '';

export async function GET() {
  let gatesPassed = false;
  try {
    const root = process.cwd();
    const manifest = JSON.parse(readFileSync(path.join(root, 'ml_model/models/hybrid_manifest.json'), 'utf8'));
    gatesPassed = manifest !== null && typeof manifest === 'object' && !Array.isArray(manifest) &&
      ['historical_nonregression_pass', 'all_policy_nonregression_pass', 'release_approved']
        .every(gate => !(gate in manifest) || manifest[gate] === true);
    const bundlePath = process.env.SCAMGUARD_MODEL_PATH ?? path.join(root, 'ml_model/models/hybrid_bundle.pkl');
    const identity = `${bundlePath}:${manifest.bundle_sha256}`;
    if (gatesPassed && (Date.now() - checkedAt > 10000 || identity !== checkedBundleIdentity)) {
      const bundle = readFileSync(bundlePath);
      ready = createHash('sha256').update(bundle).digest('hex') === manifest.bundle_sha256;
      checkedAt = Date.now();
      checkedBundleIdentity = identity;
    }
  } catch {
    ready = false;
    checkedAt = 0;
  }
  const available = ready && gatesPassed;
  return NextResponse.json({status: available ? 'ok' : 'unavailable'},
    {status: available ? 200 : 503, headers: {'Cache-Control': 'no-store'}});
}
