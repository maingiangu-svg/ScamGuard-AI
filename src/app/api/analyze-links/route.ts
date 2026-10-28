import {NextRequest, NextResponse} from 'next/server';
import {allowedOrigin, apiHeaders} from '@/lib/api-policy';
import {requestLimit} from '@/lib/rate-limit';
import {readJSONBody} from '@/lib/request-body';
import {parseLinkBatch, validLinkResults} from '@/lib/link-batch';
import {runMLLinkBatch} from '@/lib/ml-inference';

export const runtime = 'nodejs';

export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, {status: allowedOrigin(req) ? 204 : 403, headers: apiHeaders(req)});
}

export async function POST(req: NextRequest) {
  const headers = apiHeaders(req);
  if (!allowedOrigin(req)) return NextResponse.json({error: 'Origin not allowed.'}, {status: 403, headers});
  const quota = requestLimit(req);
  if (!quota.ok) return NextResponse.json({error: 'Too many requests.'},
    {status: 429, headers: {...headers, 'Retry-After': String(quota.retryAfter)}});
  const payload = await readJSONBody(req);
  if ('error' in payload) return NextResponse.json({error: payload.error}, {status: payload.status, headers});
  const urls = parseLinkBatch(payload.body);
  if (!urls) return NextResponse.json({error: 'Provide 1–20 minimized HTTP/HTTPS URLs.'}, {status: 400, headers});
  const result = await runMLLinkBatch(urls);
  if (!validLinkResults(result, urls)) return NextResponse.json({error: 'Local model unavailable or busy.'}, {status: 503, headers});
  return NextResponse.json({results: result.results}, {headers});
}
