const defaultOrigins = [
  'http://localhost:3000', 'http://127.0.0.1:3000',
  'https://scamguard-ai-940298403801.asia-southeast1.run.app',
  'chrome-extension://lamffehgecaabedhleppfmgjcagamlih',
];

export function allowedOrigin(request: Request, allowlist =
  (process.env.SCAMGUARD_ALLOWED_ORIGINS ?? defaultOrigins.join(',')).split(',').map(value => value.trim())) {
  const origin = request.headers.get('origin');
  if (origin === null) return true;
  if (/^chrome-extension:\/\/[a-p]{32}$/.test(origin)) return allowlist.includes(origin);
  try {
    if (new URL(origin).origin !== origin) return false;
    // An attacker can choose both Host and Origin during DNS rebinding.
    // Only explicitly configured browser origins may use this local/public API.
    return allowlist.includes(origin);
  } catch { return false; }
}

export function apiHeaders(request: Request): Record<string, string> {
  const headers: Record<string, string> = {
    'Cache-Control': 'no-store', Vary: 'Origin',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  const origin = request.headers.get('origin');
  if (origin && allowedOrigin(request)) headers['Access-Control-Allow-Origin'] = origin;
  return headers;
}
