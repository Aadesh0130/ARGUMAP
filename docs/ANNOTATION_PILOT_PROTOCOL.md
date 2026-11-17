# ARGUMAP — Human Annotation Pilot Protocol & Candidate-Pair Specification

* **Document Version:** 1.0.0
* **Target Audience:** Human Annotators, Computational Linguists, Adjudicators
* **Scope:** Annotation Protocol and Bounded Pilot Package for the verified 2023 UK Parliament Hansard AI Debate (`hansard_lords_ai_debate_2023.txt`).
* **Authoritative References:** [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md), [ANNOTATION_GUIDELINES.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_GUIDELINES.md), [ANNOTATION_WORKFLOW.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_WORKFLOW.md), [RELATION_WINDOW_CALIBRATION.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/RELATION_WINDOW_CALIBRATION.md)

---

## 1. Audit of Existing Annotation Specifications

A thorough cross-specification audit was conducted across `ANNOTATION_GUIDELINES.md`, `ANNOTATION_WORKFLOW.md`, `NLP_PREPROCESSING.md`, `annotation.schema.json`, `annotation_schema.json`, `hansard_lords_ai_debate_2023.json`, and template files.

### 1.1 Field Name & Schema Alignment
1. **Document-Level Fields:**
   - Both schemas (`annotation.schema.json` and `annotation_schema.json`) require: `debate_id`, `title`, `source_corpus`, `source_license`, `guideline_version`, `units`, and `relations`.
   - The pilot package adheres strictly to these fields and includes optional lifecycle metadata: `annotator_id`, `status` (`UNANNOTATED_PILOT_PACKAGE`), `attribution`, `candidate_relation_policy`, `pilot_selection`, and `instructions`.
   - The schemas have been formally updated to declare these optional document-level metadata fields, preventing schema validation failures under `additionalProperties: false`.

2. **Unit-Level Fields:**
   - In `data/processed/hansard_lords_ai_debate_2023.json`, text is stored in `"text"`.
   - In `annotation.schema.json`, `annotation_schema.json`, and annotation packages, the field is named `"unit_text"`. The package generation script maps `text` $\rightarrow$ `unit_text` preserving exact string content.
   - Slicing offsets (`char_start`, `char_end`) are strictly 0-indexed relative to the parent turn speech text, preserving the invariant:
     $$\text{turn.text}[\text{char\_start}:\text{char\_end}] == \text{unit\_text}$$

3. **Relation-Level Fields & Overrides:**
   - Relation items require: `source_unit_id`, `target_unit_id`, `relation_label`, `same_speaker`, `cross_turn`, `turn_distance`, `annotator_id`, `confidence`, `guideline_version`.
   - To support documented out-of-window overrides without breaking schema conformance, an optional boolean field `is_override` has been formally incorporated into the schemas.

4. **Lifecycle State Separation:**
   - An **unannotated package** has `component_label: null`, `confidence: null`, and candidate `relation_label: null`.
   - A **completed package** requires explicit non-null labels from `FROZEN_COMPONENT_LABELS` and `FROZEN_RELATION_LABELS` with numeric confidence scores $[0.0, 1.0]$.
   - `validate_annotations.py` enforces this distinction via `allow_unannotated=False` (default, requiring full annotations) versus `allow_unannotated=True` (for verifying structural validity of unannotated packages).
   - `check_annotation_completeness()` deterministically verifies that zero units or candidate relations remain unlabeled before adjudication.

---

## 2. Relation Candidate-Pair Universe Policy

Exhaustive pairwise pairing of argument units scales quadratically ($N(N-1)$), creating class imbalance and cognitive fatigue. Following human review and approval, the pilot candidate-pair universe is governed by **Approved Option B (Full Bidirectional across Eligible Turns)**, while full-debate rollout adopts a bounded intra-turn horizon $w=10$.

### 2.1 Formal Eligibility Rules for Pilot Package
For any ordered pair of units $(u_{\text{source}}, u_{\text{target}})$ across the pilot's eligible turns:
1. **Self-Pair Exclusion:**
   $$u_{\text{source}} \neq u_{\text{target}}$$
   Self-loops are strictly prohibited and excluded from the candidate pool ($36$ self-pairs excluded).
2. **Turn Distance Calculation:**
   $$\Delta Turn = TurnIndex(u_{\text{source}}) - TurnIndex(u_{\text{target}}), \quad TurnDist = |\Delta Turn|$$
3. **Full Bidirectional Cross-Turn & Intra-Turn Generation:**
   - Both forward and backward pairs are generated for every pair of distinct units across the pilot's turns: $(u_i \rightarrow u_j)$ and $(u_j \rightarrow u_i)$.
   - Total generated candidates: $36 \times 35 = 1,260$ directed candidate pairs (288 intra-turn pairs + 972 cross-turn pairs).
4. **Out-of-Window Links ($TurnDist > 3$):**
   - Candidate pairs connecting the ministerial summing-up (Turn 28) to earlier backbench interventions (Turns 1, 2, 3) have $TurnDist > 3$.
   - These are pre-tagged with `"is_override": true` and an explicit note (`"[PILOT_DIVERSITY_OVERRIDE] Cross-debate ministerial response candidate (Turn 28)"`).

### 2.2 Scale-Up Policy (Full Debate Rollout)
- **Intra-turn horizon ($w=10$):** For long parliamentary speeches during full dataset rollout, intra-turn candidate generation is bounded at proposition distance $w=10$, achieving a 57.7% intra-turn workload reduction while preserving >97% of empirical links.
- Long-distance references ($w > 10$ or $TurnDist > 3$) remain capturable via explicit annotator overrides (`is_override: true` with explanatory note).

### 2.3 Explicit 4-Class Candidate Field & Negative Interpretation Rule
- Every candidate pair in the candidate universe is explicitly materialized in the annotation package with `relation_label: null`.
- Human annotators must review every candidate pair and assign one of the 4 frozen labels:
  * `SUPPORTS`
  * `ATTACKS`
  * `RESPONDS_TO`
  * `NO_RELATION`
- **Negative Interpretation Rule:** An omitted pair is **NEVER** interpreted as `NO_RELATION`. Unannotated pairs are strictly treated as incomplete data.

---

## 3. Bounded Pilot Dataset Specification

### 3.1 Selection Methodology & Grounding
To maximize argumentative and dialectical diversity, a bounded subset of **36 argument units** was deterministically extracted across **4 key debate turns** (9 units per turn) from the processed 2023 UK House of Lords AI debate transcript (`hansard_lords_ai_debate_2023.json`):

* **Turn 1 (`turn_001`, Lord Ravensdale, `turn_index: 0`):**
  - **Unit Range:** `u_0010` through `u_0018` (9 units).
  - **Speaker:** `spk_001` (Debater, Neutral).
  - **Rhetorical Role:** Core technical argument on frontier AI risk, catastrophic risks, sovereign compute, and international safety governance.
* **Turn 2 (`turn_002`, Baroness Stowell of Beeston, `turn_index: 1`):**
  - **Unit Range:** `u_0064` through `u_0072` (9 units).
  - **Speaker:** `spk_002` (Debater, Neutral).
  - **Rhetorical Role:** Open-source code distribution, legal liability, corporate concentration, and separating speculative hype from present-day harms.
* **Turn 3 (`turn_003`, Lord Browne of Ladyton, `turn_index: 2`):**
  - **Unit Range:** `u_0089` through `u_0097` (9 units).
  - **Speaker:** `spk_003` (Debater, Neutral).
  - **Rhetorical Role:** Military AI adoption, accountability of the Foundation Model Taskforce, and regulation vs. innovation policy tensions.
* **Turn 28 (`turn_028`, Viscount Camrose - Parliamentary Under-Secretary of State, `turn_index: 27`):**
  - **Unit Range:** `u_0902` through `u_0910` (9 units).
  - **Speaker:** `spk_028` (Debater, Neutral).
  - **Rhetorical Role:** Official Government response directly addressing Lord Ravensdale (compute funding), Baroness Stowell (Select Committee inquiry), and Lord Browne (Taskforce reporting lines).

### 3.2 Candidate-Pair Universe for the Pilot Subset
With 36 units partitioned into 9 units per turn across 4 turns:
* **Intra-Turn Candidates:**
  - $4 \times (9 \times 8) = \mathbf{288\text{ pairs}}$
* **Cross-Turn Candidates:**
  - $6 \times (9 \times 9 \times 2) = \mathbf{972\text{ pairs}}$
* **Total Candidate Pairs to Label:** **1,260 pairs** ($36 \times 35$).
* **Self-Pairs Prohibited:** 36 pairs excluded.

---

## 4. Double-Blind Pilot Packages

Two independent, unannotated packages are generated:
* [data/annotations/pilot/hansard_2023_pilot_annotator_A.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/annotations/pilot/hansard_2023_pilot_annotator_A.json)
* [data/annotations/pilot/hansard_2023_pilot_annotator_B.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/annotations/pilot/hansard_2023_pilot_annotator_B.json)

### 4.1 Annotator Instructions
1. **Independent Work:** Annotator A and Annotator B must complete their packages in strict isolation without communicating or sharing decisions.
2. **Component Labeling:** For each of the 36 units, assign exactly one `component_label` from the 6 frozen classes (`CLAIM`, `PREMISE`, `EVIDENCE`, `COUNTERARGUMENT`, `REBUTTAL`, `OTHER`) and a confidence score $[0.0, 1.0]$.
3. **Relation Labeling:** For each of the 1,260 candidate pairs, assign exactly one `relation_label` from the 4 frozen classes (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`, `NO_RELATION`) and a confidence score $[0.0, 1.0]$.
4. **Ambiguity Logging & Adjudication Requests:**
   - If a unit is ambiguous between two categories (e.g., `CLAIM` vs `PREMISE` per Guideline §5.1, or `ATTACKS` vs `RESPONDS_TO` per Guideline §5.5), choose the best-fitting label according to the tie-breaking rules.
   - Record the alternative label and rationale in the `"note"` field prefixed with `"[AMBIGUITY]"`.
   - All `[AMBIGUITY]` notes will be compiled automatically for the formal adjudication session.

---

## 5. Validation and Gatekeeper Enforcement

1. **Structural Validation:** Verified via `scripts/dataset/validate_annotations.py` (`allow_unannotated=True`). Zero syntactic, entity, or offset errors.
2. **Completeness Enforcement:** Verified via `check_annotation_completeness()`. Packages are flagged as unannotated (36 units + 1,260 relations unlabeled = 1,296 unlabeled items) until full human completion.
3. **Model Training Gatekeeper:** Verified via `ml.data.dataset_loader:check_gold_dataset_readiness()`. Unannotated packages and pilot files are strictly rejected as gold data. Model training remains locked.
