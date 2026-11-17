"""Tests for the ARGUMAP Human Annotation Workspace.

Verifies:
1. Independent loading of packages for Annotator A and Annotator B.
2. Template immutability: original unannotated templates are never modified.
3. Safe persistence: saving and resuming preserves all decisions without lost data.
4. Exact preservation of unit text, character offsets, turn IDs, and stable identifiers.
5. Strict enforcement of frozen component and relation taxonomies.
6. Preservation of source and target directionality in relation pairs.
7. Override justification requirement on out-of-window links (turn_distance > 3).
8. Rejection of incomplete packages for export or production validation.
9. Completed exports remain rejected as gold by the model training gatekeeper.
10. Strict annotator isolation with zero data or note leakage.
11. REST API contract and FastAPI endpoint behavior.
"""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

from scripts.annotation.workspace_session import WorkspaceSession, VALID_ANNOTATORS
from scripts.annotation.annotation_workspace import create_annotation_app
from scripts.dataset.validate_annotations import (
    FROZEN_COMPONENT_LABELS,
    FROZEN_RELATION_LABELS,
)
from ml.data.dataset_loader import check_gold_dataset_readiness

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = PROJECT_ROOT / "data" / "annotations" / "pilot"


def compute_file_sha256(path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestWorkspaceSession:
    """Tests for the WorkspaceSession state manager."""

    def test_correct_loading_of_both_packages(self):
        """Annotator A and Annotator B packages load correctly with exact unit and relation counts."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"

            session_a = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )
            assert session_a.annotator_id == "annotator_A"
            assert len(session_a.get_units()) == 36
            assert len(session_a.data["relations"]) == 1260

            session_b = WorkspaceSession(
                annotator_id="annotator_B",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )
            assert session_b.annotator_id == "annotator_B"
            assert len(session_b.get_units()) == 36
            assert len(session_b.data["relations"]) == 1260

            # Initial unannotated state
            summary_a = session_a.get_summary()
            assert summary_a["labeled_units"] == 0
            assert summary_a["labeled_relations"] == 0
            assert not summary_a["is_complete"]

    def test_original_template_immutability(self):
        """Original unannotated pilot packages must remain byte-for-byte immutable."""
        tmpl_a = PILOT_DIR / "hansard_2023_pilot_annotator_A.json"
        hash_before = compute_file_sha256(tmpl_a)

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )

            # Perform mutations in session
            session.update_unit("u_0010", "CLAIM", confidence=0.9, note="Test note")
            session.update_relation(
                "u_0010", "u_0011", "SUPPORTS", confidence=0.85, note="Test rel note"
            )
            session.save_working_copy()

        hash_after = compute_file_sha256(tmpl_a)
        assert hash_before == hash_after, "Template file was modified! Immutability violated."

    def test_saving_and_resuming_without_lost_labels(self):
        """A session can be stopped and resumed without loss of any annotated labels or notes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"

            # Session 1: Make labels and save
            sess1 = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )
            sess1.update_unit("u_0010", "CLAIM", confidence=0.95, note="Key thesis on frontier risk")
            sess1.update_unit("u_0011", "PREMISE", confidence=0.90, note="Supporting syllogism")
            sess1.update_relation(
                "u_0011", "u_0010", "SUPPORTS", confidence=0.88, note="Direct premise grounding"
            )
            sess1.save_working_copy()

            # Session 2: Re-open from same workspace directory
            sess2 = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )

            u10 = sess2.get_unit("u_0010")
            assert u10["component_label"] == "CLAIM"
            assert u10["confidence"] == 0.95
            assert u10["note"] == "Key thesis on frontier risk"

            u11 = sess2.get_unit("u_0011")
            assert u11["component_label"] == "PREMISE"
            assert u11["confidence"] == 0.90
            assert u11["note"] == "Supporting syllogism"

            rel = sess2.get_relation("u_0011", "u_0010")
            assert rel["relation_label"] == "SUPPORTS"
            assert rel["confidence"] == 0.88
            assert rel["note"] == "Direct premise grounding"

            summary = sess2.get_summary()
            assert summary["labeled_units"] == 2
            assert summary["labeled_relations"] == 1

    def test_exact_preservation_of_unit_text_ids_and_offsets(self):
        """Unit text, offsets, and speaker metadata must remain perfectly intact after labeling."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
            )

            original_unit = copy.deepcopy(session.get_unit("u_0010"))
            session.update_unit("u_0010", "CLAIM", confidence=1.0)
            updated_unit = session.get_unit("u_0010")

            # Invariant fields must not mutate
            assert updated_unit["unit_id"] == original_unit["unit_id"]
            assert updated_unit["unit_text"] == original_unit["unit_text"]
            assert updated_unit["char_start"] == original_unit["char_start"]
            assert updated_unit["char_end"] == original_unit["char_end"]
            assert updated_unit["turn_id"] == original_unit["turn_id"]
            assert updated_unit["turn_index"] == original_unit["turn_index"]
            assert updated_unit["speaker_id"] == original_unit["speaker_id"]

    def test_strict_frozen_labels_enforcement(self):
        """Only frozen component and relation labels are accepted; non-taxonomy labels are rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
            )

            # Valid component labels must succeed
            for lbl in FROZEN_COMPONENT_LABELS:
                u = session.update_unit("u_0010", lbl)
                assert u["component_label"] == lbl

            # Invalid component label must raise ValueError
            with pytest.raises(ValueError, match="Invalid component label"):
                session.update_unit("u_0010", "OPINION")

            with pytest.raises(ValueError, match="Invalid component label"):
                session.update_unit("u_0010", "MAJOR_CLAIM")

            # Valid relation labels must succeed
            for lbl in FROZEN_RELATION_LABELS:
                r = session.update_relation("u_0010", "u_0011", lbl)
                assert r["relation_label"] == lbl

            # Invalid relation label must raise ValueError
            with pytest.raises(ValueError, match="Invalid relation label"):
                session.update_relation("u_0010", "u_0011", "CONTRADICTS")

            with pytest.raises(ValueError, match="Invalid relation label"):
                session.update_relation("u_0010", "u_0011", "AGREES")

    def test_relation_directionality_preservation(self):
        """Assigning relation (s -> t) preserves exact directional orientation and does not flip (t -> s)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
            )

            # Label forward edge (u_0010 -> u_0011) as ATTACKS
            session.update_relation("u_0010", "u_0011", "ATTACKS", confidence=0.9)
            rel_fwd = session.get_relation("u_0010", "u_0011")
            assert rel_fwd["relation_label"] == "ATTACKS"
            assert rel_fwd["source_unit_id"] == "u_0010"
            assert rel_fwd["target_unit_id"] == "u_0011"

            # Check that reverse edge (u_0011 -> u_0010) is unaffected
            rel_rev = session.get_relation("u_0011", "u_0010")
            assert rel_rev["relation_label"] is None
            assert rel_rev["source_unit_id"] == "u_0011"
            assert rel_rev["target_unit_id"] == "u_0010"

    def test_out_of_window_override_justification_requirement(self):
        """Out-of-window links (turn_distance > 3) strictly require an explanatory override note."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
            )

            # Link between Turn 28 (u_0902) and Turn 1 (u_0010) has turn_distance = 27 > 3
            rel = session.get_relation("u_0902", "u_0010")
            assert rel["turn_distance"] > 3
            assert rel["is_override"] is True

            # Attempting to assign label without note (or empty note) must fail
            with pytest.raises(ValueError, match="requires an explanatory override note justification"):
                session.update_relation("u_0902", "u_0010", "RESPONDS_TO", note="")

            # Providing an explanatory note must succeed
            updated = session.update_relation(
                "u_0902", "u_0010", "RESPONDS_TO", note="Minister directly answers Lord Ravensdale on compute"
            )
            assert updated["relation_label"] == "RESPONDS_TO"
            assert updated["is_override"] is True
            assert updated["note"] == "Minister directly answers Lord Ravensdale on compute"

    def test_incomplete_package_cannot_be_exported(self):
        """Exporting a partially labeled package must fail and return an informative error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )

            # Label only 1 unit and 1 relation
            session.update_unit("u_0010", "CLAIM")
            session.update_relation("u_0010", "u_0011", "SUPPORTS")

            success, msg, path = session.export_completed_package()
            assert not success
            assert "Cannot export: Package is incomplete" in msg
            assert path is None
            assert not (subm_dir / "hansard_2023_pilot_annotator_A.completed.json").exists()

    def test_completed_export_rejected_as_gold_until_adjudication(self):
        """Even a fully labeled pilot package export remains rejected by the model training gatekeeper."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"
            session = WorkspaceSession(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )

            # Label all 36 units
            for u in session.data["units"]:
                u["component_label"] = "PREMISE"
                u["confidence"] = 1.0

            # Label all 1,260 relations
            for r in session.data["relations"]:
                r["relation_label"] = "NO_RELATION"
                r["confidence"] = 1.0
                if r["turn_distance"] > 3 and not r.get("note"):
                    r["note"] = "[OVERRIDE] Cross-debate response"

            # Export must now succeed
            success, msg, out_path = session.export_completed_package()
            assert success, f"Export failed: {msg}"
            assert out_path.exists()

            # Verify exported file status
            with open(out_path, "r", encoding="utf-8") as f:
                exported_doc = json.load(f)
            assert exported_doc["status"] == "COMPLETED_INDEPENDENT_ANNOTATION"

            # Verify that model training gatekeeper STILL rejects the pilot submissions as gold data
            annot_root = PROJECT_ROOT / "data" / "annotations"
            is_ready, reason, cleared = check_gold_dataset_readiness(annot_root)
            assert not is_ready
            assert "Model training blocked" in reason
            assert len(cleared) == 0

    def test_annotator_isolation_and_no_leakage(self):
        """Annotator A cannot load or tamper with Annotator B's session or working data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"

            # Create an Annotator B working file
            work_dir.mkdir(parents=True, exist_ok=True)
            b_file = work_dir / "hansard_2023_pilot_annotator_B.working.json"
            b_data = {"annotator_id": "annotator_B", "status": "IN_PROGRESS", "units": [], "relations": []}
            with open(b_file, "w", encoding="utf-8") as f:
                json.dump(b_data, f)

            # If someone creates an annotator_A session pointing to an annotator_B file, it must raise ValueError
            a_file = work_dir / "hansard_2023_pilot_annotator_A.working.json"
            # Simulate tampering: copy B file to A path
            with open(a_file, "w", encoding="utf-8") as f:
                json.dump(b_data, f)

            with pytest.raises(ValueError, match="Integrity violation"):
                WorkspaceSession(
                    annotator_id="annotator_A",
                    workspace_dir=work_dir,
                    template_dir=PILOT_DIR,
                    submissions_dir=subm_dir,
                )


class TestWorkspaceFastAPI:
    """Tests for the local FastAPI web workspace endpoints."""

    @pytest.fixture
    def test_client(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "workspace"
            subm_dir = Path(tmp_dir) / "submissions"
            app = create_annotation_app(
                annotator_id="annotator_A",
                workspace_dir=work_dir,
                template_dir=PILOT_DIR,
                submissions_dir=subm_dir,
            )
            yield TestClient(app)

    def test_get_root_serves_html(self, test_client):
        res = test_client.get("/")
        assert res.status_code == 200
        assert "ARGUMAP — Human Annotation Workspace" in res.text
        assert "annotator_A" in res.text or "annotator-badge" in res.text

    def test_get_session_summary(self, test_client):
        res = test_client.get("/api/session")
        assert res.status_code == 200
        data = res.json()
        assert data["annotator_id"] == "annotator_A"
        assert data["total_units"] == 36
        assert data["total_relations"] == 1260

    def test_units_endpoints(self, test_client):
        # List units
        res = test_client.get("/api/units")
        assert res.status_code == 200
        units = res.json()
        assert len(units) == 36

        # Get specific unit
        res = test_client.get("/api/units/u_0010")
        assert res.status_code == 200
        assert res.json()["unit_id"] == "u_0010"

        # Update unit label
        payload = {"label": "CLAIM", "confidence": 0.95, "note": "Key stance"}
        res = test_client.post("/api/units/u_0010", json=payload)
        assert res.status_code == 200
        updated = res.json()
        assert updated["component_label"] == "CLAIM"
        assert updated["confidence"] == 0.95
        assert updated["note"] == "Key stance"

        # Invalid label returns 400
        res = test_client.post("/api/units/u_0010", json={"label": "INVALID_LABEL"})
        assert res.status_code == 400

    def test_relations_endpoints(self, test_client):
        # List relations paginated
        res = test_client.get("/api/relations?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1260
        assert len(data["items"]) == 10

        # Update standard intra-turn relation
        payload = {"label": "SUPPORTS", "confidence": 0.85, "note": "Local reason"}
        res = test_client.post("/api/relations/u_0010/u_0011", json=payload)
        assert res.status_code == 200
        assert res.json()["relation_label"] == "SUPPORTS"

        # Validation endpoint
        res = test_client.get("/api/validate")
        assert res.status_code == 200
        val = res.json()
        assert val["syntax_valid"] is True
        assert val["is_complete"] is False

        # Export fails while incomplete
        res = test_client.post("/api/export")
        assert res.status_code == 400
        assert "incomplete" in res.json()["detail"].lower()
