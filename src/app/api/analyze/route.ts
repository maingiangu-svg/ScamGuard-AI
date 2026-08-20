import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type, Schema } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const FORENSIC_SCHEMA: Schema = {
  type: Type.OBJECT,
  properties: {
    scam_detected: { type: Type.BOOLEAN },
    risk_score: { type: Type.INTEGER },
    threat_level: { type: Type.STRING, enum: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "SAFE"] },
    scam_type: { type: Type.STRING },
    executive_summary: { type: Type.STRING },
    web_intelligence: {
      type: Type.OBJECT,
      properties: {
        detected: { type: Type.BOOLEAN },
        url: { type: Type.STRING, nullable: true },
        domain: { type: Type.STRING, nullable: true },
        brand_detected: { type: Type.STRING, nullable: true },
        domain_match: { type: Type.STRING, enum: ["match", "mismatch", "unknown"] },
        website_status: { type: Type.STRING, enum: ["accessible", "unavailable", "unknown"] },
        suspicious_indicators: { type: Type.ARRAY, items: { type: Type.STRING } },
        external_evidence: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              title: { type: Type.STRING },
              source_url: { type: Type.STRING },
            },
            required: ["title", "source_url"],
          },
        },
        confidence: { type: Type.INTEGER },
      },
      required: ["detected", "domain_match", "website_status", "suspicious_indicators", "external_evidence", "confidence"],
    },
    red_flags: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: {
          evidence: { type: Type.STRING },
          official_fact: { type: Type.STRING },
          official_link: { type: Type.STRING, nullable: true },
          explanation: { type: Type.STRING },
        },
        required: ["evidence", "official_fact", "explanation"],
      },
    },
    psychological_tricks: {
      type: Type.ARRAY,
      items: {
        type: Type.OBJECT,
        properties: { tactic: { type: Type.STRING }, target_emotion: { type: Type.STRING }, analysis: { type: Type.STRING } },
        required: ["tactic", "target_emotion", "analysis"],
      },
    },
    next_move_prediction: { type: Type.STRING },
    urgent_actions: { type: Type.ARRAY, items: { type: Type.STRING } },
    family_alert_card: {
      type: Type.OBJECT,
      properties: { headline: { type: Type.STRING }, key_warning: { type: Type.STRING }, shareable_text: { type: Type.STRING } },
      required: ["headline", "key_warning", "shareable_text"],
    },
  },
  required: [
    "scam_detected", "risk_score", "threat_level", "scam_type", "executive_summary",
    "web_intelligence", "red_flags", "psychological_tricks", "next_move_prediction",
    "urgent_actions", "family_alert_card"
  ],
};

export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get("content-type") || "";
    let contents: any[] = [];

    if (contentType.includes("multipart/form-data")) {
      const formData = await req.formData();
      const image = formData.get("image") as File;
      if (!image) return NextResponse.json({ error: "Không tìm thấy ảnh" }, { status: 400 });

      const buffer = Buffer.from(await image.arrayBuffer());
      contents = [
        { inlineData: { mimeType: image.type, data: buffer.toString("base64") } },
        { text: "Giám định pháp y kỹ thuật số & bóc tách tâm lý lừa đảo bức ảnh này." }
      ];
    } else {
      const { textInput } = await req.json();
      if (!textInput?.trim()) return NextResponse.json({ error: "Nội dung trống" }, { status: 400 });
      contents = [{ text: `Giám định pháp y nội dung/đường link sau để tìm dấu hiệu lừa đảo: \n${textInput}` }];
    }

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents,
      config: {
        systemInstruction: "Bạn là ScamShield Forensic AI - Giám định lừa đảo & thao túng tâm lý tại VN. Trả về đúng JSON Schema. Trong web_intelligence: trích xuất URL/domain nếu có (nếu không có URL thì detected: false, url: null, domain: null, brand_detected: null, domain_match: 'unknown', website_status: 'unknown', suspicious_indicators: [], external_evidence: [], confidence: 0). external_evidence chứa danh sách object { title, source_url } trỏ tới URL kiểm chứng công khai hoặc link Google Search query (https://www.google.com/search?q=...). Trong red_flags: mỗi mục có evidence (trích dẫn), official_fact (thực tế chính thống), official_link (URL trang chính thức đối chiếu hoặc null), explanation (phân tích).",
        responseMimeType: "application/json",
        responseSchema: FORENSIC_SCHEMA,
      },
    });

    return NextResponse.json(JSON.parse(response.text || "{}"));
  } catch (error: any) {
    return NextResponse.json({ error: error.message || "Lỗi xử lý AI" }, { status: 500 });
  }
}