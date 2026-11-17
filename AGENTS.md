# AGENTS.md — Development Guidelines & Agent Operating Rules

This document governs the operational, architectural, and behavioral rules for all automated AI coding agents, subagents, and human contributors working within the **ARGUMAP** codebase.

---

## 1. Prime Directives

1. **Read `PROJECT_SPEC.md` Before Implementation:**
   * Always read and align with [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md) before writing code, proposing architectures, or creating tests.
   * Never deviate from the frozen taxonomy, use-case scope, or MVP definitions outlined in the specification.

2. **Do Not Modify Unrelated Files:**
   * Limit file modifications strictly to the files necessary to complete the assigned task or phase.
   * Avoid cosmetic refactoring or speculative restructuring of untouched modules.

3. **Follow the Project Architecture:**
   * Respect modular design. Maintain clean boundaries between `frontend`, `backend`, `models`, `data`, and `docs`.
   * Adhere to the designated directory roles (e.g., raw data belongs in `data/raw/`, not mixed with scripts or processed data).

4. **Security & Secrets Hygiene:**
   * **Never hardcode API keys, database credentials, or secret tokens** in any source file, test fixture, or documentation.
   * **Never commit `.env` or local configuration files.** All sensitive values must be injected via environment variables and documented in `.env.example`.

5. **Strict Architectural Separation of Concerns:**
   * **Frontend:** Responsible solely for UI, user interactions, transcript inputs, state management, and React Flow visual graph rendering.
   * **Backend:** Responsible for API contracts, database operations, coordination of the processing pipeline, graph serialization, and validation.
   * **ML & NLP:** Responsible for preprocessing, sentence/proposition segmentation, component classification, relation classification, and NetworkX topological structure analysis.
   * Do not leak database or ML training logic into the frontend, nor UI rendering logic into backend services.

6. **No Unauthorized LLM Substitution:**
   * **Do not replace supervised ML/transformer classifiers with an LLM call or prompt** unless explicitly instructed by the user.
   * Core argument mining (Component Classification and Relation Extraction) must be executed by dedicated, reproducible ML models. LLMs are reserved exclusively as a potential explanation layer in later stages.

7. **Data Integrity & Scientific Honesty:**
   * **Do not fabricate datasets, synthetic labels, or artificial training benchmarks.**
   * Datasets must be grounded in acknowledged argument mining corpora (e.g., US2016 debate corpus, Cornell eRulemaking, Argument Annotated Essays) or documented annotation schemes.

8. **Comprehensive Test-Driven Verification:**
   * Write unit, integration, and property tests for all implemented business logic, NLP parsers, ML inference pipelines, and API endpoints.
   * Ensure tests are placed under the `tests/` directory and can be executed via standard runners (`pytest`, etc.).

9. **Maintain Roadmap Discipline in `TASKS.md`:**
   * Update [TASKS.md](file:///c:/Users/hii/Downloads/ARGUMAP/TASKS.md) after completing each milestone or phase.
   * Do not mark future phases as complete without full implementation and test verification.

10. **Strict V1 Scope Control:**
    * Keep V1 scope tightly contained to the 7-step MVP defined in [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md).
    * Reject or defer features outside the V1 scope (e.g., speech recognition, debate winner prediction, fact checking, sentiment analysis).

---

## 2. Directory Responsibilities

| Path | Purpose & Ownership |
| :--- | :--- |
| `docs/` | Architecture decision records (ADRs), schemas, API specs, and technical notes. |
| `data/raw/` | Immutable, original raw transcripts and external debate datasets. |
| `data/processed/` | Preprocessed, tokenized, and cleaned transcripts ready for featurization. |
| `data/annotations/` | Labeled ground truth annotations matching frozen component and relation labels. |
| `data/splits/` | Deterministic train, validation, and test splits (with fixed random seeds). |
| `models/` | Model architecture code, training scripts, evaluation metrics, and local inference wrappers. |
| `tests/` | Automated unit, functional, integration, and regression test suites. |
| `.agents/skills/` | Custom agent skills, automation scripts, and workflow aids. |

---

## 3. Code Quality & Standards

* **Python (Backend & ML):**
  * Type hints are mandatory (`typing`, Pydantic models).
  * Follow PEP 8 guidelines.
  * Use explicit exception handling; avoid bare `except:`.
* **TypeScript / React (Frontend):**
  * Strict TypeScript mode (`strict: true`).
  * Functional components with explicit prop types.
  * Keep visual components decoupled from network client hooks.
* **Documentation & Commits:**
  * Write clear, self-explanatory commit messages reflecting the specific phase or task.
  * Update documentation whenever schemas, contracts, or public interfaces change.
