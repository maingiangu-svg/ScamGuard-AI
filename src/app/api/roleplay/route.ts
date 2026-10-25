import { NextResponse } from 'next/server';

export async function POST() {
  // A text/URL risk classifier has no training target for evaluating defensive dialogue.
  return NextResponse.json({
    error: 'Roleplay is unavailable: no locally trained dialogue evaluation model is installed.',
  }, {status: 501});
}
