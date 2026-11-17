# ARGUMAP — Machine Learning Pipeline Design

* **Document Version:** 1.0.0
* **Status:** Proposed ML Architecture & Evaluation Blueprint
* **Frameworks:** scikit-learn (Baselines), PyTorch, Hugging Face Transformers

---

## 1. Machine Learning System Architecture

ARGUMAP addresses argument mining through a two-stage sequential formulation:
1. **Task 1: Argument Component Classification** — Isolates and classifies discrete discourse propositions into one of 6 frozen argument component types.
2. **Task 2: Argument Relation Extraction** — Identifies directed rhetorical and logical relationships connecting pairs of argument units across 4 frozen relation types.

```
[Raw Discourse Turn]
         │
         ▼
[NLP Preprocessing & Segmentation]
         │
         ▼
 ┌────────────────────────────────────────────────────────┐
 │       Task 1: Argument Component Classifier           │
 │                                                        │
 │  Input:  Argument proposition text u_i                 │
 │  Output: {CLAIM, PREMISE, EVIDENCE,                    │
 │           COUNTERARGUMENT, REBUTTAL, OTHER}            │
 └──────────────────────────┬─────────────────────────────┘
                            │ Labeled Units {u_1, u_2, ..., u_n}
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │        Candidate Pair Pruner & Windowing Filter       │
 │                                                        │
 │  Filters O(n^2) pairs down to viable candidate links   │
 └──────────────────────────┬─────────────────────────────┘
                            │ Candidate Pairs (u_i, u_j)
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │          Task 2: Argument Relation Classifier         │
 │                                                        │
 │  Input:  (u_i, u_j) + Discourse Context                │
 │  Output: {SUPPORTS, ATTACKS, RESPONDS_TO, NO_RELATION} │
 └──────────────────────────┬─────────────────────────────┘
                            │ Non-trivial Edges
                            ▼
               [To Graph Compilation Engine]
```

---

## 2. Task 1: Argument Component Classification

### 2.1 Problem Formulation
Given an argument unit $u_i$ extracted from a debate turn, classify $u_i$ into exactly one of the 6 mutually exclusive frozen classes:
$$\mathcal{Y}_{\text{comp}} = \{\text{CLAIM}, \text{PREMISE}, \text{EVIDENCE}, \text{COUNTERARGUMENT}, \text{REBUTTAL}, \text{OTHER}\}$$

### 2.2 Input Representation & Preprocessing
* **Input Features:** Clean proposition text $u_i$, token count, and optional contextual signals:
  * Relative position in speech turn ($pos_{\text{turn}} \in [0.0, 1.0]$).
  * Relative position in entire debate session ($pos_{\text{debate}} \in [0.0, 1.0]$).
  * Presence of discourse connectives (e.g., *because*, *therefore*, *furthermore*, *however*, *on the contrary*, *for example*).
* **Text Normalization:**
  * Unicode normalization (NFKD) and ASCII quotation normalization.
  * Preservation of case (casing carries semantic markers in argument mining, e.g. capitalized acronyms or emphasis).
  * Punctuation normalization without stripping terminal question marks or exclamation marks.

### 2.3 Baseline Model: TF-IDF + Logistic Regression
To establish a rigorous, reproducible benchmark before evaluating deep neural architectures, ARGUMAP defines a classical machine learning baseline:
* **Feature Extraction:**
  * Word n-grams: Unigrams and bigrams ($1, 2$).
  * Sublinear term frequency scaling: $\text{tf} = 1 + \log(\text{tf})$.
  * Vocabulary constraints: $\text{min\_df} = 2$, $\text{max\_features} = 10,000$.
  * Character n-grams: Optional character 3-5 grams to capture morphological roots.
* **Classifier:** Multinomial Logistic Regression (`scikit-learn`).
  * Regularization: L2 penalty with hyperparameter $C \in [0.1, 1.0, 10.0]$ tuned via 5-fold cross-validation.
  * Class Weighting: `class_weight='balanced'` to offset class frequency skews (e.g. `PREMISE` typically outnumbers `REBUTTAL`).
  * Solver: `lbfgs` with a maximum of 1,000 iterations.

### 2.4 Transformer Model Exploration Strategy
After baseline benchmarking, transformer-based encoders will be empirically tested. **No final model architecture will be chosen without empirical validation against the baseline.**

* **Candidate Encoders for Empirical Benchmark:**
  * `microsoft/deberta-v3-base` (Strong disentangled attention and MLM pre-training on complex syntax).
  * `roberta-base` (Robust generalized representation benchmark).
  * `google/electra-base-discriminator` (High sample efficiency and discriminative capability).
* **Head Architecture:**
  * Standard sequence classification head with a dropout layer ($p=0.1$) followed by a linear projection $\mathbb{R}^{d_{\text{hidden}}} \rightarrow \mathbb{R}^{6}$.
* **Loss Function:**
  * Categorical Cross-Entropy with class-weight multipliers:
    $$\mathcal{L} = -\sum_{c=1}^{6} w_c y_c \log(\hat{y}_c)$$
  * Evaluation of Focal Loss ($\gamma = 2.0$) if minority classes (`REBUTTAL`, `EVIDENCE`) suffer severe recall suppression.

### 2.5 Training, Validation, and Testing Protocol
* **Split Strategy:** **Debate-Level Grouped Splitting** (70% Train, 15% Validation, 15% Test).
  * *Critical Rule:* All argument units from any single debate transcript must reside strictly within one partition. Splitting units randomly across the same debate causes severe data leakage through topic overlap and speaker idiosyncratic style.
* **Optimization Setup:**
  * Optimizer: AdamW ($\beta_1 = 0.9, \beta_2 = 0.999$, weight decay $= 0.01$).
  * Learning Rate: $2 \times 10^{-5}$ with linear warmup over the first 10% of training steps and cosine decay.
  * Early Stopping: Terminate training if validation Macro F1 fails to improve for 3 consecutive epochs.

### 2.6 Evaluation Metrics (Task 1)
* **Primary Metric:** **Macro-Averaged F1 Score** (treats all 6 classes equally regardless of class imbalance).
* **Secondary Metrics:**
  * Weighted F1 Score.
  * Per-class Precision, Recall, and F1 for each of the 6 frozen labels.
  * Confusion Matrix analysis to identify systemic confusions (e.g. `COUNTERARGUMENT` vs. `REBUTTAL`).

---

## 3. Task 2: Argument Relation Extraction

### 3.1 Problem Formulation
Given an ordered pair of argument units $(u_A, u_B)$, determine the directed relationship pointing from source $u_A$ to target $u_B$:
$$\mathcal{Y}_{\text{rel}} = \{\text{SUPPORTS}, \text{ATTACKS}, \text{RESPONDS_TO}, \text{NO_RELATION}\}$$

### 3.2 Mitigation of $O(n^2)$ Combinatorial Explosion
In a debate with $n = 100$ argument units, an exhaustive pairwise comparison yields $n(n - 1) = 9,900$ pairs, the vast majority of which represent `NO_RELATION`. Evaluating all pairs with a transformer cross-encoder is computationally prohibitive and amplifies false-positive edge predictions.

ARGUMAP prevents this explosion using a **4-stage heuristic pruning filter**:

```
Total Pairs: n*(n-1)
       │
       ▼
[Filter 1: Directional Chronology & Temporal Window]
  • Prune pairs where target u_B occurs significantly after source u_A.
  • In debate logic, an argument typically addresses earlier arguments.
  • Set turn distance window: Turn(u_A) - Turn(u_B) <= W (default W = 4 turns).
       │
       ▼
[Filter 2: Structural & Component Role Pruning]
  • Self-loops are strictly prohibited (u_A != u_B).
  • Units labeled OTHER are stripped from relation evaluation.
  • Evidence units can only be sources (supporting premises/claims), never targets.
       │
       ▼
[Filter 3: Speaker Dynamics Heuristics]
  • If Speaker(u_A) == Speaker(u_B): Prune ATTACKS candidates (speakers rarely attack themselves).
  • If Speaker(u_A) != Speaker(u_B): Focus candidate evaluation on ATTACKS and RESPONDS_TO.
       │
       ▼
[Filter 4: Semantic Similarity Thresholding]
  • Compute fast cosine similarity using sentence embeddings.
  • If cos_sim(u_A, u_B) < threshold_tau and distance > 1 turn, prune to NO_RELATION.
       │
       ▼
Viable Candidate Pairs (~5-10% of total) -> Evaluated by Task 2 Classifier
```

### 3.3 Relation Classifier Architecture
* **Cross-Encoder Formulation:**
  * Input string: `[CLS] Unit A: <text_A> [SEP] Unit B: <text_B> [SEP] Context: Speaker A vs Speaker B [SEP]`
  * The cross-encoder jointly computes full cross-attention between token representations of both propositions.
* **Output:** Softmax distribution over 4 classes:
  * `SUPPORTS`
  * `ATTACKS`
  * `RESPONDS_TO`
  * `NO_RELATION`
* **Handling Negative Domination:**
  * During training, negative pairs (`NO_RELATION`) are randomly downsampled to maintain a manageable ratio (e.g., $3:1$ negative-to-positive ratio).
  * During inference, only pairs classified with $\ge 0.50$ confidence into `SUPPORTS`, `ATTACKS`, or `RESPONDS_TO` are converted into graph edges.

### 3.4 Evaluation Metrics (Task 2)
* **Primary Metric:** **Macro F1 Score computed exclusively over active relations** (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`). 
  * *Note:* Including `NO_RELATION` in overall accuracy artfully inflates metrics due to trivial negative classification.
* **Secondary Metrics:**
  * Precision and Recall per relation type.
  * Directed edge accuracy (verifying source and target directions are not inverted).

---

## 4. Reproducibility & Model Versioning

1. **Seed Anchoring:** All training pipelines, feature extractors, and split algorithms must fix global random seeds (`seed = 42`).
2. **Artifact Versioning:** Checkpoints saved to `models/` must include:
   * Serialized model weights (`.pt` or `.bin`).
   * Tokenizer vocabulary and configuration (`tokenizer.json`, `config.json`).
   * Metadata descriptor (`model_card.json`) listing base architecture, hyperparameters, commit hash, and validation metrics.
