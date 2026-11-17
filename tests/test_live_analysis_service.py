"""Comprehensive Unit and Integration Tests for ARGUMAP Live Analysis Service.

Covers Phase 2 requirements:
1. Multi-sentence speaker turns.
2. Proposition-level clause segmentation.
3. Character offset integrity (turn.text[start:end] == unit.text).
4. Frozen component classification adherence and confidence scores.
5. Pairwise relationship ID validity, no self-loops, and no duplicate edges.
6. Structural insight generation and valid node references.
7. Full pipeline integration on canonical academic debate transcripts.
"""

import pytest
from pathlib import Path
import sys

# Ensure backend is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
for p in (PROJECT_ROOT, BACKEND_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.services.analysis_service import AnalysisService, analysis_service
from ml.data.label_encoder import FROZEN_COMPONENT_LABELS

FROZEN_RELATION_LABELS = {"SUPPORTS", "ATTACKS", "RESPONDS_TO", "NO_RELATION"}
VALID_INSIGHT_TYPES = {
    "UNSUPPORTED_CLAIM",
    "UNANSWERED_COUNTERARGUMENT",
    "DIRECT_CLASH",
    "ORPHAN_EVIDENCE",
}


# ==============================================================================
# 1. Multi-sentence Speaker Turns & Offset Integrity
# ==============================================================================

def test_multi_sentence_speaker_turns():
    """Verify that turns containing multiple sentences produce sequential argument units."""
    transcript = (
        "Speaker A: Artificial intelligence improves learning outcomes. "
        "It provides personalized feedback to students. "
        "Teachers can focus on mentoring rather than grading.\n"
        "Speaker B: However, algorithmic bias remains a severe risk."
    )
    result = analysis_service.run(transcript)

    assert len(result.speakers) == 2
    assert len(result.turns) == 2

    # Speaker A's turn has 3 sentences
    turn_1_args = [a for a in result.arguments if a.turn_id == result.turns[0].turn_id]
    assert len(turn_1_args) == 3

    # All units must retain correct turn order and speaker attribution
    for arg in turn_1_args:
        assert arg.speaker_name == "Speaker A"
        assert arg.turn_order == 1

    turn_1 = result.turns[0]
    for arg in turn_1_args:
        assert turn_1.text[arg.start_char:arg.end_char] == arg.text


def test_character_offset_integrity():
    """Verify that every argument unit text exactly matches the turn text slice."""
    transcript = (
        "Speaker A: In 2024, empirical studies confirmed a 23% increase in comprehension.\n"
        "Speaker B: However, excessive screen time diminishes attention spans.\n"
        "Speaker A: This concern can be addressed through scheduled offline activities."
    )
    result = analysis_service.run(transcript)
    turn_dict = {t.turn_id: t for t in result.turns}

    assert len(result.arguments) >= 3
    for arg in result.arguments:
        parent_turn = turn_dict[arg.turn_id]
        assert arg.start_char >= 0
        assert arg.end_char > arg.start_char
        assert parent_turn.text[arg.start_char:arg.end_char] == arg.text


# ==============================================================================
# 2. Proposition-Level Segmentation
# ==============================================================================

def test_proposition_level_clause_splitting():
    """Verify that independent coordinated clauses are segmented into separate units."""
    transcript = (
        "Speaker A: We must fund renewable energy initiatives, "
        "but fossil fuel subsidies continue to expand rapidly."
    )
    result = analysis_service.run(transcript)

    # Should be split into 2 units despite being a single turn
    assert len(result.arguments) == 2
    assert "We must fund renewable energy initiatives" in result.arguments[0].text
    assert "fossil fuel subsidies continue to expand rapidly" in result.arguments[1].text

    turn = result.turns[0]
    assert turn.text[result.arguments[0].start_char:result.arguments[0].end_char] == result.arguments[0].text
    assert turn.text[result.arguments[1].start_char:result.arguments[1].end_char] == result.arguments[1].text


# ==============================================================================
# 3. Classification Output & Taxonomy Adherence
# ==============================================================================

def test_classification_taxonomy_and_confidence():
    """Verify that every classified unit uses frozen labels and valid confidence scores."""
    transcript = (
        "Speaker A: AI should be used in education because it enables personalized learning at scale.\n"
        "Speaker A: A 2024 Stanford study found a 23% improvement in retention when adaptive tutoring was used.\n"
        "Speaker B: However, excessive dependence on AI can reduce students' independent critical thinking.\n"
        "Speaker A: This risk can be reduced through structured teacher supervision."
    )
    result = analysis_service.run(transcript)

    assert len(result.arguments) >= 4
    for arg in result.arguments:
        assert arg.component_type in FROZEN_COMPONENT_LABELS, f"Invalid label: {arg.component_type}"
        assert 0.0 <= arg.confidence <= 1.0, f"Confidence out of range: {arg.confidence}"

    # Verify plausible heuristic classification
    types = [a.component_type for a in result.arguments]
    assert "EVIDENCE" in types or "PREMISE" in types
    assert "COUNTERARGUMENT" in types
    assert "REBUTTAL" in types


# ==============================================================================
# 4. Relationship Extraction Integrity
# ==============================================================================

def test_relationship_id_validity_and_no_self_loops():
    """Verify that relation links refer only to valid argument IDs and contain zero self-loops."""
    transcript = (
        "Speaker A: AI should be deployed in classrooms.\n"
        "Speaker A: It enables personalized tutoring.\n"
        "Speaker B: However, it compromises critical reasoning skills.\n"
        "Speaker A: This risk can be managed with active educator guidance."
    )
    result = analysis_service.run(transcript)
    valid_arg_ids = {a.unit_id for a in result.arguments}

    seen_pairs = set()
    for rel in result.relations:
        # 1. Valid IDs
        assert rel.source_id in valid_arg_ids, f"Invalid source_id: {rel.source_id}"
        assert rel.target_id in valid_arg_ids, f"Invalid target_id: {rel.target_id}"

        # 2. No self-loops
        assert rel.source_id != rel.target_id, f"Self-referencing relation detected: {rel.relation_id}"

        # 3. Frozen relation taxonomy
        assert rel.relation_type in FROZEN_RELATION_LABELS

        # 4. No duplicate directed pairs
        pair = (rel.source_id, rel.target_id)
        assert pair not in seen_pairs, f"Duplicate relation pair: {pair}"
        seen_pairs.add(pair)


# ==============================================================================
# 5. Structural Insight Generation
# ==============================================================================

def test_structural_insights_generation_and_references():
    """Verify that reasoning engine generates valid insight types referencing real nodes."""
    transcript = (
        "Speaker A: We must completely overhaul public transportation.\n"
        "Speaker B: However, budget deficits prevent major capital expenditures.\n"
        "Speaker A: This risk can be reduced by public-private infrastructure bonds."
    )
    result = analysis_service.run(transcript)
    valid_arg_ids = {a.unit_id for a in result.arguments}

    assert len(result.insights) > 0
    for ins in result.insights:
        assert ins["type"] in VALID_INSIGHT_TYPES
        assert ins["severity"] in {"INFO", "WARNING", "ALERT"}
        assert isinstance(ins["message"], str) and len(ins["message"]) > 0

        # Check related argument IDs
        for rel_arg_id in ins.get("related_argument_ids", []):
            assert rel_arg_id in valid_arg_ids, f"Insight references non-existent node: {rel_arg_id}"


# ==============================================================================
# 6. Edge Cases
# ==============================================================================

def test_empty_transcript_handling():
    """Verify graceful handling of empty or whitespace-only discourse."""
    result = analysis_service.run("   \n\t  ")
    assert result.speakers == []
    assert result.turns == []
    assert result.arguments == []
    assert result.relations == []
    assert result.insights == []
    assert len(result.warnings) > 0


def test_single_speaker_monologue():
    """Verify pipeline functions correctly with a single speaker presenting arguments."""
    transcript = (
        "Speaker A: Renewable energy is imperative for ecological sustainability. "
        "A 2024 IPCC report showed solar costs fell by 82% over the last decade. "
        "Therefore, governments should accelerate clean energy subsidies."
    )
    result = analysis_service.run(transcript)
    assert len(result.speakers) == 1
    assert result.speakers[0].speaker_name == "Speaker A"
    assert len(result.arguments) == 3

