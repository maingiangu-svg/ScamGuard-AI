import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type, Schema } from "@google/genai";
import { enrichWebIntelligence, extractUrls, checkBrandDomain, getDomain } from "@/lib/url-verify";
import { getClientIp, rateLimit } from "@/lib/rate-limit";
import { createAssessment, getRiskLevels, isMLAvailable } from "@/lib/analysis-assessment";
import type { AnalysisAssessment, MLClassification } from "@/lib/analysis-assessment";
import { spawn } from "child_process";
import path from "path";

// ─── ML Pre-Classifier (Python subprocess) ───────────────────────────────────
async function runMLClassifier(text: string, url: string): Promise<MLClassification | null> {
  return new Promise((resolve) => {
    const scriptPath = path.join(process.cwd(), "ml_model", "predict.py");
    const payload = JSON.stringify({ text: text.slice(0, 2000), url });
    const python = spawn("python3", [scriptPath], { cwd: process.cwd(), timeout: 8000 });
    let out = "";
    let errOut = "";
    python.stdin.write(payload);
    python.stdin.end();
    python.stdout.on("data", (d: Buffer) => { out += d.toString(); });
    python.stderr.on("data", (d: Buffer) => { errOut += d.toString(); });
    python.on("close", (code: number) => {
      if (code !== 0 || !out.trim()) { resolve(null); return; }
      try { resolve(JSON.parse(out.trim())); }
      catch { resolve(null); }
    });
    python.on("error", () => resolve(null));
  });
}

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

const FORENSIC_SCHEMA: Schema = {
  type: Type.OBJECT,
  properties: {
    riskScore: { type: Type.INTEGER },
    riskLevel: { type: Type.STRING, enum: ["LOW", "MEDIUM", "HIGH"] },
    reasons: { type: Type.ARRAY, items: { type: Type.STRING } },
    detectedPatterns: { type: Type.ARRAY, items: { type: Type.STRING } },
    summary: { type: Type.STRING },
    scam_type: { type: Type.STRING },
    urgent_actions: { type: Type.ARRAY, items: { type: Type.STRING } },
  },
  required: ["riskScore", "riskLevel", "reasons", "detectedPatterns", "summary"],
};

function checkWhitelist(urlStr: string): { isWhitelisted: boolean; domain: string | null; brand: string | null } {
  if (!urlStr) return { isWhitelisted: false, domain: null, brand: null };
  try {
    let hostname = "";
    if (urlStr.startsWith("http://") || urlStr.startsWith("https://")) {
      hostname = new URL(urlStr).hostname.toLowerCase().replace(/^www\./, "");
    } else {
      hostname = urlStr.toLowerCase().split("/")[0].replace(/^www\./, "").split(":")[0];
    }

    if (hostname.endsWith(".edu.vn") || hostname.endsWith(".gov.vn") || hostname.endsWith(".gov") || hostname.endsWith(".edu")) {
      return { isWhitelisted: true, domain: hostname, brand: "Official Government / Academic Entity" };
    }

    const whitelistDomains: Record<string, string> = {
      "google.com": "Google",
      "google.com.vn": "Google Vietnam",
      "facebook.com": "Facebook",
      "fb.com": "Facebook",
      "zalo.me": "Zalo",
      "zalo.vn": "Zalo",
      "youtube.com": "YouTube",
      "github.com": "GitHub",
      "microsoft.com": "Microsoft",
      "apple.com": "Apple",
      "vietcombank.com.vn": "Vietcombank",
      "vcbdigibank.com.vn": "Vietcombank",
      "shopee.vn": "Shopee",
      "t.me": "Telegram Official",
      "telegram.org": "Telegram Official",
      "vneid.gov.vn": "VNeID Official Public Portal",
      "chongluadao.vn": "ChongLuaDao Security Portal",
      "khonggianmang.vn": "National Cyber Security Center (NCSC)"
    };

    for (const [domain, brandName] of Object.entries(whitelistDomains)) {
      if (hostname === domain || hostname.endsWith(`.${domain}`)) {
        return { isWhitelisted: true, domain: hostname, brand: brandName };
      }
    }
  } catch {}
  return { isWhitelisted: false, domain: null, brand: null };
}

function buildStructuredResponse(
  riskScore: number,
  reasons: string[],
  detectedPatterns: string[],
  summary: string,
  scamType?: string,
  urgentActions?: string[],
  webIntel?: any
): any {
  const { riskLevel, threatLevel } = getRiskLevels(riskScore);
  const scamDetected = riskLevel === "HIGH";
  const needsReview = riskLevel !== "LOW";

  return {
    riskScore,
    riskLevel,
    reasons: reasons.length ? reasons : ["No critical security risks or fraudulent patterns identified."],
    detectedPatterns,
    summary,
    scam_detected: scamDetected,
    risk_score: riskScore,
    threat_level: threatLevel,
    scam_type: scamType || (needsReview ? "Suspicious Content" : "No Scam Indicators Detected"),
    executive_summary: summary,
    web_intelligence: webIntel || {
      detected: false,
      url: null,
      domain: null,
      brand_detected: null,
      domain_match: "unknown",
      website_status: "unknown",
      suspicious_indicators: detectedPatterns,
      external_evidence: [],
      confidence: 0,
      verified_live: false,
    },
    red_flags: needsReview ? reasons.map((r) => ({
      evidence: r,
      official_fact: "Tín hiệu dựa trên nội dung được cung cấp; chưa được xác minh bằng nguồn độc lập.",
      explanation: r,
    })) : [],
    psychological_tricks: [],
    next_move_prediction: needsReview ? "Chưa đủ dữ liệu để dự đoán hành vi tiếp theo." : "None",
    urgent_actions: urgentActions || (needsReview ? [
      "Verify requests independently before sharing information or transferring money.",
    ] : []),
    family_alert_card: {
      headline: scamDetected ? `${threatLevel} RISK ALERT` : needsReview ? "SUSPICIOUS CONTENT — VERIFY FIRST" : "NO CLEAR SCAM INDICATORS",
      key_warning: needsReview ? "Verify requests before sharing credentials or transferring money." : "No clear scam indicators detected. This does not guarantee safety.",
      shareable_text: needsReview ? "⚠️ Verify suspicious content independently before acting." : "No clear scam indicators detected in the provided content; continue to verify unusual requests.",
    },
  };
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: corsHeaders,
  });
}

export async function POST(req: NextRequest) {
  try {
    const ip = getClientIp(req);
    const { ok } = rateLimit(ip);
    if (!ok) {
      return NextResponse.json(
        { error: "Too many requests. Please try again after 1 minute." },
        { status: 429, headers: corsHeaders }
      );
    }

    const contentType = req.headers.get("content-type") || "";
    let url = "";
    let title = "";
    let bodyText = "";
    let sourceText = "";
    let isImage = false;
    let imageBuffer: Buffer | null = null;
    let imageMimeType = "";

    let language = "en";

    if (contentType.includes("multipart/form-data")) {
      const formData = await req.formData();
      const image = formData.get("image") as File;
      language = (formData.get("language") as string) || "en";
      if (!image) {
        return NextResponse.json({ error: "No image file provided" }, { status: 400, headers: corsHeaders });
      }
      imageBuffer = Buffer.from(await image.arrayBuffer());
      imageMimeType = image.type;
      isImage = true;
      sourceText = "[image analysis]";
    } else {
      const body = await req.json().catch(() => ({}));
      url = body.url || "";
      title = body.title || "";
      bodyText = body.bodyText || body.textInput || "";
      language = body.language || "en";

      if (!url && !title && !bodyText) {
        return NextResponse.json({ error: "Request payload is empty" }, { status: 400, headers: corsHeaders });
      }

      sourceText = bodyText || url || title;
    }

    // 1. Whitelist Domain Check (.edu, .gov, Google, Facebook, etc.)
    const targetUrlForWhitelist = url || extractUrls(sourceText)[0] || "";
    const { isWhitelisted, domain: wlDomain, brand: wlBrand } = checkWhitelist(targetUrlForWhitelist);

    if (isWhitelisted && wlDomain) {
      const whitelistResult = buildStructuredResponse(
        0,
        [`Domain ${wlDomain} is on the official verified whitelist.`],
        [],
        `Verified legitimate website belonging to ${wlBrand || wlDomain}.`,
        "Legitimate Website (Whitelisted)",
        ["Safe to continue browsing."],
        {
          detected: true,
          url: targetUrlForWhitelist,
          domain: wlDomain,
          brand_detected: wlBrand,
          domain_match: "match",
          website_status: "accessible",
          suspicious_indicators: [],
          external_evidence: [{ title: `Official website of ${wlBrand}`, source_url: `https://${wlDomain}` }],
          confidence: 100,
          verified_live: true,
        }
      );
      return NextResponse.json(whitelistResult, { headers: corsHeaders });
    }

    // 2. Non-whitelisted domain: Send url, title, bodyText to Gemini 2.5 Flash
    const apiKey = process.env.GEMINI_API_KEY;
    let geminiParsed: Partial<AnalysisAssessment> | null = null;

    if (apiKey && apiKey.trim() !== "" && apiKey !== "your_gemini_api_key_here") {
      try {
        const ai = new GoogleGenAI({ apiKey });
        let contents: any[] = [];

        if (isImage && imageBuffer) {
          contents = [
            { inlineData: { mimeType: imageMimeType, data: imageBuffer.toString("base64") } },
            { text: "Perform digital forensic analysis on this image to evaluate scam, phishing, or financial fraud indicators." },
          ];
        } else {
          contents = [
            {
              text: `Analyze fraud, phishing, and scam risk for the following target content:
URL: ${url || "No URL provided"}
Title: ${title || "No title provided"}
Body/Content: ${bodyText || "No detailed text provided"}`,
            },
          ];
        }

        const isVi = language === "vi";
        const response = await ai.models.generateContent({
          model: "gemini-2.5-flash",
          contents,
          config: {
            systemInstruction: `You are ScamShield Forensic AI - An advanced multimodal cyber deception and fraud intelligence engine.
Evaluate fraud and phishing risk based on the provided URL, Title, and Content data.

Anti-Hallucination & Structured Output Rules:
1. riskLevel must be strictly one of: "LOW", "MEDIUM", "HIGH".
2. riskScore must be an integer between 0 and 100.
3. reasons is an array of specific anomalies, red flags, or fraudulent indicators discovered (written in ${isVi ? "Vietnamese" : "English"}).
4. detectedPatterns is an array describing identified threat patterns (written in ${isVi ? "Vietnamese" : "English"}).
5. summary is a concise ${isVi ? "Vietnamese" : "English"} forensic summary.
6. If evidence is ambiguous or insufficient, default riskLevel to "LOW".`,
            responseMimeType: "application/json",
            responseSchema: FORENSIC_SCHEMA,
          },
        });

        if (response.text) {
          geminiParsed = JSON.parse(response.text);
        }
      } catch (geminiError: any) {
        console.warn("Gemini API call failed, falling back to the available ML model:", geminiError?.message || geminiError);
      }
    }

    // The local classifiers support text and URLs, not image pixels.
    const mlResult = isImage ? null : await runMLClassifier(sourceText, targetUrlForWhitelist);
    const assessment = createAssessment(geminiParsed, mlResult, !!targetUrlForWhitelist);
    if (!assessment) {
      return NextResponse.json(
        { error: isImage
          ? "Chưa thể phân tích ảnh lúc này. Hãy nhập nội dung văn bản hoặc thử lại sau."
          : "Dịch vụ phân tích chưa sẵn sàng. Vui lòng thử lại sau." },
        { status: 503, headers: corsHeaders }
      );
    }
    const { riskScore, reasons, detectedPatterns, summary, scam_type: scamType, urgent_actions: urgentActions } = assessment;

    let finalResponse: any = buildStructuredResponse(
      riskScore,
      reasons,
      detectedPatterns,
      summary,
      scamType,
      urgentActions
    );

    // Attach ML metadata to response for UI display
    if (mlResult) {
      finalResponse.ml_classifier = {
        ml_risk_score  : mlResult.ml_risk_score,
        ml_label       : mlResult.ml_label,
        ml_confidence  : mlResult.ml_confidence,
        ml_top_signals : mlResult.ml_top_signals,
        model_ready    : isMLAvailable(mlResult),
      };
    }

    const textForVerify = [targetUrlForWhitelist, summary, ...reasons].filter(Boolean).join(" ");
    if (textForVerify && (finalResponse.web_intelligence?.detected || extractUrls(textForVerify).length > 0)) {
      finalResponse.web_intelligence = await enrichWebIntelligence(finalResponse.web_intelligence, textForVerify);
      if (finalResponse.web_intelligence?.domain_match === "mismatch" && finalResponse.riskScore < 85) {
        const mismatchReason = "Tên miền không khớp với thương hiệu được nhận diện; cần kiểm chứng độc lập.";
        finalResponse = {
          ...finalResponse,
          ...buildStructuredResponse(
            Math.min(99, finalResponse.riskScore + 10),
            [...reasons, mismatchReason],
            [...detectedPatterns, "Brand domain mismatch"],
            `${summary} ${mismatchReason}`,
            "Domain / Brand Mismatch",
            urgentActions,
            finalResponse.web_intelligence,
          ),
        };
      }
    }

    return NextResponse.json(finalResponse, { headers: corsHeaders });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "AI Processing Error";
    return NextResponse.json({ error: message }, { status: 500, headers: corsHeaders });
  }
}
