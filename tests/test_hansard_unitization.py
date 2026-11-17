"""Tests for authentic UK Hansard transcript unitization and annotation templates.

Verifies:
1. Exact source integrity and SHA-256 matching between raw file and provenance.json.
2. Turn boundaries and speaker attribution across all 29 turns.
3. Proposition unitization: stable IDs, contiguous sequence, and sentence-level segmentation.
4. Character offset fidelity: document-level turn slicing and turn-level unit slicing.
5. Strict unannotated state of annotation templates (component_label is None).
6. Training gatekeeper enforcement: rejection of unannotated templates as production gold.
"""

import json
import hashlib
from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def raw_transcript_text() -> str:
    fp = PROJECT_ROOT / "data" / "raw" / "hansard" / "hansard_lords_ai_debate_2023.txt"
    assert fp.exists(), f"Raw transcript missing: {fp}"
    with open(fp, "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def processed_data() -> dict:
    fp = PROJECT_ROOT / "data" / "processed" / "hansard_lords_ai_debate_2023.json"
    assert fp.exists(), f"Processed data missing: {fp}"
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def annotator_templates() -> tuple:
    dir_path = PROJECT_ROOT / "data" / "annotations" / "templates"
    a_fp = dir_path / "debate_001_annotator_A_template.json"
    b_fp = dir_path / "debate_001_annotator_B_template.json"
    assert a_fp.exists(), f"Template A missing: {a_fp}"
    assert b_fp.exists(), f"Template B missing: {b_fp}"
    with open(a_fp, "r", encoding="utf-8") as f:
        a_data = json.load(f)
    with open(b_fp, "r", encoding="utf-8") as f:
        b_data = json.load(f)
    return a_data, b_data


class TestHansardUnitization:
    """Tests verifying authentic transcript unitization and annotation template integrity."""

    def test_raw_transcript_provenance_and_sha256(self, raw_transcript_text):
        """Raw transcript text must match provenance.json SHA-256 exactly."""
        calculated = hashlib.sha256(raw_transcript_text.encode("utf-8")).hexdigest()
        prov_path = PROJECT_ROOT / "data" / "raw" / "provenance.json"
        with open(prov_path, "r", encoding="utf-8") as f:
            prov = json.load(f)
        doc = next(d for d in prov["documents"] if d["document_id"] == "hansard_lords_ai_debate_2023")
        assert calculated == doc["checksum_sha256"]

    def test_processed_turns_and_speakers_count(self, processed_data):
        """Processed document must contain exactly 29 turns, 28 speakers, and 988 units."""
        meta = processed_data["document"]["metadata"]
        assert meta["turn_count"] == 29
        assert meta["speaker_count"] == 28
        assert meta["unit_count"] == 988
        assert len(processed_data["turns"]) == 29
        assert len(processed_data["speakers"]) == 28
        assert len(processed_data["units"]) == 988

    def test_turn_character_offsets_traceable_to_raw_text(self, raw_transcript_text, processed_data):
        """Every turn's char_start:char_end must slice the exact turn speech text in the raw file."""
        for turn in processed_data["turns"]:
            s = turn["char_start"]
            e = turn["char_end"]
            expected_text = turn["text"]
            actual_slice = raw_transcript_text[s:e]
            assert actual_slice == expected_text, (
                f"Turn {turn['turn_id']} slice mismatch at [{s}:{e}]"
            )

    def test_unit_character_offsets_traceable_to_turn_text(self, processed_data):
        """Every unit's char_start:char_end must slice the exact unit text in its turn's speech text."""
        turn_dict = {t["turn_id"]: t["text"] for t in processed_data["turns"]}
        for u in processed_data["units"]:
            tid = u["turn_id"]
            turn_text = turn_dict[tid]
            s = u["char_start"]
            e = u["char_end"]
            expected_text = u["text"]
            actual_slice = turn_text[s:e]
            assert actual_slice == expected_text, (
                f"Unit {u['unit_id']} in turn {tid} slice mismatch at [{s}:{e}]: "
                f"expected {expected_text!r}, got {actual_slice!r}"
            )

    def test_stable_sequential_unit_ids(self, processed_data):
        """Unit IDs must be strictly contiguous from u_0001 to u_0988 without duplicates."""
        uids = [u["unit_id"] for u in processed_data["units"]]
        assert len(uids) == len(set(uids)), "Duplicate unit IDs detected"
        for i, uid in enumerate(uids):
            assert uid == f"u_{i + 1:04d}", f"Non-sequential unit ID: expected u_{i + 1:04d}, got {uid}"

    def test_speaker_attribution_consistency(self, processed_data):
        """Every unit's speaker_id must match its turn's speaker_id and a registered speaker."""
        registered_spk_ids = {s["speaker_id"] for s in processed_data["speakers"]}
        turn_spk_map = {t["turn_id"]: t["speaker_id"] for t in processed_data["turns"]}

        for u in processed_data["units"]:
            spk = u["speaker_id"]
            assert spk in registered_spk_ids, f"Unit {u['unit_id']} has unknown speaker {spk}"
            assert spk == turn_spk_map[u["turn_id"]], (
                f"Unit {u['unit_id']} speaker {spk} does not match turn speaker {turn_spk_map[u['turn_id']]}"
            )

    def test_unannotated_templates_integrity(self, annotator_templates):
        """Templates for Annotator A and B must be fully unannotated with zero fabricated labels."""
        tpl_a, tpl_b = annotator_templates
        for tpl, expected_ann in [(tpl_a, "annotator_A"), (tpl_b, "annotator_B")]:
            assert tpl["annotator_id"] == expected_ann
            assert tpl["status"] == "UNANNOTATED_TEMPLATE"
            assert tpl["candidate_relation_policy"] == "provisional_directional_k3"
            assert len(tpl["units"]) == 988
            assert tpl["relations"] == []

            for u in tpl["units"]:
                assert u["component_label"] is None, f"Unit {u['unit_id']} must have component_label None"
                assert u["confidence"] is None, f"Unit {u['unit_id']} must have confidence None"
                assert u["annotator_id"] == expected_ann

    def test_training_gatekeeper_rejects_unannotated_templates(self):
        """Training gatekeeper must strictly reject unannotated templates from being used as gold."""
        from ml.data.dataset_loader import check_gold_dataset_readiness
        templates_dir = PROJECT_ROOT / "data" / "annotations" / "templates"
        is_ready, reason, files = check_gold_dataset_readiness(templates_dir)
        # Templates are not gold; gatekeeper must reject them
        assert not is_ready
        assert "no production argumap gold annotations" in reason.lower() or "blocked" in reason.lower()
