"""Comprehensive API Endpoint Tests for ARGUMAP Backend."""

from fastapi import status


def test_root_endpoint(client):
    """Test GET / returns project metadata and status."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["project"] == "ARGUMAP"
    assert data["status"] == "running"
    assert "documentation" in data
    assert data["api_endpoints"]["health"] == "/api/health"


def test_health_check_endpoint(client):
    """Test GET /api/health returns service health and db connectivity."""
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ARGUMAP"
    assert "database" in data
    assert "timestamp" in data


def test_create_debate_success(client):
    """Test POST /api/debates successfully creates a debate session and parses turns."""
    payload = {
        "title": "Universal Healthcare Debate",
        "raw_transcript": (
            "Speaker A: Universal healthcare ensures equitable access to treatment.\n"
            "Speaker B: However, single-payer systems lead to increased wait times.\n"
            "Speaker A: Targeted funding can eliminate surgical backlogs."
        ),
    }
    response = client.post("/api/debates", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "debate_id" in data
    assert data["title"] == payload["title"]
    assert data["status"] in ("PENDING", "READY")
    assert "created_at" in data

    # Verify debate details can be retrieved
    debate_id = data["debate_id"]
    get_res = client.get(f"/api/debates/{debate_id}")
    assert get_res.status_code == status.HTTP_200_OK
    debate_data = get_res.json()
    assert debate_data["title"] == payload["title"]
    assert len(debate_data["speakers"]) == 2
    assert len(debate_data["turns"]) == 3
    assert debate_data["turns"][0]["speaker_name"] == "Speaker A"
    assert debate_data["turns"][1]["speaker_name"] == "Speaker B"


def test_create_debate_invalid_payload(client):
    """Test POST /api/debates with missing required fields returns 422 standard error."""
    response = client.post("/api/debates", json={"title": "Missing Transcript"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert len(data["error"]["details"]) > 0


def test_create_debate_empty_transcript(client):
    """Test POST /api/debates with empty whitespace transcript returns 422 error."""
    response = client.post("/api/debates", json={"title": "Empty", "raw_transcript": "   "})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EMPTY_TRANSCRIPT"


def test_get_debate_not_found(client):
    """Test GET /api/debates/{id} with non-existent ID returns 404 standard error."""
    response = client.get("/api/debates/non_existent_debate_uuid")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DEBATE_NOT_FOUND"


def test_analyze_transcript(client):
    """Test POST /api/analyze executes full NLP pipeline and returns completed analysis."""
    payload = {
        "title": "AI in Education Academic Debate",
        "raw_transcript": (
            "Speaker A: AI should be used in education because it enables personalized learning.\n"
            "Speaker B: However, excessive dependence on AI can reduce independent thinking.\n"
            "Speaker A: This risk can be reduced through teacher supervision."
        ),
        "options": {
            "include_other_components": False,
            "confidence_threshold": 0.50,
        },
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "analysis_id" in data
    assert "debate_id" in data
    assert data["status"] == "completed"
    assert len(data["speakers"]) == 2
    assert len(data["arguments"]) >= 3
    assert data["summary"]["turn_count"] == 3
    assert data["summary"]["speaker_count"] == 2
    assert data["summary"]["argument_count"] >= 3

    # Verify analysis run can be retrieved
    analysis_id = data["analysis_id"]
    get_run_res = client.get(f"/api/analysis/{analysis_id}")
    assert get_run_res.status_code == status.HTTP_200_OK
    run_data = get_run_res.json()
    assert run_data["analysis_id"] == analysis_id
    assert run_data["status"] == "completed"


def test_get_analysis_not_found(client):
    """Test GET /api/analysis/{id} with non-existent ID returns 404 standard error."""
    response = client.get("/api/analysis/non_existent_run_uuid")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ANALYSIS_NOT_FOUND"
