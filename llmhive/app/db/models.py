"""SQLAlchemy models defining persistent storage for LLMHIVE."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

from ..core.constants import FactCheckMethod, FactCheckVerdict, SubTaskRole, VoteVoter

Base = declarative_base()


class Interaction(Base):
    """Top-level user interaction that triggers orchestration."""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    user_settings_json = Column(JSON, nullable=True)
    eq_accuracy = Column(Float, default=0.8)
    eq_speed = Column(Float, default=0.4)
    eq_creativity = Column(Float, default=0.3)
    eq_cost = Column(Float, default=0.5)

    subtasks = relationship("SubTask", back_populates="interaction", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="interaction", cascade="all, delete-orphan")
    fact_checks = relationship("FactCheck", back_populates="interaction", cascade="all, delete-orphan")
    consensus = relationship("Consensus", back_populates="interaction", uselist=False, cascade="all, delete-orphan")


class SubTask(Base):
    """Individual prompt executions such as optimizer, critic, or worker."""

    __tablename__ = "subtasks"
    __table_args__ = (Index("ix_subtasks_interaction_role", "interaction_id", "role"),)

    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    role = Column(Enum(SubTaskRole), nullable=False)
    prompt_text = Column(Text, nullable=False)
    model_name = Column(String(128), nullable=True)
    params_json = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=dt.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    interaction = relationship("Interaction", back_populates="subtasks")
    outputs = relationship("ModelOutput", back_populates="subtask", cascade="all, delete-orphan")


class ModelOutput(Base):
    """Raw output returned by a model invocation."""

    __tablename__ = "model_outputs"
    __table_args__ = (Index("ix_outputs_subtask", "subtask_id"),)

    id = Column(Integer, primary_key=True)
    subtask_id = Column(Integer, ForeignKey("subtasks.id"), nullable=False)
    raw_text = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=False)
    latency_ms = Column(Float, nullable=False)
    cost_usd = Column(Float, nullable=False)
    score_quality = Column(Float, nullable=True)
    score_factuality = Column(Float, nullable=True)
    meta_json = Column(JSON, nullable=True)

    subtask = relationship("SubTask", back_populates="outputs")
    votes = relationship("Vote", back_populates="model_output", cascade="all, delete-orphan")


class Vote(Base):
    """Stores voting outcomes for model outputs."""

    __tablename__ = "votes"
    __table_args__ = (Index("ix_votes_interaction", "interaction_id"),)

    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    model_output_id = Column(Integer, ForeignKey("model_outputs.id"), nullable=False)
    voter = Column(Enum(VoteVoter), default=VoteVoter.AUTO, nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    rationale_internal = Column(Text, nullable=True)

    interaction = relationship("Interaction", back_populates="votes")
    model_output = relationship("ModelOutput", back_populates="votes")


class FactCheck(Base):
    """Fact check record storing verdict and evidence."""

    __tablename__ = "fact_checks"
    __table_args__ = (Index("ix_fact_checks_interaction", "interaction_id"),)

    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    claim_span = Column(Text, nullable=False)
    method = Column(Enum(FactCheckMethod), nullable=False)
    evidence_json = Column(JSON, nullable=True)
    verdict = Column(Enum(FactCheckVerdict), nullable=False)
    score = Column(Float, default=0.0)

    interaction = relationship("Interaction", back_populates="fact_checks")


class Consensus(Base):
    """Final consensus answer for an interaction."""

    __tablename__ = "consensus"

    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), unique=True, nullable=False)
    final_text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    style_incognito = Column(Boolean, default=True)
    meta_json = Column(JSON, nullable=True)

    interaction = relationship("Interaction", back_populates="consensus")


class ModelScorecard(Base):
    """Aggregated performance metrics for each model."""

    __tablename__ = "model_scorecards"
    __table_args__ = (UniqueConstraint("model_name", "metric_date", name="uq_scorecard_model_date"),)

    id = Column(Integer, primary_key=True)
    model_name = Column(String(128), nullable=False)
    metric_date = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    tasks = Column(Integer, default=0)
    avg_quality = Column(Float, default=0.0)
    avg_factuality = Column(Float, default=0.0)
    avg_latency_ms = Column(Float, default=0.0)
    avg_cost_usd = Column(Float, default=0.0)
