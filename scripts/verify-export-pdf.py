"""Verify Unicode content and complete pagination in the browser-downloaded PDF."""
import json
import sys
from pathlib import Path

from pypdf import PdfReader

path = Path(sys.argv[1])
reader = PdfReader(path)
text = '\n'.join(page.extract_text() for page in reader.pages)
for required in ('Báo cáo kiểm tra', 'VÍ DỤ MINH HỌA', 'không phải xác suất lừa đảo'):
    if required not in text:
        raise ValueError(f'Missing Unicode text or limitation: {required}')
if '\ufffd' in text or not reader.pages:
    raise ValueError('Invalid Unicode text or empty document')
result = dict(status='PASS', pages=len(reader.pages), bytes=path.stat().st_size,
              vietnamese_unicode=True, illustrative_disclaimer=True, model_limitations=True)
(path.parent / 'pdf-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
