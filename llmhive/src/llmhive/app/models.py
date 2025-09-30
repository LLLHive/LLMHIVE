"""SQLAlchemy models for LLMHive."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Task(Base):
    """Persisted record of an orchestration request and outcome."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_names: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    initial_responses: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    critiques: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    improvements: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    final_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False, index=True
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )
