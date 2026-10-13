import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 200, headers: corsHeaders });
}

/**
 * Calls the Python ML predictor (ml_model/predict.py) via subprocess.
 * Returns a structured ML classification result.
 */
async function runPythonClassifier(text: string, url: string): Promise<any> {
  return new Promise((resolve) => {
    const projectRoot = path.join(process.cwd());
    const scriptPath = path.join(projectRoot, "ml_model", "predict.py");
    const payload = JSON.stringify({ text, url });

    const python = spawn("python3", [scriptPath], {
      cwd: projectRoot,
      timeout: 10_000, // 10 second timeout
    });

    let stdout = "";
    let stderr = "";

    python.stdin.write(payload);
    python.stdin.end();

    python.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    python.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });

    python.on("close", (code: number) => {
      if (code !== 0 || !stdout.trim()) {
        resolve({
          ml_risk_score: 0,
          ml_label: "UNAVAILABLE",
          ml_confidence: 0,
          ml_top_signals: [],
          model_ready: false,
          error: stderr || "Python process failed",
        });
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch {
        resolve({
          ml_risk_score: 0,
          ml_label: "PARSE_ERROR",
          ml_confidence: 0,
          ml_top_signals: [],
          model_ready: false,
        });
      }
    });

    python.on("error", (err: Error) => {
      resolve({
        ml_risk_score: 0,
        ml_label: "UNAVAILABLE",
        ml_confidence: 0,
        ml_top_signals: [],
        model_ready: false,
        error: err.message,
      });
    });
  });
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const text: string = body.text || "";
    const url: string  = body.url  || "";

    if (!text && !url) {
      return NextResponse.json(
        { error: "Provide at least one of: text, url" },
        { status: 400, headers: corsHeaders }
      );
    }

    const result = await runPythonClassifier(text, url);
    return NextResponse.json(result, { headers: corsHeaders });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: msg }, { status: 500, headers: corsHeaders });
  }
}
