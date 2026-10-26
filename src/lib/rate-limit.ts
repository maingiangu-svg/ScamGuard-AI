import {isIP} from 'node:net';

type Bucket = {count: number; resetAt: number};
const state = globalThis as typeof globalThis & {scamguardRateBuckets?: Map<string, Bucket>};
const buckets = state.scamguardRateBuckets ??= new Map<string, Bucket>();
const positive = (value: string | undefined, fallback: number) =>
  Number.isSafeInteger(Number(value)) && Number(value) > 0 ? Number(value) : fallback;

export function rateLimit(key: string, limit = positive(process.env.RATE_LIMIT_PER_MINUTE, 10),
                          now = Date.now(), maxEntries = 4096): {ok: boolean; remaining: number; retryAfter: number} {
  for (const [identity, bucket] of buckets) if (now >= bucket.resetAt) buckets.delete(identity);
  let entry = buckets.get(key);
  if (!entry) {
    if (buckets.size >= maxEntries) return {ok: false, remaining: 0, retryAfter: 60};
    entry = {count: 0, resetAt: now + 60000};
    buckets.set(key, entry);
  }
  const retryAfter = Math.max(1, Math.ceil((entry.resetAt - now) / 1000));
  if (entry.count >= limit) return {ok: false, remaining: 0, retryAfter};
  entry.count++;
  return {ok: true, remaining: limit - entry.count, retryAfter};
}

export function getClientIp(req: Request, trustedHops = Number(process.env.SCAMGUARD_TRUSTED_PROXY_HOPS ?? 0)): string {
  // Configure only when ingress guarantees exactly this many trusted proxy hops.
  if (!Number.isSafeInteger(trustedHops) || trustedHops <= 0) return 'anonymous';
  const addresses = (req.headers.get('x-forwarded-for') ?? '').split(',').map(value => value.trim());
  const candidate = addresses[addresses.length - trustedHops];
  return candidate && isIP(candidate) ? candidate : 'anonymous';
}

export function requestLimit(req: Request) {
  const overall = rateLimit('total', positive(process.env.RATE_LIMIT_TOTAL_PER_MINUTE, 60));
  if (!overall.ok) return overall;
  const identity = getClientIp(req);
  return identity === 'anonymous' ? overall : rateLimit('ip:' + identity);
}
