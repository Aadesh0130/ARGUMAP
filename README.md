# ARGUMAP

**Automated Argument Structure Analysis and Debate Reasoning Using Natural Language Processing**

> **Unique Selling Proposition (USP):**  
> *"ARGUMAP reconstructs the reasoning structure of a debate by connecting claims, supporting arguments, counterarguments, and rebuttals into an interactive argument map."*

---

## Overview

ARGUMAP is a computational argumentation platform designed to move beyond traditional topic modeling and sentiment analysis. By decomposing debate discourse into proposition-level argument units and predicting logical relationships across opposing speakers, ARGUMAP reconstructs the underlying dialectical topology of a debate into an interactive, visual argument map.

---

## Current Development Status

* **Current State:** **Phase 6 Complete: NLP Preprocessing Pipeline Operational**
* **Project Foundation:** The taxonomy, data contracts, and architectural rules are frozen in [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md).
* **Completed Milestones:**
  * Phase 1: Specification frozen ([PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md), [AGENTS.md](file:///c:/Users/hii/Downloads/ARGUMAP/AGENTS.md)).
  * Phase 2: Technical blueprints established (`docs/ARCHITECTURE.md`, `DATA_SCHEMA.md`, `ML_DESIGN.md`, `ANNOTATION_GUIDELINES.md`, `API_CONTRACT.md`).
  * Phase 3: Frontend foundation built (`frontend/` React 18, Vite, TypeScript, Tailwind CSS, React Flow visual argument graph).
  * Phase 4: Backend foundation built (`backend/` FastAPI modular monolith, SQLAlchemy PostgreSQL-ready models, Pydantic v2 schemas, automated test suite).
  * Phase 5: Dataset infrastructure & annotation setup operational (`data/dataset_manifest.json`, annotation schemas, conversion framework, provenance tracking, and validators).
  * Phase 6: NLP preprocessing pipeline implemented (`backend/app/nlp/`, speaker parsing, normalization, sentence and conservative proposition segmentation, offset verification, CLI tooling, and test suite).
* **Operational Distinctions for Current State:**
  * Dataset infrastructure: COMPLETED
  * NLP preprocessing pipeline: COMPLETED
  * Component classification: NOT STARTED
  * Relation classification: NOT STARTED
  * Model training: NOT STARTED
* **Next Action:** Phase 7 (Baseline Component Classifier).

---

## Planned Architecture

ARGUMAP is designed as a **Modular Monolith** for V1 to maximize architectural cohesion while eliminating microservice operational overhead:

```text
User
 ↓
React Frontend (Vite, TypeScript, Tailwind CSS, React Flow)
 ↓ (JSON REST API)
FastAPI Backend (Session & Run Management)
 ↓
NLP Preprocessing (Speaker Parser, spaCy Proposition Segmenter)
 ↓
Argument Component Classifier (Task 1: 6 Frozen Component Labels)
 ↓
Relation Classifier (Task 2: 4 Frozen Relation Labels with O(n²) Pair Pruning)
 ↓
Argument Graph (NetworkX MultiDiGraph & Topological Layout Engine)
 ↓
Analysis Engine (Heuristic Reasoning Rule Audits & Insights)
 ↓
Results Dashboard (Interactive React Flow Canvas & Insights Panel)
```

---

## End-to-End Data Flow

1. **Ingestion:** Raw text transcripts with speaker labels are submitted via `POST /api/analyze`.
2. **Speaker Parsing:** Regex parser identifies speaker turns and chronological sequencing.
3. **Unit Segmentation:** spaCy sentence and clause boundary heuristics extract discrete argumentative propositions.
4. **Component Classification:** Supervised model tags each unit with one of 6 frozen labels (`CLAIM`, `PREMISE`, `EVIDENCE`, `COUNTERARGUMENT`, `REBUTTAL`, `OTHER`).
5. **Candidate Pruning & Relation Extraction:** Windowing filters reduce $O(n^2)$ pairs; pairwise classifier predicts relationships (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`).
6. **Graph Compilation:** NetworkX compiles nodes and directed edges, computes topological layout coordinates, and validates graph structure.
7. **Insight Generation & Visualization:** Heuristic rules flag unsupported claims, unaddressed counterarguments, and clash metrics, serialized to JSON and rendered dynamically in React Flow.

---

## Machine Learning Pipeline

ARGUMAP decouples argument mining into two disciplined stages:
* **Task 1 (Component Classification):** Individual proposition $\rightarrow$ 6 frozen classes.
  * *Baseline:* TF-IDF (unigrams + bigrams) + Multinomial Logistic Regression (`scikit-learn`).
  * *Transformer Exploration:* Empirical benchmarking across candidate encoders (e.g., DeBERTa-v3, RoBERTa) using debate-level grouped splits to prevent topic/speaker leakage.
* **Task 2 (Relation Extraction):** Ordered pair $(u_A, u_B) \rightarrow$ 4 frozen classes (`SUPPORTS`, `ATTACKS`, `RESPONDS_TO`, `NO_RELATION`).
  * *Combinatorial Pruning:* 4-stage filter (temporal turn window, structural pruning, speaker heuristics, semantic similarity thresholding) eliminating $>90\%$ of non-viable candidate pairs.
  * *Classifier:* Cross-encoder evaluating paired propositions with class-imbalance focal/weighted loss.

---

## Frozen Taxonomy (V1)

### Component Labels
* `CLAIM`
* `PREMISE`
* `EVIDENCE`
* `COUNTERARGUMENT`
* `REBUTTAL`
* `OTHER`

### Relation Labels
* `SUPPORTS`
* `ATTACKS`
* `RESPONDS_TO`
* `NO_RELATION`

---

## Development Roadmap

ARGUMAP follows a disciplined 14-phase development lifecycle. Progress is tracked continuously in [TASKS.md](file:///c:/Users/hii/Downloads/ARGUMAP/TASKS.md).

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **Specification & Project Foundation** | **Completed** |
| **Phase 2** | **Architecture and Data Design** | **Completed** |
| **Phase 3** | Frontend Foundation | Pending |
| **Phase 4** | Backend Foundation | Pending |
| **Phase 5** | Dataset Research and Annotation | Pending |
| **Phase 6** | NLP Preprocessing | Pending |
| **Phase 7** | Baseline Component Classifier | Pending |
| **Phase 8** | Transformer Component Classifier | Pending |
| **Phase 9** | Relation Extraction | Pending |
| **Phase 10** | Argument Graph | Pending |
| **Phase 11** | Analysis Engine | Pending |
| **Phase 12** | Frontend / Backend / ML Integration | Pending |
| **Phase 13** | Testing and Evaluation | Pending |
| **Phase 14** | Deployment | Pending |

---

## Repository Structure

```text
ARGUMAP/
├── docs/               # Architecture, API specifications, and design records
├── data/               # Data store
│   ├── raw/            # Original immutable debate transcripts
│   ├── processed/      # Preprocessed and tokenized text data
│   ├── annotations/    # Ground-truth component and relation annotations
│   └── splits/         # Deterministic train/validation/test splits
├── models/             # ML model architectures, training routines, and checkpoints
├── tests/              # Automated test suites
├── .agents/            # Agent skills and developer automation tooling
│   └── skills/
├── PROJECT_SPEC.md     # Frozen V1 project specification
├── AGENTS.md           # Developer rules and AI agent guidelines
├── TASKS.md            # Detailed milestone roadmap and task tracker
├── README.md           # Project introduction and overview
└── .gitignore          # Version control ignore definitions
```

---

## 🚀 Running the Project Locally

### Prerequisites

Make sure you have the following installed:
- **Python 3.10+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **npm** (comes with Node.js)

---

### Step 1 — Clone & Navigate

```bash
git clone <your-repo-url>
cd ARGUMAP
```

---

### Step 2 — Start the Backend (Terminal 1)

```powershell
# Navigate to backend
cd backend

# Install Python dependencies
python -m pip install -r requirements.txt

# Run the FastAPI server
$env:PYTHONPATH = "."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

✅ Backend is ready when you see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

> API documentation available at: **http://127.0.0.1:8000/docs**

---

### Step 3 — Start the Frontend (Terminal 2)

Open a **new terminal window**, then:

```powershell
# Navigate to frontend
cd frontend

# Install Node dependencies (first time only)
npm install

# Start the development server
npx vite --port 5173
```

✅ Frontend is ready when you see:
```
  VITE v5.x.x  ready

  ➜  Local:   http://localhost:5173/
```

---

### Step 4 — Open in Browser

👉 Go to **[http://localhost:5173](http://localhost:5173)**

---

### How to Analyze a Debate

1. Click **"Analyze"** in the navbar
2. Paste a transcript using this format (or click **"Sample Debate"** to load one):
   ```
   A: We should invest in renewable energy. It is essential for our future.
   B: However, the cost of transition is too high. Many families cannot afford it.
   A: Studies show renewables create more jobs than fossil fuels.
   B: But fossil fuels still provide reliable baseload power.
   A: In fact, battery storage technology has advanced greatly.
   C: Both speakers make valid points, but we must consider economic impact.
   ```
3. Click **"Launch Reasoning Analysis"**
4. Watch the pipeline process your transcript in real time
5. Explore the **interactive argument graph** — drag nodes, filter by speaker or component type, inspect insights

---

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze` | Analyze a transcript — returns speakers, arguments, relations, insights |
| `GET` | `/api/analysis/{id}` | Retrieve a saved analysis run |
| `POST` | `/api/speak` | 🔊 Convert text to MP3 audio (voice feature) |
| `GET` | `/api/health` | Health check |
| `GET` | `/docs` | Interactive Swagger UI |

---

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run `python -m pip install -r requirements.txt` in `backend/` |
| Frontend shows "Backend Error" | Make sure the backend is running on port `8000` |
| `npx vite` not found | Run `npm install` inside the `frontend/` folder first |
| Port already in use | Kill the process using that port or change the port number |

---

## Contributor Guidelines

All contributors and AI agents must review [AGENTS.md](file:///c:/Users/hii/Downloads/ARGUMAP/AGENTS.md) and [PROJECT_SPEC.md](file:///c:/Users/hii/Downloads/ARGUMAP/PROJECT_SPEC.md) before submitting changes. Strict boundaries govern scope, security, and architectural separation.
