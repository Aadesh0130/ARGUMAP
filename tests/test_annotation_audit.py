"""Tests for ARGUMAP annotation audit and relation agreement logic.

Covers:
- Annotation file validation (missing labels, duplicate IDs, invalid labels,
  invalid relation endpoints, self-loops, duplicate relation pairs)
- Relation agreement: shared-pairs-only method vs. union imputation method
- Relation agreement with omitted pairs and explicit NO_RELATION
- Cross-annotator alignment checks
- End-to-end audit report generation
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Path setup — make sure project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotation.calculate_component_agreement import (
    compute_cohens_kappa,
    compute_krippendorffs_alpha_nominal,
)
from scripts.annotation.calculate_relation_agreement import (
    FROZEN_RELATION_LABELS,
    compute_relation_kappa,
    compute_relation_agreement_shared_only,
)
from scripts.annotation.run_agreement_audit import (
    FROZEN_COMPONENT_LABELS,
    FROZEN_RELATION_LABELS_LIST,
    validate_annotation_file,
    check_cross_annotator_alignment,
)


# ============================================================================
# Fixtures
# ============================================================================

def _make_unit(unit_id: str, label: str = "CLAIM") -> Dict[str, Any]:
    """Build a minimal valid annotation unit."""
    return {
        "debate_id": "test_debate",
        "source_corpus": "test",
        "source_license": "TEST",
        "turn_id": "turn_001",
        "turn_index": 0,
        "speaker_id": "spk_001",
        "unit_id": unit_id,
        "unit_text": f"Text for {unit_id}",
        "char_start": 0,
        "char_end": 10,
        "component_label": label,
        "annotator_id": "test_annotator",
        "confidence": 0.9,
        "guideline_version": "1.0.0",
    }


def _make_relation(
    src: str, tgt: str, label: str = "SUPPORTS"
) -> Dict[str, Any]:
    """Build a minimal valid relation."""
    return {
        "source_unit_id": src,
        "target_unit_id": tgt,
        "relation_label": label,
        "same_speaker": True,
        "cross_turn": False,
        "turn_distance": 0,
        "annotator_id": "test_annotator",
        "confidence": 0.9,
        "guideline_version": "1.0.0",
    }


def _make_annotation_doc(
    units: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a complete annotation document."""
    return {
        "debate_id": "test_debate",
        "title": "Test Debate",
        "source_corpus": "test",
        "source_license": "TEST",
        "guideline_version": "1.0.0",
        "units": units,
        "relations": relations,
    }


def _write_annotation_file(
    tmp_path: Path, name: str, doc: Dict[str, Any]
) -> Path:
    """Write an annotation doc to a temp file and return the path."""
    filepath = tmp_path / name
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    return filepath


# ============================================================================
# Tests: validate_annotation_file
# ============================================================================

class TestValidateAnnotationFile:
    """Tests for single-file annotation validation."""

    def test_valid_file(self, tmp_path: Path):
        units = [_make_unit("u_001"), _make_unit("u_002", "PREMISE")]
        rels = [_make_relation("u_001", "u_002", "SUPPORTS")]
        doc = _make_annotation_doc(units, rels)
        fp = _write_annotation_file(tmp_path, "valid.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["unit_count"] == 2
        assert result["relation_count"] == 1

    def test_missing_file(self, tmp_path: Path):
        fp = tmp_path / "nonexistent.json"
        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("not found" in e.lower() for e in result["errors"])

    def test_invalid_json(self, tmp_path: Path):
        fp = tmp_path / "bad.json"
        fp.write_text("{invalid json", encoding="utf-8")
        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("parse error" in e.lower() for e in result["errors"])

    def test_missing_component_label(self, tmp_path: Path):
        unit = _make_unit("u_001")
        del unit["component_label"]
        doc = _make_annotation_doc([unit], [])
        fp = _write_annotation_file(tmp_path, "no_label.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("component_label" in e for e in result["errors"])

    def test_invalid_component_label(self, tmp_path: Path):
        unit = _make_unit("u_001", label="INVALID_LABEL")
        doc = _make_annotation_doc([unit], [])
        fp = _write_annotation_file(tmp_path, "bad_label.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("INVALID_LABEL" in e for e in result["errors"])

    def test_duplicate_unit_ids(self, tmp_path: Path):
        units = [_make_unit("u_001"), _make_unit("u_001", "PREMISE")]
        doc = _make_annotation_doc(units, [])
        fp = _write_annotation_file(tmp_path, "dup_ids.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("duplicate" in e.lower() for e in result["errors"])

    def test_relation_references_unknown_unit(self, tmp_path: Path):
        units = [_make_unit("u_001")]
        rels = [_make_relation("u_001", "u_999")]
        doc = _make_annotation_doc(units, rels)
        fp = _write_annotation_file(tmp_path, "bad_ref.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("u_999" in e for e in result["errors"])

    def test_relation_self_loop(self, tmp_path: Path):
        units = [_make_unit("u_001")]
        rels = [_make_relation("u_001", "u_001")]
        doc = _make_annotation_doc(units, rels)
        fp = _write_annotation_file(tmp_path, "self_loop.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("self-loop" in e.lower() for e in result["errors"])

    def test_duplicate_relation_pairs(self, tmp_path: Path):
        units = [_make_unit("u_001"), _make_unit("u_002", "PREMISE")]
        rels = [
            _make_relation("u_001", "u_002"),
            _make_relation("u_001", "u_002", "ATTACKS"),
        ]
        doc = _make_annotation_doc(units, rels)
        fp = _write_annotation_file(tmp_path, "dup_rel.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("duplicate relation" in e.lower() for e in result["errors"])

    def test_invalid_relation_label(self, tmp_path: Path):
        units = [_make_unit("u_001"), _make_unit("u_002", "PREMISE")]
        rels = [_make_relation("u_001", "u_002", "INVALID_REL")]
        doc = _make_annotation_doc(units, rels)
        fp = _write_annotation_file(tmp_path, "bad_rel.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("INVALID_REL" in e for e in result["errors"])

    def test_confidence_out_of_range(self, tmp_path: Path):
        unit = _make_unit("u_001")
        unit["confidence"] = 1.5
        doc = _make_annotation_doc([unit], [])
        fp = _write_annotation_file(tmp_path, "bad_conf.json", doc)

        result = validate_annotation_file(fp)
        assert result["valid"] is False
        assert any("confidence" in e.lower() for e in result["errors"])

    def test_frozen_labels_are_preserved(self):
        """Verify that the frozen label lists match PROJECT_SPEC.md §6."""
        assert FROZEN_COMPONENT_LABELS == [
            "CLAIM", "PREMISE", "EVIDENCE",
            "COUNTERARGUMENT", "REBUTTAL", "OTHER",
        ]
        assert FROZEN_RELATION_LABELS_LIST == [
            "SUPPORTS", "ATTACKS", "RESPONDS_TO", "NO_RELATION",
        ]


# ============================================================================
# Tests: compute_relation_agreement_shared_only
# ============================================================================

class TestRelationAgreementSharedOnly:
    """Tests for the shared-pairs-only relation agreement method."""

    def test_perfect_agreement(self):
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert result["cohens_kappa"] == 1.0
        assert result["shared_pairs"] == 2
        assert result["disagreements"] == []

    def test_complete_disagreement(self):
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "SUPPORTS"),
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "ATTACKS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert result["observed_agreement"] == 0.0
        assert len(result["disagreements"]) == 2

    def test_omitted_pairs_not_imputed(self):
        """Pairs annotated by only one annotator must NOT be counted."""
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),  # only in A
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_005", "u_006", "RESPONDS_TO"),  # only in B
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        # Only 1 shared pair -- below the minimum of 2
        assert result["status"] == "AGREEMENT NOT AVAILABLE"
        assert result["only_annotator_A_pairs"] == 1
        assert result["only_annotator_B_pairs"] == 1

    def test_partial_overlap(self):
        """Mix of shared and unshared pairs."""
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
            _make_relation("u_005", "u_006", "RESPONDS_TO"),  # only in A
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
            _make_relation("u_007", "u_008", "SUPPORTS"),  # only in B
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert result["shared_pairs"] == 2
        assert result["only_annotator_A_pairs"] == 1
        assert result["only_annotator_B_pairs"] == 1
        assert result["cohens_kappa"] == 1.0  # perfect on shared pairs

    def test_empty_relations(self):
        result = compute_relation_agreement_shared_only([], [])
        assert result["status"] == "AGREEMENT NOT AVAILABLE"

    def test_explicit_no_relation_labels(self):
        """Explicit NO_RELATION labels should be treated normally."""
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "NO_RELATION"),
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "NO_RELATION"),
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert result["cohens_kappa"] == 1.0
        assert "NO_RELATION" in result["classes"]

    def test_method_field_present(self):
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_a)
        assert result["method"] == "shared_pairs_only"


# ============================================================================
# Tests: compute_relation_kappa (union imputation)
# ============================================================================

class TestRelationKappaUnionImputation:
    """Tests for the original union-with-imputation method."""

    def test_imputes_no_relation_for_missing_pairs(self):
        """Verify that omitted pairs get NO_RELATION imputed."""
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            # u_003->u_004 omitted by B -- will be imputed as NO_RELATION
        ]
        result = compute_relation_kappa(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert result["total_pairs"] == 2
        # One disagreement: A says ATTACKS, B imputed as NO_RELATION
        assert result["observed_agreement"] < 1.0

    def test_validity_warning_present(self):
        rels = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        result = compute_relation_kappa(rels, rels)
        assert "validity_warning" in result
        assert "method" in result
        assert result["method"] == "union_with_NO_RELATION_imputation"


# ============================================================================
# Tests: check_cross_annotator_alignment
# ============================================================================

class TestCrossAnnotatorAlignment:
    """Tests for cross-annotator alignment checks."""

    def test_perfect_alignment(self):
        units = [_make_unit("u_001"), _make_unit("u_002")]
        rels = [_make_relation("u_001", "u_002")]
        doc_a = _make_annotation_doc(units, rels)
        doc_b = _make_annotation_doc(units, rels)

        result = check_cross_annotator_alignment(doc_a, doc_b, "test")
        assert result["shared_unit_ids"] == 2
        assert result["only_annotator_A_units"] == []
        assert result["only_annotator_B_units"] == []
        assert result["shared_relation_pairs"] == 1

    def test_mismatched_units(self):
        units_a = [_make_unit("u_001"), _make_unit("u_002")]
        units_b = [_make_unit("u_001"), _make_unit("u_003")]
        doc_a = _make_annotation_doc(units_a, [])
        doc_b = _make_annotation_doc(units_b, [])

        result = check_cross_annotator_alignment(doc_a, doc_b, "test")
        assert result["shared_unit_ids"] == 1
        assert "u_002" in result["only_annotator_A_units"]
        assert "u_003" in result["only_annotator_B_units"]


# ============================================================================
# Tests: Pilot data integrity (against real annotation files if available)
# ============================================================================

class TestPilotDataIntegrity:
    """Smoke tests verifying the actual pilot annotation files."""

    PILOT_DIR = PROJECT_ROOT / "data" / "annotations" / "pilot"

    @pytest.mark.skipif(
        not (PROJECT_ROOT / "data" / "annotations" / "pilot" / "debate_001_annotator_A.json").exists(),
        reason="Pilot annotations not available",
    )
    def test_pilot_files_are_valid(self):
        """All 6 pilot annotation files must pass validation."""
        for debate_num in ["001", "002", "003"]:
            for annotator in ["A", "B"]:
                fp = self.PILOT_DIR / f"debate_{debate_num}_annotator_{annotator}.json"
                result = validate_annotation_file(fp)
                assert result["valid"], (
                    f"Validation failed for {fp.name}: {result['errors']}"
                )

    @pytest.mark.skipif(
        not (PROJECT_ROOT / "data" / "annotations" / "pilot" / "debate_001_annotator_A.json").exists(),
        reason="Pilot annotations not available",
    )
    def test_no_explicit_no_relation_in_pilot(self):
        """Pilot annotations should contain zero NO_RELATION labels."""
        for debate_num in ["001", "002", "003"]:
            for annotator in ["A", "B"]:
                fp = self.PILOT_DIR / f"debate_{debate_num}_annotator_{annotator}.json"
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for rel in data.get("relations", []):
                    assert rel["relation_label"] != "NO_RELATION", (
                        f"Found explicit NO_RELATION in {fp.name}: {rel}"
                    )

    @pytest.mark.skipif(
        not (PROJECT_ROOT / "data" / "annotations" / "pilot" / "debate_001_component_agreement.json").exists(),
        reason="Existing agreement reports not available",
    )
    def test_existing_component_agreement_preserved(self):
        """Existing component agreement reports must not be overwritten.
        
        Verify the known kappa values are still present.
        """
        expected = {
            "001": 0.7035,
            "002": 0.7825,
            "003": 0.7000,
        }
        for debate_num, expected_kappa in expected.items():
            fp = self.PILOT_DIR / f"debate_{debate_num}_component_agreement.json"
            with open(fp, "r", encoding="utf-8") as f:
                report = json.load(f)
            assert abs(report["cohens_kappa"] - expected_kappa) < 0.001, (
                f"debate_{debate_num} kappa changed: "
                f"expected {expected_kappa}, got {report['cohens_kappa']}"
            )


# ============================================================================
# Tests: Component Agreement & Edge Cases
# ============================================================================

class TestComponentAgreementLogic:
    """Tests for component agreement calculation and alignment."""

    def test_valid_component_agreement(self):
        labels_a = ["CLAIM", "PREMISE", "EVIDENCE", "REBUTTAL"]
        labels_b = ["CLAIM", "PREMISE", "EVIDENCE", "REBUTTAL"]
        result = compute_cohens_kappa(labels_a, labels_b)
        assert result["status"] == "COMPLETED"
        assert result["observed_agreement"] == 1.0
        assert result["cohens_kappa"] == 1.0
        assert result["total_units"] == 4

    def test_mismatched_component_lengths(self):
        labels_a = ["CLAIM", "PREMISE"]
        labels_b = ["CLAIM"]
        with pytest.raises(ValueError):
            compute_cohens_kappa(labels_a, labels_b)

    def test_empty_component_labels(self):
        result = compute_cohens_kappa([], [])
        assert result["status"] == "AGREEMENT NOT AVAILABLE"
        assert result["cohens_kappa"] == 0.0

    def test_degenerate_kappa_single_class(self):
        """Degenerate case where both annotators use only one identical class (pe == 1.0)."""
        labels_a = ["CLAIM", "CLAIM", "CLAIM"]
        labels_b = ["CLAIM", "CLAIM", "CLAIM"]
        result = compute_cohens_kappa(labels_a, labels_b)
        assert result["status"] == "COMPLETED"
        assert result["cohens_kappa"] == 1.0

    def test_degenerate_kappa_relation_undefined(self):
        """Relation agreement degenerate case where expected agreement pe == 1.0 and po < 1.0."""
        # A says SUPPORTS, B says ATTACKS for all pairs
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "SUPPORTS"),
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "ATTACKS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert result["observed_agreement"] == 0.0
        # When classes are disjoint (A all SUPPORTS, B all ATTACKS), po = 0.0, pe = 0.0, kappa = 0.0
        assert result["cohens_kappa"] == 0.0

    def test_per_class_counts_in_shared_relation(self):
        rels_a = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "ATTACKS"),
            _make_relation("u_005", "u_006", "SUPPORTS"),
        ]
        rels_b = [
            _make_relation("u_001", "u_002", "SUPPORTS"),
            _make_relation("u_003", "u_004", "RESPONDS_TO"),
            _make_relation("u_005", "u_006", "SUPPORTS"),
        ]
        result = compute_relation_agreement_shared_only(rels_a, rels_b)
        assert result["status"] == "COMPLETED"
        assert "per_class" in result
        assert result["per_class"]["SUPPORTS"]["agreed_count"] == 2
        assert result["per_class"]["ATTACKS"]["agreed_count"] == 0


# ============================================================================
# Tests: End-to-End Audit Runner
# ============================================================================

class TestAuditRunner:
    """Tests for run_agreement_audit end-to-end report generation."""

    def test_audit_runner_generates_json_and_summary(self, tmp_path: Path, monkeypatch):
        """Run audit using temporary pilot fixtures to verify file creation."""
        # Create a mock pilot directory with 3 debates
        for d_num in ["001", "002", "003"]:
            units = [
                _make_unit("u_001", "CLAIM"),
                _make_unit("u_002", "PREMISE"),
            ]
            rels = [_make_relation("u_001", "u_002", "SUPPORTS")]
            doc_a = _make_annotation_doc(units, rels)
            doc_b = _make_annotation_doc(units, rels)
            _write_annotation_file(tmp_path, f"debate_{d_num}_annotator_A.json", doc_a)
            _write_annotation_file(tmp_path, f"debate_{d_num}_annotator_B.json", doc_b)

        import scripts.annotation.run_agreement_audit as audit_mod
        monkeypatch.setattr(audit_mod, "PILOT_DIR", tmp_path)

        report = audit_mod.run_full_audit(output_dir=tmp_path)
        assert report is not None
        assert "debate_001" in report["debates"]
        assert "debate_002" in report["debates"]
        assert "debate_003" in report["debates"]

        # Verify output files exist
        json_report = tmp_path / "agreement_audit_report.json"
        legacy_json_report = tmp_path / "annotation_quality_audit.json"
        txt_summary = tmp_path / "annotation_quality_audit_summary.txt"

        assert json_report.exists()
        assert legacy_json_report.exists()
        assert txt_summary.exists()

        with open(json_report, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["overall_status"] == "BLOCKED"  # Candidate-pair window k blocker
        assert len(data["blockers"]) >= 1

