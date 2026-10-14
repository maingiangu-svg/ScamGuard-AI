# Local ML training on Windows

Run these commands from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ml_model\requirements.txt
npm.cmd ci

$env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -u ml_model\train.py
.\.venv\Scripts\python.exe -m unittest discover -s ml_model -v

.\scripts\start-local.ps1
```

The training script reads `data/spam.csv` and `data/phishing_site_urls.csv`.
It uses all 5,572 SMS messages and a reproducible sample of 50,000 URLs from
549,346 downloaded rows, matching the existing URL training limit.
Both classifiers use stratified 5-fold validation. TF-IDF is fitted within
each training fold, and all three metrics are computed from the same fits.
The final classifiers are fitted on their complete selected training sets.
Reported scores describe these datasets; they are not a guarantee for new
messages, Vietnamese content, or newly created phishing sites.

Model files and evaluation metrics are saved in `ml_model/models/`.
The datasets, generated models, and `.venv/` are ignored by Git.

Open http://localhost:3000 after starting the app. `start-local.ps1` puts
the virtual environment on PATH and supplies the `python3` executable name
expected by the existing API. Test the trained model independently of Gemini:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://localhost:3000/api/ml-classify' `
  -ContentType 'application/json' -Body '{"text":"FREE prize! Claim now!"}'
```

Gemini analysis and roleplay require `GEMINI_API_KEY` in `.env.local`.
The local `/api/ml-classify` endpoint does not require that key.

## Analysis result checks

When Gemini is unavailable, `/api/analyze` uses the available ML score directly.
It blends scores only when both Gemini and ML return valid predictions. With no
available prediction, it returns HTTP 503 instead of a fabricated threat report.
The local classifiers cannot analyze image pixels; images require Gemini.

Risk levels follow the existing API contract: 0–40 LOW, 41–70 MEDIUM, 71–100 HIGH.
The dashboard adds detail: 0–20 SAFE, 21–40 LOW, 41–70 MEDIUM, 71–90 HIGH,
91–100 CRITICAL. Benign input has no generated phishing evidence or claims of
live verification. Warning colors follow the displayed threat level.

Run these checks with the app running locally and no Gemini key configured:

```powershell
node --test scripts/analysis-assessment.test.mjs scripts/analyze.integration.test.mjs
npm.cmd run build
```
