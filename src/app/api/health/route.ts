import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {NextResponse} from 'next/server';

export const runtime = 'nodejs';
let checkedAt = 0;
let ready = false;

export async function GET() {
  if (Date.now() - checkedAt > 10000) {
    try {
      const root = process.cwd();
      const manifest = JSON.parse(readFileSync(path.join(root, 'ml_model/models/hybrid_manifest.json'), 'utf8'));
      const bundle = readFileSync(process.env.SCAMGUARD_MODEL_PATH ?? path.join(root, 'ml_model/models/hybrid_bundle.pkl'));
      ready = createHash('sha256').update(bundle).digest('hex') === manifest.bundle_sha256;
    } catch { ready = false; }
    checkedAt = Date.now();
  }
  return NextResponse.json({status: ready ? 'ok' : 'unavailable'},
    {status: ready ? 200 : 503, headers: {'Cache-Control': 'no-store'}});
}
