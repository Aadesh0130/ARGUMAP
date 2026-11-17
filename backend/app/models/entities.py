"""SQLAlchemy Relational Models for ARGUMAP.
Strictly following docs/DATA_SCHEMA.md.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Debate(Base):
    __tablename__ = "debates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    raw_transcript = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    speakers = relationship("Speaker", back_populates="debate", cascade="all, delete-orphan")
    turns = relationship("Turn", back_populates="debate", cascade="all, delete-orphan", order_by="Turn.turn_order")
    arguments = relationship("Argument", back_populates="debate", cascade="all, delete-orphan")
    relations = relationship("Relation", back_populates="debate", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="debate", cascade="all, delete-orphan")


class Speaker(Base):
    __tablename__ = "speakers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    debate_id = Column(String(36), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    debate = relationship("Debate", back_populates="speakers")
    turns = relationship("Turn", back_populates="speaker")
    arguments = relationship("Argument", back_populates="speaker")


class Turn(Base):
    __tablename__ = "turns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    debate_id = Column(String(36), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    speaker_id = Column(String(36), ForeignKey("speakers.id", ondelete="CASCADE"), nullable=False)
    turn_order = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    debate = relationship("Debate", back_populates="turns")
    speaker = relationship("Speaker", back_populates="turns")
    arguments = relationship("Argument", back_populates="turn")


class Argument(Base):
    __tablename__ = "arguments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    debate_id = Column(String(36), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    turn_id = Column(String(36), ForeignKey("turns.id", ondelete="CASCADE"), nullable=False)
    speaker_id = Column(String(36), ForeignKey("speakers.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    component_type = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    start_char = Column(Integer, nullable=False, default=0)
    end_char = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "component_type IN ('CLAIM', 'PREMISE', 'EVIDENCE', 'COUNTERARGUMENT', 'REBUTTAL', 'OTHER')",
            name="check_argument_component_type"
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="check_argument_confidence_range"
        ),
    )

    # Relationships
    debate = relationship("Debate", back_populates="arguments")
    turn = relationship("Turn", back_populates="arguments")
    speaker = relationship("Speaker", back_populates="arguments")


class Relation(Base):
    __tablename__ = "relations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    debate_id = Column(String(36), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    source_argument_id = Column(String(36), ForeignKey("arguments.id", ondelete="CASCADE"), nullable=False)
    target_argument_id = Column(String(36), ForeignKey("arguments.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('SUPPORTS', 'ATTACKS', 'RESPONDS_TO', 'NO_RELATION')",
            name="check_relation_type"
        ),
        CheckConstraint(
            "source_argument_id <> target_argument_id",
            name="check_relation_no_self_loop"
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="check_relation_confidence_range"
        ),
    )

    # Relationships
    debate = relationship("Debate", back_populates="relations")
    source_argument = relationship("Argument", foreign_keys=[source_argument_id])
    target_argument = relationship("Argument", foreign_keys=[target_argument_id])


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    debate_id = Column(String(36), ForeignKey("debates.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), nullable=False, default="QUEUED")
    model_version = Column(String(64), nullable=False, default="v1-baseline")
    graph_snapshot = Column(JSON, nullable=True)
    insights_snapshot = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    debate = relationship("Debate", back_populates="analysis_runs")
