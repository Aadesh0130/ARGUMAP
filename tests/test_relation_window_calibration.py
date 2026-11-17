"""Tests for relation candidate-pair window calibration logic.

Covers:
- Extraction of unique positive relations and directionality preservation
- Turn distance and unit distance calculations
- Quantile and summary statistics
- Directional vs bidirectional candidate generation
- Detection of label disagreements between annotators
- Workload and positive class density simulations
"""

from pathlib import Path
import sys
from typing import Any, Dict, List
import pytest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.annotation.calibrate_relation_window import (
    load_debate_pilot_data,
    extract_unique_positive_relations,
    compute_distance_statistics,
    simulate_candidate_windows,
    run_full_calibration_analysis,
)


def _make_mock_unit(
    uid: str, turn_idx: int, spk: str = "spk_1", char_start: int = 0
) -> Dict[str, Any]:
    return {
        "unit_id": uid,
        "turn_index": turn_idx,
        "speaker_id": spk,
        "char_start": char_start,
        "component_label": "CLAIM",
        "unit_text": f"Text for {uid}",
    }


def _make_mock_relation(src: str, tgt: str, label: str = "SUPPORTS") -> Dict[str, Any]:
    return {
        "source_unit_id": src,
        "target_unit_id": tgt,
        "relation_label": label,
    }


class TestExtractUniquePositiveRelations:
    """Tests for extracting deduplicated positive relations."""

    def test_deduplication_and_agreement(self):
        units = [
            _make_mock_unit("u1", 0, "spk_1"),
            _make_mock_unit("u2", 0, "spk_1"),
            _make_mock_unit("u3", 1, "spk_2"),
        ]
        da = {
            "units": units,
            "relations": [
                _make_mock_relation("u2", "u1", "SUPPORTS"),
                _make_mock_relation("u3", "u1", "ATTACKS"),
            ],
        }
        db = {
            "units": units,
            "relations": [
                _make_mock_relation("u2", "u1", "SUPPORTS"),
                _make_mock_relation("u3", "u1", "RESPONDS_TO"),  # Label disagreement
            ],
        }
        debate_dict = {"annotator_A": da, "annotator_B": db}
        unique_rels = extract_unique_positive_relations(debate_dict)

        assert len(unique_rels) == 2

        # Check intra-turn SUPPORTS
        rel_intra = next(r for r in unique_rels if r["source_unit_id"] == "u2")
        assert rel_intra["target_unit_id"] == "u1"
        assert rel_intra["turn_distance"] == 0
        assert rel_intra["unit_distance"] == 1
        assert rel_intra["same_speaker"] is True
        assert rel_intra["same_turn"] is True
        assert rel_intra["labels"] == {"annotator_A": "SUPPORTS", "annotator_B": "SUPPORTS"}

        # Check cross-turn ATTACKS / RESPONDS_TO
        rel_cross = next(r for r in unique_rels if r["source_unit_id"] == "u3")
        assert rel_cross["target_unit_id"] == "u1"
        assert rel_cross["turn_distance"] == 1
        assert rel_cross["unit_distance"] == 2
        assert rel_cross["same_speaker"] is False
        assert rel_cross["same_turn"] is False
        assert rel_cross["labels"] == {"annotator_A": "ATTACKS", "annotator_B": "RESPONDS_TO"}

    def test_direction_preservation_forward_intra_turn(self):
        """Verify that when source comes before target in text, direction is preserved."""
        units = [
            _make_mock_unit("u1", 0, "spk_1", char_start=0),
            _make_mock_unit("u2", 0, "spk_1", char_start=50),
        ]
        da = {"units": units, "relations": [_make_mock_relation("u1", "u2", "SUPPORTS")]}
        db = {"units": units, "relations": [_make_mock_relation("u1", "u2", "SUPPORTS")]}
        unique = extract_unique_positive_relations({"annotator_A": da, "annotator_B": db})

        assert len(unique) == 1
        assert unique[0]["source_unit_id"] == "u1"
        assert unique[0]["target_unit_id"] == "u2"
        assert unique[0]["signed_unit_delta"] == -1  # Source appears before target


class TestDistanceStatistics:
    """Tests for compute_distance_statistics."""

    def test_empty_input(self):
        stats = compute_distance_statistics([])
        assert stats["count"] == 0

    def test_statistical_distribution(self):
        rels = [
            {"turn_distance": 0, "unit_distance": 1},
            {"turn_distance": 0, "unit_distance": 2},
            {"turn_distance": 1, "unit_distance": 3},
            {"turn_distance": 3, "unit_distance": 6},
            {"turn_distance": 5, "unit_distance": 10},
        ]
        stats = compute_distance_statistics(rels)
        assert stats["count"] == 5
        assert stats["turn_distance"]["min"] == 0
        assert stats["turn_distance"]["median"] == 1.0
        assert stats["turn_distance"]["max"] == 5
        assert stats["turn_distance"]["counts"] == {0: 2, 1: 1, 3: 1, 5: 1}


class TestCandidateWindowsSimulation:
    """Tests for candidate pair window simulation."""

    def test_simulation_filtering(self):
        # 3 turns, 2 units per turn = 6 units
        units = [
            _make_mock_unit("u0", 0),
            _make_mock_unit("u1", 0),
            _make_mock_unit("u2", 1),
            _make_mock_unit("u3", 1),
            _make_mock_unit("u4", 2),
            _make_mock_unit("u5", 2),
        ]
        # Relations: u1->u0 (td=0), u2->u0 (td=1), u4->u0 (td=2)
        da = {
            "units": units,
            "relations": [
                _make_mock_relation("u1", "u0"),
                _make_mock_relation("u2", "u0"),
                _make_mock_relation("u4", "u0"),
            ],
        }
        debates = {"test_deb": {"annotator_A": da, "annotator_B": da}}
        sims = simulate_candidate_windows(debates, max_k=3)

        dir_sim = sims["directional_turn"]
        bidir_sim = sims["bidirectional_turn"]

        # At k=0, only intra-turn pairs are candidates
        # Turn 0 has (u0, u1) and (u1, u0) = 2; Turn 1 has 2; Turn 2 has 2 -> total 6
        assert dir_sim["0"]["candidates"] == 6
        assert dir_sim["0"]["captured_positive"] == 1
        assert dir_sim["0"]["recall_pct"] == pytest.approx(33.33, 0.1)

        # At k=1, directional captures u1->u0 and u2->u0 (2/3)
        assert dir_sim["1"]["captured_positive"] == 2
        assert dir_sim["1"]["recall_pct"] == pytest.approx(66.67, 0.1)

        # At k=2, directional captures all 3 relations
        assert dir_sim["2"]["captured_positive"] == 3
        assert dir_sim["2"]["recall_pct"] == 100.0

        # Directional candidates should be strictly less than bidirectional candidates for k >= 1
        assert dir_sim["1"]["candidates"] < bidir_sim["1"]["candidates"]
        assert dir_sim["2"]["candidates"] < bidir_sim["2"]["candidates"]
        assert dir_sim["2"]["captured_positive"] == bidir_sim["2"]["captured_positive"]


class TestPilotDataCalibration:
    """Integration test against actual pilot debates data."""

    def test_pilot_calibration_summary(self):
        rep = run_full_calibration_analysis()
        assert rep["overall_stats"]["count"] == 34
        assert rep["overall_stats"]["turn_distance"]["min"] == 0
        assert rep["overall_stats"]["turn_distance"]["max"] == 5
        assert rep["overall_stats"]["turn_distance"]["median"] == 0.0

        # Verify 3 disagreements
        assert len(rep["label_disagreements"]) == 3
        for d in rep["label_disagreements"]:
            assert {d["annotator_A"], d["annotator_B"]} == {"ATTACKS", "RESPONDS_TO"}

        # Verify directional simulation at k=3 captures 97.1% (33/34)
        k3 = rep["simulations"]["directional_turn"]["3"]
        assert k3["captured_positive"] == 33
        assert k3["recall_pct"] == pytest.approx(97.06, 0.1)
