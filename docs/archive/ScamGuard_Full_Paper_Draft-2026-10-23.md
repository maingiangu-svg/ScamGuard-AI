# ScamGuard: a reproducible local text–URL screening baseline

Status: revised implementation draft, 23 October 2026.
Run 20261022T180106Z. This replaces earlier metrics, API-saving estimates and latency claims.
Source of results: ml_model/models/training_report.json. No test data were refitted
into the deployed bundle.

## Research question and scope

Can a lightweight logistic meta-learner combine a text discriminator and a separately
trained URL discriminator on real messages containing embedded URLs? We compare
text-only, URL-only, max fusion, linear stacking and interaction stacking. These are
existing techniques. The present experiment does not establish algorithmic novelty
or a statistically significant improvement from adding interaction.

The system runs locally for all inputs and scores, including the 30–79 review interval.
It has no external generative model and no automatic URL fetch. It does not perform
image understanding, dialogue assessment, psychological diagnosis or verified fraud attribution.

## Data and label provenance

The downloaded Combined Labeled Smishing Dataset is pinned at commit
3bf9983df4b187ee9b54a671e4b5bc5f0d48b3fc of
https://github.com/shaghayegh-hp/Smishing_Dataset. The local byte-for-byte copy is named
smishing_combined.csv. Its SHA-256 is
4dc1311965acb80b9b97536db5afdbe874a1e2175143d3b145e32caf9bb81a8d.

Upstream describes the smishing labels as keyword-derived. They are weak supervision,
not independent expert annotations. Predicting these labels can reward learning their
keyword rule; results are not estimates of clinical, legal or expert-verified scam detection.

The raw file has 84,863 rows. Shared preprocessing retained 73,989 records, including
8,995 real messages with embedded links. It quarantined 45 conflicting normalized
groups and removed 10,703 further duplicates. There are 51,428 negative and 22,561
positive retained labels. No synthetic pairs were generated.

The independent URL corpus contains 549,346 original rows labelled good/bad.
Canonical URL conflicts are quarantined and duplicates removed. All hostnames in
the SMS corpus are excluded before selecting 50,000 external URL examples.
The external URL target and the message-level target are distinct; the meta-learner
reconciles their scores rather than assuming either label implies the other.

## Shared preprocessing and estimators

Unicode NFC preserves composed Vietnamese words. Whitespace and case are normalized;
phone numbers, recognized money amounts and context-marked OTP codes are masked.
All recognized embedded HTTP/bare-domain URLs are extracted and replaced in the text.
URL parsing uses urllib.parse; hostname and scheme are normalized while path/query
case is retained. This is not a claim of complete deobfuscation or homoglyph resolution.

The text estimator uses word TF-IDF (1–2 grams, at most 10,000 features, L2-normalized,
sublinear term frequency) and class-balanced Logistic Regression (C=1).
The URL estimator combines 13 numeric lexical/structural features with at most 1,000
character TF-IDF features (3–5 grams) and HistGradientBoosting (depth 4, 100 iterations).
Numeric features are standardized within URL training. Trees do not inherently require
this scaling; retaining it in the saved pipeline ensures consistent transformations.

For message URL lists, the URL branch score is their maximum. Interaction fusion is:

s = 100 × sigmoid(beta0 + beta1*p_text + beta2*p_url + beta3*p_text*p_url).

Learned coefficients for this run are -4.347072, 7.179562, -1.467973, 2.134786.
A positive interaction coefficient is descriptive, not a hypothesis test.
Text-only or URL-only input uses its available branch. Missing models never invoke
fixed coefficients and never produce a safe verdict.

## Leakage controls and deployment contract

Connected groups link identical normalized texts and every shared URL hostname.
One grouped fold is held out before fitting vocabulary, models or meta features.
The deployed text model uses 59,190 training messages; 14,799 SMS remain untouched.
The external URL model uses 39,983 rows; 10,017 remain in a separate hostname holdout.

Five inner grouped text folds generate OOF scores strictly inside SMS training.
The fixed external URL model has never seen any SMS hostname or SMS target label,
so its scores on SMS do not require fitting on SMS validation data.
The meta-learner sees only 6,363 real paired SMS from SMS training.
Fusion is evaluated on 2,632 real paired SMS from the untouched SMS holdout.
There is no second cross-validation of a globally computed OOF table.

Groups use full hostnames, not a public-suffix-derived registrable domain or known
campaign IDs. Cross-subdomain and cross-campaign dependence can therefore remain.
All split indices, dataset hashes and boolean split-isolation checks are saved locally.

## Results

All metrics below use a 0.5 classification threshold; they are not performance
estimates for the separate 30/80 product review policy.

| Evaluation | N | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Text, SMS holdout | 14799 | 0.9381 | 0.8475 | 0.9719 | 0.9055 | 0.9892 |
| URL, external URL holdout | 10017 | 0.9310 | 0.9480 | 0.7463 | 0.8351 | 0.9682 |
| Paired SMS: text_only | 2632 | 0.8571 | 0.8536 | 0.9859 | 0.9150 | 0.9474 |
| Paired SMS: url_only | 2632 | 0.7071 | 0.7908 | 0.8490 | 0.8189 | 0.5460 |
| Paired SMS: max_fusion | 2632 | 0.7926 | 0.7910 | 0.9976 | 0.8824 | 0.9058 |
| Paired SMS: linear_meta | 2632 | 0.8853 | 0.8924 | 0.9698 | 0.9295 | 0.9475 |
| Paired SMS: interaction_meta | 2632 | 0.8868 | 0.8944 | 0.9693 | 0.9303 | 0.9475 |

Compare architectures only within the same evaluation subset.
Interaction slightly improves F1 over linear stacking but does not improve AUC.
No confidence interval or significance claim is made. Independent expert-labelled
real-world evaluation is needed before claiming improved fraud detection.
The current comparison does not isolate the contribution of each of the 13 features.

## Product behavior and performance limits

Scores below 30 are low; 30–79 indicate review; 80 and above indicate high model risk.
These are fixed policy thresholds, not empirically optimal or calibrated probabilities.
The uncertainty display is only distance from the score midpoint, not epistemic uncertainty.

Domain annotations never override a score. No whitelist returns automatic zero and no
brand rule adds points. Each request starts Python; imports and model loading contribute
to request latency. No sub-4ms endpoint latency or percentage reduction in API usage is claimed.
Dashboard timing is measured Python execution, not complete browser/network latency.

## Limitations and research work remaining

Keyword-derived label bias is the primary limitation. Real paired messages do not imply
separately verified URL ground truth. The corpus has no established Vietnamese test set,
temporal split or expert-annotated campaign benchmark. Near-duplicate templates and
registrable-domain sharing require additional controls. Fixed thresholds need validation,
scores need calibration assessment, and interaction benefits need uncertainty estimates
on independent data. These are open experiments, not completed findings.

## Reproduction and sources

Follow ml_model/README.md; train.py delegates to the single production trainer.
The bundle records preprocessing/model fingerprints and scikit-learn version.
See data/smishing_source.json for the immutable download and source-use notice.

- Dataset source: https://github.com/shaghayegh-hp/Smishing_Dataset
- URL corpus source: https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls
- Stacking: https://scikit-learn.org/stable/modules/ensemble.html#stacked-generalization
- Grouped validation: https://scikit-learn.org/stable/modules/cross_validation.html
