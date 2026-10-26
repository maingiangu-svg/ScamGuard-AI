# ScamGuard: Supervised Local Screening of SMS and URLs with Label-Provenance Controls

Method and evidence revision, 25 October 2026. This draft describes the default web model `processed-20261025`. The 23 October draft is preserved in `docs/archive/ScamGuard_Full_Paper_Draft-2026-10-23.md` as a historical experiment. The supplied ICAI PDF is a comparison document, not the source of current results. This is an implementation-grounded draft, not a submission-ready conference paper.

## Abstract

We describe a supervised local screening system with separate SMS and URL classifiers and explicit controls on label provenance and evaluation reuse. The SMS classifier combines word and character TF-IDF with Logistic Regression; the URL classifier combines 13 lexical/structural features and character TF-IDF with histogram gradient boosting. Model fitting uses 3,857 SMS and 9,123 URLs. Architecture and decision thresholds are selected on validation data. For messages containing links, the SMS classifier determines the message decision and URL scores are reported separately. No paired fusion or cloud reasoning is deployed. The new English SMS holdout contains 39 messages and yields TP=24, FN=1, FP=1, TN=13, but all 25 positive messages belong to one similarity group. The URL source-label test yields precision 0.1965 and recall 0.4928; a separate 81-case author-published human audit yields precision 0.6957 and recall 0.7273. These results describe distinct targets and sampling conditions, not a single real-world accuracy estimate. Reused Vietnamese diagnostics expose remaining false alarms and missed positives. Independent Vietnamese annotations and broader campaign coverage remain necessary.

## 1. Research question and scope

Can lightweight supervised classifiers support reproducible local SMS and URL screening when labels have different provenance and targets? We examine SMS classification, URL classification, and the limits of available evaluation sets. Established classifiers are used; no algorithmic novelty is asserted.

The SMS target is the project's annotated smishing/scam scope. Non-smishing spam maps to the negative class where supported by the retained annotation policy; negative does not necessarily mean desirable or harmless. The URL target is source-reported abuse/phishing versus benign. A message label is not a URL label. The human URL audit instead evaluates evidence-supported phishing versus legitimate.

The web application runs inference in a local Python process. Browser execution, mobile edge deployment, image understanding, dialogue assessment, automatic URL fetching and VLM escalation have not been established by these experiments.

## 2. Data and label provenance

Current SMS training combines eligible Mishra–Soni SMS Phishing Dataset v1 records, previously reviewed Vietnamese messages, and scope-screened SmishX messages. The URL branch uses eligible PhishVN dataset v4/release v3.1.0 records. Original labels, source record IDs, source hashes, merged-record lineage and review decisions accompany exported records.

| Source | Original records | Role and annotation boundary |
|---|---:|---|
| Mishra–Soni v1 | 5,971 SMS | Source ham/spam/smishing; selected semantic decisions are AI-reviewed, not independently expert-verified |
| SmishX, commit `116a8c827741e0572563f678d25ed04306b1e3ff` | 1,200 multilingual SMS | Authors report manual labels by two researchers with disagreement resolution; language/scope screening here is AI review |
| Previously reviewed Vietnamese data | Per-record manifests | AI proposals and explicit user scope decisions retain separate provenance |
| PhishVN v4 / v3.1.0 | 53,116 URLs | Positive gold and benign gold/silver only; feed/registry labels are not universal expert verification |
| PhishVN author-published human audit | 200 reserved cases | 81 evidence-supported phishing/legitimate cases scored separately; all audit domains reserved |

SmishX screening retains 1,017 English scope-eligible messages (141 positive, 876 negative). The other 183 comprise 77 other/mixed-language messages, 19 unresolved fragments and 87 scope conflicts or unresolved cases. Group overlap blocks a further 421 candidates, including one prior training record. Overlap removal is an isolation rule, not a finding that every blocked message is wrong.

| Branch / evaluation role | Train | Validation | Test | Positive counts: train / validation / test |
|---|---:|---:|---:|---|
| Current SMS | 3,857 | 962 | 39 | 193 / 49 / 25 |
| Current URL | 9,123 | 3,826 | 2,627 | 1,284 / 321 / 69 |
| Human-label URL audit | 0 | 0 | 81 | 0 / 0 / 22 |

SMS training contains 3,716 English and 141 Vietnamese messages. Of 3,857 training records, 497 carry source-human provenance; these may merge duplicates from older sources and are not necessarily 497 new messages. The corpus is not wholly human or expert verified. The SMS test is entirely English. Historical SMS (1,164) and Vietnamese (70) sets are diagnostics already inspected during project development.

The keyword-derived Combined Labeled Smishing Dataset and older 549,346-row URL corpus remain historical sources, not data for the current fit. The malformed legacy `spam.csv` is not the current fallback; the pinned UCI archive is available only for a separately declared spam-proxy experiment. IMC25 and MIMICS-3500 contribute zero records to the current fit. No fabricated or randomly paired text–URL examples are used. Originals and frozen exports are preserved; excluded records remain in quarantine with reasons.

## 3. Supervised method

### 3.1 Input representation and preprocessing

For message text t and extracted URL set U, labels y_sms and y_url are defined separately. SMS input follows frozen `round2_experiment.text_input`: trim trailing dataset URL wrappers/punctuation with `audit_url_text`, apply Unicode NFC and case folding, replace digit runs of at least four digits by `<number>`, then collapse whitespace. URL strings remain in SMS input. This differs from the historical pipeline that replaced URLs, phone numbers, money and context-marked OTPs by separate tokens. NFC is not homoglyph detection or complete deobfuscation.

URL input follows `external_training.url_input`: repair supported formatting, normalize the host with the shared parser, preserve path/query case, remove the fragment and force the scheme to `http` for model input. The original URL is retained. This removes the documented HTTP/HTTPS collection shortcut; it is not a network request or a security recommendation about transport. Invalid or ambiguous source URLs are quarantined. No page or redirect is fetched.

### 3.2 SMS classifier and supervised loss

The selected feature vector concatenates word TF-IDF (1–2 grams, up to 10,000 features) and `char_wb` TF-IDF (3–5 grams, up to 16,000 features). Both use sublinear term frequency; each vectorizer retains default L2 normalization. The word-only alternative uses the same validation rule. Vocabularies and inverse-document frequencies are fitted on training records only.

The classifier is L2-regularized Logistic Regression, C=1, balanced class weights, maximum 1,000 iterations and seed 42:

    p_sms(t) = sigmoid(w^T phi_sms(t) + b).

For labels in {0,1}, weighted cross-entropy per record is

    loss_i = -a_i [y_i log(p_i) + (1-y_i) log(1-p_i)],
    a_i = v_i × (sum_j v_j) / (2 × sum_{j:y_j=y_i} v_j).

Fixed sample weight v_i is 3 for Vietnamese records, otherwise 2 for source-human records, otherwise 1. The pinned scikit-learn 1.9.1 computes balanced class weights from sample-weighted class counts; N/(2 n_y) applies only when all sample weights are equal. The solver adds its L2 penalty under the scikit-learn C=1 convention. These weights do not certify annotation quality. The supplied PDF's signed-label loss requires labels in {-1,+1}; it cannot be applied directly with its stated {0,1} labels.

### 3.3 URL classifier

The URL feature vector concatenates 13 numeric features below with `char_wb` TF-IDF (3–5 grams, up to 1,000 features). Numeric features use a training-fitted StandardScaler. The classifier is HistGradientBoostingClassifier with maximum depth 4, maximum 100 iterations, learning rate 0.1 and seed 42. No row-subsampling ratio of 0.80 is configured.

| # | Implemented numeric feature |
|---|---|
| 1–3 | URL length, hostname length, combined path/query length |
| 4 | Count of configured keyword substrings present in the URL |
| 5–6 | Configured risk-suffix and trust-suffix flags; neither overrides a score |
| 7–8 | Digit ratio and ratio of characters in `-_@!~&=?%` across the URL |
| 9–10 | Hostname hyphen count and max(0, hostname dot count minus one) |
| 11 | Parsed IP-literal flag using `ipaddress`, not an IPv4-only regex |
| 12 | Brand substring in hostname outside configured official hostname/subdomain suffixes |
| 13 | Shannon entropy of hostname characters |

Subdomain depth is an approximate lexical feature, not the registrable-domain grouping rule. Brand checks apply to hostname, not arbitrary URL paths. Entropy is a learned feature, not proof of fraud or a guaranteed zero-day detector. No feature ablation establishes its incremental value. Source, tier, status, scenario, split and labels are excluded from classifier inputs. Scenario keywords never generate training labels.

### 3.4 Decision rule and missing inputs

For each URL u obtain p_url(u). The active decision is:

    if substantive message text exists: p = p_sms(t), threshold = 0.65
    else if URLs exist:                 p = max_u p_url(u), threshold = 0.22
    else:                              unavailable
    predicted_label = 1[p >= threshold].

Messages with links report both branch scores but use the SMS decision. SMS can use URL characters already present in its input; absence of score fusion does not mean it sees no URL information. There is no paired meta-learner in the current bundle. An explicit URL argument is screened separately and is not appended to SMS input.

Displayed scores are rounded to 0–100. UI bands (<30, 30–79, >=80) are a separate policy from binary labels computed on unrounded scores. A score of 70 meets the SMS binary threshold but remains in the UI review band. Neither scores nor score-midpoint distance are calibrated real-world fraud probabilities or epistemic uncertainty. Missing/corrupt/incompatible models return unavailable, with no fabricated safe verdict or cloud call.

### 3.5 Historical interaction stacking

The 23 October experiment used:

    p_fusion = sigmoid(beta0 + beta1*p_text + beta2*p_url + beta3*p_text*p_url).

Five inner grouped text OOF folds were restricted to training; fusion was evaluated on 2,632 separately held-out real linked messages. Interaction F1 was 0.9303 versus 0.9295 for linear stacking, with AUC 0.9475 for both at reported precision. These data, labels and models differ from the current system. This is not a current-model ablation or comparison to the 39-message test. A positive interaction coefficient alone is not a significance test.

## 4. Selection and evaluation protocol

SMS groups connect normalized duplicates, templates, registrable domains using a pinned Public Suffix List, and character similarity >=0.80. Previously reserved groups and all published URL audit domains are blocked from training. Earlier-fit groups remain training-only rather than being reassigned to the new test. Existing audits find no group or registrable-domain overlap across current splits. This does not establish full independence across all campaigns.

The URL branch preserves the eligible provider test split and removed all SMS domains known at its original preparation plus human-audit domains. A fresh audit after SmishX expansion finds seven domains shared across the current SMS and URL corpora: amazon.com, shop.app, whatsapp.com, youtu.be, zomato.com, zoom.com and zoom.us. Branch-specific train/validation/test partitions remain disjoint. Because the current classifiers are trained separately and SMS decisions do not consume URL-model scores, this is not cross-branch target fitting; nevertheless, auxiliary URL scores are not evidence of jointly domain-disjoint evaluation. A future fusion experiment must exclude these overlaps before fitting. Because eligible provider validation lacked gold positives, validation includes groups reserved from provider training plus eligible provider-validation negatives. No fully temporal SMS evaluation or invented collection dates are claimed.

Select SMS variant and thresholds on validation by maximum F2 subject to false-positive rate <=0.10, on the frozen grid 0.05–0.95 in steps of 0.01. SMS candidates are word-only and word+character; the URL estimator is fixed and its threshold selected separately. F2=5PR/(4P+R). Frozen selections are SMS word+character at 0.65 and URL at 0.22. Selection hashes precede saved test predictions. Tests were used once in their respective frozen experiments; inspecting saved predictions here is an audit, not a new selection or model evaluation. The reproduced web fit matches frozen validation scores exactly and includes no held-out rows.

## 5. Observed results and their limits

| Evaluation | N | TP / FN / FP / TN | Precision | Recall | F1 |
|---|---:|---|---:|---:|---:|
| New English SmishX SMS holdout | 39 | 24 / 1 / 1 / 13 | 0.9600 | 0.9600 | 0.9600 |
| URL provider-label holdout | 2,627 | 34 / 35 / 139 / 2,419 | 0.1965 | 0.4928 | 0.2810 |
| URL author-published human audit | 81 | 16 / 6 / 7 / 52 | 0.6957 | 0.7273 | 0.7111 |
| Reused SMS diagnostic, current model | 1,164 | 29 / 9 / 6 / 1,120 | 0.8286 | 0.7632 | 0.7945 |
| Reused Vietnamese diagnostic, current model | 70 | 14 / 3 / 9 / 44 | 0.6087 | 0.8235 | 0.7000 |

The English test has 11 similarity groups, with all positives in one group. Its 0.96 F1 does not establish generalization across independent campaigns or Vietnamese use. On the same 70-message reused Vietnamese diagnostic the previous external model yielded TP=17, FN=0, FP=20, TN=33. The current model reduces false positives to 9 but misses 3 positives. Historical diagnostics are not new independent tests or threshold-tuning data.

URL performance differs materially between source-label and human-audit tests. Their targets and sampling differ; report both without pooling or discarding the harder test. These findings do not establish deployment readiness, superiority to neural models, calibrated probabilities or algorithmic novelty. No significance or campaign-level confidence interval is asserted.

## 6. Runtime contract and evidence still needed

The web adapter verifies bundle SHA-256, frozen helper hashes, estimator runtime and thresholds. API execution starts Python per request, so loading/import costs belong in endpoint timing. No measured end-to-end mobile/edge latency, cloud benchmark, memory profile or API-call saving is established here. The supplied PDF's sub-4ms, 74.2% API-saving and calibrated VLM-routing claims are excluded.

Future work requires a separately collected human-verified Vietnamese evaluation, more independent positive campaigns, provenance-specific reporting and feature ablations on newly reserved data. A fusion study requires actual paired messages, message-level labels, training-only grouped OOF scores and untouched final evaluation. Already inspected tests must not select it. Calibration, uncertainty estimation, VLM escalation and latency benchmarking remain separate uncompleted experiments.

## Reproduction and evidence

- `ml_model/data/prepared/processed_agent_fit_2026-10-25/training_report.json`: current fit and hashes.
- `ml_model/data/prepared/smishx_training_2026-10-25/`: SMS partitions, frozen selection, predictions and group audit.
- `ml_model/data/prepared/external_training_2026-10-25/`: URL partitions, frozen selection, predictions and human audit.
- `docs/web-model-activation-2026-10-25.md`: adapter and API parity evidence.
- `docs/paper-framework-comparison-2026-10-25.md`: comparison, data decisions and missing submission evidence.
- `docs/paper-alignment-audit-2026-10-25.json`: read-only manifest/hash and saved-prediction checks for this revision.

Sources checked on 25 October 2026:

- [Mishra–Soni SMS dataset v1](https://data.mendeley.com/datasets/f45bkkt8pr/1).
- [SmishX pinned repository](https://github.com/yizhu-joy/SmishX/tree/116a8c827741e0572563f678d25ed04306b1e3ff).
- [PhishVN dataset v4](https://data.mendeley.com/datasets/b97hxbxtpd/4).
- [scikit-learn grouped evaluation guidance](https://scikit-learn.org/stable/modules/cross_validation.html).
- [scikit-learn logistic regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression).
- [scikit-learn sample-weighted class balancing](https://scikit-learn.org/stable/modules/generated/sklearn.utils.class_weight.compute_class_weight.html).
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
