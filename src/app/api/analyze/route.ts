import { NextRequest, NextResponse } from 'next/server';
import { getClientIp, rateLimit } from '@/lib/rate-limit';
import { createAssessment, getRiskLevels } from '@/lib/analysis-assessment';
import { parseInput, runMLClassifier } from '@/lib/ml-inference';
import { checkBrandDomain, getDomain } from '@/lib/url-verify';

export const runtime = 'nodejs';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export async function OPTIONS() {
  return new NextResponse(null, {status: 200, headers: corsHeaders});
}

export async function POST(req: NextRequest) {
  if (!rateLimit(getClientIp(req)).ok) {
    return NextResponse.json({error: 'Too many requests. Please try again later.'}, {status: 429, headers: corsHeaders});
  }
  if (!req.headers.get('content-type')?.includes('application/json')) {
    return NextResponse.json({error: 'Chỉ hỗ trợ văn bản và URL. Ảnh cần OCR local, hiện chưa có trong mô hình.'},
      {status: 415, headers: corsHeaders});
  }
  const input = parseInput(await req.json().catch(() => null));
  if (!input) return NextResponse.json({error: 'Provide text (up to 20,000 characters) or an HTTP URL.'}, {status: 400, headers: corsHeaders});
  const ml = await runMLClassifier(input.text, input.url);
  const assessment = createAssessment(ml, !!ml?.url_result, input.language);
  if (!assessment || !ml) {
    return NextResponse.json({error: 'Mô hình local chưa sẵn sàng hoặc không tương thích. Cần train bộ model hiện tại.'},
      {status: 503, headers: corsHeaders});
  }
  const {riskScore, riskLevel, reasons, detectedPatterns, summary, scam_type, urgent_actions} = assessment;
  const {threatLevel} = getRiskLevels(riskScore);
  const needsReview = riskScore >= 30;
  const domain = getDomain(ml.extracted_url || '');
  const brand = domain ? checkBrandDomain(domain) : null;
  // Domain annotations are separate context. They never bypass ML or modify its score.
  return NextResponse.json({
    ...assessment, risk_score: riskScore, scam_detected: riskScore >= 80, threat_level: threatLevel,
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
