"""Debate Management API Router."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.debate import DebateCreate, DebateResponse, DebateDetailResponse
from app.services.debate_service import DebateService
from app.core.errors import AppException

router = APIRouter(prefix="/debates", tags=["Debates"])


@router.post(
    "",
    response_model=DebateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Debate Session"
)
def create_debate(debate_in: DebateCreate, db: Session = Depends(get_db)):
    """Creates a new debate session record with parsed speaker turns."""
    if not debate_in.raw_transcript.strip():
        raise AppException(
            code="EMPTY_TRANSCRIPT",
            message="Field 'raw_transcript' must contain discourse text.",
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        )

    debate = DebateService.create_debate(db, debate_in)
    return DebateResponse(
        debate_id=debate.id,
        title=debate.title,
        status=debate.status,
        created_at=debate.created_at,
    )


@router.get(
    "/{debate_id}",
    response_model=DebateDetailResponse,
    summary="Get Debate Details by ID"
)
def get_debate(debate_id: str, db: Session = Depends(get_db)):
    """Retrieves debate session metadata, normalized speech turns, and analysis history."""
    debate = DebateService.get_debate(db, debate_id)
    if not debate:
        raise AppException(
            code="DEBATE_NOT_FOUND",
            message=f"Debate '{debate_id}' does not exist.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Format turns with speaker names
    speaker_dict = {s.id: s.name for s in debate.speakers}
    turns_payload = []
    for turn in debate.turns:
        turns_payload.append({
            "id": turn.id,
            "debate_id": turn.debate_id,
            "speaker_id": turn.speaker_id,
            "speaker_name": speaker_dict.get(turn.speaker_id, "Unknown"),
            "turn_order": turn.turn_order,
            "text": turn.text,
            "created_at": turn.created_at,
        })

    # Format runs
    runs_payload = []
    for run in debate.analysis_runs:
        runs_payload.append({
            "analysis_id": run.id,
            "status": run.status,
            "model_version": run.model_version,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
        })

    return DebateDetailResponse(
        debate_id=debate.id,
        title=debate.title,
        status=debate.status,
        created_at=debate.created_at,
        speakers=debate.speakers,
        turns=turns_payload,
        analysis_runs=runs_payload,
    )
