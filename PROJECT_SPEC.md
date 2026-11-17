# ARGUMAP — Project Specification

## 1. Project Overview

* **Title:** Automated Argument Structure Analysis and Debate Reasoning Using Natural Language Processing
* **Identifier:** ARGUMAP
* **Specification Version:** 1.0.0 (Frozen for V1)
* **Core Idea:** ARGUMAP analyzes a text-based debate transcript, identifies argument components and relationships between them, and generates an interactive argument structure.
* **Unique Selling Proposition (USP):**
  > "ARGUMAP reconstructs the reasoning structure of a debate by connecting claims, supporting arguments, counterarguments, and rebuttals into an interactive argument map."

---

## 2. Problem Statement

Existing text analysis tools and Natural Language Processing pipelines commonly focus on high-level topic modeling, entity extraction, keyword frequency, or sentiment analysis. However, debates and complex deliberations are defined by logic and dialectical interaction rather than sentiment. 

Current systems fail to reconstruct the underlying reasoning structure of a debate:
* They cannot isolate discrete argument units from multi-sentence turns.
* They cannot determine whether an utterance functions as a core thesis, supportive ground, piece of evidence, or direct rebuttal.
* They cannot map the relational dynamics (support, attack, response) connecting opposing speakers.
* As a result, users cannot visually navigate, evaluate logical soundness, or detect unaddressed rebuttals and unsupported claims in deliberation.

ARGUMAP bridges this gap by applying specialized argument mining and graph-based structural analysis to discourse transcripts.

---

## 3. Objectives

ARGUMAP's core objectives are to automatically process structured debate transcripts and identify:
1. **Speakers:** Attribute each segment of discourse to its respective speaker.
2. **Individual Argument Units:** Segment speaker turns into discrete, proposition-level argumentative units.
3. **Argument Component Types:** Classify each unit into a rigorous argument component category.
4. **Inter-Argument Relationships:** Predict relational links (directional dependencies and rhetorical attacks) across argument units.
5. **Overall Reasoning Structure:** Construct an interactive, directed argument graph enriched with structural reasoning insights.

---

## 4. Use Cases

### 4.1 Primary Use Case (V1 Target)
* **Academic Debate Analysis:** Enabling competitive debaters, debate adjudicators, educators, and researchers to dissect debate rounds, verify whether teams answered key arguments, spot unsupported premises, and evaluate discourse flow.

### 4.2 Potential Future Use Cases (Post-V1)
* **Student Essay Analysis:** Guiding students in structuring argumentative essays with solid claims and sufficient evidence.
* **Research Argument Mapping:** Synthesizing competing scientific or academic papers on disputed hypotheses into coherent claim-evidence trees.
* **Policy Document Analysis:** Auditing legislative drafts, civic proposals, and stakeholder consultation transcripts for unverified claims or unaddressed counterarguments.
* **Legal Argument Organization:** Assisting legal professionals in organizing briefs, witness testimonies, and precedent citations into formal argumentative chains.
* **Public Opinion & Deliberation Analysis:** Visualizing contentious public discussions to elevate debate clarity and minimize rhetorical talk-past.

---

## 5. Input Specification

ARGUMAP accepts text-based debate transcripts formatted with explicit speaker labels.

### 5.1 Input Format Requirements
* Format: Plain text (`.txt`) or UTF-8 text string.
* Structure: Turn-by-turn speech with explicit speaker identifiers preceding statements.
* Character Encoding: UTF-8.

### 5.2 Input Example
```text
Speaker A: AI should be used in education because it enables personalized learning.
Speaker B: However, excessive dependence on AI can reduce independent thinking.
Speaker A: This risk can be reduced through teacher supervision.
```

---

## 6. Frozen Taxonomy (Version 1)

To ensure consistency, model stability, and reproducible evaluation across all NLP components, the label space for components and relations is strictly frozen for V1.

### 6.1 Component Labels (Frozen)
Every segmented argument unit is assigned exactly one of the following 6 mutually exclusive labels:

| Label | Definition | Contextual Example |
| :--- | :--- | :--- |
| **CLAIM** | A central contentious statement, assertion, or thesis put forward by a speaker. | *"AI should be used in education."* |
| **PREMISE** | A reason, rationale, or foundational statement offered to substantiate or justify a claim. | *"...because it enables personalized learning."* |
| **EVIDENCE** | Empirical data, statistical facts, study findings, expert citations, or concrete real-world demonstrations supporting a premise or claim. | *"A 2024 Stanford study found a 23% improvement in retention when adaptive tutoring was used."* |
| **COUNTERARGUMENT** | An argument, objection, or opposing reasoning raised directly against an established claim or premise. | *"However, excessive dependence on AI can reduce independent thinking."* |
| **REBUTTAL** | A direct response designed to counter, diminish, or invalidate a previous counterargument or objection. | *"This risk can be reduced through teacher supervision."* |
| **OTHER** | Conversational filler, introductory/procedural remarks, acknowledgments, greetings, or non-argumentative discourse. | *"Thank you, Madame Speaker, and good afternoon everyone."* |

### 6.2 Relation Labels (Frozen)
Given an ordered pair of argument units $(\text{Unit}_A, \text{Unit}_B)$, the relationship is classified into one of the following 4 categories:

| Relation | Definition | Semantic Direction |
| :--- | :--- | :--- |
| **SUPPORTS** | $\text{Unit}_A$ reinforces, justifies, provides evidence for, or strengthens the validity of $\text{Unit}_B$. | $\text{Unit}_A \rightarrow \text{Unit}_B$ |
| **ATTACKS** | $\text{Unit}_A$ directly contradicts, challenges, weakens, or attempts to falsify $\text{Unit}_B$. | $\text{Unit}_A \rightarrow \text{Unit}_B$ |
| **RESPONDS_TO** | $\text{Unit}_A$ directly addresses, reframes, clarifies, or rebuts $\text{Unit}_B$ without necessarily being a direct binary attack or support. | $\text{Unit}_A \rightarrow \text{Unit}_B$ |
| **NO_RELATION** | No direct rhetorical, evidential, or logical argumentative link exists between $\text{Unit}_A$ and $\text{Unit}_B$. | None |

---

## 7. Machine Learning Formulation

ARGUMAP decomposes debate reasoning analysis into two distinct supervised learning tasks:

### Task 1: Argument Component Classification
* **Formulation:** Multi-class sequence classification.
* **Input:** Individual sentence or argument unit $u_i$ within discourse context $C$.
* **Mapping:** $u_i \xrightarrow{\text{Model}_{\text{comp}}} y \in \{\text{CLAIM}, \text{PREMISE}, \text{EVIDENCE}, \text{COUNTERARGUMENT}, \text{REBUTTAL}, \text{OTHER}\}$.
* **Evaluation Metrics:** Macro F1-score, Weighted F1-score, per-class Precision/Recall.

### Task 2: Argument Relation Extraction
* **Formulation:** Pairwise relation classification / link prediction.
* **Input:** Argument pair $(u_i, u_j)$ where $i \neq j$, along with speaker identity and positional context.
* **Mapping:** $(u_i, u_j) \xrightarrow{\text{Model}_{\text{rel}}} r \in \{\text{SUPPORTS}, \text{ATTACKS}, \text{RESPONDS_TO}, \text{NO_RELATION}\}$.
* **Evaluation Metrics:** Relation Macro F1-score (excluding `NO_RELATION`), Precision/Recall curves.

---

## 8. Expected Outputs

ARGUMAP transforms unannotated text into an interconnected analytical graph:
1. **Identified Speakers:** Normalized speaker catalog mapped to each speech turn.
2. **Argument Components:** Structured catalog of all segmented argument units with assigned component labels and confidence scores.
3. **Relationships:** Directed, labeled adjacency edges indicating how arguments interact.
4. **Interactive Argument Graph:** Visual representation rendered via node-link topology (nodes color-coded by component type, edges formatted by relationship type).
5. **Structural Reasoning Insights:** Automated deterministic and heuristic checks derived from the graph topology:
   * *Claim Support Coverage:* Flags claims lacking supporting premises or empirical evidence (e.g., *"Claim 3 has no detected supporting evidence"*).
   * *Unanswered Rebuttals/Attacks:* Identifies counterarguments left unaddressed by opposing speakers (e.g., *"One counterargument has no detected response"*).
   * *Direct Engagements:* Quantifies direct clash between teams (e.g., *"Two rebuttals directly address opposing arguments"*).
   * *Orphan Arguments:* Detects premises or evidence detached from any root claim.

> **CRITICAL BOUNDARY:** ARGUMAP does **NOT** predict a debate winner, adjudicate truthfulness, or assign political/persuasive victory points. The tool analyzes reasoning structure, not rhetorical verdict.

---

## 9. V1 MVP Scope Definition

The V1 Minimum Viable Product (MVP) consists strictly of the following end-to-end 7-step pipeline:

```
[1. Upload/Paste Transcript]
            ↓
  [2. Parse Speakers]
            ↓
[3. Split into Argument Units]
            ↓
[4. Classify Argument Components]
            ↓
[5. Detect Relationships]
            ↓
  [6. Build Argument Graph]
            ↓
[7. Display Structural Insights]
```

1. **Upload/Paste Transcript:** Clean text input interface with support for pasting or uploading raw transcripts.
2. **Parse Speakers:** Deterministic regex/parser to extract speaker labels and delineate speech turns.
3. **Split Transcript into Argument Units:** Sentence and clause segmentation to create discrete propositions.
4. **Classify Argument Components:** Apply Task 1 component classifier to tag each unit with one of the 6 frozen labels.
5. **Detect Relationships:** Candidate pair selection + Task 2 relation classifier to identify links.
6. **Build Argument Graph:** Aggregate components and relations into a directed NetworkX graph, serialized to JSON for graph rendering.
7. **Display Structural Insights:** Surface structural anomalies (unsupported claims, unanswered counterarguments, rebuttals count).

---

## 10. Out of Scope for V1

To safeguard project delivery and maintain scientific rigor, the following capabilities are explicitly **OUT OF SCOPE** for Version 1:
* **Audio processing:** No processing of raw audio streams, `.mp3`, `.wav`, or `.m4a` files.
* **Speech recognition (ASR):** No speech-to-text transcription engine.
* **Speaker diarization:** No acoustic speaker clustering or voiceprint identification.
* **Debate winner prediction:** No classification of winners, win margins, or point scoring.
* **Political persuasion analysis:** No bias detection, ideological leaning assessment, or stance evaluation.
* **Sentiment analysis:** No valence/arousal scoring, polarity classification, or emotional tone labeling.
* **Fake-news detection:** No truth-value scoring or misinformation tagging.
* **Generic chatbot functionality:** No open-ended conversational agent or free-form chat assistant.
* **Fact checking:** No external knowledge base querying or claim verification.
* **Automatic web research:** No automated scraping, web retrieval, or search engine integration.
* **Fully LLM-based argument classification:** The core classification pipeline must rely on dedicated, reproducible ML models (classifiers/fine-tuned transformers). LLMs may only be considered in later phases as an optional natural-language explanation layer, not as the primary argument classification engine.

---

## 11. Planned Technology Stack

*(Note: Defined for architectural alignment. No packages are installed or implemented during Phase 1.)*

### Frontend
* **Core:** React, TypeScript, Vite
* **Styling:** Tailwind CSS
* **Visualization:** React Flow (for interactive node-edge argument graph rendering)

### Backend
* **Language & Framework:** Python 3.10+, FastAPI
* **Data Modeling & Validation:** Pydantic v2
* **ORM & Database Abstraction:** SQLAlchemy v2

### Machine Learning & NLP
* **Deep Learning Framework:** PyTorch
* **Transformers & NLP Models:** Hugging Face Transformers, Hugging Face Datasets
* **Classical ML & Metrics:** scikit-learn
* **Linguistic Preprocessing & Tokenization:** spaCy
* **Data Manipulation & Scientific Computing:** pandas, NumPy
* **Graph Algorithms & Topology:** NetworkX

### Database
* **Relational Store:** PostgreSQL

### Training & Compute
* **Hardware Environment:** Google Colab / GPU compute instances for fine-tuning transformer models when required.
