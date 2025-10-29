"""Utilities for inspecting orchestration feature readiness at runtime."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Conversation, KnowledgeDocument, Task
from .orchestrator import Orchestrator


@dataclass(slots=True)
class FeatureDiagnostics:
    """Aggregated status about the major LLMHive subsystems."""

    providers_configured: List[str]
    real_providers: List[str]
    stub_only: bool
    default_models: List[str]
    live_research_enabled: bool
    live_research_configured: bool
    knowledge_documents: int
    memory_conversations: int
    last_task_at: datetime | None
    knowledge_samples: List[str]
    warnings: List[str]

    def asdict(self) -> Dict[str, object]:
        payload = asdict(self)
        # Pydantic will serialise datetime automatically, but api callers expect ISO8601.
        if payload["last_task_at"] is not None:
            payload["last_task_at"] = payload["last_task_at"].isoformat()
        return payload


class DiagnosticsService:
    """Collects diagnostic metadata about orchestration capabilities."""

    def __init__(self, session: Session, orchestrator: Orchestrator) -> None:
        self.session = session
        self.orchestrator = orchestrator

    def collect(self, *, user_id: str | None = None) -> FeatureDiagnostics:
        providers = list(self.orchestrator.providers.keys())
        real_providers = [provider for provider in providers if provider != "stub"]
        stub_only = bool(providers) and not real_providers

        knowledge_documents = self._count(KnowledgeDocument.id)
        memory_conversations = self._count(Conversation.id)
        last_task_at = self._latest_task_timestamp()

        knowledge_samples = self._sample_knowledge(user_id=user_id)

        live_research_configured = bool(os.getenv("TAVILY_API_KEY"))

        warnings: List[str] = []
        if stub_only:
            warnings.append(
                "Only stub provider configured – add real API keys to enable multi-model orchestration."
            )
        if knowledge_documents == 0:
            warnings.append(
                "Knowledge base is empty – run orchestrations with enable_knowledge=true to persist context."
            )
        if memory_conversations == 0:
            warnings.append(
                "No conversations stored – enable_memory ensures the planner can use shared memory."
            )
        if settings.enable_live_research and not live_research_configured:
            warnings.append(
                "Live research enabled but TAVILY_API_KEY missing – internet lookups will fall back to static notices."
            )

        return FeatureDiagnostics(
            providers_configured=providers,
            real_providers=real_providers,
            stub_only=stub_only,
            default_models=list(settings.default_models),
            live_research_enabled=settings.enable_live_research,
            live_research_configured=live_research_configured,
            knowledge_documents=knowledge_documents,
            memory_conversations=memory_conversations,
            last_task_at=last_task_at,
            knowledge_samples=knowledge_samples,
            warnings=warnings,
        )

    def _count(self, column) -> int:
        value = self.session.scalar(select(func.count(column)))
        return int(value or 0)

    def _latest_task_timestamp(self) -> datetime | None:
        return self.session.scalar(
            select(Task.created_at).order_by(Task.created_at.desc()).limit(1)
        )

    def _sample_knowledge(self, *, user_id: str | None) -> List[str]:
        stmt = select(KnowledgeDocument.content).order_by(KnowledgeDocument.created_at.desc()).limit(3)
        if user_id:
            stmt = stmt.where(KnowledgeDocument.user_id == user_id)
        rows = self.session.execute(stmt).scalars().all()
        snippets: List[str] = []
        for text in rows:
            snippet = (text or "").strip().replace("\n", " ")
            if len(snippet) > 160:
                snippet = snippet[:160] + "…"
            snippets.append(snippet)
        return snippets

__all__ = ["DiagnosticsService", "FeatureDiagnostics"]
