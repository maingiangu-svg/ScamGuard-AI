import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type, Schema } from "@google/genai";
import { getClientIp, rateLimit } from "@/lib/rate-limit";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

const ROLEPLAY_SCHEMA: Schema = {
  type: Type.OBJECT,
  properties: {
    eval_text: { type: Type.STRING },
    eval_status: { type: Type.STRING, enum: ["safe", "danger"] },
    scammer_reply: { type: Type.STRING },
  },
  required: ["eval_text", "eval_status", "scammer_reply"],
};

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: corsHeaders,
  });
}

export async function POST(req: NextRequest) {
  try {
    const ip = getClientIp(req);
    const { ok } = rateLimit(`roleplay:${ip}`);
    if (!ok) {
      return NextResponse.json(
        { error: "Quá nhiều yêu cầu roleplay." },
        { status: 429, headers: corsHeaders }
      );
    }

    const { scamType, scamContext, userMessage, history, isRiskyQuickChoice } = await req.json();
    if (!userMessage?.trim()) {
      return NextResponse.json(
        { error: "Tin nhắn trống" },
        { status: 400, headers: corsHeaders }
      );
    }

    const apiKey = process.env.GEMINI_API_KEY;

    if (apiKey && apiKey.trim() !== "" && apiKey !== "your_gemini_api_key_here") {
      try {
        const ai = new GoogleGenAI({ apiKey });
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

        if (response.text) {
          return NextResponse.json(JSON.parse(response.text), { headers: corsHeaders });
        }
      } catch (geminiErr) {
        console.warn("Roleplay Gemini call failed, using rule fallback:", geminiErr);
      }
    }

    // Fallback roleplay logic if API Key is missing or invalid
    const lower = userMessage.toLowerCase();
    const isDangerous = isRiskyQuickChoice || lower.includes("otp") || lower.includes("mật khẩu") || lower.includes("chuyển tiền") || lower.includes("nạp") || lower.includes("bấm link");

    return NextResponse.json(
      {
        eval_text: isDangerous
          ? "⚠️ CẢNH BÁO NGUY HIỂM: Bạn vừa sa vào bẫy! Việc gửi mã OTP, mật khẩu hoặc bấm link lạ sẽ khiến bạn bị chiếm đoạt tài khoản tức thì."
          : "✅ XỬ LÝ AN TOÀN: Rất tốt! Bạn giữ tâm lý tỉnh táo, không mắc bẫy hối thúc và chủ động từ chối / báo cáo.",
        eval_status: isDangerous ? "danger" : "safe",
        scammer_reply: isDangerous
          ? "Bẫy thành công! Kẻ gian đã nhận được thông tin xác thực và vừa thực hiện rút sạch số dư tài khoản. Hãy rút kinh nghiệm!"
          : "Nạn nhân quá tỉnh táo và dứt khoát! Kẻ lừa đảo dọa nạt không thành công đành ngắt cuộc gọi để tìm mục tiêu khác.",
      },
      { headers: corsHeaders }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Lỗi roleplay AI";
    return NextResponse.json({ error: message }, { status: 500, headers: corsHeaders });
  }
}
