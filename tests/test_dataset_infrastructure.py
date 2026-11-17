"""Automated Test Suite for ARGUMAP Dataset Infrastructure & Annotation Validation.

Verifies:
1. Dataset manifest integrity and license compliance.
2. Annotation JSON schema adherence and validation.
3. Rejection of invalid component and relation labels.
4. Rejection of duplicate IDs, broken references, invalid offsets, and loops.
5. Intermediate conversion preservation of native labels and provenance.
6. Gatekeeping of label mapping registry (prohibiting unauthorized relabeling).
"""

import sys
import copy
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.dataset.validate_dataset_manifest import validate_manifest
from scripts.dataset.validate_annotations import validate_annotation_data, validate_annotation_file
from scripts.dataset.conversion import (
    NormalizedUnit,
    ProvenanceRecord,
    MappingRegistry,
    AAEConverter,
    US2016Converter,
)
from scripts.dataset.conversion.mapping_registry import (
    UnmappedLabelError,
    UnapprovedMappingError,
)


@pytest.fixture
def valid_annotation_dict():
    """Provides a valid baseline annotation dictionary for testing."""
    return {
        "debate_id": "test_debate_01",
        "title": "Test Resolution",
        "source_corpus": "us2016",
        "source_license": "CC BY-NC-SA 4.0",
        "guideline_version": "1.0.0",
        "units": [
            {
                "debate_id": "test_debate_01",
                "source_corpus": "us2016",
                "source_license": "CC BY-NC-SA 4.0",
                "turn_id": "turn_01",
                "turn_index": 0,
                "speaker_id": "Speaker_A",
                "unit_id": "u_01",
                "unit_text": "We must invest in green energy.",
                "char_start": 0,
                "char_end": 31,
                "component_label": "CLAIM",
                "annotator_id": "ann_1",
                "confidence": 0.95,
                "guideline_version": "1.0.0",
            },
            {
                "debate_id": "test_debate_01",
                "source_corpus": "us2016",
                "source_license": "CC BY-NC-SA 4.0",
                "turn_id": "turn_01",
                "turn_index": 0,
                "speaker_id": "Speaker_A",
                "unit_id": "u_02",
                "unit_text": "because it creates high-paying jobs.",
                "char_start": 32,
                "char_end": 67,
                "component_label": "PREMISE",
                "annotator_id": "ann_1",
                "confidence": 0.90,
                "guideline_version": "1.0.0",
            },
        ],
        "relations": [
            {
                "source_unit_id": "u_02",
                "target_unit_id": "u_01",
                "relation_label": "SUPPORTS",
                "same_speaker": True,
                "cross_turn": False,
                "turn_distance": 0,
                "annotator_id": "ann_1",
                "confidence": 0.92,
                "guideline_version": "1.0.0",
            }
        ],
    }


# ==============================================================================
# Manifest Tests
# ==============================================================================

def test_dataset_manifest_is_valid():
    """Verify that the central dataset manifest exists and passes validation."""
    manifest_path = PROJECT_ROOT / "data" / "dataset_manifest.json"
    is_valid, errors, _ = validate_manifest(manifest_path)
    assert is_valid, f"Manifest validation failed with errors: {errors}"


def test_dataset_manifest_rejects_invalid_license_status(tmp_path):
    """Verify that manifest validator strictly rejects non-verified / speculative licenses."""
    import json
    invalid_manifest = {
        "schema_version": "1.0.0",
        "datasets": [
            {
                "dataset_id": "bad_ds",
                "name": "Bad Dataset",
                "source": "https://example.com",
                "paper": "Author (2020)",
                "year": 2020,
                "domain": "Test",
                "component_labels": ["Claim"],
                "relation_labels": ["Support"],
                "speaker_information": True,
                "dialogue_structure": "Debate",
                "license": "Custom",
                "license_status": "MAYBE_OPEN_SOURCE",  # Invalid! Must be VERIFIED or UNVERIFIED
                "download_status": "NOT_DOWNLOADED",
                "intended_use": "Test",
                "notes": "Testing",
            }
        ],
    }
    p = tmp_path / "manifest.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(invalid_manifest, f)

    is_valid, errors, _ = validate_manifest(p)
    assert not is_valid
    assert any("Invalid license_status" in e for e in errors)


# ==============================================================================
# Annotation Schema & Content Tests
# ==============================================================================

def test_pilot_sample_annotation_file():
    """Verify that the official pilot sample annotation file passes all checks."""
    sample_path = PROJECT_ROOT / "data" / "annotations" / "pilot" / "sample_annotation.json"
    is_valid, errors, _ = validate_annotation_file(sample_path)
    assert is_valid, f"Sample pilot annotation failed validation: {errors}"


def test_annotation_baseline_is_valid(valid_annotation_dict):
    """Verify that valid test fixture passes validation."""
    is_valid, errors, _ = validate_annotation_data(valid_annotation_dict)
    assert is_valid, f"Valid baseline failed: {errors}"


def test_annotation_rejects_invalid_component_label(valid_annotation_dict):
    """Verify that unknown/non-frozen component labels are rejected."""
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["units"][0]["component_label"] = "UNSUPPORTED_OPINION"

    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("Invalid component_label" in e for e in errors)


def test_annotation_rejects_invalid_relation_label(valid_annotation_dict):
    """Verify that unknown/non-frozen relation labels are rejected."""
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["relations"][0]["relation_label"] = "CONTRADICTS"  # Should be ATTACKS

    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("Invalid relation_label" in e for e in errors)


def test_annotation_rejects_duplicate_unit_id(valid_annotation_dict):
    """Verify that duplicate unit_ids within the same document are caught."""
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["units"][1]["unit_id"] = "u_01"  # Duplicate of first unit

    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("Duplicate unit_id detected" in e for e in errors)


def test_annotation_rejects_broken_relation_references(valid_annotation_dict):
    """Verify that relations pointing to nonexistent unit IDs are rejected."""
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["relations"][0]["target_unit_id"] = "u_999_nonexistent"

    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("does not exist in units list" in e for e in errors)


def test_annotation_rejects_invalid_offsets(valid_annotation_dict):
    """Verify that inverted or negative character offsets are rejected."""
    # Test negative start
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["units"][0]["char_start"] = -5
    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("char_start must be >= 0" in e for e in errors)

    # Test inverted range (end <= start)
    bad_data2 = copy.deepcopy(valid_annotation_dict)
    bad_data2["units"][0]["char_start"] = 40
    bad_data2["units"][0]["char_end"] = 20
    is_valid2, errors2, _ = validate_annotation_data(bad_data2)
    assert not is_valid2
    assert any("strictly greater than char_start" in e for e in errors2)


def test_annotation_rejects_invalid_confidence(valid_annotation_dict):
    """Verify that confidence outside [0.0, 1.0] is rejected."""
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["units"][0]["confidence"] = 1.5

    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("confidence must be between 0.0 and 1.0" in e for e in errors)


def test_annotation_rejects_self_referencing_loop(valid_annotation_dict):
    """Verify that self-referencing relation loops (u_i -> u_i) are rejected."""
    bad_data = copy.deepcopy(valid_annotation_dict)
    bad_data["relations"][0]["target_unit_id"] = bad_data["relations"][0]["source_unit_id"]

    is_valid, errors, _ = validate_annotation_data(bad_data)
    assert not is_valid
    assert any("Self-referencing relations (loops) are prohibited" in e for e in errors)


# ==============================================================================
# Conversion & Provenance Tests
# ==============================================================================

def test_aae_converter_preserves_native_labels():
    """Verify that AAE converter strictly preserves native 'MajorClaim' label without relabeling."""
    converter = AAEConverter()
    raw_mock = [
        {"doc_id": "essay001", "unit_id": "T1", "label": "MajorClaim", "text": "We should protect oceans."}
    ]
    normalized = converter.convert(raw_mock)
    assert len(normalized) == 1
    unit = normalized[0]

    # Source label must remain MajorClaim, NOT silently converted to CLAIM
    assert unit.source_label == "MajorClaim"
    assert unit.source_corpus == "aae"
    assert unit.provenance is not None
    assert unit.provenance.source_label == "MajorClaim"
    assert unit.provenance.source_corpus == "aae"
    assert unit.provenance.source_license == "UNVERIFIED"


def test_us2016_converter_preserves_native_labels():
    """Verify that US2016 converter preserves native IAT label ('Assertion')."""
    converter = US2016Converter()
    raw_mock = [
        {
            "debate_id": "debate_1",
            "turn_id": "turn_1",
            "speaker": "Clinton",
            "unit_id": "u_1",
            "native_label": "Assertion",
            "text": "Clean energy creates sustainable jobs.",
        }
    ]
    normalized = converter.convert(raw_mock)
    assert len(normalized) == 1
    unit = normalized[0]

    assert unit.source_label == "Assertion"
    assert unit.speaker_id == "Clinton"
    assert unit.source_corpus == "us2016"
    assert unit.provenance.source_label == "Assertion"


def test_mapping_registry_blocks_unapproved_relabeling():
    """Verify that MappingRegistry strictly blocks automatic conversion of external labels."""
    registry = MappingRegistry()

    # Unmapped label raises error
    with pytest.raises(UnmappedLabelError):
        registry.get_argumap_label("aae", "MajorClaim")

    # Registered but unapproved candidate mapping must still raise UnapprovedMappingError
    registry.register_candidate_rule(
        source_corpus="aae",
        source_label="MajorClaim",
        candidate_argumap_label="CLAIM",
        is_approved=False,
        rationale="Candidate mapping pending inter-annotator review",
    )

    with pytest.raises(UnapprovedMappingError):
        registry.get_argumap_label("aae", "MajorClaim")

    # Approved mapping succeeds
    registry.register_candidate_rule(
        source_corpus="aae",
        source_label="MajorClaim",
        candidate_argumap_label="CLAIM",
        is_approved=True,
        reviewer="lead_linguist",
        approval_date="2026-09-24",
        rationale="Audited agreement test passed",
    )
    assert registry.get_argumap_label("aae", "MajorClaim") == "CLAIM"
