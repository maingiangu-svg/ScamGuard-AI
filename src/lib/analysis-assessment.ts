import type { ForensicResult } from './types';

export interface MLClassification {
  error?: string;
  ml_risk_score: number | null;
  ml_label: string;
  ml_confidence: number;
  ml_top_signals: string[];
  model_ready: boolean;
  text_result?: { score: number; top_features: string[] } | null;
  url_result?: { score: number; top_features: string[]; urls?: {url: string; score: number}[] } | null;
  url_review_required?: boolean;
  uncertainty?: number;
  action?: string;
  normalized_text?: string;
  extracted_url?: string;
  mode?: string;
  model_prediction_label?: 0 | 1;
  decision_threshold?: number;
  decision_branch?: 'sms' | 'url';
  inference_ms?: number;
  meta_formula?: string | null;
  training?: {
    run_id?: string; method?: string; target?: string;
    text_training_samples?: number; url_training_samples?: number;
    paired_training_samples?: number; paired_holdout_samples?: number;
    synthetic_pairs?: number; probability_calibrated?: boolean;
  };
}

export interface AnalysisAssessment {
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  reasons: string[];
  detectedPatterns: string[];
  summary: string;
  scam_type: string;
  urgent_actions: string[];
}

export function getRiskLevels(score: number): {
  riskLevel: AnalysisAssessment['riskLevel'];
  threatLevel: ForensicResult['threat_level'];
} {
  return {
    riskLevel: score >= 80 ? 'HIGH' : score >= 30 ? 'MEDIUM' : 'LOW',
    threatLevel: score > 90 ? 'CRITICAL' : score >= 80 ? 'HIGH'
      : score >= 30 ? 'MEDIUM' : score > 20 ? 'LOW' : 'SAFE',
  };
}

export function isMLAvailable(ml: MLClassification | null): ml is MLClassification & {ml_risk_score: number} {
  return ml?.model_ready === true && typeof ml.ml_risk_score === 'number'
    && Number.isInteger(ml.ml_risk_score) && ml.ml_risk_score >= 0 && ml.ml_risk_score <= 100
    && Number.isFinite(ml.ml_confidence) && ml.ml_confidence > 0 && ml.ml_confidence <= 100;
}

export function createAssessment(ml: MLClassification | null, hasUrl: boolean, language = 'vi'): AnalysisAssessment | null {
  if (!isMLAvailable(ml)) return null;
  const riskScore = ml.ml_risk_score;
  const urlReview = hasUrl && ml.url_review_required === true;
  // The inference adapter owns branch-specific alert thresholds, before rounding.
  const scoreLevel = ml.action === 'BLOCK' ? 'HIGH' : ml.action === 'REVIEW' ? 'MEDIUM'
    : ml.action === 'CLEAR' ? 'LOW' : getRiskLevels(riskScore).riskLevel;
  const riskLevel = scoreLevel === 'LOW' && urlReview ? 'MEDIUM' : scoreLevel;
  const low = riskLevel === 'LOW';
  const urlOnly = ml.mode === 'hybrid_url_only';
  const vi = language === 'vi';
  const signals = Array.isArray(ml.ml_top_signals)
    ? ml.ml_top_signals.filter((s): s is string => typeof s === 'string' && !!s.trim()) : [];
  return {
    riskScore, riskLevel,
    scam_type: urlReview ? 'URL Requires Independent Review'
      : low ? 'Below Model Thresholds / Unverified' : riskLevel === 'MEDIUM' ? 'Suspicious Content'
      : hasUrl ? 'Suspected URL / Message Risk' : 'Suspected Smishing',
    summary: urlReview
      ? vi ? 'Nhánh URL vượt ngưỡng phát hiện riêng. Điểm chính vẫn là điểm SMS; cần xác minh liên kết trước khi thao tác.'
        : 'The URL branch crossed its own detection threshold. The primary score remains the SMS score; verify the link before acting.'
      : vi
      ? low ? urlOnly
          ? 'Điểm URL chưa đạt ngưỡng phát hiện của mô hình. Website chưa được xác minh trực tiếp; kết quả không bảo đảm an toàn.'
          : 'Điểm mô hình dưới 30. Chưa phát hiện tín hiệu rõ ràng; kết quả không bảo đảm an toàn.'
        : riskLevel === 'MEDIUM' ? urlOnly
          ? 'Điểm URL đạt ngưỡng phát hiện của mô hình. Cần xác minh liên kết qua kênh độc lập.'
          : 'Nội dung nằm trong vùng nghi ngờ 30–79 điểm. Cần xác minh người gửi và yêu cầu qua kênh độc lập.'
        : 'Mô hình đánh giá rủi ro cao. Cần xác minh độc lập trước khi cung cấp thông tin hoặc chuyển tiền.'
      : low ? urlOnly
          ? 'The URL score is below the model detection threshold. The website has not been verified live; this does not guarantee safety.'
          : 'Model score below 30. No clear signals detected; this does not guarantee safety.'
        : riskLevel === 'MEDIUM' ? urlOnly
          ? 'The URL score meets the model detection threshold. Verify the link independently.'
          : 'Model score is in the 30–79 review range. Verify the sender and request independently.'
        : 'The model indicates high risk. Verify independently before sharing credentials or transferring funds.',
    reasons: urlReview ? [vi ? 'Mô hình URL yêu cầu kiểm tra liên kết độc lập với nội dung tin nhắn.'
      : 'The URL model requires link review independently of the message text.'] : low ? [] : signals.length
      ? signals.map(s => (vi ? 'Đặc trưng tăng điểm của mô hình: ' : 'Positive model feature: ') + s)
      : [(vi ? 'Điểm mô hình: ' : 'Model score: ') + riskScore + '/100.'],
    detectedPatterns: low ? [] : signals,
    urgent_actions: low ? [] : [vi ? 'Xác minh qua kênh chính thức trước khi bấm link, chia sẻ OTP hoặc chuyển tiền.'
      : 'Verify through an official channel before opening links, sharing OTPs or sending money.'],
  };
}
