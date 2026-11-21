"""Debate and Analysis Service Layer."""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.entities import Debate, Speaker, Turn, Argument, Relation, AnalysisRun
from app.schemas.debate import DebateCreate, SpeakerSchema
from app.schemas.argument import ArgumentSchema, RelationSchema
from app.schemas.analysis import AnalysisSummary, InsightSchema
from app.services.analysis_service import AnalysisPipelineResult


def parse_speaker_turns(raw_text: str) -> List[Dict[str, str]]:
    """Deterministic regex parser to extract speaker names and turns.

    Supports both colon-separated ("Speaker: text") and dash/em-dash
    separated ("Speaker – text") formats.
    """
    turns = []
    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]

    # Accept colon, en-dash, em-dash, or plain dash as separators
    turn_regex = re.compile(r"^([^:\-\u2013\u2014]{1,80}?)[\:\-\u2013\u2014]\s*(.*)$")
    current_speaker = "Unknown"

    for line in lines:
        match = turn_regex.match(line)
        if match:
            candidate = match.group(1).strip()
            # Reject URLs / time-stamps mistaken for speaker names
            if len(candidate.split()) <= 6 and not re.search(r"\d{2}:\d{2}", candidate):
                current_speaker = candidate
                utterance = match.group(2).strip()
                turns.append({"speaker": current_speaker, "text": utterance})
                continue
        # Continuation or unrecognised line
        if turns:
            turns[-1]["text"] += f" {line}"
        else:
            turns.append({"speaker": current_speaker, "text": line})

    return turns


class DebateService:
    @staticmethod
    def create_debate(db: Session, debate_in: DebateCreate) -> Debate:
        """Persists a new debate and extracts speaker turns."""
        debate = Debate(
            id=str(uuid.uuid4()),
            title=debate_in.title,
            raw_transcript=debate_in.raw_transcript,
            status="PENDING",
        )
        db.add(debate)
        db.flush()

        parsed_turns = parse_speaker_turns(debate_in.raw_transcript)
        speaker_map: Dict[str, Speaker] = {}

        for order, item in enumerate(parsed_turns, start=1):
            spk_name = item["speaker"]
            if spk_name not in speaker_map:
                speaker = Speaker(
                    id=str(uuid.uuid4()),
                    debate_id=debate.id,
                    name=spk_name,
                )
                db.add(speaker)
                db.flush()
                speaker_map[spk_name] = speaker

            speaker = speaker_map[spk_name]
            turn = Turn(
                id=str(uuid.uuid4()),
                debate_id=debate.id,
                speaker_id=speaker.id,
                turn_order=order,
                text=item["text"],
            )
            db.add(turn)

        debate.status = "READY"
        db.commit()
        db.refresh(debate)
        return debate

    @staticmethod
    def get_debate(db: Session, debate_id: str) -> Optional[Debate]:
        """Fetches debate session by ID."""
        return db.query(Debate).filter(Debate.id == debate_id).first()

    @staticmethod
    def save_full_analysis(
        db: Session,
        title: str,
        raw_transcript: str,
        result: AnalysisPipelineResult,
    ) -> Dict[str, Any]:
        """Atomically persists a debate session, its speakers, speech turns,
        relational argument propositions, inferred relations, analysis run record,
        and JSON graph/insights snapshots.
        """
        now = datetime.now(timezone.utc)
        try:
            # 1. Persist Debate record
            debate = Debate(
                id=str(uuid.uuid4()),
                title=title or "Debate Analysis Session",
                raw_transcript=raw_transcript,
                status="READY",
                created_at=now,
                updated_at=now,
            )
            db.add(debate)
            db.flush()

            # 2. Persist Speakers
            pipeline_spk_to_db: Dict[str, Speaker] = {}
            for spk in result.speakers:
                db_spk = Speaker(
                    id=str(uuid.uuid4()),
                    debate_id=debate.id,
                    name=spk.speaker_name,
                    created_at=now,
                )
                db.add(db_spk)
                pipeline_spk_to_db[spk.speaker_id] = db_spk
            db.flush()

            # 3. Persist Speech Turns
            pipeline_turn_to_db: Dict[str, Turn] = {}
            default_spk_id = next(iter(pipeline_spk_to_db.values())).id if pipeline_spk_to_db else None
            for t in result.turns:
                spk_obj = pipeline_spk_to_db.get(t.speaker_id)
                spk_id = spk_obj.id if spk_obj else default_spk_id
                db_turn = Turn(
                    id=str(uuid.uuid4()),
                    debate_id=debate.id,
                    speaker_id=spk_id,
                    turn_order=t.turn_index + 1,
                    text=t.text,
                    created_at=now,
                )
                db.add(db_turn)
                pipeline_turn_to_db[t.turn_id] = db_turn
            db.flush()

            # 4. Persist Argument Units
            pipeline_unit_to_db: Dict[str, Argument] = {}
            default_turn_id = next(iter(pipeline_turn_to_db.values())).id if pipeline_turn_to_db else None
            for arg in result.arguments:
                t_obj = pipeline_turn_to_db.get(arg.turn_id)
                s_obj = pipeline_spk_to_db.get(arg.speaker_id)
                turn_id = t_obj.id if t_obj else default_turn_id
                speaker_id = s_obj.id if s_obj else default_spk_id
                db_arg = Argument(
                    id=str(uuid.uuid4()),
                    debate_id=debate.id,
                    turn_id=turn_id,
                    speaker_id=speaker_id,
                    text=arg.text,
                    component_type=arg.component_type,
                    confidence=arg.confidence,
                    start_char=arg.start_char,
                    end_char=arg.end_char,
                    created_at=now,
                )
                db.add(db_arg)
                pipeline_unit_to_db[arg.unit_id] = db_arg
            db.flush()

            # 5. Persist Relations
            db_relations: List[Relation] = []
            for rel in result.relations:
                source_arg = pipeline_unit_to_db.get(rel.source_id)
                target_arg = pipeline_unit_to_db.get(rel.target_id)
                if source_arg and target_arg and source_arg.id != target_arg.id:
                    db_rel = Relation(
                        id=str(uuid.uuid4()),
                        debate_id=debate.id,
                        source_argument_id=source_arg.id,
                        target_argument_id=target_arg.id,
                        relation_type=rel.relation_type,
                        confidence=rel.confidence,
                        created_at=now,
                    )
                    db.add(db_rel)
                    db_relations.append(db_rel)
            db.flush()

            # 6. Map Structural Insights (re-link related argument IDs to DB argument IDs)
            db_insights: List[Dict[str, Any]] = []
            for ins in result.insights:
                mapped_ids = [
                    pipeline_unit_to_db[uid].id
                    for uid in ins.get("related_argument_ids", [])
                    if uid in pipeline_unit_to_db
                ]
                db_insights.append({
                    "id": ins["id"],
                    "type": ins["type"],
                    "severity": ins["severity"],
                    "message": ins["message"],
                    "related_argument_ids": mapped_ids,
                })

            # 7. Serialise Schemas for Response & Snapshots
            speaker_schemas = [
                SpeakerSchema(
                    id=s.id,
                    debate_id=debate.id,
                    name=s.name,
                    created_at=s.created_at,
                )
                for s in pipeline_spk_to_db.values()
            ]

            turn_order_map = {t.id: t.turn_order for t in pipeline_turn_to_db.values()}
            argument_schemas = [
                ArgumentSchema(
                    id=a.id,
                    turn_id=a.turn_id,
                    speaker_id=a.speaker_id,
                    text=a.text,
                    component_type=a.component_type,
                    confidence=a.confidence,
                    turn_order=turn_order_map.get(a.turn_id, 1),
                    start_char=a.start_char,
                    end_char=a.end_char,
                )
                for a in pipeline_unit_to_db.values()
            ]

            relation_schemas = [
                RelationSchema(
                    id=r.id,
                    source_argument_id=r.source_argument_id,
                    target_argument_id=r.target_argument_id,
                    relation_type=r.relation_type,
                    confidence=r.confidence,
                )
                for r in db_relations
            ]

            insight_schemas = [
                InsightSchema(
                    id=ins["id"],
                    type=ins["type"],
                    severity=ins["severity"],
                    message=ins["message"],
                    related_argument_ids=ins.get("related_argument_ids", []),
                )
                for ins in db_insights
            ]

            summary = AnalysisSummary(
                speaker_count=len(speaker_schemas),
                turn_count=len(pipeline_turn_to_db),
                argument_count=len(argument_schemas),
                relation_count=len(relation_schemas),
                insights_count=len(insight_schemas),
            )

            # 8. Persist AnalysisRun with populated snapshots
            graph_snapshot = {
                "arguments": [a.model_dump() for a in argument_schemas],
                "relations": [r.model_dump() for r in relation_schemas],
                "summary": summary.model_dump(),
            }

            run = AnalysisRun(
                id=str(uuid.uuid4()),
                debate_id=debate.id,
                status="COMPLETED",
                model_version=result.model_version,
                graph_snapshot=graph_snapshot,
                insights_snapshot=db_insights,
                error_message=None,
                created_at=now,
                completed_at=now,
            )
            db.add(run)

            # 9. Atomic Commit
            db.commit()
            db.refresh(run)
            db.refresh(debate)

            return {
                "debate": debate,
                "run": run,
                "speakers": speaker_schemas,
                "arguments": argument_schemas,
                "relations": relation_schemas,
                "insights": insight_schemas,
                "summary": summary,
            }
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create_analysis_run(
        db: Session,
        debate: Debate,
        model_version: str,
        argument_count: int = 0,
        relation_count: int = 0,
        insights: Optional[List[Dict[str, Any]]] = None,
        arguments: Optional[List[Dict[str, Any]]] = None,
        relations: Optional[List[Dict[str, Any]]] = None,
        summary: Optional[Dict[str, Any]] = None,
        status: str = "COMPLETED",
        error_message: Optional[str] = None,
    ) -> AnalysisRun:
        """Creates an analysis run record populated with real argument units,
        relations, structural insights, and summary counts.
        """
        now = datetime.now(timezone.utc)

        # Resolve arguments: explicit argument payload or serialized from debate
        resolved_args: List[Dict[str, Any]] = []
        if arguments is not None:
            resolved_args = arguments
        elif debate and debate.arguments:
            turn_map = {t.id: t.turn_order for t in (debate.turns or [])}
            resolved_args = [
                {
                    "id": a.id,
                    "turn_id": a.turn_id,
                    "speaker_id": a.speaker_id,
                    "text": a.text,
                    "component_type": a.component_type,
                    "confidence": a.confidence,
                    "turn_order": turn_map.get(a.turn_id, 1),
                    "start_char": a.start_char,
                    "end_char": a.end_char,
                }
                for a in debate.arguments
            ]

        # Resolve relations: explicit relation payload or serialized from debate
        resolved_rels: List[Dict[str, Any]] = []
        if relations is not None:
            resolved_rels = relations
        elif debate and debate.relations:
            resolved_rels = [
                {
                    "id": r.id,
                    "source_argument_id": r.source_argument_id,
                    "target_argument_id": r.target_argument_id,
                    "relation_type": r.relation_type,
                    "confidence": r.confidence,
                }
                for r in debate.relations
            ]

        resolved_insights = insights if insights is not None else []

        # Resolve summary counts
        if summary is not None:
            resolved_summary = summary
        else:
            resolved_summary = {
                "speaker_count": len(debate.speakers) if debate and debate.speakers else 0,
                "turn_count": len(debate.turns) if debate and debate.turns else 0,
                "argument_count": len(resolved_args) if resolved_args else argument_count,
                "relation_count": len(resolved_rels) if resolved_rels else relation_count,
                "insights_count": len(resolved_insights),
            }

        snapshot = {
            "arguments": resolved_args,
            "relations": resolved_rels,
            "summary": resolved_summary,
        }

        try:
            run = AnalysisRun(
                id=str(uuid.uuid4()),
                debate_id=debate.id,
                status=status,
                model_version=model_version,
                graph_snapshot=snapshot,
                insights_snapshot=resolved_insights,
                error_message=error_message,
                created_at=now,
                completed_at=now if status == "COMPLETED" else None,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return run
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create_placeholder_analysis_run(db: Session, debate: Debate) -> AnalysisRun:
        """Creates a pending analysis run with placeholder disclaimer (kept for backwards compat)."""
        now = datetime.now(timezone.utc)
        try:
            run = AnalysisRun(
                id=str(uuid.uuid4()),
                debate_id=debate.id,
                status="PENDING",
                model_version="v1-foundation (ML uninitialized)",
                error_message="ML analysis pipeline will be connected in a later phase.",
                graph_snapshot={"arguments": [], "relations": [], "summary": {}},
                insights_snapshot=[],
                created_at=now,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return run
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_analysis_run(db: Session, analysis_id: str) -> Optional[AnalysisRun]:
        """Fetches analysis run by ID."""
        return db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()

