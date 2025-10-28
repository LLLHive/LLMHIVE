"""Conversation memory management for LLMHive."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Conversation, MemoryEntry


@dataclass(slots=True)
class MemoryContext:
    """Represents contextual information retrieved from memory."""

    conversation_id: int
    summary: str
    recent_messages: List[str]

    def as_prompt_context(self) -> str:
        recent = "\n".join(self.recent_messages)
        return f"Previous context summary: {self.summary}\nRecent turns:\n{recent}" if recent else self.summary


class MemoryManager:
    """Handles retrieval and persistence of conversational memory."""

    def __init__(self, session: Session):
        self.session = session

    def _create_conversation(self, *, user_id: str | None, topic: str | None) -> Conversation:
        conversation = Conversation(user_id=user_id, topic=topic or "general", summary="")
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def get_or_create_conversation(self, conversation_id: Optional[int], *, user_id: str | None, topic: str | None) -> Conversation:
        if conversation_id:
            conversation = self.session.get(Conversation, conversation_id)
            if conversation:
                return conversation
        return self._create_conversation(user_id=user_id, topic=topic)

    def append_entry(
        self,
        conversation: Conversation,
        *,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            conversation_id=conversation.id,
            role=role,
            content=content,
            payload=metadata or {},
            created_at=dt.datetime.utcnow(),
        )
        self.session.add(entry)
        return entry

    def fetch_recent_context(self, conversation: Conversation, *, limit: int = 6) -> MemoryContext:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.conversation_id == conversation.id)
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        rows = list(self.session.scalars(stmt))
        recent = list(reversed([entry.render_for_prompt() for entry in rows]))
        summary = conversation.summary or "No long-term summary recorded yet."
        return MemoryContext(conversation_id=conversation.id, summary=summary, recent_messages=recent)

    def update_summary(self, conversation: Conversation, *, summary: str) -> None:
        conversation.summary = summary
        conversation.updated_at = dt.datetime.utcnow()
        self.session.add(conversation)

    def auto_summarize(self, conversation: Conversation) -> None:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.conversation_id == conversation.id)
            .order_by(MemoryEntry.created_at.desc())
            .limit(20)
        )
        entries = list(self.session.scalars(stmt))
        if not entries:
            conversation.summary = "No prior conversation."  # type: ignore[assignment]
            return
        snippets = [entry.content for entry in entries[-5:]]
        summary = " | ".join(snippet[:120] for snippet in snippets)
        conversation.summary = summary
        conversation.updated_at = dt.datetime.utcnow()
        self.session.add(conversation)


def build_context_string(context: MemoryContext | None) -> str | None:
    if context is None:
        return None
    return context.as_prompt_context()
