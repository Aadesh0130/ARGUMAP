# ARGUMAP Machine Learning Package (`ml/`)

This directory contains the machine learning infrastructure, model architectures, dataset loading pipelines, and evaluation routines for **Task 1: Argument Component Classification**.

---

## 1. Directory Structure

```text
ml/
├── __init__.py                # Package-level exports
├── config.py                 # Configuration dataclasses (TF-IDF, Transformer, Splits, Experiments)
├── data/
│   ├── __init__.py
│   ├── dataset_loader.py     # ARGUMAP annotation format parser & gold readiness validator
│   ├── dataset_splitter.py   # Debate-level 70/15/15 deterministic non-leaking splitter
│   └── label_encoder.py      # Frozen 6-class component taxonomy & strict validator
├── preprocessing/
│   ├── __init__.py
│   └── text_features.py      # Configurable TF-IDF feature extractor
├── baseline/
│   ├── __init__.py
│   ├── tfidf_classifier.py   # TF-IDF + Logistic Regression baseline classifier
│   └── train_baseline.py     # Baseline training orchestration with data-integrity halts
├── transformer/
│   ├── __init__.py
│   ├── classifier.py         # PyTorch / Hugging Face sequence classifier wrapper
│   ├── dataset.py            # PyTorch Dataset supporting single-unit & context-aware input
│   ├── train.py              # Transformer fine-tuning loop with class weighting
│   └── evaluate.py           # Evaluation pipeline over test partitions
└── evaluation/
    ├── __init__.py
    ├── metrics.py            # Macro F1, weighted F1, per-class metrics, confusion matrix
    └── reports.py            # Human-readable distribution and evaluation report formatters
```

---

## 2. Frozen Taxonomy

The component classifier classifies each discrete discourse unit into exactly one of six frozen classes:

1. `CLAIM`
2. `PREMISE`
3. `EVIDENCE`
4. `COUNTERARGUMENT`
5. `REBUTTAL`
6. `OTHER`

Label validation is strict: unknown or modified labels fail loudly with `ValueError`.

---

## 3. Data Integrity & Readiness

* **Production Gold Annotation Status:** Currently **PENDING** annotation collection.
* **Pilot Annotation Safeguard:** The files under `data/annotations/pilot/` are strictly demonstration fixtures and are rejected by default from training pipelines.
* If training is initiated without valid gold data, the system reports:
  ```text
  Training status: BLOCKED
  Reason: ARGUMAP gold annotation dataset unavailable
  ```
  No fake benchmarks, synthetic samples, or fabricated accuracies are reported.

---

## 4. Debate-Level Splitting

Units are partitioned grouped strictly by `debate_id` (70% train, 15% validation, 15% test) using a fixed random seed (`seed = 42`). This guarantees **zero debate and topic leakage** between training and test sets.

---

## 5. Model Architecture Overview

### Baseline: TF-IDF + Logistic Regression
* **Role:** Reproducible, computationally lightweight benchmark.
* **Features:** Sublinear word n-grams (1, 2), max 10,000 features, min document frequency 2.
* **Classifier:** Multinomial Logistic Regression with balanced class weights (`class_weight='balanced'`).

### Primary Model: Transformer Encoder (RoBERTa / DeBERTa)
* **Role:** State-of-the-art contextual argument classifier.
* **Base Encoder:** `roberta-base` (configurable to `microsoft/deberta-v3-base`).
* **Loss Function:** CrossEntropyLoss with inverse frequency class-weight multipliers to mitigate class imbalance.
* **Context Preparation:** `ArgumentUnitDataset` includes slots for `previous_unit`, `current_unit`, `next_unit`, and `speaker` for future context-aware classification iterations.

---

## 6. CLI Commands

```powershell
# Prepare dataset and report class distribution
python scripts/ml/prepare_component_dataset.py

# Train classical baseline
python scripts/ml/train_baseline.py --annotations-dir data/annotations --output-dir models/baseline_tfidf

# Fine-tune Transformer classifier
python scripts/ml/train_transformer.py --model-name roberta-base --epochs 3 --batch-size 16

# Evaluate saved model
python scripts/ml/evaluate_component_classifier.py --model-dir models/baseline_tfidf --model-type baseline
```
