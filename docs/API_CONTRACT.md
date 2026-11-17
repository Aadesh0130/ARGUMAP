# ARGUMAP — REST API Contract Specification

* **Document Version:** 1.0.0
* **Status:** Initial API Contract Blueprint (Frozen for V1)
* **Base URL:** `/api`
* **Content-Type:** `application/json`

---

## 1. Overview & General Standards

The ARGUMAP backend exposes a RESTful API for debate transcript ingestion, asynchronous/synchronous pipeline analysis, graph retrieval, and reasoning insights.

### 1.1 HTTP Status Codes
* `200 OK`: Request succeeded and returned requested data.
* `201 Created`: Resource successfully created.
* `400 Bad Request`: Malformed payload or invalid input syntax.
* `404 Not Found`: Requested resource (debate or analysis run) does not exist.
* `422 Unprocessable Entity`: Semantic validation failure (e.g. empty transcript, missing speaker labels).
* `500 Internal Server Error`: Unhandled server-side exception.

### 1.2 Standard Error Response Envelope
All error responses adhere to the following schema:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Transcript does not contain valid speaker turn labels.",
    "details": [
      {
        "field": "raw_transcript",
        "issue": "Expected pattern 'Speaker <Name>: <Utterance>'"
      }
    ]
  }
}
```

---

## 2. API Endpoints

---

### 2.1 Health Check
`GET /api/health`

#### Purpose
Verify that the FastAPI service is healthy and the database is accessible.

#### Request
* **Method:** `GET`
* **Headers:** None
* **Body:** None

#### Response
* **Status Code:** `200 OK`
* **Response Body Example:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2026-09-24T14:30:00Z"
}
```

#### Possible Errors
* `500 Internal Server Error`: Database connection unavailable or server internal fault.

---

### 2.2 Create Debate
`POST /api/debates`

#### Purpose
Create a new debate session record with raw transcript text without immediately running ML inference.

#### Request
* **Method:** `POST`
* **Headers:** `Content-Type: application/json`
* **Request Body Example:**
```json
{
  "title": "AI in Education Academic Debate",
  "raw_transcript": "Speaker A: AI should be used in education because it enables personalized learning.\nSpeaker B: However, excessive dependence on AI can reduce independent thinking.\nSpeaker A: This risk can be reduced through teacher supervision."
}
```

#### Response
* **Status Code:** `201 Created`
* **Response Body Example:**
```json
{
  "debate_id": "deb_9f3a1e2b-8c4d-4e5f-a6b7-1c2d3e4f5a6b",
  "title": "AI in Education Academic Debate",
  "status": "PENDING",
  "created_at": "2026-09-24T14:31:00Z"
}
```

#### Possible Errors
* `422 Unprocessable Entity`: Missing `title` or empty `raw_transcript`.
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'raw_transcript' must not be empty.",
    "details": []
  }
}
```

---

### 2.3 Analyze Debate Transcript
`POST /api/analyze`

#### Purpose
Ingest transcript text (or reference an existing `debate_id`), execute the full 7-step analysis pipeline, and return the generated argument graph and insights.

#### Request
* **Method:** `POST`
* **Headers:** `Content-Type: application/json`
* **Request Body (Direct Transcript Ingestion):**
```json
{
  "title": "AI in Education Academic Debate",
  "raw_transcript": "Speaker A: AI should be used in education because it enables personalized learning.\nSpeaker B: However, excessive dependence on AI can reduce independent thinking.\nSpeaker A: This risk can be reduced through teacher supervision.",
  "options": {
    "include_other_components": false,
    "confidence_threshold": 0.50
  }
}
```

#### Response
* **Status Code:** `200 OK` (or `202 Accepted` if asynchronous task queue is configured)
* **Response Body Example:**
```json
{
  "analysis_id": "run_01h7x8z9-3b2c-4f1e-9a8d-7c6b5a4e3d2f",
  "debate_id": "deb_9f3a1e2b-8c4d-4e5f-a6b7-1c2d3e4f5a6b",
  "status": "COMPLETED",
  "model_version": "v1-baseline",
  "created_at": "2026-09-24T14:32:00Z",
  "completed_at": "2026-09-24T14:32:02Z",
  "summary": {
    "speaker_count": 2,
    "turn_count": 3,
    "argument_count": 3,
    "relation_count": 2,
    "insights_count": 2
  },
  "speakers": [
    { "id": "spk_01", "name": "Speaker A" },
    { "id": "spk_02", "name": "Speaker B" }
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

#### Possible Errors
* `400 Bad Request`: Transcript parsing failure (e.g. no speaker turn markers found).
* `422 Unprocessable Entity`: Validation error on request body.
* `500 Internal Server Error`: Pipeline failure during model inference.

---

### 2.4 Get Analysis Run by ID
`GET /api/analysis/{id}`

#### Purpose
Retrieve a previously executed analysis run, including its serialized argument graph and insights snapshot.

#### Request
* **Method:** `GET`
* **Path Parameter:** `id` (`UUID` or string identifier of analysis run)
* **Headers:** None
* **Body:** None

#### Response
* **Status Code:** `200 OK`
* **Response Body:** Returns the exact analysis payload detailed in Section 2.3.

#### Possible Errors
* `404 Not Found`:
```json
{
  "error": {
    "code": "ANALYSIS_NOT_FOUND",
    "message": "Analysis run 'run_invalid_id' does not exist."
  }
}
```

---

### 2.5 Get Debate Details
`GET /api/debates/{id}`

#### Purpose
Retrieve a debate session, its full transcript, associated speakers, turns, and history of analysis runs.

#### Request
* **Method:** `GET`
* **Path Parameter:** `id` (`UUID` of debate)
* **Headers:** None
* **Body:** None

#### Response
* **Status Code:** `200 OK`
* **Response Body Example:**
```json
{
  "debate_id": "deb_9f3a1e2b-8c4d-4e5f-a6b7-1c2d3e4f5a6b",
  "title": "AI in Education Academic Debate",
  "status": "COMPLETED",
  "created_at": "2026-09-24T14:31:00Z",
  "speakers": [
    { "id": "spk_01", "name": "Speaker A" },
    { "id": "spk_02", "name": "Speaker B" }
  ],
  "turns": [
    {
      "id": "trn_01",
      "speaker_id": "spk_01",
      "speaker_name": "Speaker A",
      "turn_order": 1,
      "text": "AI should be used in education because it enables personalized learning."
    },
    {
      "id": "trn_02",
      "speaker_id": "spk_02",
      "speaker_name": "Speaker B",
      "turn_order": 2,
      "text": "However, excessive dependence on AI can reduce independent thinking."
    },
    {
      "id": "trn_03",
      "speaker_id": "spk_01",
      "speaker_name": "Speaker A",
      "turn_order": 3,
      "text": "This risk can be reduced through teacher supervision."
    }
  ],
  "analysis_runs": [
    {
      "analysis_id": "run_01h7x8z9-3b2c-4f1e-9a8d-7c6b5a4e3d2f",
      "status": "COMPLETED",
      "model_version": "v1-baseline",
      "created_at": "2026-09-24T14:32:00Z",
      "completed_at": "2026-09-24T14:32:02Z"
    }
  ]
}
```

#### Possible Errors
* `404 Not Found`:
```json
{
  "error": {
    "code": "DEBATE_NOT_FOUND",
    "message": "Debate 'deb_invalid_id' does not exist."
  }
}
```
