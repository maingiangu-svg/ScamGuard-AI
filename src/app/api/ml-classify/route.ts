import { NextRequest, NextResponse } from 'next/server';
import { getMLInputError, parseInput, runMLClassifier } from '@/lib/ml-inference';
import { isMLAvailable } from '@/lib/analysis-assessment';
import { readJSONBody } from '@/lib/request-body';
import { apiHeaders, allowedOrigin } from '@/lib/api-policy';
import { requestLimit } from '@/lib/rate-limit';

export const runtime = 'nodejs';
export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, {status: allowedOrigin(req) ? 204 : 403, headers: apiHeaders(req)});
}
export async function POST(req: NextRequest) {
  const corsHeaders = apiHeaders(req);
  if (!allowedOrigin(req)) return NextResponse.json({error: 'Origin not allowed.'}, {status: 403, headers: corsHeaders});
  const quota = requestLimit(req);
  if (!quota.ok) return NextResponse.json({error: 'Too many requests. Please try again later.'},
    {status: 429, headers: {...corsHeaders, 'Retry-After': String(quota.retryAfter)}});
  const payload = await readJSONBody(req);
  if ('error' in payload) return NextResponse.json({error: payload.error}, {status: payload.status, headers: corsHeaders});
  const input = parseInput(payload.body);
  if (!input) return NextResponse.json({error: 'Provide valid text or URL.'}, {status: 400, headers: corsHeaders});
  const result = await runMLClassifier(input.text, input.url);
  const inputError = getMLInputError(result, input.language);
  if (inputError) return NextResponse.json({error: inputError}, {status: 400, headers: corsHeaders});
  if (!isMLAvailable(result)) {
    return NextResponse.json({error: 'Local model unavailable or busy. Please try again later.', model_ready: false},
      {status: 503, headers: corsHeaders});
  }
  return NextResponse.json(result, {headers: corsHeaders});
}
