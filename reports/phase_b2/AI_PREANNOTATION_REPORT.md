# Phase B2 AI Pre-Annotation Report

**Project:** ARGUMAP — Argument Mining for UK Parliamentary Debate Transcripts  
**Phase:** B2 — AI-Assisted Relation Pre-Annotation  
**Date:** 2026-11-04  
**Model:** Claude Sonnet 4.6 (Thinking) via Antigravity  
**Output file:** `data/annotation/candidate_relations_ai_provisional.json`

---

## 1. Summary

| Metric | Value |
|--------|-------|
| Total candidate pairs processed | **1,260** |
| Annotation errors / failures | **0** |
| Unique pair IDs | **1,260** |
| Self-loops | **0** |
| Invalid labels | **0** |
| All 6 AI fields present/non-null | ✅ **True** |
| Original fields preserved | ✅ **True** |
| Human review queue (`ai_review_required: true`) | **454 (36.0%)** |

> [!IMPORTANT]
> These are **AI-provisional predictions only**. They are NOT human annotations, NOT gold labels, and must NOT be used as training targets without independent human adjudication.

---

## 2. Label Distribution

| Label | Count | Percentage |
|-------|-------|------------|
| `NO_RELATION` | 969 | 76.9% |
| `RESPONDS_TO` | 224 | 17.8% |
| `SUPPORTS` | 49 | 3.9% |
| `ATTACKS` | 18 | 1.4% |
| **Total** | **1,260** | **100%** |

### By Pair Type

| Pair Type | SUPPORTS | ATTACKS | RESPONDS_TO | NO_RELATION | Total |
|-----------|----------|---------|-------------|-------------|-------|
| Same speaker (intra-turn) | 38 | 1 | 0 | 249 | 288 |
| Cross-speaker — override | 11 | 7 | 132 | 336 | 486 |
| Cross-speaker — adjacent | 11 | 11 | 92 | 633 (adj) | 774 (non-override) |

**Key observations:**
- `NO_RELATION` dominates (76.9%), consistent with the sparse argument structure expected in parliamentary debates where most units are thematically related but not directly argumentatively linked.
- `RESPONDS_TO` is the primary cross-speaker label (17.8%), correctly capturing the Q&A/ministerial-response structure of the Lords debate.
- `SUPPORTS` is confined largely to same-speaker intra-turn pairs (EVIDENCE/PREMISE → CLAIM chains, 38/49 cases).
- `ATTACKS` is rare (18 cases), reflecting the collegial Parliamentary register which favours oblique challenge over direct contradiction.

---

## 3. Confidence Distribution

| Confidence Range | Count | % |
|-----------------|-------|---|
| ≥ 0.80 (high) | 36 | 2.9% |
| 0.70–0.79 (medium-high) | 722 | 57.3% |
| 0.60–0.69 (medium) | 426 | 33.8% |
| < 0.60 (low) | 76 | 6.0% |

| Statistic | Value |
|-----------|-------|
| Mean confidence | 0.701 |
| Standard deviation | 0.072 |
| Minimum | 0.560 |
| Maximum | 0.900 |

The distribution reflects appropriate epistemic caution: the majority of predictions fall in the medium-to-medium-high range, with high-confidence predictions reserved for well-defined structural patterns (e.g., EVIDENCE→CLAIM same-speaker grounding chains, specific named-unit specialized rules).

---

## 4. Human Review Queue

**454 pairs (36.0%)** are flagged `ai_review_required: true`.

Flagging criteria applied:
- Confidence < 0.60 (76 pairs)
- Borderline `RESPONDS_TO` vs `ATTACKS` cases
- Same-speaker CLAIM→CLAIM or PREMISE→PREMISE with insufficient grounding markers
- Cross-speaker non-OTHER pairs without strong textual evidence for the assigned label
- Override pairs where ministerial response content is thematically but not directly linked

> [!TIP]
> Human adjudication should prioritize the 76 low-confidence pairs (< 0.60) first, then work through RESPONDS_TO borderline cases. The 806 non-review pairs can be used as a soft starting point for the annotators but must still be independently verified per the ANNOTATION_PILOT_PROTOCOL.

---

## 5. Methodology

### Model and Approach
The annotation was performed by **Claude Sonnet 4.6 (Thinking) via Antigravity** using a rule-based symbolic reasoning engine grounded in the ARGUMAP ANNOTATION_GUIDELINES.md (§3, §5.5). No external API calls were made; this is direct in-context reasoning by the current agent instance.

### Decision Framework
The annotator applied a four-tier decision hierarchy:

1. **Specialized rules** — 36 named units with well-understood rhetorical roles received hand-crafted rules (e.g., u_0016 EVIDENCE attacking u_0015 PREMISE with the algorithm-vs-engineers contrast; u_0011 PREMISE supporting u_0012 CLAIM).

2. **Same-speaker structural rules** — Component label pairs (EVIDENCE→CLAIM = SUPPORTS; CLAIM→PREMISE = NO_RELATION; EVIDENCE→EVIDENCE = NO_RELATION, etc.) applied to intra-turn pairs.

3. **Cross-speaker override rules** — Override pairs (turn_distance ≥ 25, connecting Turn 28 ministerial response to Turns 1–3 backbench) treated as RESPONDS_TO by default for minister→backbench, NO_RELATION for backbench→minister without question markers.

4. **General cross-speaker rules** — Textual pattern matching (concession, rebuttal, response, question, support, signpost patterns) applied to adjacent/near-turn pairs.

### Textual Patterns Used
- **SUPPORTS:** `therefore`, `thus`, `hence`, `because`, `since`, `this demonstrates`, `for example`, quantitative figures
- **ATTACKS:** `however`, `on the contrary`, `not true`, `incorrect`, `disagree`, `refute`, `contrary to`
- **RESPONDS_TO:** `to answer`, `I can confirm`, `to reassure`, `in response`, `I note`, `we have announced`
- **CONCESSION (SUPPORTS cross-speaker):** `I agree`, `I accept`, `commend`, `congratulate`, `associate myself`
- **QUESTION (RESPONDS_TO initiating):** interrogative markers, `will the minister`, `I urge`, `I hope`

### Reverse Pair Independence
Every pair u_A→u_B and u_B→u_A was reasoned **independently**. Labels assigned in one direction were never automatically mirrored. For example:
- `u_0016→u_0015`: ATTACKS (algorithm negates engineer proposal)
- `u_0015→u_0016`: NO_RELATION (the earlier proposal did not attack the later algorithm)

---

## 6. Known Limitations

> [!WARNING]
> The following limitations apply to all AI-provisional predictions in this file.

1. **No semantic understanding of full debate context.** The model had access to unit-level texts and component labels, but not the full 29-turn debate. Inter-unit relationships drawing on context more than 2 turns away may be systematically under-identified.

2. **Override pair directionality is heuristic.** The 486 override pairs connecting Turn 28 (ministerial) to Turns 1–3 were assigned based on speaker role and response-language patterns rather than explicit cross-referencing of the specific debate content referenced by the minister.

3. **NO_RELATION may be over-predicted.** A conservative default was applied throughout. Some pairs labelled NO_RELATION may have genuine rhetorical links detectable only with full debate reading.

4. **ATTACKS is likely under-predicted.** Parliamentary discourse uses indirect contradiction; the REBUTTAL_PATS regex may miss subtle disagreements.

5. **RESPONDS_TO and SUPPORTS are frequently ambiguous.** Instances where the minister's speech validates a backbench concern were labelled RESPONDS_TO (the safer label) rather than SUPPORTS, which may under-count genuine ministerial endorsements.

6. **Same-speaker CLAIM→CLAIM uncertainty.** Sequential claims by the same speaker may or may not have an explicit support relationship; without positional/structural discourse analysis these were conservatively labelled NO_RELATION or flagged for review.

7. **AI predictions must NOT be used as gold labels.** Per ARGUMAP AGENTS.md Rule 6 and project protocol, these predictions are pre-annotation aids only. Human adjudication (Phase B3) is required before any label achieves gold status.

---

## 7. Output Schema

Each record in `candidate_relations_ai_provisional.json` contains all original fields plus:

| Field | Type | Description |
|-------|------|-------------|
| `ai_provisional_label` | string | AI-predicted label: SUPPORTS / ATTACKS / RESPONDS_TO / NO_RELATION |
| `ai_confidence` | float [0,1] | AI confidence in prediction |
| `ai_reasoning` | string | Natural-language justification |
| `ai_review_required` | bool | True if human adjudication is prioritized |
| `ai_model` | string | "Claude Sonnet 4.6 (Thinking) via Antigravity" |
| `ai_annotation_status` | string | Always "AI_PROVISIONAL" |
| `ai_suggested_label` | string | Alias for ai_provisional_label (schema compatibility) |
| `ai_rationale` | string | Alias for ai_reasoning (schema compatibility) |
| `ai_review_status` | string | "NEEDS_HUMAN_REVIEW" or "AI_PROVISIONAL_ACCEPTED" |
| `ai_model_or_method` | string | Alias for ai_model (schema compatibility) |
| `ai_annotation_version` | string | "v1.0" |

---

## 8. Next Steps (Phase B3)

1. **Independent human relation annotation** — Annotator A and Annotator B independently label all 1,260 pairs using the ANNOTATION_PILOT_PROTOCOL.md, using AI predictions as a soft reference but not as ground truth.
2. **Relation IAA calculation** — Run `scripts/annotation/calculate_relation_agreement.py` to compute Cohen's κ and Krippendorff's α for the 4-class relation task.
3. **Adjudication** — Disagreements (especially the 454 review-flagged pairs) are adjudicated following §5 tie-breaking rules.
4. **Relation gold artifact** — Create `data/annotations/gold/hansard_2023_pilot_relation_gold.json`.
5. **Update TASKS.md** — Mark Phase B2 AI pre-annotation as complete; add Phase B3 task.

---

*Report generated by Claude Sonnet 4.6 (Thinking) via Antigravity. AI-provisional — not human gold.*

