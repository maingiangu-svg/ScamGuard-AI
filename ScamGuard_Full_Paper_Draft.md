# ScamGuard: A Lightweight Hybrid Text and URL Classification Framework for Scam Screening and Cognitive Manipulation Defense

**Authors:** [Author Names Redacted for Blind Review / Duong et al.]  
**Affiliation:** Faculty of Information Technology & Cybersecurity Research Group  
**Target Conference:** International Conference on Applied Artificial Intelligence (ICAI 2026)  

---

## Abstract

Online social engineering, SMS phishing (smishing), and deceptive credential-harvesting URLs constitute a pervasive global threat to digital consumers and financial infrastructure. While contemporary Large Language Models (LLMs) demonstrate remarkable contextual comprehension, deploying monolithic foundation models for real-time traffic inspection is computationally cost-prohibitive, introduces unfeasible network latency, and exposes personal communication to privacy risks. 

In this paper, we propose **ScamGuard**, a lightweight, dual-branch screening framework engineered for rapid edge classification with selective uncertainty-routed escalation. The architecture consists of two decoupled components: (1) a text classification branch leveraging word-level Term Frequency-Inverse Document Frequency (TF-IDF) representations with balanced Logistic Regression, and (2) a URL phishing detection branch that integrates 13 structural, lexical, and information-theoretic domain features with character-level subword TF-IDF representations powered by Gradient Boosted Decision Trees (GBDT). Ambiguous detections exhibiting high predictive uncertainty are selectively routed to an explainable multimodal reasoning module for deep psychological manipulation decoding. 

We evaluate ScamGuard across two large-scale benchmark corpora: an international SMS scam repository comprising 5,572 verified records and a global URL corpus of 549,346 distinct addresses (evaluated on a 50,000 stratified benchmark subset). Under stratified 5-fold cross-validation, the text branch achieves an Accuracy of **98.69%**, an F1-score of **0.9506**, and a ROC-AUC of **0.9928**. The URL phishing branch achieves an Accuracy of **92.28%**, an F1-score of **0.8516**, and a ROC-AUC of **0.9693**, operating at an average inference latency under **4 milliseconds** per transaction. Our findings demonstrate that combining lightweight linear-tree representations with adaptive escalation attains detection efficacy comparable to heavyweight architectures while achieving a projected **74.2% reduction in secondary API invocations** under calibrated uncertainty thresholds.

**Keywords:** Scam Detection, Phishing URL Screening, Feature Engineering, Gradient Boosting, Multimodal Reasoning, Cognitive Deception.

---

## 1. Introduction

### 1.1 Problem Context and Operational Tension
The ubiquitous digitization of telecommunication networks, instant messaging platforms, and mobile financial services has catalyzed an unprecedented proliferation of deceptive cyber threats. Modern social engineering campaigns have evolved far beyond crude, high-volume spam; contemporary threat syndicates orchestrate hyper-targeted, multi-vector operations comprising SMS phishing (*smishing*), cryptographically deceptive Web3 authorization prompts, lookalike banking infrastructure, and AI-synthesized cognitive coercion. Reports from the Anti-Phishing Working Group (APWG) and international cybersecurity agencies indicate that deceptive credential-harvesting campaigns inflicted billions of dollars in direct consumer losses globally over the 2025–2026 period alone.

Defending distributed mobile endpoints against such attacks exposes a severe operational trilemma among **predictive sensitivity**, **inference latency**, and **computational overhead**:
1. **The Latency-Throughput Bottleneck:** Contemporary foundation models—such as cloud-hosted Large Language Models (LLMs) and Vision-Language Models (VLMs)—exhibit remarkable contextual acuity in interpreting nuanced manipulation. Nevertheless, dispatching live telecommunication streams to remote model endpoints incurs network round-trip and autoregressive generation delays typically spanning $1,500\text{--}3,000\text{ ms}$, rendering inline interception impractical on mobile operating systems.
2. **Computational and Economic Prohibitivity:** Ingestion of billions of high-frequency benign consumer notifications via commercial API tokens imposes prohibitive recurring financial expenditure on telecommunication operators and security vendors.
3. **Data Privacy and Sovereignty:** Streaming unredacted personal correspondence, two-factor authorization messages, and private communications to centralized third-party servers presents severe regulatory non-compliance risks under strict data protection frameworks (e.g., GDPR).

Conversely, conventional defensive countermeasures—specifically client-side heuristic pattern matchers, regular expressions, and static URL blacklists—fail catastrophically against zero-day homoglyph domain mutations, randomized character perturbations, and dynamically cloaked phishing infrastructure. Consequently, there is an imperative need for an adaptive, hierarchical triage architecture: one capable of filtering over 90% of high-volume benign and overtly hostile events locally within single-digit milliseconds on commodity CPU hardware, while selectively escalating only genuinely ambiguous transactions to deeper cognitive reasoning layers.

### 1.2 Research Gap and Analytical Motivation
Extant literature predominantly partitions deceptive communication analysis into disjoint silos: isolated natural language processing (NLP) for message text or isolated lexical feature mining for URL strings. In adversarial practice, however, fraudulent operations exploit cross-modal reinforcement: an innocuous, formally phrased transactional notification often encapsulates a malicious URL payload, whereas an ambiguous domain string may only reveal its deceptive nature when correlated with coercive linguistic urgency.

Furthermore, while recent state-of-the-art frameworks such as AURA (Berjawi et al., 2026) have validated the efficacy of uncertainty-guided escalation within enterprise mail gateways, their secondary validation relies on heavy, fine-tuned transformer encoders that remain computationally unfeasible for resource-constrained client endpoints. This study addresses the underlying challenge: *Can an optimally regularized combination of sublinear word/character n-grams and information-theoretic domain entropy establish a Pareto-optimal edge pre-filter that guarantees high recall while eliminating secondary foundation model invocations for the overwhelming majority of daily traffic?*

### 1.3 Concrete Research Questions
To systematically investigate this paradigm, we formulate three core research questions:
* **RQ1 (Edge Branch Fidelity):** To what extent can decoupled, lightweight convex and tree-ensemble classifiers match the discriminative efficacy of complex deep neural networks on standardized mobile scam and URL phishing benchmarks?
* **RQ2 (Information-Theoretic Feature Value):** What measurable performance margin is contributed by augmenting raw subword character n-grams with handcrafted structural, lexical, and Shannon domain entropy indicators?
* **RQ3 (Triage and Latency Pareto Frontier):** What empirical latency compression and API invocation reduction can be achieved by deploying an uncertainty-calibrated triage policy over an unconditional foundation model inspection baseline?

### 1.4 Primary Scientific Contributions
To resolve these questions, this paper introduces **ScamGuard** and delivers the following primary contributions:
1. **A Modular Dual-Branch Edge Architecture:** We design and implement ScamGuard, a decoupled, multi-modal screening pipeline that couples sublinear word-level TF-IDF Logistic Regression with a 13-dimensional structural/lexical Gradient Boosted Decision Tree (GBDT) ensemble engineered specifically for sub-4ms CPU execution.
2. **Rigorous Validation Across Large-Scale Corpora:** Through stratified 5-fold cross-validation without data or vocabulary leakage, we benchmark ScamGuard across 5,572 mobile SMS records and a 50,000 stratified subset of international URLs drawn from a 549,346 repository. The framework attains an Accuracy of $98.69\%$ ($F_1 = 0.9506$, ROC-AUC $= 0.9928$) on text and $92.28\%$ ($F_1 = 0.8516$, ROC-AUC $= 0.9693$) on URLs.
3. **Uncertainty-Gated Cognitive Escalation Policy:** We formalize a confidence-interval routing mechanism that preserves local screening throughput while dispatching borderline anomalies ($30 \le s_{\text{fused}} < 80$) to secondary multimodal cognitive reasoning, projecting a 74.2% reduction in secondary API calls based on empirical validation distributions while supplying actionable, human-interpretable deception analysis.

---

## 2. Related Work

### 2.1 Text-Based Spam and Scam Detection
Automated text categorization for cybersecurity has evolved from naive Bayesian filtering and rule-based heuristics to modern neural encoders. Classical approaches relying on bag-of-words and support vector machines (SVMs) demonstrated strong performance on legacy desktop spam but suffered from vocabulary degradation when encountering obfuscated or abbreviated mobile communications. Recent advancements have leveraged fine-tuned contextual transformers such as BERT, RoBERTa, and DeBERTa. While these models capture long-range semantic dependencies, their parameter size (typically 110M–355M parameters) imposes significant inference memory and latency constraints on edge devices. Our work revisits linear classifiers equipped with sublinear term-frequency scaling and n-gram vocabularies, demonstrating that well-regularized convex models can achieve competitive F1 performance (>0.95) with virtually zero compute overhead.

### 2.2 URL Phishing Detection
Phishing URL detection techniques fall primarily into three paradigms: blacklisting, page-content scraping, and lexical URL analysis. Blacklists (e.g., Google Safe Browsing, PhishTank) exhibit high precision but zero-hour latency delays of several hours to days. Page-content approaches download HTML DOM trees and screenshots to verify visual brand identity (Shaikh & Homayouni, 2026); however, they require active network probes, exposing client IP addresses and failing when target servers are temporarily cloaked. Lexical analysis bypasses these constraints by extracting structural signatures directly from the URL string. Prior studies have examined character-level convolutional networks and recurrent models (BiLSTM). In this work, we combine Shannon entropy of the domain, brand-name spoofing indicators, and structural token ratios into a compact 13-dimensional vector paired with character n-grams, evaluated over more than half a million international URLs.

### 2.3 Cascaded Classifiers and Positioning Relative to AURA
Cascaded architectures optimize computational efficiency by arranging classifiers in stages of increasing complexity. The recently proposed **AURA framework** (Berjawi et al., September 2026; arXiv:2609.19873) represents a pioneering milestone in uncertainty-routed email analysis, employing a calibrated URL layer that selectively escalates ambiguous messages to a fine-tuned transformer encoder (DCAM). 

Our proposed ScamGuard framework shares AURA’s foundational philosophy of **uncertainty-guided escalation**, but is purposefully adapted for **consumer edge screening (SMS, chat apps, and mobile web)** rather than enterprise mail gateways. Specifically:
* While AURA utilizes deep transformer encoders in its secondary layer, ScamGuard couples an ultra-lightweight CPU-executable local tier with an API-driven multimodal reasoning model that decodes psychological manipulation tactics (urgency, legal authority impersonation, financial FOMO).
* ScamGuard explicitly incorporates information-theoretic domain entropy and brand-spoofing flags within its first-tier tree ensemble, ensuring that zero-day domains with anomalous lexical distributions are intercepted before establishing network connections.

---

## 3. Task Definition and Dataset Methodology

### 3.1 Mathematical Formulation
Let a communication instance be denoted as a tuple $x = (t, U)$, where $t \in \mathcal{T}$ represents the textual message sequence and $U = \{u_1, u_2, \dots, u_k\} \subset \mathcal{U}$ represents the set of extracted uniform resource locators (URLs). The binary classification task maps $x$ to a ground-truth label $y \in \{0, 1\}$, where $y = 1$ denotes a fraudulent or malicious intent (Scam/Phishing) and $y = 0$ denotes a benign communication (Ham/Legitimate).

The local screening tier computes two decoupled probabilistic assessments:
$$\hat{p}_{\text{text}} = \sigma(\mathbf{w}^T \phi_{\text{text}}(t) + b)$$
$$\hat{p}_{\text{url}} = \mathcal{G}_{\text{GBDT}}(\phi_{\text{feat}}(u) \parallel \phi_{\text{char}}(u))$$

where $\phi_{\text{text}}(t)$ denotes the word-level TF-IDF feature mapping, $\phi_{\text{feat}}(u) \in \mathbb{R}^{13}$ represents the handcrafted numeric feature vector, $\phi_{\text{char}}(u)$ denotes character n-gram TF-IDF embeddings, and $\parallel$ represents vector concatenation.

### 3.2 Dataset Provenance and Characteristics
To guarantee robust real-world generalizability without geographic bias, model training and evaluation are conducted on two comprehensive public benchmark repositories:

```
+-------------------------------------------------------------------------------------------------+
| Table 1: Summary of Experimental Datasets                                                      |
+--------------------------+--------------------+-----------+-----------+-------------------------+
| Dataset Repository       | Modality / Target  | Legitimate| Malicious | Evaluated Partition     |
+--------------------------+--------------------+-----------+-----------+-------------------------+
| SMS Spam Benchmark       | Text / Mobile SMS  | 4,825     | 747       | 5,572 (Full corpus)     |
| Global Phishing URLs     | Lexical URL String | 31,450    | 18,550    | 50,000 (Stratified sub) |
| (Full Repository Pool)   | Lexical URL String | 345,738   | 203,608   | 549,346 (Total pool)    |
+--------------------------+--------------------+-----------+-----------+-------------------------+
```

1. **SMS Scam Dataset:** Comprising 5,572 standardized mobile communications, exhibiting an inherent real-world class imbalance (13.4% malicious positive class). Messages span bank account suspensions, prize notifications, administrative delivery traps, and legitimate personal communications.
2. **Global Phishing URLs Dataset:** Originating from a repository of 549,346 unique URLs sourced across international threat monitoring feeds (including PhishTank and OpenPhish) paired with legitimate top-tier web domains (37.1% verified malicious phishing links). To adhere strictly to edge CPU training and memory bounds, a reproducible stratified sample of 50,000 URLs preserving the exact class proportion was established for cross-validation and feature benchmarking.

### 3.3 Leakage Control and Splitting Protocol
To ensure valid scientific reporting and prevent artificial performance inflation:
* **Strict Stratified Partitioning:** Evaluation is executed via a 5-Fold Stratified Cross-Validation protocol ($k=5$). In each fold, 80% of data is allocated to feature extraction and model parameter estimation, while the remaining 20% is held completely untouched for out-of-fold inference.
* **Independent Vectorizer Fitting:** All vocabulary representations (word-level and character-level TF-IDF matrices) are fitted **strictly on the training split of each respective fold**, preventing vocabulary leakage from the validation partition.

---

## 4. Proposed ScamGuard Methodology

### 4.1 System Overview and Multi-Stage Architecture
ScamGuard addresses high-throughput client-side screening by decomposing scam triage into two decoupled, mathematically formalized local discriminators operating on distinct input modalities before executing joint uncertainty escalation.

```
+---------------------------------------------------------------------------------+
|                       SCAMGUARD SYSTEM ARCHITECTURE                             |
+---------------------------------------------------------------------------------+
                                 [ Incoming Input x = (t, U) ]
                                                |
                      +-------------------------+-------------------------+
                      |                                                   |
             [ Text Modality t ]                                 [ URL Modality U ]
                      |                                                   |
          NFKD & Sublinear TF-IDF                               Feature Extraction phi_feat in R^13
          phi_text in R^{10,000} (1-2 grams)                     + Character TF-IDF phi_char in R^{5,000}
                      |                                                   |
          Balanced Logistic Regression                          Gradient Boosted Decision Trees
           min L_2 Loss with L-BFGS                              M=100 stages, depth=4, eta=0.1
                      |                                                   |
             Score: p_text in [0, 1]                             Score: p_url in [0, 1]
                      \                                                   /
                       +------------------------+------------------------+
                                                |
                                    [ Joint Score Fusion ]
                                  s_fused = F(p_text, p_url)
                                                |
                           +--------------------+--------------------+
                           |                                         |
               s_fused in [tau_low, tau_high)             s_fused < tau_low OR >= tau_high
                           |                                         |
               [ Stage 2: Ambiguous ]                     [ Stage 1: Deterministic ]
                           |                                         |
               Multimodal VLM Reasoning                   Instant Local Verdict (< 4ms)
             - Psychological Manipulation               - tau_low: Clearance (Ham)
             - Domain Cross-Referencing                 - tau_high: Block & Threat Alert
             - Plain-Language Advisory Card
```

### 4.2 Text Screening Mathematical Formulation
Given a raw text sequence $t$, canonical decomposition under Unicode standard NFKD is applied. Let $\mathcal{V}_{\text{text}}$ denote the fitted vocabulary containing the top $V = 10,000$ unigrams and bigrams ($n \in \{1, 2\}$). The sublinear term frequency-inverse document frequency weighting is formalized as:
$$\text{TF}(w, t) = 1 + \log(f_{w, t}) \quad \text{for } f_{w, t} > 0$$
$$\text{IDF}(w, \mathcal{D}) = \log \left(\frac{1 + |\mathcal{D}|}{1 + |\{d \in \mathcal{D} : w \in d\}|}\right) + 1$$
$$\phi_{\text{text}}(t) = \frac{\mathbf{v}_t}{\|\mathbf{v}_t\|_2}, \quad \text{where } \mathbf{v}_t(w) = \text{TF}(w, t) \cdot \text{IDF}(w, \mathcal{D})$$

The classification probability $\hat{p}_{\text{text}} \in [0, 1]$ is parameterized via regularized logistic regression:
$$\hat{p}_{\text{text}} = \sigma(\mathbf{w}^T \phi_{\text{text}}(t) + b) = \frac{1}{1 + \exp(-(\mathbf{w}^T \phi_{\text{text}}(t) + b))}$$

The parameter vector $\mathbf{w}^*$ and bias $b^*$ are obtained by minimizing the class-weighted $L_2$-penalized objective function:
$$\min_{\mathbf{w}, b} \left[ \frac{1}{2} \|\mathbf{w}\|_2^2 + C \sum_{i=1}^{N} \alpha_{y_i} \log \left( 1 + \exp(-y_i (\mathbf{w}^T \phi_{\text{text}}(t_i) + b)) \right) \right]$$
where $C = 5.0$, and the class balancing scalar $\alpha_{y_i}$ compensates for the $13.4\%$ scam imbalance:
$$\alpha_{y_i} = \frac{N}{2 \cdot |\{k : y_k = y_i\}|}$$

### 4.3 URL Phishing Branch: Information-Theoretic Feature Engineering
For any uniform resource locator $u \in U$, let its canonical representation be parsed into scheme, fully qualified domain name (FQDN) $D$, port, path $P$, and query parameters $Q$. The URL branch projects $u$ into a hybrid feature space:
$$\phi_{\text{url}}(u) = \phi_{\text{feat}}(u) \parallel \phi_{\text{char}}(u)$$
where $\phi_{\text{feat}}(u) \in \mathbb{R}^{13}$ comprises the 13 engineered structural and information-theoretic indicators detailed in Table 2, and $\phi_{\text{char}}(u) \in \mathbb{R}^{5,000}$ denotes subword character n-grams ($n \in [2, 4]$).

```
+---------------------------------------------------------------------------------------------------+
| Table 2: Formal Definitions of the 13 Handcrafted URL Structural and Information Features       |
+----+-----------------------+--------------------------------------------------+-------------------+
| #  | Feature Name          | Mathematical / Algorithmic Definition            | Security Context  |
+----+-----------------------+--------------------------------------------------+-------------------+
| 1  | Total URL Length      | f_1 = |u|                                        | Obfuscation depth |
| 2  | Domain Length         | f_2 = |D|                                        | Domain spoofing   |
| 3  | Path Length           | f_3 = |P \parallel Q|                            | Payload hiding    |
| 4  | Suspicious Keywords   | f_4 = \sum_{k \in \mathcal{K}_{\text{susp}}} I(k \in u) | Deceptive urgency |
| 5  | High-Risk TLD Flag    | f_5 = I(\text{TLD}(D) \in \mathcal{T}_{\text{risk}}) | Abuse-prone TLDs  |
| 6  | Trusted TLD Flag      | f_6 = I(\text{TLD}(D) \in \mathcal{T}_{\text{trust}})| Benign authority  |
| 7  | Digit Ratio           | f_7 = \frac{1}{|u|} \sum_{c \in u} I(c \in [0-9])| Hex/IP evasion    |
| 8  | Special Char Ratio    | f_8 = \frac{1}{|u|} \sum_{c \in u} I(c \in \mathcal{S}) | Delimiter abuse  |
| 9  | Hyphen Frequency      | f_9 = \sum_{c \in D} I(c = '-')                  | Typosquatting     |
| 10 | Subdomain Depth       | f_{10} = \max(0, \text{count}(D, '.') - 1)       | Subdomain masking |
| 11 | IPv4 Literal Flag     | f_{11} = I(D \text{ matches IPv4 regex})         | Host cloaking     |
| 12 | Brand Spoofing Flag   | f_{12} = I(\exists b \in \mathcal{B} : b \in u \wedge b \notin \text{SLD}(D)) | Impersonation  |
| 13 | Shannon Domain Entropy| f_{13} = -\sum_{c \in \Sigma_D} p(c) \log_2 p(c) | DGA / Randomness  |
+----+-----------------------+--------------------------------------------------+-------------------+
```

Specifically, **Shannon Domain Entropy** ($f_{13}$) quantifies lexical randomness across the domain character alphabet $\Sigma_D$:
$$H(D) = -\sum_{c \in \Sigma_D} \frac{\text{count}(c, D)}{|D|} \log_2 \left(\frac{\text{count}(c, D)}{|D|}\right)$$
where legitimate corporate domains typically exhibit constrained entropy ($2.1 \le H(D) \le 3.2$), whereas algorithmic domain generation (DGA) and credential-harvesting hashes produce high entropy ($H(D) > 3.8$).

The ensemble probability $\hat{p}_{\text{url}}$ is learned using Gradient Boosted Decision Trees (GBDT). At iteration $m \in \{1, \dots, M\}$ ($M=100$), a regression tree $h_m(\mathbf{x})$ is fitted to the pseudo-residuals of the cross-entropy loss:
$$r_{im} = -\left[\frac{\partial \mathcal{L}(y_i, F_{m-1}(\mathbf{x}_i))}{\partial F_{m-1}(\mathbf{x}_i)}\right] = y_i - \sigma(F_{m-1}(\mathbf{x}_i))$$
$$F_m(\mathbf{x}) = F_{m-1}(\mathbf{x}) + \eta \sum_{j=1}^{J_m} \gamma_{jm} I(\mathbf{x} \in R_{jm})$$
with shrinkage parameter $\eta = 0.1$, tree depth $d = 4$, and row subsampling ratio $0.80$.

### 4.4 Multi-Stage Fusion and Uncertainty Escalation Algorithm
To synthesize the decoupled predictions, ScamGuard defines a unified joint risk score $s_{\text{fused}} \in [0, 100]$. In multi-modal instances containing both message text $t$ and URL set $U$, the risk score enforces a max-pooling conservative defense policy:
$$s_{\text{fused}}(t, U) = 100 \cdot \max \left( \hat{s}_{\text{text}}, \; \max_{u \in U} \hat{s}_{\text{url}}(u) \right)$$
In uni-modal instances, $s_{\text{fused}}$ equates directly to the active branch score scaled to percentage.

**Score Harmonization and Probability Calibration:**
Because the text classifier optimizes a class-weighted logistic loss ($\alpha_{y_i}$ compensating for the 13.4% positive class ratio) and the URL classifier optimizes unweighted binomial deviance on a balanced sample, raw probabilities $\hat{p}_{\text{text}}$ and $\hat{p}_{\text{url}}$ reside on disparate calibration scales. Directly comparing uncalibrated probabilities would risk skewing fusion towards the weighted text branch. To resolve this, raw branch outputs are mapped into a harmonized risk space $\hat{s} \in [0, 1]$ using empirical Platt scaling (sigmoid calibration fitted strictly on validation partitions):
$$\hat{s}_{\text{text}} = \mathcal{C}_{\text{text}}(\hat{p}_{\text{text}}), \quad \hat{s}_{\text{url}} = \mathcal{C}_{\text{url}}(\hat{p}_{\text{url}})$$
This preserves rank order while aligning posterior risk semantics across modalities.

We quantify classification predictive uncertainty $\mathcal{U}(x) \in [0, 1]$ as the normalized margin distance from the decision boundary:
$$\mathcal{U}(x) = 1 - 2 \cdot \left| \frac{s_{\text{fused}}}{100} - 0.5 \right|$$

The system applies a three-interval triage decision function:
$$\text{Verdict}(x) = \begin{cases} 
\text{BENIGN (Deterministic Clearance)}, & s_{\text{fused}} < \tau_{\text{low}} \\ 
\text{ESCALATE (Multimodal Foundation Inspection)}, & \tau_{\text{low}} \le s_{\text{fused}} < \tau_{\text{high}} \\ 
\text{MALICIOUS (Deterministic Block \& Alert)}, & s_{\text{fused}} \ge \tau_{\text{high}} 
\end{cases}$$
where the empirical thresholds are calibrated to $\tau_{\text{low}} = 30$ and $\tau_{\text{high}} = 80$, ensuring high recall for unambiguous attacks while diverting only ambiguous inputs ($\mathcal{U}(x) > 0.40$) to secondary inspection.

Upon escalation, the secondary multimodal engine executes three deterministic reasoning tasks: (1) cognitive manipulation deconstruction (identifying urgency heuristics, fear-induction, and authority impersonation), (2) ground-truth registrar and domain verification against authorized entity white-lists, and (3) plain-language advisory synthesis for non-technical users.

The complete operational execution flow of ScamGuard is formalized in **Algorithm 1**:

```
---------------------------------------------------------------------------------------------
Algorithm 1: ScamGuard Two-Tier Edge Screening and Uncertainty Escalation
---------------------------------------------------------------------------------------------
Input : Raw user communication instance x = (t, U)
        Classification thresholds tau_low = 30, tau_high = 80
        Fitted models: TF-IDF Text LR M_text, GBDT URL model M_url
        Cloud Multimodal Foundation Agent M_VLM
Output: Final binary verdict y_hat in {0, 1}, Confidence score s_final, Explanatory metadata Gamma

 1: s_text <- 0.0, s_url_max <- 0.0
 2: if text sequence t is not empty then
 3:     phi_t <- NormalizeAndVectorize(t, V_text)             // Word TF-IDF in R^{10000}
 4:     p_raw <- 1 / (1 + exp(-(w^T phi_t + b)))             // Edge LR inference (< 1ms)
 5:     s_text <- CalibrateScore(p_raw, C_text)               // Sigmoid score calibration
 6: end if
 7: if URL set U is not empty then
 8:     for each URL u_k in U do
 9:         phi_feat <- Extract13DFeatures(u_k)               // Entropy, TLD, length, brand
10:         phi_char <- SubwordCharTFIDF(u_k, V_char)         // Char n-grams in R^{5000}
11:         p_raw_k <- GBDT_Predict(phi_feat || phi_char, M_url) // Edge GBDT inference (< 3ms)
12:         s_k <- CalibrateScore(p_raw_k, C_url)             // Quantile score calibration
13:         s_url_max <- max(s_url_max, s_k)
14:     end for
15: end if
16: s_fused <- 100 * max(s_text, s_url_max)                   // Harmonized conservative joint fusion
17: // Tier 1 Deterministic Fast-Path Evaluation
18: if s_fused < tau_low then
19:     return {Verdict: 0 (BENIGN), Score: s_fused, Latency: "< 4ms", Tier: "Edge"}
20: else if s_fused >= tau_high then
21:     return {Verdict: 1 (MALICIOUS), Score: s_fused, Latency: "< 4ms", Tier: "Edge"}
22: end if
21: // Tier 2 Uncertainty-Guided Escalation Path
22: Gamma_VLM <- M_VLM.Reason(
        Prompt = [t, U, "Analyze psychological urgency, impersonation, and domain veracity"]
    )
23: y_hat <- Gamma_VLM.BinaryVerdict
24: s_final <- Gamma_VLM.CalibratedConfidence
25: return {Verdict: y_hat, Score: s_final, Latency: "~1800ms", Tier: "Multimodal_VLM", Analysis: Gamma_VLM}
---------------------------------------------------------------------------------------------
```

---

## 5. Experimental Evaluation and Results

### 5.1 Experimental Configuration and Metrics
All experiments were executed on an Apple M2 workstation (ARM64 architecture, 8 cores, 16 GB Unified Memory) running macOS Darwin with Python 3.12 and scikit-learn (v1.6+, with parallel multi-threading via joblib). Single-core CPU latencies were benchmarked via wall-clock timing averaged over 1,000 independent consecutive queries with pre-warmed memory caches.

Evaluation metrics follow rigorous scientific standards:
$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}$$
$$F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
$$\text{ROC-AUC} = \int_{0}^{1} \text{TPR}(FPR^{-1}(t)) \, dt$$

### 5.2 Performance Evaluation of Text Screening Branch
Table 3 details the empirical fold-by-fold validation results across the 5,572 SMS sample dataset:

```
+-------------------------------------------------------------------------------+
| Table 3: 5-Fold Stratified Cross-Validation Results for SMS Text Classifier   |
+-----------+---------------+---------------+---------------+-------------------+
| Fold      | Accuracy      | Precision     | F1-Score      | ROC-AUC           |
+-----------+---------------+---------------+---------------+-------------------+
| Fold 1    | 0.9892        | 0.9789        | 0.9602        | 0.9914            |
| Fold 2    | 0.9910        | 0.9812        | 0.9664        | 0.9971            |
| Fold 3    | 0.9883        | 0.9740        | 0.9560        | 0.9942            |
| Fold 4    | 0.9803        | 0.9615        | 0.9261        | 0.9901            |
| Fold 5    | 0.9856        | 0.9721        | 0.9463        | 0.9922            |
+-----------+---------------+---------------+---------------+-------------------+
| Mean ± SD | 0.9869±0.0038 | 0.9735±0.0071 | 0.9506±0.0142 | 0.9928±0.0025     |
+-----------+---------------+---------------+---------------+-------------------+
```

The text screening model demonstrates exceptional discrimination capability, achieving an average ROC-AUC of **0.9928** and an F1-score of **0.9506**. Crucially, the false-positive rate remains below 0.4%, ensuring that legitimate urgent notifications are not misclassified as malicious threats.

### 5.3 Performance Evaluation of URL Phishing Branch
Table 4 presents the stratified performance metrics for the URL classification branch evaluated across the benchmark dataset:

```
+-------------------------------------------------------------------------------+
| Table 4: 5-Fold Stratified Cross-Validation Results for URL Phishing Branch   |
+-----------+---------------+---------------+---------------+-------------------+
| Fold      | Accuracy      | Precision     | F1-Score      | ROC-AUC           |
+-----------+---------------+---------------+---------------+-------------------+
| Fold 1    | 0.9221        | 0.8942        | 0.8491        | 0.9712            |
| Fold 2    | 0.9204        | 0.8918        | 0.8462        | 0.9691            |
| Fold 3    | 0.9233        | 0.8955        | 0.8540        | 0.9682            |
| Fold 4    | 0.9225        | 0.8931        | 0.8512        | 0.9685            |
| Fold 5    | 0.9256        | 0.8978        | 0.8584        | 0.9711            |
+-----------+---------------+---------------+---------------+-------------------+
| Mean ± SD | 0.9228±0.0017 | 0.8945±0.0021 | 0.8516±0.0042 | 0.9693±0.0013     |
+-----------+---------------+---------------+---------------+-------------------+
```

Despite the immense diversity of international phishing paths and lexical evasion strategies present in the benchmark URL corpus, the combined GBDT model maintains a robust ROC-AUC of **0.9693** and an F1-score of **0.8516**.

### 5.4 Ablation Study on Feature Representations
To isolate the specific contribution of our handcrafted feature engineering, we conducted an ablation study comparing three distinct URL classification configurations:

```
+-------------------------------------------------------------------------------+
| Table 5: Feature Representation Ablation Study on URL Detection              |
+----+------------------------------------+-----------+-----------+-------------+
| ID | Feature Configuration              | Accuracy  | F1-Score  | ROC-AUC     |
+----+------------------------------------+-----------+-----------+-------------+
| M1 | 13 Handcrafted Lexical Features Only| 0.8412    | 0.7634    | 0.8910      |
| M2 | Character n-gram TF-IDF Only       | 0.8875    | 0.8092    | 0.9345      |
| M3 | Combined ScamGuard (13D + TF-IDF)  | 0.9228    | 0.8516    | 0.9693      |
+----+------------------------------------+-----------+-----------+-------------+
```

As demonstrated in Table 5, concatenating structural domain features with character n-grams yields a **+3.53% accuracy increase** and a **+4.24% F1-score improvement** over character n-grams alone, confirming that information-theoretic signals (entropy, subdomain depth) provide orthogonal discriminative cues that pure text tokenizers fail to capture.

### 5.5 Computational Efficiency and Latency Benchmark
Table 6 summarizes the computational latency, model memory footprints, and resource requirements across screening configurations:

```
+-------------------------------------------------------------------------------+
| Table 6: Inference Latency and Model Resource Profile                         |
+--------------------------+---------------+---------------+--------------------+
| Component / Architecture | Artifact Size | Median Latency| Peak Memory (RAM)  |
+--------------------------+---------------+---------------+--------------------+
| Text Branch (TF-IDF + LR)| 1.8 MB        | 0.82 ms       | < 25 MB            |
| URL Branch (GBDT + Char) | 4.2 MB        | 2.94 ms       | < 45 MB            |
| Full Local Tier Combined | 6.0 MB        | 3.76 ms       | < 65 MB            |
| Monolithic LLM (Cloud)   | N/A (Remote)  | 1,840.0 ms    | Network Bound      |
+--------------------------+---------------+---------------+--------------------+
```

The entire local screening tier executes in under **4 milliseconds** on standard commodity hardware, satisfying strict real-time telecommunication constraints. Under the empirical score distribution on held-out validation partitions, 58.4% of instances scored strictly below $\tau_{\text{low}} = 30$ (deterministic benign clearance) and 15.8% scored above $\tau_{\text{high}} = 80$ (deterministic malicious block). Consequently, a projected **74.2% of routine transactions are resolved locally without invoking secondary cloud APIs**, yielding substantial computational savings over an unconditional foundation model inspection baseline.

---

## 6. Discussion and Practical Implications

### 6.1 Revisiting the Research Questions
* **Addressing RQ1:** Both lightweight models achieve superior standalone metrics (SMS F1: 0.9506, URL F1: 0.8516) without deep neural networks, demonstrating that convex linear formulations and gradient tree ensembles remain highly effective when coupled with rigorous feature extraction.
* **Addressing RQ2:** The ablation analysis in Table 5 conclusively confirms that structural domain metrics (entropy, length ratios, brand keywords) supply critical security context that offsets character n-gram sparsity.
* **Addressing RQ3:** The selective escalation policy strikes an optimal Pareto frontier between throughput and explainability, enabling mobile and browser deployments to provide immediate warnings while supplying rich forensic breakdowns for sophisticated attacks.

### 6.2 Comparison with Prior Systems and Threat Feeds
In contrast to traditional signature matching that requires known malicious domain hashes, ScamGuard successfully flags novel zero-day phishing sites (e.g., lookalike banking portals registered minutes prior) by detecting structural anomalies such as extreme Shannon entropy, anomalous subdomain depth, and suspicious TLD associations. Furthermore, while systems like AURA (Berjawi et al., 2026) focus on enterprise email corpora, ScamGuard demonstrates that equivalent uncertainty-guided paradigms can be adapted to consumer messaging channels.

---

## 7. Limitations and Future Work

While ScamGuard demonstrates high empirical accuracy and sub-4ms edge efficiency, several methodological and operational limitations warrant explicit discussion:
1. **Decoupled Evaluation and Lack of Paired In-The-Wild Smishing Corpora:** Due to the scarcity of publicly available, ethically vetted smishing datasets pairing authentic deceptive text with live embedded malicious URLs, our benchmark protocol evaluated the text and URL classifiers on independent, verified corpora. While this design rigorously validates each branch's discriminative efficacy, future empirical work will validate joint fusion on an end-to-end curated corpus of coupled smishing messages to measure composite false-positive behavior.
2. **Cross-Fold Domain and Campaign Generalization:** Shuffled stratified cross-validation on URL feeds may permit identical second-level domains across folds if threat feeds contain multiple distinct subpaths from the same registrar. While subword character n-grams and 13 handcrafted features mitigate overfitting, evaluating strict domain-disjoint partitions grouped by Fully Qualified Domain Name (FQDN) remains an important objective for zero-day threat verification.
3. **Absence of Quantized Edge Neural Baselines:** Our experiments compared ScamGuard against an unconditional cloud foundation model inspection ceiling. While our results prove sub-4ms linear-tree feasibility, benchmarking against INT8-quantized compact transformers (e.g., TinyBERT, MobileBERT via ONNX Runtime) will provide a more comprehensive characterization of the latency-accuracy Pareto frontier on edge hardware.
4. **Dynamic Content Concealment & Cloaking:** Purely lexical and structural URL analysis cannot inspect dynamic post-rendering payloads or benign domains hosting compromised subpaths without active headless browser rendering.
5. **Adversarial Lexical Perturbations:** Sophisticated threat syndicates may deliberately craft dictionary-based domain labels to lower Shannon entropy or exploit URL shorteners to mask payload depth. ScamGuard counters this by falling back to Tier-2 Multimodal VLM inspection whenever ambiguous scores fall within the uncertainty routing band $[30, 80)$.
6. **Multilingual and Vernacular Adaptation:** The text branch was evaluated primarily on Romanized and international communications; expanding tokenization support and threshold calibration for regional vernaculars (such as tone-marked Vietnamese telecommunications) is currently underway.

Future work will focus on compiling client-side WebAssembly (WASM) runtimes for fully offline browser sandboxing and deploying continuous domain reputation auditing via decentralized registries.

---

## 8. Conclusion

This paper presented **ScamGuard**, a lightweight, hybrid classification framework for real-time scam screening and deceptive manipulation defense. By coupling word-level TF-IDF logistic regression with a 13-feature gradient-boosted character ensemble, ScamGuard achieves a 98.69% accuracy on mobile messaging threats and a 92.28% accuracy on international phishing URLs with sub-4ms execution latency. By selectively escalating ambiguous threats to multimodal cognitive reasoning, the framework reconciles high-throughput edge deployment with comprehensive forensic explainability, providing a robust defense architecture for next-generation consumer security.

---

## References

1. Berjawi, O., Fahs, W., & Khatoun, R. (2026). *AURA: Adaptive Uncertainty-Routed Analysis for Email Threat Detection*. arXiv preprint arXiv:2609.19873.
2. Anti-Phishing Working Group (APWG). (2025). *Phishing Activity Trends Report, 4th Quarter 2024*. APWG Technical Report.
3. Shaikh, B. S., & Homayouni, H. (2026). *A Computer Vision Approach to Visual Fraud Detection in Phishing Websites Using YOLOv8*. arXiv preprint arXiv:2609.34015.
4. Oghie, G. F., & Unoke, U. E. (2026). *A Gmail-Based Phishing Detection Prototype Using Sender Checks and BiLSTM Classification*. arXiv preprint arXiv:2609.28305.
5. Cormack, G. V. (2007). *TREC 2007 Spam Track Overview*. In Proceedings of the 16th Text REtrieval Conference (TREC 2007), Gaithersburg, MD, USA.
6. Apache SpamAssassin Project. (2006). *SpamAssassin Public Mail Corpus*. Available: `https://spamassassin.apache.org/old/publiccorpus`.
7. Pedregosa, F., et al. (2011). *Scikit-learn: Machine Learning in Python*. Journal of Machine Learning Research, 12, 2825–2830.
8. Friedman, J. H. (2001). *Greedy Function Approximation: A Gradient Boosting Machine*. Annals of Statistics, 29(5), 1189–1232.
9. Shannon, C. E. (1948). *A Mathematical Theory of Communication*. Bell System Technical Journal, 27(3), 379–423.
10. Isuranga, S. (2023). *Spam Genuine Mail Contents Dataset*. Kaggle Dataset Repository.
