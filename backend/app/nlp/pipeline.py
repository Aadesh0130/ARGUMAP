"""High-level Orchestration Pipeline for ARGUMAP NLP Preprocessing.

Coordinates:
Raw Transcript -> Normalization -> Speaker/Turn Parsing -> Sentence Segmentation
-> Proposition Segmentation -> Offset & Integrity Validation -> PreprocessingResult.
"""

import hashlib
from typing import Optional, Dict, Any, List
from .models import (
    DebateDocument,
    Speaker,
    Turn,
    ArgumentUnit,
    PreprocessingValidation,
    PreprocessingResult,
)
from .normalization import TextNormalizer
from .speaker_parser import SpeakerParser
from .sentence_segmenter import SentenceSegmenter
from .proposition_segmenter import PropositionSegmenter


class PreprocessingPipeline:
    """End-to-end deterministic NLP Preprocessing Pipeline."""

    def __init__(
        self,
        normalizer: Optional[TextNormalizer] = None,
        speaker_parser: Optional[SpeakerParser] = None,
        sentence_segmenter: Optional[SentenceSegmenter] = None,
        proposition_segmenter: Optional[PropositionSegmenter] = None,
    ):
        self.normalizer = normalizer or TextNormalizer()
        self.speaker_parser = speaker_parser or SpeakerParser()
        self.sentence_segmenter = sentence_segmenter or SentenceSegmenter()
        self.proposition_segmenter = proposition_segmenter or PropositionSegmenter()

    def process(
        self,
        transcript_text: str,
        document_id: Optional[str] = None,
        source_corpus: str = "custom",
        source_license: str = "UNVERIFIED",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PreprocessingResult:
        """Processes raw debate discourse into structured argument units."""
        metadata = metadata or {}
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Deterministic Document ID generation
        if not document_id:
            # Deterministic hash of first 100 characters + length
            h = hashlib.sha256(transcript_text.encode("utf-8")).hexdigest()[:8]
            document_id = f"debate_{h}"

        # 2. Check for empty transcript
        if not transcript_text or not transcript_text.strip():
            warnings.append("Empty transcript submitted for preprocessing.")
            doc = DebateDocument(
                document_id=document_id,
                source_corpus=source_corpus,
                source_license=source_license,
                text="",
                metadata=metadata,
            )
            return PreprocessingResult(
                document=doc,
                speakers=[],
                turns=[],
                units=[],
                metadata=metadata,
                validation=PreprocessingValidation(is_valid=True, warnings=warnings),
            )

        # 3. Normalization
        normalized_text = self.normalizer.normalize(transcript_text)

        # 4. Speaker and Turn Extraction
        speakers, turns, spk_warnings = self.speaker_parser.parse(normalized_text)
        warnings.extend(spk_warnings)

        # 5. Sentence and Proposition Segmentation
        all_units: List[ArgumentUnit] = []
        turn_map = {t.turn_id: t for t in turns}

        for turn in turns:
            # Sentence segmentation
            sentences = self.sentence_segmenter.segment(turn.text)
            if not sentences and turn.text.strip():
                # Fallback for turn without sentence delimiters
                sentences = [{
                    "sentence_index": 0,
                    "text": turn.text.strip(),
                    "char_start": 0,
                    "char_end": len(turn.text.strip()),
                }]

            # Proposition segmentation
            turn_units = self.proposition_segmenter.segment_turn(
                document_id=document_id,
                turn_id=turn.turn_id,
                speaker_id=turn.speaker_id,
                turn_index=turn.turn_index,
                turn_text=turn.text,
                sentences=sentences,
                unit_offset_counter=len(all_units) + 1,
            )
            all_units.extend(turn_units)

        # 6. Integrity & Offset Validation
        for unit in all_units:
            # Check component_label is strictly None
            if unit.component_label is not None:
                errors.append(f"Unit {unit.unit_id} has assigned component_label '{unit.component_label}'. Must be None.")

            # Validate offsets relative to parent turn
            parent_turn = turn_map.get(unit.turn_id)
            if not parent_turn:
                errors.append(f"Unit {unit.unit_id} references nonexistent turn {unit.turn_id}.")
                continue

            # Verify substring match
            turn_slice = parent_turn.text[unit.char_start:unit.char_end]
            if turn_slice != unit.text:
                errors.append(
                    f"Offset mismatch for {unit.unit_id}: "
                    f"expected '{unit.text}', got slice '{turn_slice}'."
                )

        doc = DebateDocument(
            document_id=document_id,
            source_corpus=source_corpus,
            source_license=source_license,
            text=normalized_text,
            metadata={
                **metadata,
                "raw_character_count": len(transcript_text),
                "normalized_character_count": len(normalized_text),
                "speaker_count": len(speakers),
                "turn_count": len(turns),
                "unit_count": len(all_units),
            },
        )

        is_valid = len(errors) == 0
        validation_report = PreprocessingValidation(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
        )

        return PreprocessingResult(
            document=doc,
            speakers=speakers,
            turns=turns,
            units=all_units,
            metadata=doc.metadata,
            validation=validation_report,
        )


# Global default pipeline instance
default_pipeline = PreprocessingPipeline()


def preprocess_transcript(
    transcript_text: str,
    document_id: Optional[str] = None,
    source_corpus: str = "custom",
    source_license: str = "UNVERIFIED",
    metadata: Optional[Dict[str, Any]] = None,
) -> PreprocessingResult:
    """Convenience functional interface for preprocessing debate transcripts."""
    return default_pipeline.process(
        transcript_text=transcript_text,
        document_id=document_id,
        source_corpus=source_corpus,
        source_license=source_license,
        metadata=metadata,
    )
