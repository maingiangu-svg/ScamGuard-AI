# Project quality constraints

Hold the existing verified checks while completing the remaining release work.

- `npm.cmd run lint`, `npm.cmd run check:types`, `npm.cmd run build` must pass.
- Preserve the existing 150-test baseline and add checks for new behavior. Do
  not delete/skip assertions, silence failures, or weaken checks to reach green.
- Container image scan must count every High/Critical finding: no blanket CVE
  suppression, ignore-unfixed shortcut or removal of package metadata. Physically
  omit unused components or ship fixed components, then verify real inference.
- Do not publish secrets, raw/private datasets or reviewer identities without
  authorization. Image/root/model paths may not come from public request input.
- Supervised learning only: retain label origin and expert verification status.
  New benchmark/test data must not enter fitting, calibration or threshold selection.
- An AI review is not an expert signature. Missing reviewers, labels or evidence
  must produce a pending/blocked gate, never synthetic completion.
- Existing score is not a calibrated fraud probability. New calibration needs
  provenance, disjoint groups, bound model/input identities and held-out metrics.
- Never promise that a low score guarantees safety. No finite benchmark proves
  that guarantee.
- Preserve keyboard access, zoom and responsive layouts. Measure page performance
  after user-facing changes against the existing local CLS 0 baseline.

Verification: existing GitHub `verify` workflow plus the new focused tests and
runtime/scan evidence. No merge or deploy is implied by a passing code test.
