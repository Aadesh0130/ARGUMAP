# ARGUMAP — Dataset Partitioning & Split Strategy

This document defines the strict partitioning strategy for creating training, validation, and evaluation splits in **ARGUMAP**.

---

## 1. Split Ratios

The standard dataset partition follows a **70 / 15 / 15** distribution:

* **Train Set (`train.jsonl`):** 70% of total debates. Used for fitting baseline feature extractors and supervised neural weights.
* **Validation Set (`val.jsonl`):** 15% of total debates. Used exclusively for hyperparameter tuning, learning rate scheduling, threshold calibration, and early stopping.
* **Test Set (`test.jsonl`):** 15% of total debates. Held-out benchmark evaluated once to report final generalization metrics.

---

## 2. Prime Rule: Debate-Level Grouped Splitting

> **CRITICAL PREVENTIVE RULE:**  
> **Splitting must ALWAYS occur at the debate/document level, NEVER randomly at the individual proposition, turn, or relation-pair level.**

### Why Random Splitting is Prohibited:
1. **Contextual & Topic Leakage:** A single debate focuses on a specific contentious resolution (e.g., *"Universal Basic Income"* or *"Carbon Taxation"*). If propositions from the same debate appear in both Train and Test splits, classifiers will memorize topic-specific vocabulary and speaker idiolects rather than learning generalizable argumentative discourse logic.
2. **Relational Graph Corruption:** A relation edge connects two propositions from the same dialogue ($u_{\text{source}} \rightarrow u_{\text{target}}$). If $u_{\text{source}}$ is assigned to Train while $u_{\text{target}}$ is assigned to Test, the relational edge is bisected, causing catastrophic graph corruption.
3. **Overstated Generalization:** Random proposition splitting yields artificially inflated F1 scores (+15–25% accuracy inflation) that completely collapse when tested on unseen real-world debates.

---

## 3. Stratification & Split Criteria

When creating the 70/15/15 partitions:
1. **Group Key:** `debate_id` (all turns, units, and relations of a debate must stay grouped together).
2. **Stratification Variables:**
   * Topic domain (e.g., healthcare, education, environmental policy, foreign relations).
   * Total unit count (ensuring balanced length and density distribution across splits).
   * Speaker format (2-person podium debate vs. multi-party panel discussion).
3. **Deterministic Random Seed:** Every split generation script must explicitly fix `seed = 42`.
4. **Split Manifest:** Every generated partition will be accompanied by `data/splits/split_manifest.json`, documenting the exact debate IDs in each fold, class balance metrics, and cryptographic hashes (SHA-256) of each split file.

---

## 4. Planned Out-of-Source (OOS) Test Set

In later evaluation phases, an additional **Out-of-Source (OOS) Test Set** will be introduced:
* Transcripts sourced from completely distinct debate formats (e.g., collegiate parliamentary debates or municipal council deliberations) that were not present in any training corpus.
* This tests the true domain-adaptation capacity and robustness of ARGUMAP when confronted with unfamiliar acoustics, debate tempos, and rhetorical conventions.
