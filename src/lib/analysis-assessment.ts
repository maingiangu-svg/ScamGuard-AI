import type { ForensicResult } from './types';

type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface MLClassification {
  ml_risk_score: number;
  ml_label: string;
  ml_confidence: number;
  ml_top_signals: string[];
  model_ready: boolean;
}

export interface AnalysisAssessment {
  riskScore: number;
  riskLevel: RiskLevel;
  reasons: string[];
  detectedPatterns: string[];
  summary: string;
  scam_type: string;
  urgent_actions: string[];
}

export function getRiskLevels(score: number): {
  riskLevel: RiskLevel;
  threatLevel: ForensicResult['threat_level'];
} {
  return {
    riskLevel: score > 70 ? 'HIGH' : score > 40 ? 'MEDIUM' : 'LOW',
    threatLevel: score > 90 ? 'CRITICAL' : score > 70 ? 'HIGH'
      : score > 40 ? 'MEDIUM' : score > 20 ? 'LOW' : 'SAFE',
  };
}

function validScore(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 100;
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : [];
}

export function isMLAvailable(ml: MLClassification | null): ml is MLClassification {
  return !!ml?.model_ready && validScore(ml.ml_risk_score)
    && Number.isFinite(ml.ml_confidence) && ml.ml_confidence > 0 && ml.ml_confidence <= 100;
}

export function createAssessment(
  gemini: Partial<AnalysisAssessment> | null,
  ml: MLClassification | null,
  hasUrl: boolean,
): AnalysisAssessment | null {
  const geminiScore = validScore(gemini?.riskScore) ? gemini.riskScore : null;
  const mlScore = isMLAvailable(ml) ? ml.ml_risk_score : null;
  if (geminiScore === null && mlScore === null) return null;

  const riskScore = geminiScore !== null && mlScore !== null
    ? Math.round(0.4 * mlScore + 0.6 * geminiScore)
    : (mlScore ?? geminiScore)!;
  const { riskLevel } = getRiskLevels(riskScore);
  const geminiAgrees = geminiScore !== null && getRiskLevels(geminiScore).riskLevel === riskLevel;
  const lowRisk = riskLevel === 'LOW';
  const highRisk = riskLevel === 'HIGH';
  const signals = mlScore !== null ? strings(ml?.ml_top_signals) : [];
  const reasons = geminiAgrees ? strings(gemini?.reasons)
    : signals.map(signal => `Tín hiệu mô hình: ${signal}`);
  const category = highRisk
    ? (hasUrl ? 'Suspected URL Phishing' : 'Suspected Spam / Scam Message')
    : (lowRisk ? 'No Scam Indicators Detected' : 'Suspicious Content');

  return {
    riskScore,
    riskLevel,
    scam_type: highRisk && geminiAgrees && typeof gemini?.scam_type === 'string' && gemini.scam_type.trim()
      ? gemini.scam_type : category,
    summary: lowRisk
      ? 'Không phát hiện dấu hiệu lừa đảo rõ ràng trong nội dung đã nhập. Kết quả này không bảo đảm an toàn tuyệt đối.'
      : geminiAgrees && typeof gemini?.summary === 'string' && gemini.summary.trim()
      ? gemini.summary
      : highRisk
      ? 'Nội dung được đánh giá có nguy cơ lừa đảo cao. Cần kiểm chứng độc lập trước khi làm theo yêu cầu.'
      : 'Nội dung có tín hiệu đáng ngờ. Cần thêm ngữ cảnh và kiểm chứng trước khi kết luận.',
    reasons: lowRisk ? [] : reasons.length ? reasons : [`Điểm rủi ro do mô hình dự đoán: ${riskScore}/100.`],
    detectedPatterns: lowRisk ? [] : geminiAgrees ? strings(gemini?.detectedPatterns) : signals,
    urgent_actions: lowRisk ? [] : geminiAgrees && strings(gemini?.urgent_actions).length
      ? strings(gemini?.urgent_actions)
      : ['Xác minh yêu cầu qua kênh chính thức trước khi cung cấp thông tin hoặc chuyển tiền.'],
  };
}
