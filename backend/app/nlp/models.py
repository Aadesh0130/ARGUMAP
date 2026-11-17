"""Data Models for ARGUMAP NLP Preprocessing Pipeline.

Provides strongly-typed schemas for documents, speakers, turns, argument units,
and validation results.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, model_validator


class DebateDocument(BaseModel):
    """Represents the raw/normalized debate discourse document."""
    document_id: str
    source_corpus: str = "custom"
    source_license: str = "UNVERIFIED"
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Speaker(BaseModel):
    """Represents a participant or debater in the transcript."""
    speaker_id: str
    speaker_name: str
    speaker_role: Optional[str] = None  # e.g., 'Debater', 'Moderator', 'Audience'
    speaker_side: Optional[str] = None  # e.g., 'Affirmative', 'Negative', 'Neutral'


class Turn(BaseModel):
    """Represents an uninterrupted utterance block attributed to a single speaker."""
    turn_id: str
    turn_index: int
    speaker_id: str
    speaker_name: str
    text: str
    char_start: int  # Offset in parent document.text
    char_end: int    # Offset in parent document.text

    @model_validator(mode="after")
    def validate_turn_offsets(self) -> "Turn":
        if self.char_start < 0:
            raise ValueError(f"char_start must be non-negative, got {self.char_start}")
        if self.char_end <= self.char_start and len(self.text) > 0:
            raise ValueError(f"char_end ({self.char_end}) must be greater than char_start ({self.char_start})")
        return self


class ArgumentUnit(BaseModel):
    """Represents a segmented argumentative proposition ready for downstream classification."""
    unit_id: str
    document_id: str
    turn_id: str
    speaker_id: str
    turn_index: int
    unit_index: int
    text: str
    char_start: int  # Offset relative to parent Turn.text
    char_end: int    # Offset relative to parent Turn.text
    sentence_index: int
    component_label: Optional[str] = None  # Strictly null/unset during preprocessing!

    @model_validator(mode="after")
    def validate_unit_offsets(self) -> "ArgumentUnit":
        if self.char_start < 0:
            raise ValueError(f"char_start must be non-negative, got {self.char_start}")
        if self.char_end <= self.char_start and len(self.text) > 0:
            raise ValueError(f"char_end ({self.char_end}) must be greater than char_start ({self.char_start})")
        # Ensure component_label is NOT assigned in preprocessing
        if self.component_label is not None:
            raise ValueError("component_label must remain None during Step 6 preprocessing.")
        return self


class PreprocessingValidation(BaseModel):
    """Validation report generated during transcript preprocessing."""
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PreprocessingResult(BaseModel):
    """Comprehensive structured payload returned by the NLP Preprocessing Pipeline."""
    document: DebateDocument
    speakers: List[Speaker]
    turns: List[Turn]
    units: List[ArgumentUnit]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    validation: PreprocessingValidation = Field(default_factory=PreprocessingValidation)
