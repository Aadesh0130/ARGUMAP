# TASKS.md — ARGUMAP Phased Roadmap & Progress Tracker

This document defines the complete phased roadmap for **ARGUMAP** from specification through production deployment.

* **Current Status:** Phase 7 ML Infrastructure Complete + Step 8 Gold Dataset Pilot Complete + Phase B1 Component Pilot Complete + **Phase B2 AI Pre-Annotation Complete**.
* **Next Action:** Phase B2 Human Relation Annotation (Annotators A & B independently label 1,260 candidate pairs using AI predictions as soft reference) → Relation IAA calculation → Phase B3 Adjudication & Relation Gold Artifact.

---

## Roadmap Overview

- [x] **Phase 1: Specification** *(Completed)*
- [x] **Phase 2: Architecture and Data Design** *(Completed)*
- [x] **Phase 3: Frontend Foundation** *(Completed)*
- [x] **Phase 4: Backend Foundation** *(Completed)*
- [x] **Phase 5: Dataset Research and Annotation Setup** *(Completed)*
- [x] **Phase 6: NLP Preprocessing Pipeline** *(Completed)*
- [ ] **Phase 7: Baseline Component Classifier** *(Pending)*
- [ ] **Phase 8: Transformer Component Classifier** *(Pending)*
- [ ] **Phase 9: Relation Extraction** *(Pending)*
- [ ] **Phase 10: Argument Graph** *(Pending)*
- [ ] **Phase 11: Analysis Engine** *(Pending)*
- [ ] **Phase 12: Frontend / Backend / ML Integration** *(Pending)*
- [ ] **Phase 13: Testing and Evaluation** *(Pending)*
- [ ] **Phase 14: Deployment** *(Pending)*

---

### Operational Status Distinction:
* **Dataset infrastructure:** COMPLETED
* **NLP Preprocessing Pipeline:** COMPLETED
* **Authentic Hansard Ingestion & Unitization:** COMPLETED — 988 units across 29 turns and 28 speakers prepared from authentic UK Lords 2023 debate (`hansard_lords_ai_debate_2023.txt`). Slicing character offsets 100% verified. Full-debate unannotated annotation templates created for Annotators A & B.
* **Human Annotation Pilot Package (Authentic Hansard):** COMPLETED & FINALIZED — Bounded 4-turn dialectical diversity pilot subset generated (36 units across Turns 1, 2, 3, and Turn 28 ministerial response, 1,260 candidate pairs under approved Option B bidirectional policy). Independent A and B packages (`hansard_2023_pilot_annotator_A.json`, `hansard_2023_pilot_annotator_B.json`) validated with zero prefilled labels. Scale-up policy established ($w=10$ intra-turn horizon with override).
* **Phase B1 Component Pilot Reconciliation & Adjudication:** COMPLETED — 36-unit component pilot fully annotated by Annotators A & B (77.78% raw agreement, κ = 0.6923, α = 0.6895). All 8 dialectical disagreements (`u_0010`, `u_0011`, `u_0013`, `u_0017`, `u_0072`, `u_0093`, `u_0095`, `u_0096`) adjudicated by Lead Computational Linguist and codified in `data/annotations/ambiguity_log.json` (`AMB_018`–`AMB_025`). Official gold component artifact exported to `data/annotations/gold/hansard_2023_pilot_gold.json` (10 CLAIM, 6 PREMISE, 7 EVIDENCE, 0 COUNTERARGUMENT, 0 REBUTTAL, 13 OTHER). Passed all syntactic and semantic validation checks.
* **Phase B2 AI Relation Pre-Annotation:** COMPLETED — All 1,260 directed candidate pairs annotated by Claude Sonnet 4.6 (Thinking) via Antigravity using ARGUMAP guidelines (§3, §5.5). Distribution: NO_RELATION=969 (76.9%), RESPONDS_TO=224 (17.8%), SUPPORTS=49 (3.9%), ATTACKS=18 (1.4%). 454 pairs flagged for human review. All 8 integrity checks passed (1,260 pairs, 0 self-loops, 0 invalid labels, all AI fields present). Output: `data/annotation/candidate_relations_ai_provisional.json`. Report: `reports/phase_b2/AI_PREANNOTATION_REPORT.md`. **AI predictions are pre-annotation aids only — NOT gold labels.**
* **Human Annotation Workspace:** COMPLETED — Local, dedicated FastAPI web workspace and CLI launcher implemented (`scripts/annotation/annotation_workspace.py`, `workspace_session.py`, `templates/workspace.html`). Ensures strict annotator isolation, atomic persistence, frozen label validation, override justifications, and immutability of original pilot templates. Full test suite passing (132 passed).
* **Gold Dataset Pilot (Phase 1):** PILOT COMPLETE — 63 demo units across 3 debates. Formal kappa computation complete on pilot. Real training data scale-up ready for human annotation on authentic Hansard templates.
* **Component classification:** BLOCKED (requires completed human gold annotations)
* **Relation classification:** BLOCKED (requires completed human gold annotations)
* **Model training:** BLOCKED (requires completed human gold annotations)

---

## Detailed Phase Breakdown

### [x] Phase 1: Specification
*Status: Completed*
* [x] Establish official project repository structure (`docs/`, `data/`, `models/`, `tests/`, `.agents/skills/`).
* [x] Formulate and freeze [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md) (problem, objectives, V1 MVP, 6 component labels, 4 relation labels, out-of-scope constraints, tech stack).
* [x] Create [AGENTS.md](file:///c:/Users/hii/Downloads/ARGUMAP/AGENTS.md) establishing coding guidelines, security constraints, and separation of concerns.
* [x] Define phased development plan in [TASKS.md](file:///c:/Users/hii/Downloads/ARGUMAP/TASKS.md).
* [x] Initialize comprehensive [README.md](file:///c:/Users/hii/Downloads/ARGUMAP/README.md) and [.gitignore](file:///c:/Users/hii/Downloads/ARGUMAP/.gitignore).

---

### [x] Phase 2: Architecture and Data Design
*Status: Completed*
* [x] Define modular monolith system architecture and data flow across all layers in [ARCHITECTURE.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ARCHITECTURE.md).
* [x] Specify relational database entities (`Debate`, `Speaker`, `Turn`, `Argument`, `Relation`, `AnalysisRun`), Mermaid ER diagram, and React Flow data bridge in [DATA_SCHEMA.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/DATA_SCHEMA.md).
* [x] Design two-stage ML pipeline (Task 1 Component Classifier with TF-IDF baseline + Transformer exploration; Task 2 Relation Classifier with $O(n^2)$ pair pruning) in [ML_DESIGN.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ML_DESIGN.md).
* [x] Create rigorous human annotation protocol for all 6 component and 4 relation labels with tie-breakers in [ANNOTATION_GUIDELINES.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_GUIDELINES.md).
* [x] Formulate REST API contract (`/api/health`, `/api/debates`, `/api/analyze`, `/api/analysis/{id}`, `/api/debates/{id}`) in [API_CONTRACT.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/API_CONTRACT.md).

---

### [x] Phase 3: Frontend Foundation
*Status: Completed*
* [x] Initialize React + TypeScript + Vite project in `frontend/`.
* [x] Configure Tailwind CSS design system with curated research palette and semantic component tokens (`CLAIM`, `PREMISE`, `EVIDENCE`, `COUNTERARGUMENT`, `REBUTTAL`, `OTHER`).
* [x] Implement routing across 7 application views: `/`, `/analyze`, `/processing`, `/results`, `/how-it-works`, `/technology`, `/about`.
* [x] Build professional landing page with hero heading, CTA buttons, problem overview, pipeline roadmap, and features.
* [x] Build Analyze page with transcript editor, sample debate loader, character/turn counters, and document upload UI.
* [x] Build Processing page with animated 7-step visual pipeline ladder and real-time execution terminal stream.
* [x] Build Results dashboard with 5 component statistic cards, interactive React Flow argument graph (custom nodes, color-coded relational edges, zoom/pan/drag), node inspection sidebar, and structural reasoning insights panel.
* [x] Define future API TypeScript types in `src/types/index.ts` aligned with `DATA_SCHEMA.md`.
* [x] Verify full TypeScript strict compilation and production build (`npm run build`).

---

### [x] Phase 4: Backend Foundation
*Status: Completed*
* [x] Initialize FastAPI application structure (`app/api/`, `app/core/`, `app/db/`, `app/models/`, `app/schemas/`, `app/services/`).
* [x] Implement Pydantic v2 schemas for Debates, Turns, Speakers, Arguments, Relations, and Analysis Runs.
* [x] Implement SQLAlchemy v2 models (`Debate`, `Speaker`, `Turn`, `Argument`, `Relation`, `AnalysisRun`) with PostgreSQL-readiness and graceful local development fallback.
* [x] Implement endpoints: `GET /`, `GET /api/health`, `POST /api/debates`, `GET /api/debates/{id}`, `POST /api/analyze` (placeholder response), and `GET /api/analysis/{id}`.
* [x] Configure configurable CORS middleware and standard API error envelope.
* [x] Author comprehensive pytest test suite (100% pass rate over 8 automated test cases).
* [x] Verify live server execution on port 8000 (Swagger UI at `/docs` and OpenAPI JSON at `/openapi.json`).

---

### [x] Phase 5: Dataset Research and Annotation Setup
*Status: Completed*
* [x] Establish data directory layout (`data/raw/`, `data/processed/`, `data/annotations/`, `data/splits/`, `data/README.md`) with `.gitkeep` and storage hygiene.
* [x] Create [dataset_manifest.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/dataset_manifest.json) cataloging candidate primary (QT30, US2016, ElecDeb60To20) and auxiliary (AAE, M-Arg, IBM Evidence, AbstRCT, Web Discourse, Microtexts) corpora with strict license verification.
* [x] Create machine-readable [annotation_schema.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/annotations/annotation_schema.json) and Draft-07 [annotation.schema.json](file:///c:/Users/hii/Downloads/ARGUMAP/data/annotations/annotation.schema.json).
* [x] Implement annotation validator script (`scripts/dataset/validate_annotations.py`) enforcing taxonomy adherence, character offsets, duplicate checks, and relation integrity.
* [x] Implement manifest validator script (`scripts/dataset/validate_dataset_manifest.py`) enforcing required provenance and strict `UNVERIFIED` license tracking.
* [x] Build modular conversion framework (`scripts/dataset/conversion/`) preserving native labels (`NormalizedUnit`, `ProvenanceRecord`, `BaseCorpusConverter`, `AAEConverter`, `US2016Converter`).
* [x] Create `MappingRegistry` gatekeeper blocking unauthorized/automatic conversion of external labels to ARGUMAP labels.
* [x] Formulate [data/splits/README.md](file:///c:/Users/hii/Downloads/ARGUMAP/data/splits/README.md) establishing debate-level grouped splitting (70/15/15) to prevent context and speaker leakage.
* [x] Create [docs/ANNOTATION_WORKFLOW.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/ANNOTATION_WORKFLOW.md) defining the 9-stage annotation pipeline, pilot calibration, provisional ambiguity resolution, and candidate-pair distance window ($k$ to be determined during pilot).
* [x] Create pilot annotation workspace (`data/annotations/pilot/README.md`, `sample_annotation.json`) prominently marked as `DEMO / NOT TRAINING DATA`.
* [x] Implement descriptive dataset statistics script (`scripts/dataset/dataset_statistics.py`) without fabricating synthetic numbers.
* [x] Author automated test suite in `tests/test_dataset_infrastructure.py` (14 passing tests, 100% pass rate).
* [x] **Step 5 Correction:** Audited and corrected all candidate dataset license entries in `data/dataset_manifest.json` to strictly reflect `UNVERIFIED` license and status where authoritative proof is absent (QT30, US2016, AAE, M-Arg, IBM Evidence, ElecDeb60To20, AbstRCT, Web Discourse, Microtexts).

---

### [x] Phase 6: NLP Preprocessing Pipeline
*Status: Completed*
* [x] Implement deterministic text normalization (`backend/app/nlp/normalization.py`) preserving punctuation, casing, numbers, quotes, and citations.
* [x] Implement deterministic speaker and turn extractor (`backend/app/nlp/speaker_parser.py`) supporting inline colons, standalone headers, turn consolidation, and `UNKNOWN_SPEAKER_1` fallback.
* [x] Implement deterministic sentence boundary segmenter (`backend/app/nlp/sentence_segmenter.py`) with abbreviation/initial/decimal protection and exact offset tracking.
* [x] Implement conservative proposition/clause segmenter (`backend/app/nlp/proposition_segmenter.py`) enforcing sentence default and strict independent clause splitting rules.
* [x] Implement high-level pipeline orchestrator (`backend/app/nlp/pipeline.py`) ensuring `component_label` remains strictly `None` and character offsets match verbatim turn slices.
* [x] Implement CLI transcript preprocessing utility (`scripts/nlp/preprocess_transcript.py`).
* [x] Author comprehensive pytest test suite in `tests/test_nlp_preprocessing.py` (15 tests passing, 100% pass rate).
* [x] Document pipeline architecture, rules, and edge cases in `docs/NLP_PREPROCESSING.md`.

---

### [x] Phase 7: Component Classification
*Status: ML Infrastructure Completed (Gold Training Blocked — License Unverified)*
* [x] **ML Infrastructure:** COMPLETED — Established modular `ml/` package containing configuration, dataset loading, debate-level non-leaking splitting, feature extraction, evaluation metrics, reporting, and CLI scripts.
* [x] **TF-IDF Baseline Implementation:** COMPLETED — Implemented `TFIDFBaselineClassifier` with configurable n-grams, sublinear scaling, multinomial Logistic Regression, balanced class weighting, and model persistence in `ml/baseline/`.
* [x] **Transformer Implementation:** COMPLETED — Implemented `ArgumentComponentTransformer` and `ArgumentUnitDataset` supporting `roberta-base`, device auto-selection (CUDA/CPU), class-weighted cross-entropy loss, and contextual discourse slots (`ml/transformer/`).
* [x] **Evaluation & Data Integrity:** COMPLETED — Implemented strict frozen 6-class confusion matrix, Macro F1 (primary), Weighted F1, per-class metrics, and dataset distribution reporting in `ml/evaluation/`.
* [x] **Step 8 Gold Annotation Pilot:** COMPLETED — 63 double-annotated gold units across 3 debates (UK Hansard, US2016, Kennedy–Nixon), 34 active relations, 17 adjudicated ambiguity cases, observed component agreement ~79.4%, relation agreement ~88.2%. All data marked `UNVERIFIED` per provenance protocol. Formal kappa computation pending.
* [ ] **Formal Kappa Computation:** PENDING — Run `calculate_component_agreement.py` + `calculate_relation_agreement.py`. Gate: κ ≥ 0.70 (component), κ ≥ 0.65 (relation).
* [ ] **License Verification:** BLOCKED — All pilot corpora remain `UNVERIFIED`. Contact corpus maintainers before scaling annotation.
* [ ] **Training on Real ARGUMAP Gold Data:** BLOCKED — Pending license clearance and annotation volume ≥ 500 units. Synthetic benchmark fabrication is prohibited.
* [ ] **Actual Model Performance:** NOT AVAILABLE until gold annotations exist.

---

### [ ] Phase 8: Transformer Component Classifier
*Status: Pending*
* [ ] Build Hugging Face Dataset loaders and tokenization pipelines for component classification.
* [ ] Fine-tune transformer model (e.g., DeBERTa-v3 / RoBERTa) on the 6 frozen component labels using PyTorch.
* [ ] Conduct hyperparameter tuning and model checkpointing in `models/component_classifier/`.
* [ ] Evaluate against classical baseline and generate confusion matrix and error analysis.

---

### [ ] Phase 9: Relation Extraction
*Status: Pending*
* [ ] Formulate candidate pair generation logic (pruning cross-sentence pairs based on speaker turns and distance windows).
* [ ] Implement pairwise transformer classifier taking concatenated argument units $(u_i, u_j)$ to predict relation (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`, `NO_RELATION`).
* [ ] Fine-tune and evaluate relation extraction model with class-imbalance weighting.
* [ ] Save relation model weights and evaluation reports in `models/relation_classifier/`.

---

### [ ] Phase 10: Argument Graph
*Status: Pending*
* [ ] Implement NetworkX graph builder to construct directed argument multigraphs from predicted units and relations.
* [ ] Implement graph validation (cycle detection, disconnected component analysis, root claim identification).
* [ ] Implement graph serializer producing frontend-ready JSON compatible with React Flow node-edge structures.
* [ ] Write unit tests covering diverse argument topology scenarios.

---

### [ ] Phase 11: Analysis Engine
*Status: Pending*
* [ ] Implement graph inspection algorithms:
  * Unsupported Claim Detector (claims without incoming `SUPPORTS` edges).
  * Unanswered Counterargument Detector (counterarguments without incoming `REBUTTAL` or `RESPONDS_TO` edges).
  * Direct Rebuttal / Clash Analyzer (quantification of cross-speaker attacks and responses).
  * Argument density and speaker balance metrics.
* [ ] Generate human-readable structural reasoning insight summaries.
* [ ] Write unit tests verifying insight accuracy against canonical debate patterns.

---

### [ ] Phase 12: Frontend / Backend / ML Integration
*Status: Pending*
* [ ] Connect frontend transcript submission to backend analysis pipeline.
* [ ] Stream or poll pipeline progress states (Parsing → Segmenting → Classifying → Mapping → Insights).
* [ ] Render dynamic React Flow graph with interactive node inspection, edge highlight on click, and filter controls.
* [ ] Display structural reasoning insights in side panel with interactive jump-to-node navigation.

---

### [ ] Phase 13: Testing and Evaluation
*Status: Pending*
* [ ] Execute end-to-end integration tests on full academic debate transcripts.
* [ ] Benchmark system latency, memory footprint, and inference throughput.
* [ ] Perform cross-validation and robustness testing on edge cases (single-speaker monologues, noisy transcript formats, interruptions).
* [ ] Document final evaluation benchmarks in `docs/evaluation_report.md`.

---

### [ ] Phase 14: Deployment
*Status: Pending*
* [ ] Containerize backend service and frontend client using Docker.
* [ ] Configure production ASGI server setup (Uvicorn / Gunicorn) and static asset hosting.
* [ ] Set up automated CI/CD pipeline for linting, type checks, and automated tests.
* [ ] Author deployment handbook and user onboarding documentation in `docs/deployment.md`.
