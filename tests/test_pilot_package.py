"""Tests for the ARGUMAP Human Annotation Pilot Package.

Verifies:
1. Deterministic pilot selection (36 units across 3 turns and 3 speakers).
2. Exact source text, turn character offsets, and unit ID preservation.
3. Candidate-pair eligibility, directionality, self-pair exclusion, and count (828 candidates).
4. Explicit labels required for every candidate before an annotation is marked complete.
5. Rejection of unannotated or incomplete pilot packages as gold data.
6. Independent A and B packages containing no prefilled component or relation labels.
7. Structural validity of unannotated pilot packages against the annotation schema.
"""

import copy
import json
from pathlib import Path
import pytest

from scripts.annotation.generate_pilot_package import (
    PILOT_UNIT_RANGES,
    get_pilot_target_unit_ids,
    extract_pilot_units,
    generate_candidate_relation_pairs,
    build_annotator_pilot_package,
)
from scripts.dataset.validate_annotations import (
    validate_annotation_data,
    validate_annotation_file,
    check_annotation_completeness,
    check_candidate_pair_coverage,
    FROZEN_COMPONENT_LABELS,
    FROZEN_RELATION_LABELS,
)
from ml.data.dataset_loader import check_gold_dataset_readiness

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def processed_hansard_data() -> dict:
    fp = PROJECT_ROOT / "data" / "processed" / "hansard_lords_ai_debate_2023.json"
    assert fp.exists(), f"Processed data missing: {fp}"
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def pilot_packages() -> tuple:
    dir_path = PROJECT_ROOT / "data" / "annotations" / "pilot"
    a_fp = dir_path / "hansard_2023_pilot_annotator_A.json"
    b_fp = dir_path / "hansard_2023_pilot_annotator_B.json"
    assert a_fp.exists(), f"Pilot package A missing: {a_fp}"
    assert b_fp.exists(), f"Pilot package B missing: {b_fp}"
    with open(a_fp, "r", encoding="utf-8") as f:
        a_data = json.load(f)
    with open(b_fp, "r", encoding="utf-8") as f:
        b_data = json.load(f)
    return a_data, b_data


class TestPilotPackage:
    """Test suite for the Human Annotation Pilot Package."""

    def test_deterministic_pilot_selection(self, processed_hansard_data):
        """Pilot selection must be strictly deterministic, spanning 36 units across 4 turns (9 per turn)."""
        target_ids = get_pilot_target_unit_ids()
        assert len(target_ids) == 36

        # Check turn composition (9 units each)
        assert len(target_ids.intersection({f"u_{i:04d}" for i in range(10, 19)})) == 9
        assert len(target_ids.intersection({f"u_{i:04d}" for i in range(64, 73)})) == 9
        assert len(target_ids.intersection({f"u_{i:04d}" for i in range(89, 98)})) == 9
        assert len(target_ids.intersection({f"u_{i:04d}" for i in range(902, 911)})) == 9

        extracted = extract_pilot_units(processed_hansard_data)
        assert len(extracted) == 36

        # Verify speakers and turns
        speakers = {u["speaker_id"] for u in extracted}
        turns = {u["turn_id"] for u in extracted}
        assert speakers == {"spk_001", "spk_002", "spk_003", "spk_028"}
        assert turns == {"turn_001", "turn_002", "turn_003", "turn_028"}

    def test_exact_source_text_and_id_preservation(self, processed_hansard_data, pilot_packages):
        """Every unit must preserve exact text, IDs, and character offsets relative to turn text."""
        pkg_a, pkg_b = pilot_packages
        proc_units = {u["unit_id"]: u for u in processed_hansard_data["units"]}
        turn_dict = {t["turn_id"]: t["text"] for t in processed_hansard_data["turns"]}

        for pkg in (pkg_a, pkg_b):
            assert len(pkg["units"]) == 36
            for u in pkg["units"]:
                u_id = u["unit_id"]
                assert u_id in proc_units, f"Unit {u_id} not found in processed transcript"
                orig = proc_units[u_id]

                # Exact text match
                assert u["unit_text"] == orig["text"]
                assert u["char_start"] == orig["char_start"]
                assert u["char_end"] == orig["char_end"]
                assert u["turn_id"] == orig["turn_id"]
                assert u["turn_index"] == orig["turn_index"]
                assert u["speaker_id"] == orig["speaker_id"]

                # Slicing invariant: turn_text[start:end] == unit_text
                turn_text = turn_dict[u["turn_id"]]
                sliced = turn_text[u["char_start"]:u["char_end"]]
                assert sliced == u["unit_text"], (
                    f"Slice mismatch for {u_id}: {sliced!r} != {u['unit_text']!r}"
                )

    def test_candidate_pair_eligibility_and_directionality(self, pilot_packages):
        """Candidate pairs must strictly satisfy approved Option B bidirectional rules (1,260 pairs)."""
        pkg_a, _ = pilot_packages
        relations = pkg_a["relations"]
        unit_map = {u["unit_id"]: u for u in pkg_a["units"]}

        # Expected candidate count: 288 intra + 972 cross = 1,260 pairs (36 * 35)
        assert len(relations) == 1260

        intra_count = 0
        cross_count = 0
        seen_pairs = set()

        for rel in relations:
            src_id = rel["source_unit_id"]
            tgt_id = rel["target_unit_id"]
            pair = (src_id, tgt_id)

            # Rule 1: No duplicate candidate pairs
            assert pair not in seen_pairs, f"Duplicate pair detected: {pair}"
            seen_pairs.add(pair)

            # Rule 2: Self-pairs strictly prohibited
            assert src_id != tgt_id, f"Self-loop detected: {src_id} -> {tgt_id}"

            s_u = unit_map[src_id]
            t_u = unit_map[tgt_id]
            delta_turn = s_u["turn_index"] - t_u["turn_index"]
            turn_dist = abs(delta_turn)

            # Directionality & distance checks
            if delta_turn == 0:
                intra_count += 1
                assert rel["cross_turn"] is False
                assert rel["turn_distance"] == 0
                assert rel["is_override"] is False
            else:
                cross_count += 1
                assert rel["cross_turn"] is True
                assert rel["turn_distance"] == turn_dist
                if turn_dist > 3:
                    assert rel["is_override"] is True
                    assert rel["note"] is not None
                else:
                    assert rel["is_override"] is False

        assert intra_count == 288
        assert cross_count == 972

        # Verify full bidirectionality: for every (u_i, u_j), (u_j, u_i) must also exist
        for s_id, t_id in seen_pairs:
            assert (t_id, s_id) in seen_pairs, (
                f"Candidate pool missing reverse direction: ({t_id} -> {s_id})"
            )

    def test_explicit_labels_required_for_completeness(self, pilot_packages):
        """Unannotated packages must be marked incomplete; all items must have non-null frozen labels."""
        pkg_a, _ = pilot_packages

        # Initially unannotated: must be incomplete (36 units + 1260 relations = 1296)
        is_complete, missing = check_annotation_completeness(pkg_a)
        assert not is_complete
        assert len(missing) == 36 + 1260

        # Create a fully labeled copy
        labeled_pkg = copy.deepcopy(pkg_a)
        labeled_pkg["status"] = "ANNOTATED_PILOT_MOCK"
        for u in labeled_pkg["units"]:
            u["component_label"] = "PREMISE"
            u["confidence"] = 0.95
        for r in labeled_pkg["relations"]:
            r["relation_label"] = "NO_RELATION"
            r["confidence"] = 1.0

        is_complete, missing = check_annotation_completeness(labeled_pkg)
        assert is_complete
        assert len(missing) == 0

        # Fully labeled package must pass strict validation
        is_valid, errors, _ = validate_annotation_data(labeled_pkg, allow_unannotated=False)
        assert is_valid, f"Fully labeled package failed validation: {errors}"

        # If even one candidate relation is omitted or left None, it must fail completeness
        incomplete_pkg = copy.deepcopy(labeled_pkg)
        incomplete_pkg["relations"][0]["relation_label"] = None
        is_complete, missing = check_annotation_completeness(incomplete_pkg)
        assert not is_complete
        assert len(missing) == 1
        assert "missing relation_label" in missing[0]

        # And fail strict validation (omitted pairs cannot be assumed to be NO_RELATION)
        is_valid, errors, _ = validate_annotation_data(incomplete_pkg, allow_unannotated=False)
        assert not is_valid

    def test_rejection_of_unannotated_pilot_packages_as_gold(self):
        """Training gatekeeper must strictly reject unannotated pilot packages."""
        annot_dir = PROJECT_ROOT / "data" / "annotations"
        ready, reason, cleared = check_gold_dataset_readiness(annot_dir)
        assert not ready
        assert "Model training blocked" in reason
        assert len(cleared) == 0

    def test_independent_ab_packages_contain_no_prefilled_labels(self, pilot_packages):
        """Annotator A and B packages must be independent and contain zero prefilled labels."""
        pkg_a, pkg_b = pilot_packages

        assert pkg_a["annotator_id"] == "annotator_A"
        assert pkg_b["annotator_id"] == "annotator_B"

        # Check all units have null labels and null confidence
        for pkg in (pkg_a, pkg_b):
            for u in pkg["units"]:
                assert u["component_label"] is None
                assert u["confidence"] is None
                assert u["note"] is None
                assert u["annotator_id"] == pkg["annotator_id"]

            for r in pkg["relations"]:
                assert r["relation_label"] is None
                assert r["confidence"] is None
                assert r["annotator_id"] == pkg["annotator_id"]

    def test_structural_validity_of_unannotated_pilot_packages(self, pilot_packages):
        """Pilot packages must pass schema and validation with allow_unannotated=True."""
        dir_path = PROJECT_ROOT / "data" / "annotations" / "pilot"
        for ann_id in ["annotator_A", "annotator_B"]:
            fp = dir_path / f"hansard_2023_pilot_{ann_id}.json"
            is_valid, errors, warnings = validate_annotation_file(fp, allow_unannotated=True)
            assert is_valid, f"{fp.name} failed unannotated validation: {errors}"
            assert len(errors) == 0

    def test_candidate_pair_coverage_and_omission_rejection(self, pilot_packages):
        """All 1,260 candidate pairs must be explicitly present; omitted pairs are never inferred as NO_RELATION."""
        pkg_a, _ = pilot_packages
        expected_candidates = {
            (r["source_unit_id"], r["target_unit_id"]) for r in pkg_a["relations"]
        }
        assert len(expected_candidates) == 1260

        # Full coverage verification
        is_covered, missing, extra = check_candidate_pair_coverage(pkg_a, expected_candidates)
        assert is_covered
        assert len(missing) == 0
        assert len(extra) == 0

        # Simulate an omitted pair: an annotator failed to tag a pair and removed it
        tampered_pkg = copy.deepcopy(pkg_a)
        removed_pair = tampered_pkg["relations"].pop(0)
        removed_edge = (removed_pair["source_unit_id"], removed_pair["target_unit_id"])

        is_covered, missing, extra = check_candidate_pair_coverage(tampered_pkg, expected_candidates)
        assert not is_covered
        assert missing == [removed_edge]

    def test_source_and_target_direction_preservation(self, pilot_packages):
        """Source and target orientation must be strictly preserved across candidate pairs."""
        pkg_a, _ = pilot_packages
        unit_map = {u["unit_id"]: u for u in pkg_a["units"]}

        # Check that pairs maintain exact directional attribution
        for r in pkg_a["relations"]:
            src_u = unit_map[r["source_unit_id"]]
            tgt_u = unit_map[r["target_unit_id"]]
            assert r["source_unit_id"] == src_u["unit_id"]
            assert r["target_unit_id"] == tgt_u["unit_id"]
            assert r["source_unit_id"] != r["target_unit_id"]
            expected_dist = abs(src_u["turn_index"] - tgt_u["turn_index"])
            assert r["turn_distance"] == expected_dist

    def test_out_of_window_link_override_validation(self, pilot_packages):
        """Links with turn_distance > 3 require is_override=True and an explanatory note justification."""
        pkg_a, _ = pilot_packages
        labeled_pkg = copy.deepcopy(pkg_a)
        for u in labeled_pkg["units"]:
            u["component_label"] = "CLAIM"
            u["confidence"] = 1.0
        for r in labeled_pkg["relations"]:
            r["relation_label"] = "NO_RELATION"
            r["confidence"] = 1.0

        # Add a unit from Turn 5 (turn_index: 4) to test an actual out-of-window link (turn_distance = 4 > 3)
        turn_5_unit = {
            "debate_id": "uk_hansard_lords_2023",
            "source_corpus": "uk_parliament_hansard",
            "source_license": "Open Parliament Licence v3.0",
            "turn_id": "turn_005",
            "turn_index": 4,
            "speaker_id": "spk_005",
            "unit_id": "u_0150",
            "unit_text": "Military AI requires specific battlefield regulation.",
            "char_start": 0,
            "char_end": 54,
            "component_label": "CLAIM",
            "annotator_id": "annotator_A",
            "confidence": 1.0,
            "guideline_version": "1.1.0",
        }
        labeled_pkg["units"].append(turn_5_unit)

        # Add a legitimate out-of-window override (Turn 5 -> Turn 1, delta_turn = 4 - 0 = 4 > 3)
        override_link = {
            "source_unit_id": "u_0150",
            "target_unit_id": "u_0010",
            "relation_label": "ATTACKS",
            "same_speaker": False,
            "cross_turn": True,
            "turn_distance": 4,
            "is_override": True,
            "annotator_id": "annotator_A",
            "confidence": 0.9,
            "note": "[OVERRIDE: k=4] Rebuttal directly challenging the opening thesis from Turn 1",
            "guideline_version": "1.1.0",
        }
        labeled_pkg["relations"].append(override_link)

        # Valid override must pass validation without out-of-window warnings
        is_valid, errors, warnings = validate_annotation_data(labeled_pkg, allow_unannotated=False)
        assert is_valid, f"Valid override failed validation: {errors}"
        assert not any("is not flagged with 'is_override: true'" in w for w in warnings)
        assert not any("requires an explanatory justification" in w for w in warnings)

        # Unflagged out-of-window link must produce warnings
        unflagged_link = copy.deepcopy(override_link)
        unflagged_link["is_override"] = False
        unflagged_link["note"] = None
        labeled_pkg["relations"][-1] = unflagged_link

        is_valid, errors, warnings = validate_annotation_data(labeled_pkg, allow_unannotated=False)
        assert any("is not flagged with 'is_override: true'" in w for w in warnings)
        assert any("explanatory 'note' justification" in w for w in warnings)
