"""Pydantic Schemas for Analysis Requests, Runs, and Insights."""

from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.debate import SpeakerSchema
from app.schemas.argument import ArgumentSchema, RelationSchema

InsightType = Literal[
    "UNSUPPORTED_CLAIM",
    "UNANSWERED_COUNTERARGUMENT",
    "DIRECT_CLASH",
    "ORPHAN_EVIDENCE",
]

InsightSeverity = Literal[
    "INFO",
    "WARNING",
    "ALERT",
]


class InsightSchema(BaseModel):
    id: str
    type: InsightType
    severity: InsightSeverity
    message: str
    related_argument_ids: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class AnalysisOptions(BaseModel):
    include_other_components: Optional[bool] = False
    confidence_threshold: Optional[float] = Field(0.50, ge=0.0, le=1.0)


class AnalysisRequest(BaseModel):
    title: Optional[str] = Field("Debate Analysis Session", min_length=1, max_length=255)
    raw_transcript: str = Field(..., min_length=1, description="Raw debate transcript text with speaker labels")
    options: Optional[AnalysisOptions] = Field(default_factory=AnalysisOptions)


class AnalysisSummary(BaseModel):
    speaker_count: int = 0
    turn_count: int = 0
    argument_count: int = 0
    relation_count: int = 0
    insights_count: int = 0


class AnalysisResponse(BaseModel):
    analysis_id: str
    debate_id: str
    status: str
    message: Optional[str] = None
    model_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    summary: Optional[AnalysisSummary] = None
    speakers: List[SpeakerSchema] = []
    arguments: List[ArgumentSchema] = []
    relations: List[RelationSchema] = []
    insights: List[InsightSchema] = []

    model_config = ConfigDict(from_attributes=True)
