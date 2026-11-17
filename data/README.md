# ARGUMAP — Dataset Strategy & Data Directory Guide

This document establishes the official dataset acquisition, annotation, and governance strategy for **ARGUMAP**.

---

## 1. Directory Structure & Storage Policy

```text
data/
├── raw/                         # Immutable external transcripts and source downloads (untracked in git)
├── processed/                   # Intermediate normalized representations (untracked in git)
├── annotations/                 # Ground truth annotation schemas and validated gold records
│   ├── pilot/                   # Pilot trial records (clearly labeled demo/pilot)
│   ├── annotation_schema.json   # Machine-readable specification of ARGUMAP annotation format
│   └── annotation.schema.json   # Draft-07 JSON Schema validation specification
├── splits/                      # Deterministic debate-level train/val/test partitions (untracked in git)
├── dataset_manifest.json        # Central provenance registry for all candidate datasets
└── README.md                    # This document
```

### Storage & Version Control Rules
1. **No Large Data in Version Control:** Raw downloads, heavy text splits, and embeddings must never be committed to Git. Only schemas, `.gitkeep` files, documentation, and small sample test fixtures are tracked.
2. **Immutability of `data/raw/`:** Files downloaded into `data/raw/` are treated as read-only upstream artifacts. Any cleaning, tokenization, or proposition segmentation occurs in scripts that output to `data/processed/`.
3. **Scientific Integrity:** No synthetic or fabricated dataset records are allowed. All data must trace back to verifiable transcripts and documented annotation schemes.

---

## 2. Approved Dataset Strategy

ARGUMAP targets **turn-based, multi-party spoken debate discourse**. The dataset strategy distinguishes between **Primary Custom-Data Sources** and **Auxiliary Benchmark Sources**.

### 2.1 Primary Custom-Data Sources
These corpora provide real-world political and academic debate transcripts from which the **ARGUMAP Gold Standard Dataset** will be curated and annotated:

| Corpus ID | Name & Domain | Role in ARGUMAP | Dialogue Properties |
| :--- | :--- | :--- | :--- |
| **`qt30`** | BBC Question Time (30 episodes) | Primary transcript source for multi-party deliberation | Turn-taking panel debate with host, politicians, and public |
| **`US2016`** | US 2016 Presidential Debates | Primary transcript source for head-to-head rebuttal dynamics | Two-candidate podium debate with direct cross-turn attacks |
| **`elecdeb60to20`** | US Presidential Debates (1960–2020) | Scaled transcript repository for extensive coverage | 60 years of multi-turn televised political debates |

> **Crucial Rule:** These datasets provide high-quality **dialogue transcripts**. Although some contain external annotations (e.g., AIF/IAT graphs), their native schemas **do not** match the ARGUMAP V1 taxonomy. They will be used as raw text inputs for human annotation under the ARGUMAP annotation protocol.

### 2.2 Auxiliary Sources
These established argument mining corpora serve as secondary linguistic references, vocabulary guides, or baseline segmentation checks:

* **`aae` (Argument Annotated Essays v2):** Monologic student essays (Stab & Gurevych, 2017). Useful for initial proposition segmentation checks and premise/claim baseline algorithms, but lacks conversational dialogue and cross-speaker rebuttals.
* **`m-arg` (Multimodal Argumentation):** Competitive debate recordings and transcripts (Mancini et al., 2022). Useful for analyzing turn length and debate argument density.
* **`ibm-evidence` (IBM Debater Evidence Detection):** Sentence-level evidence detection (Rinott et al., 2015). Informs our criteria for distinguishing factual/empirical `EVIDENCE` from deductive `PREMISE`.
* **`abstrct` (Clinical Trial Abstracts):** Scientific literature argument mining (Mayer et al., 2020). Provides reference for distinguishing empirical findings from overarching claims.
* **`web-discourse` (Web Discourse Corpus):** Forum comments and blogs (Habernal & Gurevych, 2016). Informs how informal user rebuttals operate.
* **`microtexts` (Arg-Microtexts):** Short controlled texts (Peldszus & Stede, 2015). Used for studying formal tree and DAG structural properties.

---

## 3. Strict Rule Against Automatic Relabeling

> **CRITICAL SCIENTIFIC DIRECTIVE:**  
> **External labels must NEVER be silently or automatically converted into ARGUMAP V1 labels.**

None of the auxiliary or external corpora natively use the frozen ARGUMAP V1 6-component / 4-relation scheme:
* For example, AAE's `MajorClaim` and `Claim` cannot be naively equated with ARGUMAP's `CLAIM`, because in a debate, a statement may be a constructive `CLAIM`, a `COUNTERARGUMENT`, or a `REBUTTAL` depending entirely on who spoke it and what turn it addresses.
* In AIFdb datasets (`qt30`, `US2016`), nodes are labeled with Inference Anchoring Theory categories (`Assertion`, `Default Inference`, `Default Conflict`). An `Assertion` might function as a `CLAIM`, `PREMISE`, or `COUNTERARGUMENT` depending on the context.
* Converting these labels automatically creates noisy, corrupted ground truth that invalidates scientific evaluation.
* Any future mapping must undergo formal mapping review, agreement testing, and explicit documentation.

---

## 4. Licensing & Provenance Compliance

1. **License Verification Requirement:** All datasets in `data/dataset_manifest.json` have their license recorded. If the upstream repository lacks an explicit permissive license, the dataset is marked with:
   ```json
   "license_status": "UNVERIFIED"
   ```
2. **No Speculation:** Unverified licenses will not be guessed. Before any data derived from such corpora is published or redistributed, legal licensing must be confirmed.
3. **Traceability:** Every processed unit must retain complete provenance (`source_corpus`, `source_document_id`, `source_license`, `source_url`).
