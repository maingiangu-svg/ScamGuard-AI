# TASK SPEC: Puppeteer Headless Browser Agent

## Objective
Implement an automated web crawling engine using Puppeteer in Next.js API to simulate real user browsing, capture screenshots, and extract rendered DOM content before passing to Gemini AI.

## Target File
`src/lib/puppeteer-agent.ts` and `src/app/api/analyze/route.ts`[cite: 3]

## Implementation Steps

### 1. Install Dependency
- Add `puppeteer-core` or `chrome-aws-lambda` (or `puppeteer`) for serverless/Cloud Run environments.

### 2. Create Browser Crawler (`src/lib/puppeteer-agent.ts`)
- Function `crawlAndCapture(url: string)`:
  - Launch headless Chrome instance.
  - Set User-Agent to standard Chrome browser on macOS/Windows.
  - Set viewport to 1280x800.
  - Navigate to URL with `waitUntil: 'networkidle2'`, timeout 10s.
  - Auto-scroll down 500px to trigger lazy-loaded elements.
  - Take base64 screenshot (`page.screenshot({ encoding: 'base64' })`).
  - Get full inner text and interactive elements (buttons, inputs, forms).
  - Close browser cleanly.

### 3. Update Analysis Endpoint (`src/app/api/analyze/route.ts`)
- Receive `url` from request body[cite: 3].
- Call `crawlAndCapture(url)` to get screenshot and rendered content.
- Pass base64 image + text payload to Gemini Multimodal API (`gemini-2.5-flash`).
- Return JSON analysis result to frontend[cite: 5].