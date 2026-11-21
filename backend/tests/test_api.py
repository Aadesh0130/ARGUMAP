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
    assert data["status"] == "READY"
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


def test_health_check_disconnected_db(client, monkeypatch):
    """Test GET /api/health accurately returns 503 and unhealthy when database is disconnected."""
    from app.api import health as health_module

    # Mock database check returning disconnected
    monkeypatch.setattr(
        health_module,
        "check_db_connection",
        lambda: {"connected": False, "dialect": "unknown", "error": "Connection refused"},
    )

    response = client.get("/api/health")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "disconnected"
    assert data["database_dialect"] == "unknown"
    # Ensure no credentials or raw error traceback are leaked
    assert "error" not in data
    assert "Connection refused" not in str(data)


def test_analyze_and_retrieve_consistency(client):
    """Test POST /api/analyze returns real arguments, relations, and insights,
    and GET /api/analysis/{id} returns the exact matching data and summary counts.
    """
    payload = {
        "title": "Renewable Energy Policy",
        "raw_transcript": (
            "Speaker A: Solar energy reduces carbon emissions significantly.\n"
            "Speaker B: However, battery storage technology is currently too expensive.\n"
            "Speaker A: Government subsidies can lower the initial capital expenditure."
        ),
    }
    post_res = client.post("/api/analyze", json=payload)
    assert post_res.status_code == status.HTTP_200_OK
    post_data = post_res.json()

    analysis_id = post_data["analysis_id"]
    debate_id = post_data["debate_id"]
    assert post_data["status"] == "completed"
    assert len(post_data["speakers"]) == 2
    assert len(post_data["arguments"]) >= 3
    assert len(post_data["relations"]) >= 1
    assert "summary" in post_data

    # Verify summary count matches actual arrays
    post_summary = post_data["summary"]
    assert post_summary["argument_count"] == len(post_data["arguments"])
    assert post_summary["relation_count"] == len(post_data["relations"])
    assert post_summary["insights_count"] == len(post_data["insights"])
    assert post_summary["speaker_count"] == len(post_data["speakers"])

    # Retrieve analysis snapshot
    get_res = client.get(f"/api/analysis/{analysis_id}")
    assert get_res.status_code == status.HTTP_200_OK
    get_data = get_res.json()

    assert get_data["analysis_id"] == analysis_id
    assert get_data["debate_id"] == debate_id
    assert get_data["status"] == "completed"
    assert get_data["model_version"] == post_data["model_version"]

    # Verify identical arguments
    assert len(get_data["arguments"]) == len(post_data["arguments"])
    post_arg_ids = [a["id"] for a in post_data["arguments"]]
    get_arg_ids = [a["id"] for a in get_data["arguments"]]
    assert get_arg_ids == post_arg_ids

    # Verify identical relations
    assert len(get_data["relations"]) == len(post_data["relations"])
    post_rel_ids = [r["id"] for r in post_data["relations"]]
    get_rel_ids = [r["id"] for r in get_data["relations"]]
    assert get_rel_ids == post_rel_ids

    # Verify identical insights
    assert len(get_data["insights"]) == len(post_data["insights"])
    post_ins_types = [i["type"] for i in post_data["insights"]]
    get_ins_types = [i["type"] for i in get_data["insights"]]
    assert get_ins_types == post_ins_types

    # Verify summary consistency in GET
    get_summary = get_data["summary"]
    assert get_summary["argument_count"] == len(get_data["arguments"])
    assert get_summary["relation_count"] == len(get_data["relations"])
    assert get_summary["insights_count"] == len(get_data["insights"])
    assert get_summary == post_summary


def test_analyze_empty_transcript_returns_422(client):
    """Test POST /api/analyze with empty or whitespace transcript returns 422 standard error."""
    response = client.post("/api/analyze", json={"title": "Empty", "raw_transcript": "   \n\t  "})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "EMPTY_TRANSCRIPT"


def test_persistence_rollback_on_failure(client, monkeypatch):
    """Verify that if an error occurs during analysis persistence, the transaction
    rolls back cleanly and does not leave orphaned records.
    """
    import pytest
    from app.services.debate_service import DebateService
    from app.models.entities import Debate
    from app.db.session import SessionLocal

    def failing_save(*args, **kwargs):
        # Force a database failure during transaction
        db = kwargs.get("db") or args[0]
        db.add(Debate(id="orphan-probe-id", title="Should Roll Back", raw_transcript="test", status="PENDING"))
        db.flush()
        db.rollback()
        raise RuntimeError("Simulated mid-transaction persistence error")

    monkeypatch.setattr(DebateService, "save_full_analysis", failing_save)

    payload = {
        "title": "Rollback Test",
        "raw_transcript": "Speaker A: This should trigger a rollback.\nSpeaker B: Agreed.",
    }
    with pytest.raises(RuntimeError):
        client.post("/api/analyze", json=payload)

    # Check database state using a fresh session: orphan-probe-id must NOT exist
    with SessionLocal() as check_db:
        orphan = check_db.query(Debate).filter(Debate.id == "orphan-probe-id").first()
        assert orphan is None


def test_cors_options_and_headers(client):
    """Verify that requests from allowed origins receive appropriate CORS headers."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/analyze", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
