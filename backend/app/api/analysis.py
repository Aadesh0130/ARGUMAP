"""Analysis Execution & Retrieval API Router."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import AppException
from app.db.session import get_db
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSummary,
    InsightSchema,
)
from app.schemas.argument import ArgumentSchema, RelationSchema
from app.schemas.debate import DebateCreate, SpeakerSchema
from app.services.analysis_service import analysis_service
from app.services.debate_service import DebateService
from app.services.tts_service import tts_service, TTSUnavailableError

router = APIRouter(tags=["Analysis"])


# ---------------------------------------------------------------------------
# POST /analyze  — Full pipeline (speaker parse → classify → insight)
# ---------------------------------------------------------------------------

@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Debate Transcript – Speaker POVs, Claims, Rebuttals & Insights",
)
def analyze_transcript(request: AnalysisRequest, db: Session = Depends(get_db)):
    """
    Ingests a debate / discussion transcript and runs the full argument
    analysis pipeline:

    * **Speaker detection** – identifies each participant (A, B, C …) and
      their point of view across turns.
    * **Argument classification** – labels each sentence as CLAIM, PREMISE,
      EVIDENCE, COUNTERARGUMENT, REBUTTAL, or OTHER.
    * **Relation inference** – links supporting and attacking argument units
      across speakers.
    * **Structural insights** – flags unsupported claims, unanswered
      counterarguments, direct clashes, and orphan evidence.
    * **Corrections** – per-unit confidence scores indicate how strongly the
      heuristic classifier agrees with each label.
    """
    if not request.raw_transcript.strip():
        raise AppException(
            code="EMPTY_TRANSCRIPT",
            message="Field 'raw_transcript' must contain debate discourse text.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # ---- Run the full NLP + classification pipeline --------------------
    result = analysis_service.run(request.raw_transcript)

    # ---- Persist debate, entities, graph snapshots & run atomically ---
    saved = DebateService.save_full_analysis(
        db=db,
        title=request.title or "Debate Analysis Session",
        raw_transcript=request.raw_transcript,
        result=result,
    )
    debate = saved["debate"]
    run = saved["run"]

    return AnalysisResponse(
        analysis_id=run.id,
        debate_id=debate.id,
        status="completed",
        message=(
            f"Analysis complete. {len(result.warnings)} parser warning(s). "
            + ("; ".join(result.warnings) if result.warnings else "")
        ).strip(),
        model_version=result.model_version,
        created_at=run.created_at,
        completed_at=run.completed_at,
        summary=saved["summary"],
        speakers=saved["speakers"],
        arguments=saved["arguments"],
        relations=saved["relations"],
        insights=saved["insights"],
    )


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get Analysis Run by ID"
)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieves an analysis run with its serialized argument graph and insights snapshot."""
    run = DebateService.get_analysis_run(db, analysis_id)
    if not run:
        raise AppException(
            code="ANALYSIS_NOT_FOUND",
            message=f"Analysis run '{analysis_id}' does not exist.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    debate = run.debate
    speaker_schemas = [
        SpeakerSchema(id=s.id, debate_id=s.debate_id, name=s.name, created_at=s.created_at)
        for s in (debate.speakers if debate else [])
    ]

    graph_snapshot = run.graph_snapshot or {}
    insights_snapshot = run.insights_snapshot or []

    # Reconstruct arguments: prefer snapshot, fallback to relational records
    if graph_snapshot.get("arguments"):
        argument_schemas = [ArgumentSchema(**a) for a in graph_snapshot["arguments"]]
    elif debate and debate.arguments:
        turn_map = {t.id: t.turn_order for t in debate.turns}
        argument_schemas = [
            ArgumentSchema(
                id=a.id,
                turn_id=a.turn_id,
                speaker_id=a.speaker_id,
                text=a.text,
                component_type=a.component_type,
                confidence=a.confidence,
                turn_order=turn_map.get(a.turn_id, 1),
                start_char=a.start_char,
                end_char=a.end_char,
            )
            for a in debate.arguments
        ]
    else:
        argument_schemas = []

    # Reconstruct relations: prefer snapshot, fallback to relational records
    if graph_snapshot.get("relations"):
        relation_schemas = [RelationSchema(**r) for r in graph_snapshot["relations"]]
    elif debate and debate.relations:
        relation_schemas = [
            RelationSchema(
                id=r.id,
                source_argument_id=r.source_argument_id,
                target_argument_id=r.target_argument_id,
                relation_type=r.relation_type,
                confidence=r.confidence,
            )
            for r in debate.relations
        ]
    else:
        relation_schemas = []

    # Reconstruct insights
    insight_schemas = [
        InsightSchema(
            id=ins["id"],
            type=ins["type"],
            severity=ins["severity"],
            message=ins["message"],
            related_argument_ids=ins.get("related_argument_ids", []),
        )
        for ins in insights_snapshot
    ]

    # Reconstruct summary
    if graph_snapshot.get("summary"):
        summary = AnalysisSummary(**graph_snapshot["summary"])
    else:
        summary = AnalysisSummary(
            speaker_count=len(speaker_schemas),
            turn_count=len(debate.turns) if debate else 0,
            argument_count=len(argument_schemas),
            relation_count=len(relation_schemas),
            insights_count=len(insight_schemas),
        )

    return AnalysisResponse(
        analysis_id=run.id,
        debate_id=run.debate_id,
        status=run.status.lower(),
        message=run.error_message or ("Analysis completed." if run.status == "COMPLETED" else "Pipeline queued."),
        model_version=run.model_version,
        created_at=run.created_at,
        completed_at=run.completed_at,
        summary=summary,
        speakers=speaker_schemas,
        arguments=argument_schemas,
        relations=relation_schemas,
        insights=insight_schemas,
    )


# ---------------------------------------------------------------------------
# POST /speak  — Optional voice / TTS endpoint
# ---------------------------------------------------------------------------

class SpeakRequest(BaseModel):
    text: str
    lang: str = "en"


@router.post(
    "/speak",
    summary="[Voice] Convert analysis text to spoken MP3 audio",
    response_class=FileResponse,
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 audio file"},
        503: {"description": "gTTS not installed – voice feature unavailable"},
    },
)
def speak_text(payload: SpeakRequest):
    """
    Accepts plain text and returns a streamed MP3 audio file generated by
    Google TTS (gTTS).  Requires the ``gtts`` package to be installed.

    * Pass any sentence, argument, or insight message from the analysis result.
    * Supports any BCP-47 language code accepted by gTTS (default: ``en``).

    Returns HTTP 503 when gTTS is not installed so callers can degrade
    gracefully without breaking the rest of the API.
    """
    if not tts_service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Voice feature unavailable: gTTS is not installed. "
                "Run `pip install gtts>=2.5.0` to enable it."
            ),
        )
    if not payload.text or not payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'text' field must not be empty.",
        )
    try:
        mp3_path = tts_service.synthesize(payload.text, lang=payload.lang)
    except TTSUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS error: {exc}") from exc

    return FileResponse(mp3_path, media_type="audio/mpeg", filename="analysis_audio.mp3")
