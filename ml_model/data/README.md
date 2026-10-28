# Dataset sources

- smishing_combined.csv is a byte-for-byte copy of Combined-Labeled-Dataset.csv
  from shaghayegh-hp/Smishing_Dataset at commit
  3bf9983df4b187ee9b54a671e4b5bc5f0d48b3fc.
  Run python ml_model/download_data.py to retrieve and verify its SHA-256.
  Upstream has 84,863 rows, message/spam label/smishing label columns.
  Smishing labels are derived from keyword rules. The upstream README permits
  academic/research use; do not assume an unrestricted commercial license.
- phishing_site_urls.csv uses URL/Label columns with good/bad labels.
  Existing source: https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls
  Download the original file yourself if it is absent.
- spam.csv is the optional SMS Spam Collection fallback. Its spam/ham task is
  explicitly reported as a proxy, not treated as expert smishing ground truth.
  This legacy CSV has split/merged message records. Future fallback training reads
  the checksum-pinned original UCI archive in reference/ instead (see ../README.md).

Run python ml_model/prepare_data.py to generate prepared/ datasets and review
queues without modifying originals or retraining. Each exported record includes
its source file, source record and SHA-256. Quarantined conflicts stay excluded;
auxiliary missing/nonbinary labels are preserved for review, never guessed.
Prepared candidates retain weak/inherited label provenance. They are not a new
expert-labelled test set. The 200-message review sample has pending labels.

Original datasets and generated cleaned CSV files remain local and are Git-ignored.
Do not add synthetic examples to the reported real holdout. Preprocessing writes
smishing_preprocessed.csv; training_report.json records actual counts and hashes.

English SMS additions, 2026-10-25: the official SmishX/SOUPS 2025 source has
1,200 manually re-labeled messages (259 smishing, 319 spam, 622 legitimate).
The official IMC 2025 corpus adds 22,078 source-English rows with GPT-4o scam
annotations, a different label confidence level. Both were downloaded at pinned
commits and exported with provenance; neither has been added to model training.
SmishX overlaps existing SMS/holdouts and must not be called a fresh benchmark.
See `../../docs/english-smishing-data-2026-10-25.md` for files, checksums, label
mapping, source terms and overlap counts. All new records remain blocked from
fitting until group isolation and scope review are complete.

Follow-up: SmishX source is multilingual, despite the initial English export
names. Screening retained 1,017 English/project-scope rows, then grouping and
holdout exclusions produced a completed isolated SMS experiment in
`prepared/smishx_training_2026-10-25/`. Use its train/validation/test manifests;
the initial download exports remain unassigned and must not be concatenated
into training. See `../../docs/smishx-training-2026-10-25.md` for actual usage.
The initial IMC review pool remains blocked from fitting.

English expansion, 2026-10-28: a new pinned source from the NCSU IEEE S&P 2024
SMS phishing release is stored in `reference/english_expansion_2026-10-28/`.
It has 68,029 raw SMS records and 35,128 campaign records. The prepared package
is `prepared/english_expansion_2026-10-28/`; use its final report and explicit
training-additions export, never concatenate the raw source. Feed-derived labels
retain their provenance; AI template scope screening is not expert verification.
Unknowns, promotions, reserved groups and redundant variants remain outside
training. Campaign URLs have no individual verdict and stay in a blocked review
pool. See `../../docs/english-data-expansion-2026-10-28.md` for the workflow.

English negative additions, 2026-10-28: the pinned original UCI archive supplies
62 unused source-ham inputs after language screening and historical component
isolation. The package is `prepared/english_ham_expansion_2026-10-28/`. Use only
its additions export; 4,455 blocked inputs remain excluded. Source ham is a
negative-label proxy, not expert smishing verification. The combined inventory
has 4,053 English plus 133 Vietnamese rows and requires regrouping before a
future fitting experiment. No fitting or activation occurred. See
`../../docs/english-ham-expansion-2026-10-28.md`.

Training follow-up, 2026-10-29: the 62 admitted source-ham messages now
participate in the activated conservative English confirmation workflow.
The previous model files referenced by older package hashes are archived in
`prepared/conservative_sms_english_gate_2026-10-29/parent_bundle.pkl` and
`parent_manifest.json`. Data exports and source labels remain unchanged.
Use that release's `release_artifact.py verify` to check current sources plus
the exact archived parent. See `../../docs/conservative-sms-training-2026-10-29.md`.
