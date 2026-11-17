# ARGUMAP — NLP Preprocessing Pipeline Specification

* **Document Version:** 1.0.0
* **Pipeline Component:** `backend/app/nlp/`
* **Status:** Operational Implementation Specification
* **Target Audience:** Computational Linguists, ML Engineers, Backend Developers

---

## 1. Pipeline Architecture & Sequence

The ARGUMAP NLP Preprocessing Pipeline transforms raw, unstructured debate discourse transcripts into standardized, offset-verified argumentative units. It serves as the deterministic feeder for both human annotation workflows (Step 5) and downstream machine learning classification (Step 7+).

```
[Raw Discourse Transcript]
            │
            ▼
[Stage 1: Text Normalization]
  • Convert line endings to LF (\n)
  • Normalize typographic quotes and dashes
  • Collapse intra-line whitespace and excessive blank lines
            │
            ▼
[Stage 2: Speaker & Turn Extraction]
  • Extract speaker tags (inline colons, uppercase headers)
  • Attribute chronological turns with document character offsets
  • Consolidate consecutive turns by the same speaker
  • Apply documented fallback (UNKNOWN_SPEAKER_1) if unlabelled
            │
            ▼
[Stage 3: Sentence Boundary Detection]
  • Segment turn texts into sequential grammatical sentences
  • Protect abbreviations, initials, decimals, percentages, and ellipses
  • Track exact turn-level character offsets (char_start, char_end)
            │
            ▼
[Stage 4: Conservative Proposition Segmentation]
  • Default: 1 sentence = 1 argumentative unit
  • Split coordinated independent clauses (comma + and/but/yet/however + independent subject)
  • Prevent aggressive splitting on lists, prepositional phrases, or dependent clauses
            │
            ▼
[Stage 5: Integrity & Offset Validation]
  • Verify char_start >= 0, char_end > char_start
  • Confirm exact substring slice match: turn.text[char_start:char_end] == unit.text
  • Guarantee component_label is strictly None
            │
            ▼
[Structured PreprocessingResult]
  • document, speakers, turns, units, metadata, validation
```

---

## 2. Stage Details

### 2.1 Text Normalization (`normalization.py`)
* **Objective:** Clean formatting noise without modifying semantic content or removing linguistic markers.
* **Safe Actions:**
  * Replaces Windows (`\r\n`) and legacy Mac (`\r`) line breaks with Unix line breaks (`\n`).
  * Normalizes typographic smart quotes (`\u2018`, `\u2019`, `\u201c`, `\u201d`) to standard quotes.
  * Replaces em dashes (`\u2014`) with `" -- "` and non-breaking spaces (`\u00a0`) with `" "`.
  * Collapses multiple internal spaces and tabs to single spaces.
  * Collapses runs of 3+ consecutive newlines to 2 newlines.
* **Prohibited Actions:**
  * Stopword removal (prohibited: stopwords such as *because*, *however*, *therefore* are essential discourse connectives for argument mining).
  * Stemming / Lemmatization (prohibited: inflectional morphology carries tense and modality).
  * Punctuation stripping (prohibited: terminal punctuation marks clause and sentence boundaries).

### 2.2 Speaker & Turn Parsing (`speaker_parser.py`)
* **Supported Formats:**
  1. *Inline Colon:* `Speaker A: text...` or `[Moderator]: text...`
  2. *Header Line:* `SPEAKER A\ntext...` or `MR. TRUMP\ntext...`
* **Turn Consolidation:** If a speaker has multiple consecutive speech blocks separated by whitespace without an intervening speaker, they are merged into a single chronological turn.
* **Fallback Attribution:** If a transcript contains no recognizable speaker prefixes, it is safely attributed to `UNKNOWN_SPEAKER_1` with a logged warning, allowing single-author or unsegmented text to process cleanly.
* **Deterministic Identifiers:**
  * Speakers: `spk_001`, `spk_002`, ...
  * Turns: `turn_001`, `turn_002`, ...

### 2.3 Sentence Boundary Detection (`sentence_segmenter.py`)
* **Rule-Based Delimitation:** Identifies terminal punctuation (`.`, `!`, `?`) followed by whitespace and uppercase letters or quotes.
* **Protected Patterns:**
  * Honorifics & Titles: `Mr.`, `Mrs.`, `Ms.`, `Dr.`, `Prof.`, `Sen.`, `Rep.`, `Gov.`
  * Academic & Latin: `e.g.`, `i.e.`, `etc.`, `vs.`, `al.`
  * Organizations & Acronyms: `U.S.`, `U.K.`, `E.U.`, `U.N.`, `U.S.A.`
  * Numbers & Percentages: `3.14`, `12.5%`, `No. 1`, `$1.5`
  * Ellipses: `...`

### 2.4 Conservative Proposition Segmentation (`proposition_segmenter.py`)
* **Philosophy:** In debate argument mining, excessive proposition splitting fragments context and creates artificial micro-propositions. Therefore, **sentence-level units are the default**.
* **Clause Splitting Criteria:** A sentence is divided into multiple units if and only if:
  1. It contains a coordinating conjunction preceded by punctuation: `, and `, `, but `, `, yet `, `; however, `, `; moreover, `, `; furthermore, `.
  2. Both the left clause and the right clause contain $\ge 4$ words.
  3. The right clause does not begin with a dependent subordinator (`because`, `although`, `if`, `since`, `unless`) or a pure prepositional phrase (`in`, `at`, `for`, `with`).
* **Non-Splitting Cases:**
  * Complex sentences with subordinate rationale (`"AI improves education because it enables personalized learning."`) remain **one unit**.
  * Serial lists (`"We must act quickly, carefully, and decisively."`) remain **one unit**.

---

## 3. Offset Strategy & Mathematical Invariants

For every generated `ArgumentUnit` $u$ extracted from parent `Turn` $t$:

$$\text{char\_start}(u) \ge 0$$
$$\text{char\_end}(u) > \text{char\_start}(u)$$
$$t.\text{text}[\text{char\_start}(u) : \text{char\_end}(u)] \equiv u.\text{text}$$

Offsets are zero-indexed and relative to the trimmed text of the parent turn.

---

## 4. Deterministic ID Strategy

All identifiers are generated deterministically:
* `document_id`: If not provided by caller, generated as `debate_{hash}` using SHA-256 over the transcript text.
* `speaker_id`: Numbered sequentially (`spk_001`, `spk_002`, ...) in order of appearance.
* `turn_id`: Numbered sequentially (`turn_001`, `turn_002`, ...) matching `turn_index + 1`.
* `unit_id`: Numbered sequentially across the entire debate (`u_001`, `u_002`, ...).

Running the identical input multiple times guarantees bit-for-bit identical IDs and output.

---

## 5. Feeding Step 7 (Baseline Component Classification)

In Phase 7, the preprocessed `ArgumentUnit` objects will serve as the exact input representations for the Task 1 Component Classifier:

```
[ArgumentUnit (text, offsets)] -> [Feature Extractor: TF-IDF / Sublinear Scaling]
                               -> [Multinomial Logistic Regression]
                               -> [Predicted Component Label: CLAIM, PREMISE, ...]
```

Because `component_label` remains strictly `None` during Step 6, there is zero risk of data leakage or synthetic labeling.

---

## 6. Known Limitations & Future Extensibility

1. **Informal Spoken Fillers:** Highly disfluent spoken transcripts containing repeated false starts (*"I mean, you know, we, we think..."*) are preserved verbatim. A dedicated disfluency cleaner can be attached in later stages if audio transcripts require it.
2. **Multi-Party Cross-Talk:** Overlapping dialogue where two speakers speak simultaneously is flattened to sequential turns based on transcript order.
3. **Complex Embedded Sub-Clauses:** Deeply nested non-restrictive relative clauses remain within their parent sentence to maintain context integrity.
