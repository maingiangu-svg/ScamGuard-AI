// Bound JSON before parsing, including requests without a trustworthy Content-Length.
export const MAX_JSON_BYTES = 256 * 1024;

export async function readJSONBody(request: Request): Promise<
  {body: unknown} | {error: string; status: number}
> {
  if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    return {error: 'Only JSON text and URL input is supported. Local image OCR is unavailable.', status: 415};
  }
  if (Number(request.headers.get('content-length')) > MAX_JSON_BYTES) {
    return {error: 'Request body is too large.', status: 413};
  }
  if (!request.body) return {error: 'Invalid JSON body.', status: 400};
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_JSON_BYTES) {
        await reader.cancel();
        return {error: 'Request body is too large.', status: 413};
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.byteLength;
    }
    return {body: JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes))};
  } catch {
    return {error: 'Invalid JSON body.', status: 400};
  } finally {
    reader.releaseLock();
  }
}
