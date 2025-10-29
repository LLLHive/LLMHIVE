"""SQLAlchemy models for LLMHive."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation", back_populates="tasks")


class Conversation(Base):
    """Conversation metadata for persistent memory."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )

    entries: Mapped[List["MemoryEntry"]] = relationship(
        "MemoryEntry", back_populates="conversation", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="conversation")
    knowledge_documents: Mapped[List["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument", back_populates="conversation", cascade="all, delete-orphan"
    )


class MemoryEntry(Base):
    """Individual conversational memory entries."""

    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="entries")

    def render_for_prompt(self) -> str:
        prefix = "User" if self.role == "user" else "Assistant"
        return f"{prefix}: {self.content}"


class KnowledgeDocument(Base):
    """Embeddings-backed knowledge snippets for retrieval augmented generation."""

    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    payload: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, nullable=False, index=True
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )

    conversation: Mapped[Conversation | None] = relationship(
        "Conversation", back_populates="knowledge_documents"
    )
