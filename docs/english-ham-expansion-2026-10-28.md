# English legitimate SMS additions — 2026-10-28

Added **62 source-labeled legitimate SMS from 61 connected groups** to the
prepared training inventory. No model was fitted, scored or activated in this
slice. Serving weights and earlier experiments remain unchanged. This is more
usable data from an existing source, not a new benchmark or evidence of better
model accuracy.

## Source and label confidence

The pinned original [UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms%2Bspam%2Bcollection)
contains 5,574 records, including 4,827 labeled `ham`. UCI describes these as
legitimate messages and identifies the contributing collections. Its current
page lists CC BY 4.0; the original archive's license/disclaimer is also retained
verbatim. Attribution: Almeida, T. & Hidalgo, J. (2011), SMS Spam Collection,
DOI 10.24432/C5CC84.

Archive: `ml_model/data/reference/uci_sms_spam_collection.zip`.
SHA-256: `1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3`.
The corrupted legacy `spam.csv` is not used.

Only source `ham` becomes project label `0`. Provenance remains
`uci_source_ham_proxy_not_expert_smishing_verdict`; no new human verification
or expert verdict is claimed. Source record numbers, hashes, normalized
duplicate memberships and original text variants are retained.

## Admission results

| Stage | Count |
| --- | ---: |
| Original source ham records | 4,827 |
| Distinct normalized model inputs | 4,517 |
| Already present in prior 4,124-row fitting inventory | 2,741 |
| Unused source inputs before isolation | 1,776 |
| Unused inputs blocked by protected historical components | 1,684 |
| Remaining inputs without confident English classification | 30 |
| Admitted source-negative inputs | **62** |
| Admitted templates / connected groups | **62 / 61** |

The audit covers 255,746 historical text/role records and retains 94,157
previous group edges. Exact content, normalized templates, public/private
domain owners, recorded groups and character-ngram cosine similarity at least
0.80 connect components. There were 105 near-duplicate queries against 87,353
distinct reference signatures. Test, validation or quarantine membership blocks
the whole component. Previously inspected raw Combined data is exposed material
and cannot become a fresh test.

Screening uses the existing separate `langid==1.1.6` installation, all languages,
at least five words after URL masking and normalized English confidence >=0.95.
This is automated language screening. Caps of three records per template and
twenty per component removed no further records in this intake.

The combined inventory has **4,186 rows: 4,053 English and 133 Vietnamese**.
English labels are 3,584 negative and 469 positive. The prior 338 NCSU positive
additions retain their weaker feed-derived label provenance.

## Outputs and use

Local, Git-ignored package:
`ml_model/data/prepared/english_ham_expansion_2026-10-28/`.

- `sms_train_additions.jsonl` / `.csv`: 62 eligible source negatives.
- `sms_quarantine.jsonl` / `.csv`: 4,455 excluded normalized inputs, reasons
  and `do_not_train=true`.
- `sms_train_merged.jsonl` / `.csv`: combined inventory for inspection.
  **Recompute fitting groups before future cross-validation**; this concatenated
  inventory is not a frozen experiment split.
- `source_ham.*`, `source_readme.txt`: source membership and original terms.
- `historical_inputs.json`, `similarity_edges.json`, `protocol.json`,
  `prepare_code.py`, `final_report.json`: admission and reproducibility evidence.
- `verification_report.json`: independent source-record, partition, label,
  duplicate and hash checks.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe ml_model/english_ham_expansion.py verify
.\.venv\Scripts\python.exe -m unittest discover -s ml_model -p test_english_ham_expansion.py -v
```

`prepare` requires a new output directory and refuses to overwrite a package.
Source files, historical exports and serving-model hashes are pinned. No SMS
URLs were visited. No labels were inferred from model predictions.

## Validation and limits

All **170 Python tests pass**, including four new tests for parsing, duplicate
memberships, admission and historical group bridges. Verification maps all
4,827 source ham records exactly once to admitted or blocked exports. The
combined inventory has no repeated case IDs or model inputs. All protected
historical and serving hashes match. JavaScript and build were not rerun for
this Python/data-only slice.

Most additions are informal personal conversations. They do not fill the gap
in modern legitimate banking, delivery, OTP and promotional SMS. Some contain
adult language or profanity present in the original source. A source `ham`
label is not a claim about general content safety or current URL safety. The
61 connected groups do not establish 61 independent campaigns.

Two other sources were inspected but not imported: the authors'
[NUS SMS corpus](https://github.com/kite1988/nus-sms-corpus) README does not
establish fraud labels for individual messages, and the inspected
[Sift dataset card](https://huggingface.co/datasets/Gwen1220/sift-sms-dataset)
at revision `bd5b136f7cb16dcfeed3a55e9ca1cdab9c33e808` supplies no license
field. Public availability was not treated as supervised negative evidence
or a verified license. No author was contacted.

Active bundle remains
`26373a849458c95c3bfea30f73e93be7460e7a2b314a5ece80a71fa890efd008`;
manifest remains
`b14bd6e155354321398b676ac2a3c7a0ce9d623e7a4ade176d0629efc374e1ac`.
Future fitting requires a new frozen protocol and regrouping; preserve release
gates and unlabeled heldout pools. No accuracy gain is claimed by this intake.
