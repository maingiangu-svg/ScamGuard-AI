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
        { error: "Too many roleplay simulation requests." },
        { status: 429, headers: corsHeaders }
      );
    }

    const { scamType, scamContext, userMessage, history, isRiskyQuickChoice } = await req.json();
    if (!userMessage?.trim()) {
      return NextResponse.json(
        { error: "Message content cannot be empty" },
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
            text: `Scam Scenario: ${scamType}\nContext: ${scamContext}\n\nConversation History:\n${historyText}\n\nUser's latest response: "${userMessage}"\n\nEvaluate the user's defensive reflex (safe/danger) and generate the scammer's subsequent response (concise, persuasive or coercive, in English).`,
          }],
          config: {
            systemInstruction: "You are the Roleplay Simulation Engine of ScamShield - simulating an adversarial social engineer/scammer while evaluating user cybersecurity reflexes. Set eval_status='danger' if the user discloses OTP, passwords, clicks suspicious links, or complies with financial transfers. Set eval_status='safe' if the user refuses, challenges identity, or verifies via official channels. Return JSON adhering to schema.",
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
    const isDangerous =
      isRiskyQuickChoice ||
      lower.includes("otp") ||
      lower.includes("password") ||
      lower.includes("transfer") ||
      lower.includes("click") ||
      lower.includes("send code") ||
      lower.includes("here is");

    return NextResponse.json(
      {
        eval_text: isDangerous
          ? "⚠️ CRITICAL DEFENSE FAILURE: You succumbed to the scam hook! Disclosing OTPs, credentials, or clicking links enables immediate account takeover."
          : "✅ SAFE REFLEX RESPONSE: Excellent! You remained composed, resisted urgent coercion, and refused to comply with unauthorized requests.",
        eval_status: isDangerous ? "danger" : "safe",
        scammer_reply: isDangerous
          ? "Trap succeeded! The adversary intercepted your credentials and initiated an unauthorized withdrawal. Review your defensive reflexes!"
          : "The scammer realized coercion was ineffective against your vigilant response and abruptly terminated the interaction.",
      },
      { headers: corsHeaders }
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "AI Roleplay Error";
    return NextResponse.json({ error: message }, { status: 500, headers: corsHeaders });
  }
}
