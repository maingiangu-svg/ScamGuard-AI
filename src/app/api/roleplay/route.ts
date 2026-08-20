import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type, Schema } from "@google/genai";
import { getClientIp, rateLimit } from "@/lib/rate-limit";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const ROLEPLAY_SCHEMA: Schema = {
  type: Type.OBJECT,
  properties: {
    eval_text: { type: Type.STRING },
    eval_status: { type: Type.STRING, enum: ["safe", "danger"] },
    scammer_reply: { type: Type.STRING },
  },
  required: ["eval_text", "eval_status", "scammer_reply"],
};

export async function POST(req: NextRequest) {
  try {
    const ip = getClientIp(req);
    const { ok } = rateLimit(`roleplay:${ip}`);
    if (!ok) {
      return NextResponse.json({ error: "Quá nhiều yêu cầu roleplay." }, { status: 429 });
    }

    if (!process.env.GEMINI_API_KEY) {
      return NextResponse.json({ error: "Thiếu GEMINI_API_KEY." }, { status: 500 });
    }

    const { scamType, scamContext, userMessage, history } = await req.json();
    if (!userMessage?.trim()) {
      return NextResponse.json({ error: "Tin nhắn trống" }, { status: 400 });
    }

    const historyText = (history || [])
      .slice(-6)
      .map((m: { sender: string; text: string }) => `${m.sender}: ${m.text}`)
      .join("\n");

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [{
        text: `Kịch bản lừa đảo: ${scamType}\nBối cảnh: ${scamContext}\n\nLịch sử hội thoại:\n${historyText}\n\nNgười dùng vừa trả lời: "${userMessage}"\n\nĐánh giá phản xạ của người dùng (safe/danger) và viết câu trả lời tiếp theo của kẻ lừa đảo (ngắn gọn, tiếng Việt, sát thực tế VN).`,
      }],
      config: {
        systemInstruction: "Bạn là engine Roleplay Lab của ScamShield - mô phỏng kẻ lừa đảo và huấn luyện viên an toàn số. eval_status='danger' nếu user cung cấp OTP/mật khẩu/bấm link/chuyển tiền. eval_status='safe' nếu user từ chối, xác minh qua kênh chính thống, báo cáo. Trả JSON đúng schema.",
        responseMimeType: "application/json",
        responseSchema: ROLEPLAY_SCHEMA,
      },
    });

    return NextResponse.json(JSON.parse(response.text || "{}"));
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Lỗi roleplay AI";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
