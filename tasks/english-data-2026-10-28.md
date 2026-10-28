# English data expansion — 2026-10-28

User authorizes improving and adding English data. Scope: source acquisition,
traceable data preparation, conservative leakage exclusions and usable exports.
Keep the active models and all historical frozen datasets unchanged. The existing
Vietnamese plan and its outstanding independent benchmark remain intact.

1. [x] Acquire real SMS from primary research sources with pinned revision,
   checksum, reuse terms and label methodology; reject synthetic replacements.
2. [x] Prepare English SMS additions using existing normalization/domain/template
   helpers; preserve original labels, distinguish feed/AI/manual provenance,
   exclude historical reserved groups and unresolved language/scope.
3. [x] Reserve novel groups before any learning; export training candidates,
   annotation/holdout candidates, quarantines and a reconciled membership ledger.
   Do not call an unreviewed holdout a gold benchmark.
4. [x] Add URL source evidence only when independently supplied by the source;
   never derive a URL label from the SMS label or assert unknown page language.
5. [x] Verify grouping, conflicts, Unicode round-trips and training guards with
   focused tests; run the ML suite, check protected checksums and report counts.

Acceptance: real new source records exist locally; every record has provenance
and a disposition; no reserved group enters train; no expert verification is
invented; model and old frozen dataset checksums remain unchanged. No retraining
or deployment is required by this data-only update.

Completed: 68,029 real source SMS acquired; 338 new English training messages
from 102 groups retained after screening/caps; merged English train 3,991 rows
(469 positives). Reserved 95 validation and 96 test candidates remain unlabeled;
3,003 campaign-associated URLs remain blocked pending individual verdicts.
All 154 Python tests pass; protected model and historical hashes are unchanged.
Evidence: docs/english-data-expansion-2026-10-28.md and .json. This does not
complete an independently human-verified benchmark or authorize model deployment.
