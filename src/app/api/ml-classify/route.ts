import { NextRequest, NextResponse } from 'next/server';
import { parseInput, runMLClassifier } from '@/lib/ml-inference';
import { isMLAvailable } from '@/lib/analysis-assessment';

export const runtime = 'nodejs';
const corsHeaders = {
  'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
export async function OPTIONS() {
  return new NextResponse(null, {status: 200, headers: corsHeaders});
}
export async function POST(req: NextRequest) {
  const input = parseInput(await req.json().catch(() => null));
  if (!input) return NextResponse.json({error: 'Provide valid text or URL.'}, {status: 400, headers: corsHeaders});
  const result = await runMLClassifier(input.text, input.url);
  if (!isMLAvailable(result)) {
    return NextResponse.json({error: 'Local model unavailable.', model_ready: false},
      {status: 503, headers: corsHeaders});
  }
  return NextResponse.json(result, {headers: corsHeaders});
}
