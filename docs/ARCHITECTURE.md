# ARGUMAP — System Architecture Document

* **Document Version:** 1.0.0
* **Status:** Approved Architecture Blueprint
* **System Design Pattern:** Modular Monolith (Single-service backend, decoupled SPA frontend)

---

## 1. Executive Architectural Overview

ARGUMAP is architected as an end-to-end, high-precision argument mining and visualization platform. The system ingests text-based debate transcripts, segments them into proposition-level units, classifies their dialectical components, extracts relational links, synthesizes a directed argument multigraph, and exposes actionable reasoning insights through an interactive visual canvas.

### 1.1 Architectural Pattern: Modular Monolith
To prevent unnecessary operational complexity, distributed transaction overhead, and premature microservice fragmentation, ARGUMAP V1 is built as a **Modular Monolith**:
* **Frontend:** Single Page Application (SPA) built with React, TypeScript, and Vite, utilizing React Flow for node-link graph visualization.
* **Backend:** Asynchronous Python service using FastAPI, structured into cleanly decoupled internal modules (API router, preprocessing, ML inference orchestration, graph compilation, database persistence).
* **Database:** Single relational PostgreSQL instance handling operational records, normalized discourse turns, argument nodes, relation edges, and analysis runs.

```
┌────────────────────────────────────────────────────────────────────────┐
│                                 USER                                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Browser (HTTP / WebSocket)
┌───────────────────────────────────▼────────────────────────────────────┐
│                       React SPA Frontend (Vite)                        │
│   • Transcript Ingestion UI          • Interactive React Flow Canvas   │
│   • Component/Speaker Filter Hub     • Structural Insights Panel       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON REST API
┌───────────────────────────────────▼────────────────────────────────────┐
│                        FastAPI Backend Engine                          │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                      API Routing & Validation                  │   │
│   │   • /api/debates                 • /api/analyze                │   │
│   │   • /api/analysis/{id}           • /api/health                 │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│   ┌───────────────────────────────▼────────────────────────────────┐   │
│   │                    NLP Preprocessing Pipeline                  │   │
│   │   • Speaker Turn Parser          • Proposition Segmenter       │   │
│   │   • spaCy Sentence Boundary      • Text Normalizer             │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Discrete Argument Units            │
│   ┌───────────────────────────────▼────────────────────────────────┐   │
│   │                    ML Classification Engine                    │   │
│   │   • Task 1: Component Classifier (6 Frozen Labels)             │   │
│   │   • Candidate Pair Pruning & Windowing Filter                  │   │
│   │   • Task 2: Pairwise Relation Classifier (4 Frozen Labels)     │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Labeled Units & Relations          │
│   ┌───────────────────────────────▼────────────────────────────────┐   │
│   │                   Graph Processing & Topology                  │   │
│   │   • NetworkX Directed Multigraph Construction                  │   │
│   │   • Cycle Detection & Validation • Hierarchical Layout Calc    │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Graph Structure                    │
│   ┌───────────────────────────────▼────────────────────────────────┐   │
│   │                    Structural Analysis Engine                  │   │
│   │   • Unsupported Claim Detector   • Unanswered Counterattacks   │   │
│   │   • Rebuttal / Clash Quantifier  • Speaker Balance Metrics     │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │ Serialized Graph + Insights        │
│   ┌───────────────────────────────▼────────────────────────────────┐   │
│   │                    Persistence & ORM Layer                     │   │
│   │   • SQLAlchemy v2                • Alembic Migrations          │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │ SQL
┌───────────────────────────────────▼────────────────────────────────────┐
│                         PostgreSQL Database                            │
│   • debates  • speakers  • turns  • arguments  • relations  • runs     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Responsibilities & Separation of Concerns

### 2.1 Frontend Layer (`frontend/`)
* **Technology:** React 18+, TypeScript, Vite, Tailwind CSS, React Flow.
* **Responsibilities:**
  * Provide transcript entry interfaces (raw paste, text file upload, and sample debates).
  * Render an interactive node-link argument graph using React Flow with custom nodes representing argument components and directed edges representing relations.
  * Offer interactive exploration: zoom/pan, node selection, filtering by speaker, filtering by component type (`CLAIM`, `PREMISE`, etc.), and edge path highlighting.
  * Display a dedicated structural reasoning panel summarizing anomalies (unsupported claims, unanswered counterarguments).
  * **Strict Boundary:** The frontend never executes linguistic rules, graph topological validations, or classification algorithms. It acts purely as a consumer of backend API payloads.

### 2.2 Backend & API Gateway Layer (`backend/app/api/`)
* **Technology:** Python 3.10+, FastAPI, Pydantic v2.
* **Responsibilities:**
  * Expose RESTful endpoints adhering to [API_CONTRACT.md](file:///c:/Users/hii/Downloads/ARGUMAP/docs/API_CONTRACT.md).
  * Validate incoming requests against strict Pydantic schemas.
  * Orchestrate the lifecycle of an analysis run (queued $\rightarrow$ processing $\rightarrow$ completed $\rightarrow$ failed).
  * Handle HTTP errors, exceptions, and structured JSON error envelopes.
  * Serve health check and metadata introspection endpoints.

### 2.3 NLP Preprocessing Layer (`backend/app/nlp/`)
* **Technology:** spaCy (`en_core_web_sm` / `en_core_web_md`), Regular Expressions.
* **Responsibilities:**
  * **Speaker Turn Parsing:** Decompose continuous transcript text into discrete chronological turns, extracting speaker names and raw utterances.
  * **Proposition / Unit Segmentation:** Split multi-sentence turns into fine-grained argumentative units. Standard sentence boundaries are segmented and enriched with clause-level discourse marker splitting (e.g., identifying causal conjuncts such as *because*, *therefore*, *however*).
  * **Normalization:** Sanitize whitespace, strip non-standard formatting, and calculate token-level character offsets relative to original turns.

### 2.4 ML Classification Layer (`backend/app/ml/`)
* **Technology:** PyTorch, Hugging Face Transformers / scikit-learn.
* **Responsibilities:**
  * **Component Classification (Task 1):** Classify each segmented argument unit into exactly one of the 6 frozen labels: `CLAIM`, `PREMISE`, `EVIDENCE`, `COUNTERARGUMENT`, `REBUTTAL`, or `OTHER`. Outputs the predicted class along with a confidence probability score ($[0.0, 1.0]$).
  * **Candidate Pair Generation & Pruning:** Prevent an $O(n^2)$ combinatorial explosion across long debates by applying intelligent temporal, speaker-based, and semantic windowing.
  * **Relation Extraction (Task 2):** Classify pruned candidate pairs $(u_i, u_j)$ into one of the 4 frozen relation labels: `SUPPORTS`, `ATTACKS`, `RESPONDS_TO`, or `NO_RELATION`, outputting directional link probabilities.
  * **Local Model Wrappers:** Encapsulate inference pipelines behind clean interfaces (`predict_components()`, `predict_relations()`) so classical baselines and deep transformer checkpoints can be swapped transparently without modifying upstream services.

### 2.5 Graph Processing & Topological Engine (`backend/app/graph/`)
* **Technology:** NetworkX.
* **Responsibilities:**
  * Ingest classified argument units as graph nodes and predicted relational links as directed edges into a `networkx.MultiDiGraph`.
  * Validate structural integrity: detect self-loops, analyze connectivity, detect cycles, and identify weakly connected components.
  * Compute graph layout coordinates (hierarchical Sugiyama-style or force-directed coordinates) to feed directly into React Flow node positions.
  * Serialize graph topology into the standardized ML-to-Graph JSON format.

### 2.6 Structural Analysis Engine (`backend/app/analysis/`)
* **Technology:** Pure Python graph algorithms built over NetworkX.
* **Responsibilities:**
  * Execute deterministic heuristic rules over the graph topology to identify reasoning patterns:
    1. **Unsupported Claims:** Nodes with `component_type == CLAIM` having zero incoming `SUPPORTS` edges.
    2. **Unanswered Counterarguments:** Nodes with `component_type == COUNTERARGUMENT` having zero incoming `REBUTTAL` or `RESPONDS_TO` edges.
    3. **Dialectical Clash:** Count and ratio of cross-speaker `ATTACKS` and `RESPONDS_TO` edges relative to total arguments.
    4. **Orphan Evidences:** Nodes with `component_type == EVIDENCE` that do not link to any `PREMISE` or `CLAIM`.
  * Synthesize structured, human-readable insights for frontend display.

### 2.7 Persistence & Data Access Layer (`backend/app/db/`)
* **Technology:** PostgreSQL 15+, SQLAlchemy v2 (async), Alembic.
* **Responsibilities:**
  * Persist debate metadata, speaker identities, turns, segmented arguments, relation edges, and execution run logs.
  * Guarantee transactional consistency via foreign key relationships and cascade deletes.
  * Enable rapid retrieval of previously analyzed debates and graph topologies without re-running ML inference.

---

## 3. End-to-End Data Flow

The complete journey of a transcript from initial ingestion to interactive visualization proceeds through 7 explicit pipeline stages:

```
[Raw Transcript]
       │
       ▼
Stage 1: Ingestion & Record Creation (Backend / DB)
  • Transcript string submitted via POST /api/analyze
  • Debate & AnalysisRun records initialized with status = "PROCESSING"
       │
       ▼
Stage 2: Speaker Parsing & Turn Normalization (NLP)
  • Regex extracts speaker labels: "Speaker A", "Speaker B"
  • Raw text chunked into ordered `Turn` records with turn indices
       │
       ▼
Stage 3: Argument Unit Segmentation (NLP)
  • spaCy pipeline processes each turn into discrete proposition units
  • Character offsets (start_char, end_char) tracked for text highlighting
       │
       ▼
Stage 4: Component Classification (ML Task 1)
  • Unit texts fed to Component Classifier (Baseline or Fine-tuned Transformer)
  • Each unit tagged: CLAIM, PREMISE, EVIDENCE, COUNTERARGUMENT, REBUTTAL, OTHER
  • Confidence score assigned to each unit
       │
       ▼
Stage 5: Candidate Generation & Relation Extraction (ML Task 2)
  • Windowing algorithm filters out distant or invalid pairs
  • Candidate pairs (Unit_A, Unit_B) evaluated by Pairwise Relation Classifier
  • Relations assigned: SUPPORTS, ATTACKS, RESPONDS_TO (NO_RELATION pruned)
       │
       ▼
Stage 6: Graph Compilation & Layout Computation (Graph Engine)
  • NetworkX graph assembled from units (nodes) and relations (edges)
  • Cycle checks and topological layout coordinates computed (x, y)
  • Graph translated into React Flow compatible node/edge structure
       │
       ▼
Stage 7: Structural Reasoning & Insight Extraction (Analysis Engine)
  • Heuristics audit graph topology for unsupported claims and unanswered attacks
  • Insights compiled with target node IDs and severity levels
  • Full payload saved to PostgreSQL; AnalysisRun status = "COMPLETED"
  • JSON payload dispatched to React Frontend for interactive rendering
```

---

## 4. ML-to-Graph Internal Data Format (React Flow Bridge)

To ensure seamless interoperability between the Python NetworkX backend and the React Flow frontend canvas, the backend serializes graph outputs into a standard, typed JSON schema:

```json
{
  "debate_id": "deb_01h7x8q4",
  "analysis_id": "run_01h7x8z9",
  "status": "COMPLETED",
  "metadata": {
    "title": "AI in Education Academic Debate",
    "turn_count": 3,
    "argument_count": 3,
    "relation_count": 2
  },
  "speakers": [
    {
      "id": "spk_01",
      "name": "Speaker A"
    },
    {
      "id": "spk_02",
      "name": "Speaker B"
    }
  ],
  "arguments": [
    {
      "id": "arg_01",
      "turn_id": "trn_01",
      "speaker_id": "spk_01",
      "text": "AI should be used in education",
      "component_type": "CLAIM",
      "confidence": 0.94,
      "turn_order": 1,
      "graph_node": {
        "id": "arg_01",
        "type": "argumentNode",
        "position": { "x": 250, "y": 50 },
        "data": {
          "label": "AI should be used in education",
          "component_type": "CLAIM",
          "speaker_name": "Speaker A",
          "confidence": 0.94
        }
      }
    },
    {
      "id": "arg_02",
      "turn_id": "trn_01",
      "speaker_id": "spk_01",
      "text": "it enables personalized learning",
      "component_type": "PREMISE",
      "confidence": 0.91,
      "turn_order": 1,
      "graph_node": {
        "id": "arg_02",
        "type": "argumentNode",
        "position": { "x": 100, "y": 180 },
        "data": {
          "label": "it enables personalized learning",
          "component_type": "PREMISE",
          "speaker_name": "Speaker A",
          "confidence": 0.91
        }
      }
    },
    {
      "id": "arg_03",
      "turn_id": "trn_02",
      "speaker_id": "spk_02",
      "text": "excessive dependence on AI can reduce independent thinking",
      "component_type": "COUNTERARGUMENT",
      "confidence": 0.88,
      "turn_order": 2,
      "graph_node": {
        "id": "arg_03",
        "type": "argumentNode",
        "position": { "x": 400, "y": 180 },
        "data": {
          "label": "excessive dependence on AI can reduce independent thinking",
          "component_type": "COUNTERARGUMENT",
          "speaker_name": "Speaker B",
          "confidence": 0.88
        }
      }
    }
  ],
  "relations": [
    {
      "id": "rel_01",
      "source_argument_id": "arg_02",
      "target_argument_id": "arg_01",
      "relation_type": "SUPPORTS",
      "confidence": 0.92,
      "graph_edge": {
        "id": "rel_01",
        "source": "arg_02",
        "target": "arg_01",
        "type": "argumentEdge",
        "label": "SUPPORTS",
        "animated": false,
        "data": {
          "relation_type": "SUPPORTS",
          "confidence": 0.92
        }
      }
    },
    {
      "id": "rel_02",
      "source_argument_id": "arg_03",
      "target_argument_id": "arg_01",
      "relation_type": "ATTACKS",
      "confidence": 0.86,
      "graph_edge": {
        "id": "rel_02",
        "source": "arg_03",
        "target": "arg_01",
        "type": "argumentEdge",
        "label": "ATTACKS",
        "animated": true,
        "data": {
          "relation_type": "ATTACKS",
          "confidence": 0.86
        }
      }
    }
  ],
  "insights": [
    {
      "id": "ins_01",
      "type": "UNANSWERED_COUNTERARGUMENT",
      "severity": "WARNING",
      "message": "Counterargument by Speaker B ('excessive dependence on AI...') has no detected response.",
      "related_argument_ids": ["arg_03"]
    },
    {
      "id": "ins_02",
      "type": "DIRECT_CLASH",
      "severity": "INFO",
      "message": "Speaker B directly attacked Speaker A's central claim.",
      "related_argument_ids": ["arg_03", "arg_01"]
    }
  ]
}
```

---

## 5. Non-Functional Architecture Requirements

1. **Determinism & Reproducibility:** Fixed random seeds across any probabilistic ML inference step; identical transcript inputs must yield identical node-edge topological outputs.
2. **Sub-Second Graph Processing:** For typical debate transcripts (up to 50 turns / 150 argument units), NLP segmentation, pair pruning, graph building, and layout calculations must complete in $< 1.5$ seconds (excluding deep transformer forward pass latency).
3. **Graceful Degradation:** If a model predicts zero non-trivial relations, the graph must still render all isolated argument nodes without error, clearly flagging orphan components.
4. **Modularity:** The ML inference pipeline can be run in offline batch mode (via CLI scripts during training and evaluation) or online mode (wrapped in FastAPI service) using the exact same underlying Python modules.
