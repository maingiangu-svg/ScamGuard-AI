export interface LinkBatchResult {
  model_ready: true;
  results: {url: string; riskScore: number; riskLevel: 'LOW' | 'MEDIUM' | 'HIGH'; model_id: string}[];
}

export function parseLinkBatch(body: unknown): string[] | null {
  if (!body || typeof body !== 'object' || !('urls' in body) || !Array.isArray(body.urls)
    || body.urls.length < 1 || body.urls.length > 20) return null;
  for (const value of body.urls) {
    if (typeof value !== 'string' || value.length > 4096) return null;
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.href !== value || url.username || url.password
        || url.search || url.hash || url.origin === 'http://localhost:3000') return null;
    } catch { return null; }
  }
  return [...new Set(body.urls)] as string[];
}

export function validLinkResults(value: unknown, urls: string[]): value is LinkBatchResult {
  if (!value || typeof value !== 'object' || !('model_ready' in value) || value.model_ready !== true
    || !('results' in value) || !Array.isArray(value.results) || value.results.length !== urls.length) return false;
  return value.results.every((row, index) => row && typeof row === 'object' && row.url === urls[index]
    && Number.isInteger(row.riskScore) && row.riskScore >= 0 && row.riskScore <= 100
    && ['LOW', 'MEDIUM', 'HIGH'].includes(row.riskLevel) && typeof row.model_id === 'string' && row.model_id.length > 0);
}
