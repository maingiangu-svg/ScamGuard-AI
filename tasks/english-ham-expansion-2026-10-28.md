# Add source-labeled English legitimate SMS without reusing protected groups

- [x] Parse and verify the already pinned original UCI archive. Keep ham labels
  as source labels, not expert phishing ground truth; preserve source records.
- [x] Exclude current model inputs, non-English/uncertain language, and complete
  components connected to historical validation, test or quarantine. Include
  template, public/private domain, normalized model-input and >=0.80 similarity
  edges. Retain historical group links where recorded.
- [x] Freeze an eligible negative additions export with per-template/group caps,
  hashes and provenance. Keep every exclusion in a blocked audit export.
- [x] Verify the full data package and serving-model hashes, run regression
  tests, and document actual counts and limitations. No historical test scoring,
  model tuning, automatic label invention or serving-model replacement.

The earlier positive expansion and both failed training experiments remain
immutable. Newly acquired unlicensed/unlabeled sources will not be trained.
This slice improves the labeled training data; fitting is conditional on a
nonempty isolated export and a separately frozen training protocol.

Completed: 62 unused UCI source negatives admitted from 61 groups, increasing
the English prepared inventory to 4,053 (total 4,186). Four new regression tests
and all 170 Python tests pass. The package/source membership and every protected
hash were verified. Current weights and earlier experiments are unchanged.
Most additions are personal conversations; transactional/OTP/advertising data
remains a gap. See docs/english-ham-expansion-2026-10-28.md and .json.
