# ARGUMAP — Argument Component Classification Specification & Architecture

* **Document Version:** 1.0.0
* **Status:** Implemented ML Framework (Training Blocked: Pending Gold Data)
* **Target Task:** Task 1 — Argument Component Classification

---

## 1. Problem Definition

Argument Component Classification is the first supervised machine learning stage in the ARGUMAP pipeline. Given a discourse proposition or segmented argument unit $u_i$ originating from a debate speech turn, the task is to predict its rhetorical and functional argument category:

$$\hat{y}_i = f_{\theta}(u_i) \in \mathcal{Y}_{\text{comp}}$$

where $\mathcal{Y}_{\text{comp}}$ is the frozen six-class taxonomy.

---

## 2. Frozen Component Taxonomy

ARGUMAP strictly defines six mutually exclusive argument component labels:

| Label | Definition | Linguistic / Rhetorical Role |
| :--- | :--- | :--- |
| `CLAIM` | A central contentious thesis, proposition, or concluding assertion. | Main stance anchor; requires justification or support. |
| `PREMISE` | A reason, rationale, or explanatory proposition offered in support or defense. | Logical stepping stone linking evidence or ideas to claims. |
| `EVIDENCE` | An empirical datum, statistical citation, historical precedent, or factual quotation. | Verifiable factual support backing a premise or claim. |
| `COUNTERARGUMENT` | An argument, claim, or premise presented against an opposing perspective. | Direct rhetorical opposition addressing the opposing case. |
| `REBUTTAL` | A direct answer, refutation, or mitigation targeting a counterargument. | Restores defensive validity by undermining an attack. |
| `OTHER` | Discourse scaffolding, procedural framing, pleasantries, or non-argumentative text. | Filtered out of downstream argument reasoning graphs. |

> [!IMPORTANT]
> The taxonomy is frozen for V1. Models must classify every segmented unit into exactly one of these six classes. No label modification, merging, or omission is permitted.

---

## 3. Dataset Requirements & Scientific Integrity

### 3.1 Current Status: No Production Gold Dataset
* As documented in Step 5 and `data/README.md`, ARGUMAP does not currently possess an approved, annotated production gold dataset.
* The files located under `data/annotations/pilot/` are purely illustrative demonstration artifacts and **must not be used for model training**.
* External corpora (e.g. US2016, AAE) use incompatible native annotation schemes; automatically mapping external labels into ARGUMAP labels without human adjudication is explicitly prohibited.

### 3.2 Scientific Honesty Policy
* If training scripts (`train_baseline.py`, `train_transformer.py`) are invoked without validated production gold data in `data/annotations/`, the pipeline immediately halts with:
  ```text
  Training status: BLOCKED
  Reason: ARGUMAP gold annotation dataset unavailable
  ```
* No synthetic benchmark figures or fabricated F1 scores may be reported.

---

## 4. Train, Validation, and Test Splitting Strategy

### 4.1 Debate-Level Grouped Splitting
* **Split Ratios:** 70% Train, 15% Validation, 15% Test.
* **Grouping Key:** All units from any single debate transcript are kept strictly within one partition.
* **Leakage Prevention:** Randomly splitting units across sentences or speech turns leaks topic semantics, speaker idioms, and context. Partitioning by debate ID eliminates this leakage.
* **Deterministic Reproducibility:** Shuffling of debate IDs is controlled via a fixed seed (`seed = 42`).

---

## 5. Model Architectures

ARGUMAP implements a dual-model framework:

```text
ARGUMAP Preprocessing
        ↓
Annotated Argument Units
        ↓
Dataset Loader
        ↓
Debate-Level Split
        ↓
       ┌──────────────────────┐
       │                      │
       ▼                      ▼
TF-IDF + Logistic       Transformer Encoder
Regression              (RoBERTa/DeBERTa)
       │                      │
       ▼                      ▼
Baseline Metrics        Main Model Metrics
```

### 5.1 Baseline: TF-IDF + Logistic Regression
* **Purpose:** Provides a deterministic, computationally lightweight, transparent baseline benchmark.
* **Feature Extraction:**
  * Word n-grams: Unigrams and bigrams (`ngram_range=(1, 2)`).
  * Sublinear term frequency scaling (`sublinear_tf=True`).
  * Vocabulary constraints: `min_df=2`, `max_features=10000`.
* **Classifier:** Multinomial Logistic Regression (`scikit-learn`).
  * Class weighting: `class_weight='balanced'`.
  * Solver: `lbfgs` with `max_iter=1000`.
* **Why Retained:** Guarantees a reproducible floor against which transformer gains are measured.

### 5.2 Primary Model: Transformer Encoder (RoBERTa / DeBERTa)
* **Purpose:** Core production model capturing nuanced rhetorical semantics, negation, epistemic modality, and argumentative connectives.
* **Base Encoders:**
  * Initial default: `roberta-base`.
  * Configurable alternatives: `microsoft/deberta-v3-base`, `google/electra-base-discriminator`.
* **Classification Head:** Linear projection layer mapping `d_model` to $\mathbb{R}^6$.
* **Hardware Detection:** Dynamically detects and leverages `CUDA` if an Nvidia GPU is available; falls back smoothly to `CPU`.
* **Why Primary:** Deep bidirectional self-attention captures long-range syntactic subtleties and discursive markers that bag-of-words completely overlooks.

---

## 6. Class Imbalance Mitigation

Minority classes (e.g. `REBUTTAL`, `EVIDENCE`) frequently exhibit lower frequency than `PREMISE` or `CLAIM`. ARGUMAP mitigates this imbalance systematically:
1. **Baseline Model:** Employs scikit-learn's `class_weight='balanced'` to inversely weight class contributions in the cross-entropy loss.
2. **Transformer Model:** Computes normalized balanced class weights:
   $$w_c = \frac{N}{K \cdot N_c}$$
   and supplies them to PyTorch's `nn.CrossEntropyLoss(weight=w)`.
3. **No Synthetic Oversampling:** No synthetic training examples or SMOTE variations are applied, ensuring scientific reproducibility.

---

## 7. Context-Aware Transformer Interface Preparation

While initial model training classifies individual propositions, the dataset interface (`ArgumentUnitDataset` and `ArgumentUnitSample`) includes explicit slots for debate context:
* `previous_unit`: Preceding discourse proposition in the debate.
* `current_unit`: The proposition being classified.
* `next_unit`: Subsequent proposition.
* `speaker`: Speaker identifier.
* `turn_index`: Sequential turn index.

This enables future iterations to incorporate cross-turn context without restructuring the data loader.

---

## 8. Evaluation Protocol & Metrics

### 8.1 Primary Metric: Macro F1
* Macro-averaged F1 score treats all six classes equally, preventing dominant classes from masking catastrophic failure on minority classes (`REBUTTAL`, `COUNTERARGUMENT`).

### 8.2 Secondary Metrics
* Overall Accuracy.
* Weighted F1 score.
* Per-class Precision, Recall, F1, and Support.
* 6x6 Confusion Matrix strictly formatted in frozen order:
  `CLAIM`, `PREMISE`, `EVIDENCE`, `COUNTERARGUMENT`, `REBUTTAL`, `OTHER`.

### 8.3 Test Set Integrity
* The test set remains untouched during training and hyperparameter search.
* Validation Macro F1 is used for early stopping and checkpoint selection.

---

## 9. Experiment Tracking & Model Artifacts

All training sessions record an `experiment_record.json` documenting:
* `experiment_id`
* `model_name`
* `dataset_version`
* `dataset_split_seed`
* `hyperparameters`
* `training_date`
* `device` (CUDA/CPU)
* Sample counts (`train`, `val`, `test`)
* Validation / Test metrics
* `status` (`COMPLETED` or `BLOCKED`)

Trained weights (`*.bin`, `*.pt`, `*.safetensors`, `*.joblib`) are stored in `models/` and excluded from git version control via `.gitignore`.

---

## 10. LLM Boundary

The trained component classifier must **never** be replaced with an LLM call or prompt. ARGUMAP preserves strict architectural boundaries:
* **Preprocessing & Classification:** Supervised, reproducible local ML models.
* **LLM Role (Future Phases):** High-level natural language explanation of graph topology and strategic reasoning insights—never token or unit classification.
