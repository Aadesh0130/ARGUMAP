# ARGUMAP — Relation Candidate-Pair Window Calibration Report

* **Document Version:** 1.0.0
* **Status:** Provisional Calibration Report (Phase 1 Annotation Pilot)
* **Authoritative Reference:** [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md) §6–7, [ANNOTATION_WORKFLOW.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_WORKFLOW.md) §4
* **Analysis Script:** [scripts/annotation/calibrate_relation_window.py](file:///c:/Users/hii/Downloads/ARGUMAP/scripts/annotation/calibrate_relation_window.py)
* **Verification Test Suite:** [tests/test_relation_window_calibration.py](file:///c:/Users/hii/Downloads/ARGUMAP/tests/test_relation_window_calibration.py)

---

## 1. Executive Summary

In argument mining on debate transcripts, determining inter-argument relations requires pairing discrete proposition units. Exhaustive pairwise evaluation of $N$ units scales quadratically as $N(N - 1)$. For a debate with 100 units, exhaustive evaluation demands reviewing 9,900 pairs, over 97% of which have no rhetorical link.

To prevent annotator cognitive overload and class imbalance degradation, `ANNOTATION_WORKFLOW.md` §4 specifies restricting candidates via a **Turn Distance Window ($k$)** and a **Directional Chronology filter**, with the exact value of $k$ to be empirically calibrated from pilot annotations.

This report analyzes the empirical link distances, directionality, and candidate space across all three pilot debates (`debate_001_hansard`, `debate_002_us2016`, `debate_003_kennedy_nixon_1960`) comprising 63 aligned units and 34 unique positive relation edges.

### Key Empirical Findings

1. **Strict Temporal Backward Arrow in Cross-Turn Debate:** In 100% of observed cross-turn relations, speakers address or challenge **earlier** turns ($Turn_{\text{source}} > Turn_{\text{target}}$). No cross-turn forward links exist ($Turn_{\text{source}} < Turn_{\text{target}} = 0$).
2. **Bidirectional Intra-Turn Reasoning:** Within the same turn ($Turn_{\text{source}} == Turn_{\text{target}}$), argument structure is not strictly linear: 13.0% (3 of 23 unique intra-turn links) represent forward-directed links where a foundational premise or evidence is stated *before* the claim or counterargument it substantiates.
3. **Turn Distance vs. Unit Distance:** A single speech turn contains an average of 3.8 argument units (range: 1 to 7). Unit-index distance is an invalid proxy for relation candidacy because long speech turns separate units at opposite ends of the same turn by up to 6 positions, while cross-turn links reach unit distances of 15 despite spanning only 5 turns.
4. **Link Distribution & 95th Percentile:**
   * Median turn distance: **0.0 turns** (67.6% of relations are intra-turn).
   * 90th percentile: **1.70 turns**.
   * 95th percentile: **3.00 turns** (captures 33 of 34 links, or 97.06% empirical recall).
   * Maximum observed distance: **5 turns** (a single long-range thesis response in Debate 001).
5. **Workload Reduction via Directional Filtering:**
   * At $k = 3$, directional candidate filtering ($Turn_{\text{source}} \ge Turn_{\text{target}}$) generates **670 candidate pairs** across the three debates (~223 pairs/debate) compared to **1,092 pairs** under bidirectional filtering (~364 pairs/debate), reducing annotator workload by **38.6%** with zero loss of captured positive links.
6. **Provisional Recommendation:** A provisional window of **$k = 3$ turns with directional filtering** is recommended for the expanded Phase 2 pilot. The window must **not** be frozen permanently because the pilot sample size is small and long-format debates may exhibit longer rhetorical horizons.

---

## 2. Representation of Debate Structure

The ARGUMAP schema structures debates across three primary hierarchical levels:

```
[Debate Transcript]
       │
       ├── Speech Turns (turn_id, turn_index: 0..T, speaker_id, speaker_side)
       │         │
       │         └── Argument Units (unit_id, char_start, char_end, component_label)
       │
       └── Relations (source_unit_id → target_unit_id, relation_label, same_speaker, cross_turn, turn_distance)
```

### 2.1 Argument Units and Dialogue Turns

* **Turn Index (`turn_index`):** A monotonically increasing zero-indexed integer indicating speaker transitions. In Debate 001 there are 7 turns (0–6); in Debate 002 there are 5 turns (0–4); in Debate 003 there are 3 turns (0–2).
* **Multiple Units Per Turn:** Debaters frequently present multi-sentence or multi-clause constructive arguments in a single turn:
  * Debate 001 (UK Hansard AI): 22 units across 7 turns (1 to 5 units per turn; mean = 3.1).
  * Debate 002 (US 2016 Trump-Clinton): 23 units across 5 turns (3 to 6 units per turn; mean = 4.6).
  * Debate 003 (Kennedy-Nixon 1960): 18 units across 3 turns (4 to 7 units per turn; mean = 6.0).
* **Unit Identifiers (`unit_id`):** Formatted as `u_001`, `u_002`, etc. While currently sequential within pilot files, unit IDs must be treated by all parsing logic as arbitrary categorical identifiers. **Unit IDs do not define chronological sequence.** True chronological order is strictly determined by `turn_index` and `char_start` (character offset within the turn).

### 2.2 Relation Endpoints and Semantics

Relations are directed edges $(u_{\text{source}} \rightarrow u_{\text{target}})$ where $u_{\text{source}}$ acts rhetorically upon $u_{\text{target}}$:
* **`SUPPORTS`:** $u_{\text{source}}$ provides deductive rationale or empirical backing for $u_{\text{target}}$.
* **`ATTACKS`:** $u_{\text{source}}$ directly attempts to falsify, contradict, or invalidate $u_{\text{target}}$.
* **`RESPONDS_TO`:** $u_{\text{source}}$ reframes, clarifies, or engages with $u_{\text{target}}$ without constituting a binary attack or support.
* **`NO_RELATION`:** Absence of direct argumentative link.

---

## 3. Empirical Link Distance & Directionality Analysis

### 3.1 Data Inventory

The Phase 1 pilot corpus was annotated independently by Annotator A and Annotator B:
* **Debate 001:** 22 units. Annotator A identified 12 relations; Annotator B identified 11 relations. 11 pairs are shared; 1 pair (`u_011 -> u_005`) was annotated only by A. Total unique pairs = 12.
* **Debate 002:** 23 units. Both annotators identified 15 relations across identical pairs. Total unique pairs = 15.
* **Debate 003:** 18 units. Both annotators identified 7 relations across identical pairs. Total unique pairs = 7.
* **Total Edges in Files:** 67 edges (A: 34, B: 33).
* **Total Unique Positive Pairs (Union):** **34 pairs**.
* **Total Shared Positive Pairs (Intersection):** **33 pairs** (97.1% pair overlap).

### 3.2 Annotator Label Disagreements on Shared Pairs

Of the 33 shared pairs, 30 pairs had identical relation labels (90.9% raw label agreement). Exactly 3 pairs exhibited label disagreement:

| Debate | Source $\rightarrow$ Target | Turn Distance | Unit Distance | Annotator A Label | Annotator B Label | Adjudication Context |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **001** | `u_018` $\rightarrow$ `u_012` | 1 | 6 | `ATTACKS` | `RESPONDS_TO` | Wollaston challenges Clark's historical innovation analogy. |
| **002** | `u_020` $\rightarrow$ `u_016` | 1 | 4 | `ATTACKS` | `RESPONDS_TO` | Clinton challenges Trump's corporate tax cut premise. |
| **003** | `u_018` $\rightarrow$ `u_011` | 1 | 7 | `RESPONDS_TO` | `ATTACKS` | Nixon engages with Kennedy's federal action claim. |

> **Diagnostic Insight:** 100% of annotator disagreements occurred between `ATTACKS` and `RESPONDS_TO` at turn distance 1, validating the tie-breaking rules introduced in Guideline v1.1.0 §5.5 (`ATTACKS` vs `RESPONDS_TO`).

### 3.3 Distribution of Observed Distances

#### Turn Distance Distribution (Unique Positive Pairs, $N = 34$)

| Turn Distance ($k$) | Count | Percentage | Cumulative Recall | Relation Types Observed |
| :---: | :---: | :---: | :---: | :--- |
| **0** | 23 | 67.65% | 67.65% | `SUPPORTS` (23) |
| **1** | 7 | 20.59% | 88.24% | `ATTACKS` (5), `RESPONDS_TO` (2) |
| **2** | 1 | 2.94% | 91.18% | `SUPPORTS` (1, same-speaker re-take) |
| **3** | 2 | 5.88% | 97.06% | `ATTACKS` (2) |
| **4** | 0 | 0.00% | 97.06% | None |
| **5** | 1 | 2.94% | 100.00% | `RESPONDS_TO` (1, opening thesis response) |
| **$\ge 6$** | 0 | 0.00% | 100.00% | None |

#### Summary Quantiles (Turn Distance)

$$\text{Min} = 0, \quad \text{Median} = 0.0, \quad \text{Mean} = 0.68, \quad \text{P90} = 1.70, \quad \text{P95} = 3.00, \quad \text{Max} = 5$$

#### Unit Sequence Distance Distribution ($N = 34$)

$$\text{Min} = 1, \quad \text{Median} = 2.0, \quad \text{Mean} = 3.38, \quad \text{P90} = 7.00, \quad \text{P95} = 7.35, \quad \text{Max} = 15$$

* 1 unit apart: 13 pairs (38.2%)
* 2 units apart: 8 pairs (23.5%)
* 3 units apart: 3 pairs (8.8%)
* 4 units apart: 2 pairs (5.9%)
* 5 units apart: 1 pair (2.9%)
* 6 units apart: 2 pairs (5.9%)
* 7 units apart: 3 pairs (8.8%)
* 8 units apart: 1 pair (2.9%)
* 15 units apart: 1 pair (2.9%)

### 3.4 Directionality and Temporal Flow

Analyzing the signed turn difference ($\Delta Turn = Turn_{\text{source}} - Turn_{\text{target}}$) and signed unit difference reveals a fundamental asymmetry between intra-turn and cross-turn argumentation:

1. **Cross-Turn Links ($\Delta Turn > 0$):**
   * Total cross-turn unique links: 11 pairs.
   * All 11 links (100%) have $Turn_{\text{source}} > Turn_{\text{target}}$.
   * Zero links (0%) have $Turn_{\text{source}} < Turn_{\text{target}}$.
   * **Linguistic Principle:** Spoken debate is strictly sequential. Speakers react to, refute, or build upon prior statements. They cannot attack future statements.
2. **Intra-Turn Links ($\Delta Turn = 0$):**
   * Total intra-turn unique links: 23 pairs.
   * **Backward Intra-Turn (20 pairs, 87.0%):** $Index_{\text{source}} > Index_{\text{target}}$. The speaker states an overarching claim, followed by subordinate supporting premises or evidence ($u_{\text{premise}} \rightarrow u_{\text{claim}}$).
   * **Forward Intra-Turn (3 pairs, 13.0%):** $Index_{\text{source}} < Index_{\text{target}}$. The speaker introduces empirical evidence or historical premises *first*, and then derives their conclusion:
     * *Debate 001:* `u_012` (historical premise) $\rightarrow$ `u_013` (conclusion claim).
     * *Debate 003:* `u_009` (premise) $\rightarrow$ `u_011` (claim).
     * *Debate 003:* `u_010` (evidence) $\rightarrow$ `u_011` (claim).
3. **Cross-Turn Same-Speaker Support:**
   * In Debate 002, `u_023` (turn 4, Donald Trump) supports `u_016` (turn 2, Donald Trump) across a turn distance of 2 ($\Delta Turn = 2$).
   * Between turns 2 and 4, Hillary Clinton spoke in turn 3. In turn 4, Trump retook the floor and supplied additional rationale for his earlier trade policy claim.
   * **Linguistic Principle:** Cross-turn links are not restricted to cross-speaker attacks; constructive debaters frequently reinforce their own prior claims when retaking the floor.

---

## 4. Candidate-Pair Space & Workload Simulation

To determine the impact of different candidate window definitions on annotation workload and class imbalance, simulations were executed across the combined pilot dataset (63 units across 3 debates; 34 ground-truth positive pairs; 1,274 total directed pairs).

### 4.1 Strategy A: Directional Turn Window ($Turn_{\text{source}} \ge Turn_{\text{target}}$)

Candidate pairs $(u_i, u_j)$ satisfy:
$$0 \le Turn(u_i) - Turn(u_j) \le k \quad \text{and} \quad u_i \neq u_j$$

| Window ($k$) | Total Candidate Pairs | Captured Positive Links | Empirical Recall (%) | Positive Class Density (%) | Imbalance Ratio (Neg:Pos) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$k = 0$** | 248 | 23 / 34 | 67.65% | 9.27% | 9.8 : 1 |
| **$k = 1$** | 482 | 30 / 34 | 88.24% | 6.22% | 15.1 : 1 |
| **$k = 2$** | 608 | 31 / 34 | 91.18% | 5.10% | 18.6 : 1 |
| **$k = 3$** | **670** | **33 / 34** | **97.06%** | **4.93%** | **19.3 : 1** |
| **$k = 4$** | 718 | 33 / 34 | 97.06% | 4.60% | 20.8 : 1 |
| **$k = 5$** | 749 | 34 / 34 | 100.00% | 4.54% | 21.0 : 1 |
| **$k = 6$** | 761 | 34 / 34 | 100.00% | 4.47% | 21.4 : 1 |
| **All ($k = \infty$)** | 761 | 34 / 34 | 100.00% | 4.47% | 21.4 : 1 |

### 4.2 Strategy B: Bidirectional Turn Window ($|Turn_{\text{source}} - Turn_{\text{target}}| \le k$)

Candidate pairs $(u_i, u_j)$ satisfy:
$$|Turn(u_i) - Turn(u_j)| \le k \quad \text{and} \quad u_i \neq u_j$$

| Window ($k$) | Total Candidate Pairs | Captured Positive Links | Empirical Recall (%) | Positive Class Density (%) | Imbalance Ratio (Neg:Pos) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$k = 0$** | 248 | 23 / 34 | 67.65% | 9.27% | 9.8 : 1 |
| **$k = 1$** | 716 | 30 / 34 | 88.24% | 4.19% | 22.9 : 1 |
| **$k = 2$** | 968 | 31 / 34 | 91.18% | 3.20% | 30.2 : 1 |
| **$k = 3$** | **1,092** | **33 / 34** | **97.06%** | **3.02%** | **32.1 : 1** |
| **$k = 4$** | 1,188 | 33 / 34 | 97.06% | 2.78% | 35.0 : 1 |
| **$k = 5$** | 1,250 | 34 / 34 | 100.00% | 2.72% | 35.8 : 1 |
| **$k = 6$** | 1,274 | 34 / 34 | 100.00% | 2.67% | 36.5 : 1 |
| **All ($k = \infty$)** | 1,274 | 34 / 34 | 100.00% | 2.67% | 36.5 : 1 |

### 4.3 Workload & Efficiency Comparison

```
Strategy Comparison at k = 3:
  Bidirectional:  ████████████████████████████████████████  1,092 candidates (3.02% density)
  Directional:    ████████████████████                    670 candidates (4.93% density)
  Savings:        38.6% candidate reduction with identical 97.06% link recall
```

* **Why Directional Filtering Succeeds:** Omitting cross-turn forward candidates ($Turn_{\text{source}} < Turn_{\text{target}}$) eliminates 422 impossible candidate pairs at $k = 3$ with zero false negatives.
* **Why Unit-Index Filtering Fails:** Restricting candidates by proposition index ($|Index_{\text{source}} - Index_{\text{target}}| \le w$) fails to model conversational turns:
  * Setting $w = 5$ misses 6 cross-turn links (79.4% recall) while requiring 544 candidates.
  * Capturing the long-range link at unit distance 15 requires $w = 15$, which generates 1,026 candidates—higher than the directional turn window while introducing arbitrary cutoffs inside long turns.

---

## 5. Methodological Limitations & Sample Size Caveat

> [!WARNING]
> **Pilot Sample Constraint:**  
> The Phase 1 pilot consists of 3 debates, 63 units, 15 turns, and 34 positive links.
> A 95th percentile of $k = 3$ on this dataset is a **descriptive empirical summary of these three specific transcripts**, not universal proof that 95% of all debate reasoning in general discourse occurs within 3 turns.

1. **Short Debate Horizon in Pilot:** The pilot transcripts represent short excerpts (3 to 7 turns each). In collegiate, parliamentary, or full presidential debates spanning 50–100 turns:
   * A closing speaker often delivers a comprehensive summary that attacks an opponent's opening thesis delivered 20 turns prior.
   * A strict window of $k = 3$ would truncate such macro-dialectic relations.
2. **Risk of Premature Freezing:** Freezing $k = 3$ at this stage would artificially bias the dataset toward local clash and blind the machine learning models to long-range structural reasoning.
3. **Preservation of Audit Independence:** The existing component agreement reports ($\kappa = 0.7035, 0.7825, 0.7000$) must remain intact and must not be recalculated with imputed negative pairs.

---

## 6. Provisional Window Recommendation

Based on empirical link capture, workload feasibility, and dialectical validity:

1. **Adopt a Provisional Candidate Window:**
   $$\mathbf{k_{\text{prov}} = 3 \text{ turns with Directional Filtering}}$$
   * Intra-turn ($Turn_s = Turn_t$): Evaluate all ordered pairs $(u_i, u_j)$ where $i \neq j$.
   * Cross-turn ($Turn_s > Turn_t$): Evaluate ordered pairs where $1 \le Turn(u_s) - Turn(u_t) \le 3$.
2. **Phase 2 Calibration Protocol:**
   * Apply $k_{\text{prov}} = 3$ to an expanded pilot of 10 diverse debate transcripts (collegiate debate, parliamentary proceedings, television panel deliberations).
   * Include an **"Out-of-Window Long-Range Link" override mechanism**: Annotators are permitted to manually record an argument link targeting an earlier turn beyond $k = 3$ without being forced to evaluate the entire combinatorial candidate matrix for $k > 3$.
   * Track the frequency of out-of-window overrides to determine if $k$ must be expanded to $k = 4$ or $k = 5$ before production annotation begins.

---

## 7. Protocol for Explicit Candidate-Pair Labeling

To transition from active-edge annotation to a mathematically well-defined candidate-pair universe with valid inter-annotator agreement:

1. **Deterministic Candidate Pair Generation:**
   For any segmented transcript with units $U$, candidate pair generator $G(U, k)$ deterministically produces ordered candidate set $C_k$:
   $$C_k = \{(u_i, u_j) \in U \times U \mid i \neq j \text{ and } 0 \le Turn(u_i) - Turn(u_j) \le k\}$$
2. **Exhaustive 4-Class Categorization:**
   Annotators are presented with each candidate pair $(u_i, u_j) \in C_k$ and must explicitly assign one of the 4 frozen labels:
   * `SUPPORTS`
   * `ATTACKS`
   * `RESPONDS_TO`
   * `NO_RELATION`
3. **Handling Negative & Missing Pairs:**
   * **Explicit `NO_RELATION`:** Every evaluated pair lacking an argumentative relationship is explicitly recorded with label `NO_RELATION`. Omission is prohibited.
   * **Ineligible / Out-of-Window ($OOW$):** Pairs outside $C_k$ ($Turn_i < Turn_j$ or $Turn_i - Turn_j > k$) are systematically categorized as out-of-window and excluded from relation evaluation. They are neither positive nor negative examples.
   * **Missing Candidate Detection:** If an annotator submits a file missing an evaluation for any pair in $C_k$, the validation script rejects the file with an `UNANNOTATED_CANDIDATE_PAIR` error, preventing silent negative imputation.

---

## 8. Dataset Licensing & Legal Compliance Audit

Under ARGUMAP Prime Directives 4 & 7 (Security, Hygiene, and Scientific Honesty), datasets and training benchmarks must not be fabricated, and license terms must be verified from primary legal sources before model training.

### 8.1 Current Licensing Status in Repository

| Resource Path / ID | Corpus Name | Stated License Status | Legal Source Evidence Needed Before ML Training |
| :--- | :--- | :---: | :--- |
| `data/annotations/pilot/debate_001_*.json` | UK Hansard AI Debate 2024 | `UNVERIFIED` | Verify Open Parliament Licence (OPL) v3.0 terms and ensure compliance with UK Parliamentary attribution requirements. |
| `data/annotations/pilot/debate_002_*.json` | US 2016 Presidential Debate (Trump-Clinton) | `UNVERIFIED` | Document transcript provenance (e.g. CPD public broadcast vs UCSB American Presidency Project public domain transcript) and confirm third-party markup rights. |
| `data/annotations/pilot/debate_003_*.json` | Kennedy-Nixon First Debate 1960 | `UNVERIFIED` | Verify public domain status under US government/historic broadcast exceptions and establish source attribution. |
| `data/dataset_manifest.json` candidate entries (`qt30`, `elecdeb60to20`, `aae`, etc.) | External Research Corpora | `UNVERIFIED` / `NOT_DOWNLOADED` | All candidate datasets remain strictly unverified. Full redistribution terms, academic research licenses, and usage permissions must be audited before downloading. |

### 8.2 Mandatory Training Gatekeeper

> [!CAUTION]
> **BLOCKER TO ML TRAINING:**  
> Machine learning model training (Phase 3+) will **NOT** begin until:
> 1. Every training transcript in `data/processed/` has an authoritative, documented open-access research license.
> 2. `data/dataset_manifest.json` reflects verified license terms.
> 3. `scripts/dataset/validate_dataset_manifest.py` passes with zero `UNVERIFIED` statuses for active training sets.
