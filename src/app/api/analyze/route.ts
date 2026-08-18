import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type } from "@google/genai";

const apiKey = process.env.GEMINI_API_KEY;

export async function POST(req: NextRequest) {
  try {
    if (!apiKey) {
      return NextResponse.json(
        { error: "GEMINI_API_KEY is not configured" },
        { status: 500 }
      );
    }

    const formData = await req.formData();
    const file = formData.get("image") as File | null;

    if (!file) {
      return NextResponse.json(
        { error: "Vui lòng chọn hoặc kéo thả một hình ảnh." },
        { status: 400 }
      );
    }

    const bytes = await file.arrayBuffer();
    const base64Data = Buffer.from(bytes).toString("base64");
    const mimeType = file.type || "image/jpeg";

    const ai = new GoogleGenAI({ apiKey });

    const response = await ai.models.generateContent({
      model: "gemini-3.5-flash-lite",
      contents: [
        {
          role: "user",
          parts: [
            {
              inlineData: {
                data: base64Data,
                mimeType: mimeType,
              },
            },
            {
              text: "Hãy phân tích hình ảnh này để bóc tách dấu hiệu lừa đảo và thủ thuật thao túng tâm lý theo đúng JSON schema.",
            },
          ],
        },
      ],
      config: {
        systemInstruction: `Bạn là ScamShield Forensic AI - Chuyên gia giám định pháp y kỹ thuật số và phân tích tâm lý lừa đảo không gian mạng tại Việt Nam.
Nhiệm vụ: Phân tích hình ảnh (ảnh chụp màn hình tin nhắn, giao diện web, ứng dụng mạo danh, thông báo ngân hàng giả...) để bóc tách toàn diện các dấu hiệu lừa đảo và thủ thuật thao túng tâm lý.
Quy tắc:
1. Độc lập & Khách quan: Chỉ dựa trên dấu hiệu trực quan trong ảnh.
2. Bóc tách tâm lý chuyên sâu: Chỉ rõ các kỹ thuật thao túng (FOMO, sợ hãi, khẩn cấp, mạo danh quyền lực).
3. Đóng vòng lặp hành động: Đưa ra hành động 60s và thông điệp cảnh báo người thân.
Bắt buộc trả về đúng định dạng JSON theo schema.`,
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          required: [
            "scam_detected",
            "risk_score",
            "threat_level",
            "scam_type",
            "executive_summary",
            "red_flags",
            "psychological_tricks",
            "next_move_prediction",
            "urgent_actions",
            "family_alert_card",
          ],
          properties: {
            scam_detected: { type: Type.BOOLEAN },
            risk_score: { type: Type.INTEGER },
            threat_level: {
              type: Type.STRING,
              enum: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "SAFE"],
            },
            scam_type: { type: Type.STRING },
            executive_summary: { type: Type.STRING },
            red_flags: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                required: ["evidence", "explanation"],
                properties: {
                  evidence: { type: Type.STRING },
                  explanation: { type: Type.STRING },
                },
              },
            },
            psychological_tricks: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                required: ["tactic", "target_emotion", "analysis"],
                properties: {
                  tactic: { type: Type.STRING },
                  target_emotion: { type: Type.STRING },
                  analysis: { type: Type.STRING },
                },
              },
            },
            next_move_prediction: { type: Type.STRING },
            urgent_actions: {
              type: Type.ARRAY,
              items: { type: Type.STRING },
            },
            family_alert_card: {
              type: Type.OBJECT,
              required: ["headline", "key_warning", "shareable_text"],
              properties: {
                headline: { type: Type.STRING },
                key_warning: { type: Type.STRING },
                shareable_text: { type: Type.STRING },
              },
            },
          },
        },
      },
    });

    const outputText = response.text;
    if (!outputText) {
      throw new Error("Không nhận được phản hồi từ AI Model");
    }

    const parsedData = JSON.parse(outputText);
    return NextResponse.json(parsedData);
  } catch (error: any) {
    console.error("Forensic analysis error:", error);
    return NextResponse.json(
      { error: error.message || "Máy chủ AI đang bận, vui lòng thử lại sau vài giây." },
      { status: 500 }
    );
  }
}