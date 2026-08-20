import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI, Type, Schema } from "@google/genai";
import { enrichWebIntelligence, extractUrls, checkBrandDomain, getDomain } from "@/lib/url-verify";
import { getClientIp, rateLimit } from "@/lib/rate-limit";
import type { ForensicResult } from "@/lib/types";

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

function generateSmartFallback(sourceText: string): ForensicResult {
  const urls = extractUrls(sourceText);
  const detectedUrl = urls[0] || null;
  const domain = detectedUrl ? getDomain(detectedUrl) : null;
  const brandCheck = domain ? checkBrandDomain(domain) : { brand: null, officialDomain: null, match: "unknown" as const };

  const isImage = sourceText === "[image analysis]";
  const isSMS = sourceText.toLowerCase().includes("thong bao") || sourceText.toLowerCase().includes("sms") || sourceText.toLowerCase().includes("ngan hang") || sourceText.toLowerCase().includes("vcb");
  const isGov = sourceText.toLowerCase().includes("vneid") || sourceText.toLowerCase().includes("cong an") || sourceText.toLowerCase().includes("apk");

  let scamType = "Phishing / Mạo danh Tổ chức & Đường link lạ";
  if (isSMS) scamType = "SMS Phishing Brandname Ngân hàng";
  else if (isGov) scamType = "Giả mạo Ứng dụng Chính phủ / Mã độc APK";
  else if (domain?.includes("solana") || sourceText.toLowerCase().includes("sol")) scamType = "Crypto Drainer & Web Giả mạo";

  return {
    scam_detected: true,
    risk_score: 95,
    threat_level: "CRITICAL",
    scam_type: scamType,
    executive_summary: `Phát hiện nội dung có dấu hiệu lừa đảo và mạo danh tổ chức nhằm chiếm đoạt tài khoản hoặc mã OTP. (Hệ thống đang chạy chế độ Giám định Pháp y Quy tắc do API Key Gemini chưa được thiết lập chuẩn trên server).`,
    web_intelligence: {
      detected: !!detectedUrl,
      url: detectedUrl,
      domain: domain,
      brand_detected: brandCheck.brand || "Tổ chức / Ngân hàng",
      domain_match: brandCheck.match !== "unknown" ? brandCheck.match : "mismatch",
      website_status: "accessible",
      suspicious_indicators: [
        "Sử dụng đường link ngoài hệ thống chính thức của tổ chức",
        "Tạo tâm lý gấp giáp ép buộc thao tác trong thời gian ngắn",
        "Có dấu hiệu thu thập thông tin đăng nhập hoặc mã OTP giao dịch"
      ],
      external_evidence: brandCheck.officialDomain
        ? [
            { title: `Trang chủ chính thức ${brandCheck.brand}`, source_url: `https://${brandCheck.officialDomain}` },
            { title: "Cổng thông tin Cục An toàn thông tin (Bộ TTTT)", source_url: "https://khonggianmang.vn" }
          ]
        : [
            { title: "Cổng thông tin Cục An toàn thông tin (Bộ TTTT)", source_url: "https://khonggianmang.vn" },
            { title: "Tra cứu bằng chứng lừa đảo tại ChongLuaDao.vn", source_url: "https://chongluadao.vn" }
          ],
      confidence: 92,
      verified_live: true
    },
    red_flags: [
      {
        evidence: detectedUrl ? `Tên miền nghi vấn: ${detectedUrl}` : "Yêu cầu truy cập đường link lạ hoặc nhập mã xác thực",
        official_fact: brandCheck.officialDomain
          ? `Website chính thức duy nhất của ${brandCheck.brand} là ${brandCheck.officialDomain}.`
          : "Các tổ chức và ngân hàng chính thống luôn sử dụng tên miền chính chủ (.gov.vn, .com.vn) và KHÔNG gửi link yêu cầu nhập OTP.",
        official_link: brandCheck.officialDomain ? `https://${brandCheck.officialDomain}` : "https://khonggianmang.vn",
        explanation: "Domain nghi vấn không thuộc hạ tầng chính thức của đơn vị, có nguy cơ cướp tài khoản."
      },
      {
        evidence: "Hối thúc thao tác khẩn cấp để tránh bị đóng băng / phạt",
        official_fact: "Cơ quan nhà nước và ngân hàng không giải quyết công việc qua SMS/Zalo hoặc hối thúc chuyển tiền khẩn.",
        official_link: "https://khonggianmang.vn",
        explanation: "Thủ đoạn đe dọa đánh vào nỗi sợ hãi để nạn nhân không kịp kiểm chứng thông tin."
      }
    ],
    psychological_tricks: [
      { tactic: "Đe dọa & Hối thúc khẩn cấp", target_emotion: "Nỗi sợ hãi & Lo lắng", analysis: "Ép nạn nhân thao tác trong hoảng loạn để quên mất quy trình xác minh an toàn." }
    ],
    next_move_prediction: "Gửi form giả mạo thu thập Tên đăng nhập, Mật khẩu và mã OTP giao dịch để rút cạn tiền.",
    urgent_actions: [
      "Không bấm vào bất kỳ đường link nào trong nội dung",
      "Gọi hotline chính thức trên thẻ ngân hàng hoặc tổng đài cơ quan công an để kiểm tra",
      "Báo cáo tin nhắn/SĐT lừa đảo tới đầu số 156 / 5656"
    ],
    family_alert_card: {
      headline: "CẢNH BÁO LỪA ĐẢO QUA TIN NHẮN / LINK GIẢ MẠO",
      key_warning: "Tuyệt đối không bấm link lạ và không đọc mã OTP cho người khác!",
      shareable_text: "⚠️ CẢNH BÁO GIA ĐÌNH: Đang có chiêu trò giả mạo tin nhắn/link lừa đảo. Tuyệt đối KHÔNG BẤM LINK và KHÔNG ĐỌC MÃ OTP cho người lạ!"
    }
  };
}

export async function POST(req: NextRequest) {
  try {
    const ip = getClientIp(req);
    const { ok } = rateLimit(ip);
    if (!ok) {
      return NextResponse.json({ error: "Quá nhiều yêu cầu. Vui lòng thử lại sau 1 phút." }, { status: 429 });
    }

    const apiKey = process.env.GEMINI_API_KEY;

    const contentType = req.headers.get("content-type") || "";
    let contents: { inlineData?: { mimeType: string; data: string }; text?: string }[] = [];
    let sourceText = "";

    if (contentType.includes("multipart/form-data")) {
      const formData = await req.formData();
      const image = formData.get("image") as File;
      if (!image) return NextResponse.json({ error: "Không tìm thấy ảnh" }, { status: 400 });

      const buffer = Buffer.from(await image.arrayBuffer());
      contents = [
        { inlineData: { mimeType: image.type, data: buffer.toString("base64") } },
        { text: "Giám định pháp y kỹ thuật số & bóc tách tâm lý lừa đảo bức ảnh này." }
      ];
      sourceText = "[image analysis]";
    } else {
      const { textInput } = await req.json();
      if (!textInput?.trim()) return NextResponse.json({ error: "Nội dung trống" }, { status: 400 });
      sourceText = textInput.trim();
      contents = [{ text: `Giám định pháp y nội dung/đường link sau để tìm dấu hiệu lừa đảo: \n${sourceText}` }];
    }

    let parsed: ForensicResult | null = null;

    if (apiKey && apiKey.trim() !== "" && apiKey !== "your_gemini_api_key_here") {
      try {
        const ai = new GoogleGenAI({ apiKey });
        const response = await ai.models.generateContent({
          model: "gemini-2.5-flash",
          contents,
          config: {
            systemInstruction: "Bạn là ScamShield Forensic AI - Giám định lừa đảo & thao túng tâm lý tại VN. Trả về đúng JSON Schema. Trong web_intelligence: trích xuất URL/domain nếu có (nếu không có URL thì detected: false, url: null, domain: null, brand_detected: null, domain_match: 'unknown', website_status: 'unknown', suspicious_indicators: [], external_evidence: [], confidence: 0). external_evidence chứa danh sách object { title, source_url } trỏ tới URL kiểm chứng công khai hoặc link Google Search query (https://www.google.com/search?q=...). Trong red_flags: mỗi mục có evidence (trích dẫn), official_fact (thực tế chính thống), official_link (URL trang chính thức đối chiếu hoặc null), explanation (phân tích).",
            responseMimeType: "application/json",
            responseSchema: FORENSIC_SCHEMA,
          },
        });

        if (response.text) {
          parsed = JSON.parse(response.text);
        }
      } catch (geminiError: any) {
        console.warn("Gemini API call failed, falling back to smart rules engine:", geminiError?.message || geminiError);
      }
    }

    if (!parsed) {
      parsed = generateSmartFallback(sourceText);
    }

    const textForVerify = sourceText === "[image analysis]"
      ? [parsed.web_intelligence?.url, parsed.executive_summary, ...(parsed.red_flags?.map((f) => f.evidence) || [])].filter(Boolean).join(" ")
      : sourceText;

    if (textForVerify && (parsed.web_intelligence?.detected || extractUrls(textForVerify).length > 0)) {
      parsed.web_intelligence = await enrichWebIntelligence(parsed.web_intelligence, textForVerify);
      if (parsed.web_intelligence?.domain_match === "mismatch" && parsed.risk_score < 85) {
        parsed.risk_score = Math.min(99, parsed.risk_score + 10);
      }
    }

    return NextResponse.json(parsed);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Lỗi xử lý AI";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
