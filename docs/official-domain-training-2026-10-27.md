# Official service URL supervised expansion, 2026-10-27

User-authorized task: train the URL head using the discussed official service
URLs. Reuse the current supervised estimator and existing train-only sigmoid
calibration; preserve the SMS head, input preprocessing and alert thresholds.
There is no runtime domain allowlist or score override.

## Frozen protocol (before fitting)

- The checked-in `ml_model/data/official_domain_seeds.json` records 14 exact URLs,
  first-party evidence, review date and AI-review provenance. These are legitimate
  service URL seeds, not expert-verified content-safety labels.
- Bind the original fit rows to the active bundle's manifest and verify the
  original repaired dataset. Never use a historical validation/test/quarantined
  owner domain for a new training seed. Keep blocked seeds in the decision report.
- Deduplicate exact canonical URLs; quarantine conflicting labels. Join new rows
  to an existing owner-domain calibration group when one exists. Each new row
  has ordinary weight 1; no oversampling or fabricated phishing labels.
- Reuse the fixed URL estimator. Run 3 outer / 3 inner grouped folds on training
  rows only, then final 3-fold sigmoid fitting. Fixed URL alert threshold: 0.50.
  Calibration gate: Brier score and log loss must not increase versus raw scores
  on the outer held-out training folds. No hyperparameter/threshold search.
- Freeze the fitted candidate before evaluating historical URL tests exactly
  once. Report baseline/candidate confusion matrices at 0.50. Release gate:
  false positives must not increase and true positives must not decrease.
  These reused source-label diagnostics are not a fresh independent benchmark.
- Report official URL scores separately as a seen-seed sanity check, not accuracy.
  Passing gates permits local artifact activation with a backup; no remote
  deployment is part of this task. A failed gate preserves the active bundle.
- Bind source/seed/code/fit/calibration/evaluation checksums and export actual fit
  rows. Activation must reject changed evidence, artifacts or an active parent.

## Commands

```powershell
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
.\.venv\Scripts\python.exe ml_model\official_domain_training.py fit
.\.venv\Scripts\python.exe ml_model\official_domain_training.py evaluate
.\.venv\Scripts\python.exe ml_model\official_domain_training.py activate
.\.venv\Scripts\python.exe -m unittest discover -s ml_model -v
npm.cmd test
npm.cmd run lint
npm.cmd run build
npm.cmd run check:types
```

## Completed result

The single frozen run fitted 31,309 URL rows: 31,299 previously accepted URL
training rows plus 10 exact official URL seeds. The 3,786-row SMS head was
preserved. Fitting took 208.809 seconds. No runtime scoring code changed.

Added domains: `youtube.com`, `facebook.com`, `zalo.me`, `shopee.vn`, `tiki.vn`,
`vietcombank.com.vn`, `bidv.com.vn`, `momo.vn`, `dichvucong.gov.vn`, `vnexpress.net`.

Blocked domains: `google.com`, `microsoft.com`, `apple.com`, `wikipedia.org`.
These owner domains are represented in historical test/quarantine groups;
new official URLs on them remain excluded from training as well.

Train-only nested-group source-label calibration passed: Brier decreased from
0.043717 to 0.039981, and log loss from 0.159767 to 0.132947. This checks
source-label estimates, not expert-verified fraud probabilities.

The fixed 0.50 alert-threshold comparison on 9,935 reused historical URL tests:

| Measure | Active baseline | Trained candidate |
|---|---:|---:|
| Legitimate URLs correctly cleared | 7,545 | 7,541 |
| False alarms | 160 | 164 |
| Bad URLs missed | 606 | 619 |
| Bad URLs detected | 1,624 | 1,611 |
| Precision | 91.03% | 90.76% |
| Recall | 72.83% | 72.24% |
| F1 | 80.92% | 80.45% |

**Release gate failed. The candidate was not activated.** An attempted activation
was rejected before writing serving artifacts; the active bundle and manifest
checksums were verified unchanged. The source-labeled historical diagnostic
does not establish real-world safety or independent accuracy. There was no
second fit, tuning pass or repeated evaluation against these test results.

Selected exact-seed alert scores (rounded 0–100; these are seen training
examples, not an independent benchmark):

| Exact URL | Baseline | Candidate |
|---|---:|---:|
| `https://www.youtube.com/` | 39 | 17 |
| `https://www.facebook.com/` | 25 | 7 |
| `https://www.momo.vn/` | 64 | 39 |
| `https://zalo.me/pc` | 75 | 65 |
| `https://www.vietcombank.com.vn/` | 78 | 77 |

Zalo and Vietcombank still require review even after fitting. Adding one
legitimate URL per service is insufficient to teach a general guarantee about
the whole domain. Domain ownership does not verify posts or redirect targets.

## Artifacts and verification

- Local run directory: `ml_model/data/prepared/official_domains_2026-10-27/`.
  It contains frozen fit-row exports, seed decisions, protocol, calibration
  predictions/report, candidate weights/manifest and the single evaluation.
  Original datasets and active artifacts were preserved.
- Candidate bundle SHA-256:
  `2bd32ba07111692040836f9e13ccfe132a8b11a78cf82e217eb938268835ab37`.
- Active baseline bundle SHA-256:
  `6a0fd38b35570bff4b0ae56dd52a07747a6670d3dc2eceda304e1f10898314d0`.
- Shareable numerical evidence: [JSON report](official-domain-training-2026-10-27.json).
- 118 Python tests passed, including 10 new checks covering holdout isolation,
  label evidence, duplicates/conflicts, release rejection and activation evidence
  tampering. A deliberately inverted domain-exclusion condition was caught by
  the tests in a temporary copy; the frozen training source was not modified.
- 47 JavaScript unit tests, 3 inference-lifecycle tests, 17 API integration tests,
  lint, production build and TypeScript checks passed. The first API run had one
  CORS preflight failure because test port 3107 was not in the test server's
  allowed origins. After configuring that test server origin, the focused test
  and a complete 17-test API run passed. Production CORS settings were unchanged.
