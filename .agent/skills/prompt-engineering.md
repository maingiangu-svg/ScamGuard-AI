# SKILL: Structured JSON Output & Anti-Hallucination

## Purpose
Ensure LLM (Gemini API) responses are strictly formatted JSON with deterministic risk scoring for the ScamGuard engine.

## Execution Rules
1. **Structured Output Enforcement:**
   - Force response schema to contain:
     - `riskLevel`: `"LOW" | "MEDIUM" | "HIGH"`
     - `riskScore`: integer between `0` and `100`
     - `detectedPatterns`: array of string indicators
     - `summary`: concise explanation in Vietnamese
2. **Anti-Hallucination Rules:**
   - Strictly base risk evaluation on provided DOM text, URL features, or image context.
   - If evidence is ambiguous, output `riskLevel: "LOW"` with a request for more input.