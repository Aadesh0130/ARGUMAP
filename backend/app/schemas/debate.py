"""Pydantic Schemas for Debate Sessions, Speakers, and Turns."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SpeakerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Speaker name")


class SpeakerSchema(SpeakerBase):
    id: str
    debate_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TurnBase(BaseModel):
    speaker_id: str
    turn_order: int = Field(..., ge=1, description="Chronological turn sequence index")
    text: str = Field(..., min_length=1, description="Utterance text for the turn")


class TurnSchema(TurnBase):
    id: str
    debate_id: Optional[str] = None
    speaker_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DebateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Title of the debate")
    raw_transcript: str = Field(..., min_length=1, description="Raw debate transcript text with speaker labels")


class DebateResponse(BaseModel):
    debate_id: str
    title: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunSummary(BaseModel):
    analysis_id: str
    status: str
    model_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DebateDetailResponse(BaseModel):
    debate_id: str
    title: str
    status: str
    created_at: datetime
    speakers: List[SpeakerSchema] = []
    turns: List[TurnSchema] = []
    analysis_runs: List[AnalysisRunSummary] = []

    model_config = ConfigDict(from_attributes=True)
