export interface ExternalEvidenceItem {
  title: string;
  source_url: string;
}

export interface WebIntelligence {
  detected: boolean;
  url: string | null;
  domain: string | null;
  brand_detected: string | null;
  domain_match: "match" | "mismatch" | "unknown";
  website_status: "accessible" | "unavailable" | "unknown";
  suspicious_indicators: string[];
  external_evidence: ExternalEvidenceItem[];
  confidence: number;
  verified_live?: boolean;
  http_status?: number | null;
}

export interface RedFlagItem {
  evidence: string;
  official_fact: string;
  official_link?: string | null;
  explanation: string;
}

export interface ForensicResult {
  scam_detected: boolean;
  risk_score: number;
  threat_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "SAFE";
  scam_type: string;
  executive_summary: string;
  web_intelligence?: WebIntelligence;
  red_flags: RedFlagItem[];
  psychological_tricks: { tactic: string; target_emotion: string; analysis: string }[];
  next_move_prediction: string;
  urgent_actions: string[];
  family_alert_card: { headline: string; key_warning: string; shareable_text: string };
}

export interface RoleplayMessage {
  id: string;
  sender: "scammer" | "user" | "eval";
  text: string;
  evalStatus?: "safe" | "danger";
}
