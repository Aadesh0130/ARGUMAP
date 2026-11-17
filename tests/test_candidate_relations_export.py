"""Tests for candidate relations full export.

Verifies:
1. Target file existence at data/annotation/candidate_relations_full.json
2. Exact pair count of 1,260 directed candidate relation pairs
3. Canonical text fidelity: source_text and target_text match processed dataset verbatim
4. Metadata preservation: pair_id, speakers, turns, override flags, notes, and ordering
5. Bidirectional completeness: all reverse-direction pairs exist
6. Zero duplicates, zero invalid unit references, zero missing texts
"""

import json
from pathlib import Path
import sys
import subprocess
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotation.export_candidate_relations import (
    DEFAULT_CANONICAL_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PILOT_PATH,
    export_candidate_relations,
    load_canonical_units,
)


@pytest.fixture(scope="module")
def canonical_units():
    return load_canonical_units(DEFAULT_CANONICAL_PATH)


@pytest.fixture(scope="module")
def exported_pairs():
    assert DEFAULT_OUTPUT_PATH.exists(), f"Target file does not exist: {DEFAULT_OUTPUT_PATH}"
    with open(DEFAULT_OUTPUT_PATH, "r", encoding="utf-8") as f:
        pairs = json.load(f)
    return pairs


class TestCandidateRelationsExport:
    """Validation test suite for data/annotation/candidate_relations_full.json."""

    def test_file_exists_and_is_valid_json(self):
        assert DEFAULT_OUTPUT_PATH.exists()
        assert DEFAULT_OUTPUT_PATH.is_file()
        assert DEFAULT_OUTPUT_PATH.stat().st_size > 0

    def test_exact_pair_count(self, exported_pairs):
        assert len(exported_pairs) == 1260

    def test_required_fields_present_in_every_pair(self, exported_pairs):
        required_keys = [
            "pair_id",
            "source_unit_id",
            "source_text",
            "target_unit_id",
            "target_text",
            "source_speaker",
            "target_speaker",
            "source_turn",
            "target_turn",
            "is_override",
            "notes",
            "note",
            "annotation_status",
            "label",
            "relation_label",
        ]
        for idx, pair in enumerate(exported_pairs):
            for k in required_keys:
                assert k in pair, f"Pair #{idx + 1} ({pair.get('pair_id')}) missing required key '{k}'"

    def test_no_duplicate_pair_ids(self, exported_pairs):
        pair_ids = [p["pair_id"] for p in exported_pairs]
        assert len(pair_ids) == len(set(pair_ids))
        assert len(pair_ids) == 1260

    def test_canonical_text_grounding(self, exported_pairs, canonical_units):
        """Verifies that source and target text originate from the canonical dataset."""
        for pair in exported_pairs:
            s_id = pair["source_unit_id"]
            t_id = pair["target_unit_id"]

            assert s_id in canonical_units, f"Unknown source unit '{s_id}'"
            assert t_id in canonical_units, f"Unknown target unit '{t_id}'"

            expected_src_text = canonical_units[s_id]["text"]
            expected_tgt_text = canonical_units[t_id]["text"]

            assert pair["source_text"] == expected_src_text, f"Text mismatch for source {s_id}"
            assert pair["target_text"] == expected_tgt_text, f"Text mismatch for target {t_id}"

            # Ensure texts are non-empty
            assert pair["source_text"].strip() != ""
            assert pair["target_text"].strip() != ""

    def test_speakers_and_turns_resolution(self, exported_pairs, canonical_units):
        for pair in exported_pairs:
            s_id = pair["source_unit_id"]
            t_id = pair["target_unit_id"]

            assert pair["source_speaker"] == canonical_units[s_id]["speaker_name"]
            assert pair["target_speaker"] == canonical_units[t_id]["speaker_name"]

            assert pair["source_turn"] == canonical_units[s_id]["turn_id"]
            assert pair["target_turn"] == canonical_units[t_id]["turn_id"]

    def test_bidirectional_coverage(self, exported_pairs):
        """Every directed edge (u_i -> u_j) must have its reverse (u_j -> u_i)."""
        pairs_set = {(p["source_unit_id"], p["target_unit_id"]) for p in exported_pairs}
        assert len(pairs_set) == 1260

        for s_id, t_id in pairs_set:
            assert (t_id, s_id) in pairs_set, f"Reverse pair ({t_id} -> {s_id}) missing"

    def test_no_self_loops(self, exported_pairs):
        for pair in exported_pairs:
            assert pair["source_unit_id"] != pair["target_unit_id"]

    def test_override_metadata_integrity(self, exported_pairs):
        overrides = [p for p in exported_pairs if p["is_override"]]
        assert len(overrides) == 486

        for p in overrides:
            assert p["turn_distance"] > 3
            assert p["notes"] is not None
            assert "[PILOT_DIVERSITY_OVERRIDE]" in p["notes"]
            assert p["note"] == p["notes"]

        non_overrides = [p for p in exported_pairs if not p["is_override"]]
        assert len(non_overrides) == 774
        for p in non_overrides:
            assert p["turn_distance"] <= 3

    def test_annotation_status_unannotated_pilot(self, exported_pairs):
        for pair in exported_pairs:
            assert pair["annotation_status"] == "UNANNOTATED"
            assert pair["label"] is None
            assert pair["relation_label"] is None

    def test_ordering_matches_pilot_package(self, exported_pairs):
        with open(DEFAULT_PILOT_PATH, "r", encoding="utf-8") as f:
            pilot_data = json.load(f)
        pilot_rels = pilot_data["relations"]

        assert len(exported_pairs) == len(pilot_rels)
        for exp_p, orig_r in zip(exported_pairs, pilot_rels):
            assert exp_p["source_unit_id"] == orig_r["source_unit_id"]
            assert exp_p["target_unit_id"] == orig_r["target_unit_id"]
            assert exp_p["is_override"] == orig_r.get("is_override", False)
            assert exp_p["turn_distance"] == orig_r["turn_distance"]

    def test_exporter_function_report(self):
        pairs, report = export_candidate_relations(dry_run=True)
        assert report["total_pairs"] == 1260
        assert report["missing_source_texts"] == 0
        assert report["missing_target_texts"] == 0
        assert report["duplicate_pair_ids"] == 0
        assert report["invalid_unit_references"] == 0
        assert report["override_pairs_count"] == 486
        assert report["unannotated_pairs_count"] == 1260
        assert report["annotated_pairs_count"] == 0
