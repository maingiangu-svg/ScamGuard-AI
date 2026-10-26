import { NextRequest, NextResponse } from 'next/server';
import { requestLimit } from '@/lib/rate-limit';
import { apiHeaders, allowedOrigin } from '@/lib/api-policy';
import { createAssessment, getRiskLevels } from '@/lib/analysis-assessment';
import { getMLInputError, parseInput, runMLClassifier } from '@/lib/ml-inference';
import { checkBrandDomain, getDomain } from '@/lib/url-verify';
import { readJSONBody } from '@/lib/request-body';

export const runtime = 'nodejs';

export async function OPTIONS(req: NextRequest) {
  return new NextResponse(null, {status: allowedOrigin(req) ? 204 : 403, headers: apiHeaders(req)});
}

export async function POST(req: NextRequest) {
  const corsHeaders = apiHeaders(req);
  if (!allowedOrigin(req)) return NextResponse.json({error: 'Origin not allowed.'}, {status: 403, headers: corsHeaders});
  const quota = requestLimit(req);
  if (!quota.ok) {
    return NextResponse.json({error: 'Too many requests. Please try again later.'},
      {status: 429, headers: {...corsHeaders, 'Retry-After': String(quota.retryAfter)}});
  }
  const payload = await readJSONBody(req);
  if ('error' in payload) return NextResponse.json({error: payload.error}, {status: payload.status, headers: corsHeaders});
  const input = parseInput(payload.body);
  if (!input) return NextResponse.json({error: 'Provide text (up to 20,000 characters) or an HTTP URL.'}, {status: 400, headers: corsHeaders});
  const ml = await runMLClassifier(input.text, input.url);
  const inputError = getMLInputError(ml, input.language);
  if (inputError) return NextResponse.json({error: inputError}, {status: 400, headers: corsHeaders});
  const assessment = createAssessment(ml, !!ml?.url_result, input.language);
  if (!assessment || !ml) {
    return NextResponse.json({error: 'Mô hình local chưa sẵn sàng, không tương thích hoặc đang bận. Vui lòng thử lại sau.'},
      {status: 503, headers: corsHeaders});
  }
  const {riskScore, riskLevel, reasons, detectedPatterns, summary, scam_type, urgent_actions} = assessment;
  const threatLevel = riskLevel === 'HIGH' ? getRiskLevels(riskScore).threatLevel
    : riskLevel === 'MEDIUM' ? 'MEDIUM' : 'LOW';
  const needsReview = riskLevel !== 'LOW';
  const domain = getDomain(ml.extracted_url || '');
  const brand = domain ? checkBrandDomain(domain) : null;
  // Domain annotations are separate context. They never bypass ML or modify its score.
  return NextResponse.json({
    ...assessment, risk_score: riskScore, scam_detected: riskLevel === 'HIGH', threat_level: threatLevel,
    executive_summary: summary, scam_type, urgent_actions,
    web_intelligence: {
      detected: !!domain, url: ml.extracted_url || null, domain,
      brand_detected: brand?.brand ?? null, domain_match: brand?.match ?? 'unknown',
      website_status: 'unknown', verified_live: false, confidence: 0,
      suspicious_indicators: [], external_evidence: [],
    },
    red_flags: needsReview ? reasons.map(evidence => ({
      evidence, official_fact: 'Model-derived signal; not independently verified.', explanation: evidence,
    })) : [],
    psychological_tricks: [], next_move_prediction: 'Not evaluated by this classifier.',
    family_alert_card: {
      headline: riskLevel === 'HIGH' ? 'HIGH MODEL RISK' : needsReview ? 'VERIFY BEFORE ACTING' : 'NO CLEAR MODEL SIGNALS',
      key_warning: summary, shareable_text: summary,
    },
    detectedPatterns,
    ml_classifier: {
      ...ml, text_score: ml.text_result ? Math.round(ml.text_result.score * 100) : null,
      url_score: ml.url_result ? Math.round(ml.url_result.score * 100) : null,
      text_tokens: ml.text_result?.top_features ?? [], url_signals: ml.url_result?.top_features ?? [],
    },
  }, {headers: corsHeaders});
}
