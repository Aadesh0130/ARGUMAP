"""Comprehensive Test Suite for ARGUMAP NLP Preprocessing Pipeline.

Validates:
1. Speaker parsing (inline, header, repeated, unknown fallback).
2. Normalization (whitespace, line endings, preservation of punctuation/numbers/quotes).
3. Sentence segmentation (abbreviations, decimals, questions, quotes).
4. Conservative proposition segmentation (default sentence, independent clauses, no aggressive splitting).
5. Offset integrity (char_start >= 0, char_end > char_start, exact substring match).
6. Determinism (idempotency, identical IDs and ordering).
7. Strict absence of fake component and relation classifications.
8. Edge cases (empty transcript, single speaker, unformatted text).
"""

import sys
from pathlib import Path
import pytest

# Ensure backend is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.nlp import (
    preprocess_transcript,
    TextNormalizer,
    SpeakerParser,
    SentenceSegmenter,
    PropositionSegmenter,
)


# ==============================================================================
# 1. Normalization Tests
# ==============================================================================

def test_normalization_whitespace_and_line_endings():
    raw = "Speaker A:   Hello   world.  \r\n\r\n\r\nSpeaker B:\tThis is   a test.\r\n"
    normalized = TextNormalizer.normalize(raw)
    assert "\r" not in normalized
    assert "   " not in normalized
    assert "\t" not in normalized
    assert "Speaker A: Hello world.\n\nSpeaker B: This is a test." == normalized


def test_normalization_preserves_punctuation_numbers_quotes():
    raw = 'Speaker A: In 2024, the U.S. economy grew by 2.5%; however, "inflation" remained high?'
    normalized = TextNormalizer.normalize(raw)
    assert "2024" in normalized
    assert "2.5%" in normalized
    assert "?" in normalized
    assert ";" in normalized
    assert '"inflation"' in normalized


# ==============================================================================
# 2. Speaker and Turn Extraction Tests
# ==============================================================================

def test_speaker_parser_inline_colon():
    transcript = (
        "Speaker A: Universal healthcare ensures equitable access.\n"
        "Speaker B: However, single-payer systems lead to increased wait times.\n"
        "Speaker A: Targeted funding can eliminate surgical backlogs."
    )
    parser = SpeakerParser()
    speakers, turns, warnings = parser.parse(transcript)

    assert len(speakers) == 2
    assert len(turns) == 3
    assert speakers[0].speaker_name == "Speaker A"
    assert speakers[1].speaker_name == "Speaker B"
    assert turns[0].turn_index == 0
    assert turns[0].speaker_name == "Speaker A"
    assert turns[1].speaker_name == "Speaker B"
    assert turns[2].speaker_name == "Speaker A"


def test_speaker_parser_consecutive_turns_consolidation():
    transcript = (
        "Speaker A: First sentence.\n"
        "Speaker A: Second sentence immediately following."
    )
    parser = SpeakerParser()
    speakers, turns, _ = parser.parse(transcript)

    assert len(speakers) == 1
    assert len(turns) == 1
    assert "First sentence. Second sentence immediately following." == turns[0].text


def test_speaker_parser_standalone_header():
    transcript = (
        "CLINTON\n"
        "Clean energy investments create high-paying domestic jobs.\n\n"
        "TRUMP\n"
        "These regulations hurt American manufacturing."
    )
    parser = SpeakerParser()
    speakers, turns, _ = parser.parse(transcript)

    assert len(speakers) == 2
    assert len(turns) == 2
    assert speakers[0].speaker_name == "CLINTON"
    assert speakers[1].speaker_name == "TRUMP"


def test_speaker_parser_unknown_fallback():
    transcript = "This is a plain paragraph without any speaker indicators or colons."
    parser = SpeakerParser()
    speakers, turns, warnings = parser.parse(transcript)

    assert len(speakers) == 1
    assert speakers[0].speaker_name == "UNKNOWN_SPEAKER_1"
    assert len(turns) == 1
    assert any("Defaulted to UNKNOWN_SPEAKER_1" in w for w in warnings)


# ==============================================================================
# 3. Sentence Segmentation Tests
# ==============================================================================

def test_sentence_segmenter_basic_and_punctuation():
    text = "AI improves education! Does it really? Yes, it certainly does."
    segmenter = SentenceSegmenter()
    sentences = segmenter.segment(text)

    assert len(sentences) == 3
    assert sentences[0]["text"] == "AI improves education!"
    assert sentences[1]["text"] == "Does it really?"
    assert sentences[2]["text"] == "Yes, it certainly does."
    for s in sentences:
        assert text[s["char_start"]:s["char_end"]] == s["text"]


def test_sentence_segmenter_handles_abbreviations_and_decimals():
    text = "Dr. Smith met with Sen. Jones at 10 a.m. regarding the U.S. economy. Growth was 3.5%."
    segmenter = SentenceSegmenter()
    sentences = segmenter.segment(text)

    # Should not split on Dr., Sen., U.S., or 3.5
    assert len(sentences) == 2
    assert sentences[0]["text"] == "Dr. Smith met with Sen. Jones at 10 a.m. regarding the U.S. economy."
    assert sentences[1]["text"] == "Growth was 3.5%."
    for s in sentences:
        assert text[s["char_start"]:s["char_end"]] == s["text"]


def test_sentence_segmenter_empty_input():
    segmenter = SentenceSegmenter()
    assert segmenter.segment("") == []
    assert segmenter.segment("   ") == []


# ==============================================================================
# 4. Proposition / Clause Segmentation Tests
# ==============================================================================

def test_proposition_segmenter_default_sentence_behavior():
    # Causal "because" should remain one unit by default
    turn_text = "AI should be used in education because it enables personalized learning."
    sentences = [{
        "sentence_index": 0,
        "text": turn_text,
        "char_start": 0,
        "char_end": len(turn_text),
    }]
    segmenter = PropositionSegmenter()
    units = segmenter.segment_turn("doc1", "turn1", "spk1", 0, turn_text, sentences)

    assert len(units) == 1
    assert units[0].text == turn_text
    assert units[0].component_label is None


def test_proposition_segmenter_splits_independent_clauses():
    # Coordinated independent clauses with comma + conjunction and independent subjects
    turn_text = "Automated tutoring improves student math proficiency, and personalized systems reduce repetitive grading for instructors."
    sentences = [{
        "sentence_index": 0,
        "text": turn_text,
        "char_start": 0,
        "char_end": len(turn_text),
    }]
    segmenter = PropositionSegmenter()
    units = segmenter.segment_turn("doc1", "turn1", "spk1", 0, turn_text, sentences)

    assert len(units) == 2
    assert units[0].text == "Automated tutoring improves student math proficiency"
    assert units[1].text == "personalized systems reduce repetitive grading for instructors."
    for u in units:
        assert turn_text[u.char_start:u.char_end] == u.text
        assert u.component_label is None


def test_proposition_segmenter_avoids_aggressive_comma_splitting():
    # Comma-separated list should NOT be split into clauses
    turn_text = "We must approach this issue carefully, methodically, and comprehensively."
    sentences = [{
        "sentence_index": 0,
        "text": turn_text,
        "char_start": 0,
        "char_end": len(turn_text),
    }]
    segmenter = PropositionSegmenter()
    units = segmenter.segment_turn("doc1", "turn1", "spk1", 0, turn_text, sentences)

    assert len(units) == 1
    assert units[0].text == turn_text


# ==============================================================================
# 5. Full Pipeline & Offset Integrity Tests
# ==============================================================================

def test_full_pipeline_offsets_and_subspans():
    transcript = (
        "Speaker A: AI improves education because it enables personalized learning.\n"
        "Speaker B: However, excessive dependence on AI reduces critical thinking.\n"
        "Speaker A: This risk can be mitigated through strict supervision."
    )
    result = preprocess_transcript(transcript)

    assert result.validation.is_valid
    assert len(result.speakers) == 2
    assert len(result.turns) == 3
    assert len(result.units) >= 3

    # Check offset integrity for every unit relative to parent turn
    turn_map = {t.turn_id: t for t in result.turns}
    for unit in result.units:
        turn = turn_map[unit.turn_id]
        extracted_slice = turn.text[unit.char_start:unit.char_end]
        assert extracted_slice == unit.text
        assert unit.char_start >= 0
        assert unit.char_end > unit.char_start
        # Crucial: component_label must remain None
        assert unit.component_label is None


def test_pipeline_determinism():
    transcript = (
        "Speaker A: We need carbon taxation to curb emissions.\n"
        "Speaker B: Carbon taxation places an unfair burden on working families."
    )
    run1 = preprocess_transcript(transcript)
    run2 = preprocess_transcript(transcript)

    # Identical IDs, counts, and texts
    assert run1.document.document_id == run2.document.document_id
    assert [s.speaker_id for s in run1.speakers] == [s.speaker_id for s in run2.speakers]
    assert [t.turn_id for t in run1.turns] == [t.turn_id for t in run2.turns]
    assert [u.unit_id for u in run1.units] == [u.unit_id for u in run2.units]
    assert [u.text for u in run1.units] == [u.text for u in run2.units]
    assert run1.model_dump() == run2.model_dump()


def test_pipeline_edge_cases():
    # Empty transcript
    empty_res = preprocess_transcript("")
    assert empty_res.validation.is_valid
    assert len(empty_res.turns) == 0
    assert len(empty_res.units) == 0

    # Whitespace only
    ws_res = preprocess_transcript("   \n\n\t  ")
    assert ws_res.validation.is_valid
    assert len(ws_res.turns) == 0

    # Single short turn
    single_res = preprocess_transcript("Speaker A: Yes.")
    assert single_res.validation.is_valid
    assert len(single_res.turns) == 1
    assert len(single_res.units) == 1
    assert single_res.units[0].text == "Yes."
