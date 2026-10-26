import { spawn } from 'node:child_process';
import path from 'node:path';
import { existsSync } from 'node:fs';
import type { MLClassification } from './analysis-assessment';

export function getMLInputError(ml: MLClassification | null, language: string): string | null {
  if (ml?.error !== 'INVALID_URL') return null;
  return language === 'vi'
    ? 'URL chưa đầy đủ hoặc không hợp lệ. Hãy nhập đầy đủ tên miền, ví dụ https://example.com.'
    : 'The URL is incomplete or invalid. Enter a complete hostname, for example https://example.com.';
}

export function parseInput(body: unknown): {text: string; url: string; language: string} | null {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null;
  const input = body as Record<string, unknown>;
  for (const key of ['text', 'textInput', 'bodyText', 'title', 'url', 'language']) {
    if (input[key] !== undefined && typeof input[key] !== 'string') return null;
  }
  const text = (input.bodyText ?? input.textInput ?? input.text ?? input.title ?? '') as string;
  const url = (input.url ?? '') as string;
  if (text.length > 20000 || url.length > 4096 || !(text.trim() || url.trim())) return null;
  if (url && !/^(?:https?:\/\/|[a-z0-9][a-z0-9.-]*\.)/i.test(url)) return null;
  return {text, url, language: input.language === 'vi' ? 'vi' : 'en'};
}

export async function runMLClassifier(text: string, url: string): Promise<MLClassification | null> {
  const root = process.cwd();
  const localPython = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const executable = process.env.PYTHON_EXECUTABLE || (existsSync(localPython) ? localPython : 'python3');
  const scripts: Record<string, string> = {
    hybrid: 'predict_hybrid.py', processed: 'predict_processed.py', legacy: 'predict.py',
  };
  const inferenceScript = scripts[process.env.SCAMGUARD_INFERENCE_MODE ?? 'hybrid'];
  if (!inferenceScript) return null;
  return new Promise(resolve => {
    const python = spawn(executable, [path.join(root, 'ml_model', inferenceScript)], {
      cwd: root, timeout: 15000, windowsHide: true,
      env: {...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', OMP_NUM_THREADS: '1'},
    });
    let output = '';
    let oversized = false;
    python.stdout.on('data', (chunk: Buffer) => {
      output += chunk.toString('utf8');
      if (output.length > 1000000) { oversized = true; python.kill(); }
    });
    // Drain stderr without returning internal paths or input data to the client.
    python.stderr.on('data', () => {});
    python.stdin.on('error', () => resolve(null));
    python.on('error', () => resolve(null));
    python.on('close', code => {
      if (code !== 0 || oversized) return resolve(null);
      try {
        const parsed: unknown = JSON.parse(output);
        resolve(parsed && typeof parsed === 'object' ? parsed as MLClassification : null);
      } catch { resolve(null); }
    });
    python.stdin.end(JSON.stringify({text, url}));
  });
}
