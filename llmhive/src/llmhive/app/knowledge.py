"""Lightweight retrieval-augmented memory store used during orchestration."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import KnowledgeDocument

_WORD_PATTERN = re.compile(r"[a-z0-9]{2,}")


def _tokenize(text: str) -> Counter[str]:
    tokens = _WORD_PATTERN.findall(text.lower())
    return Counter(tokens)


def _normalize(counter: Counter[str]) -> dict[str, float]:
    if not counter:
        return {}
    norm = math.sqrt(sum(value * value for value in counter.values()))
    if not norm:
        return {}
    return {token: value / norm for token, value in counter.items()}


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


@dataclass(slots=True)
class KnowledgeHit:
    """Represents a retrieved memory snippet relevant to the current prompt."""

    content: str
    metadata: dict[str, object]
    score: float


class KnowledgeBase:
    """Stores and retrieves long-term knowledge for grounding responses."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record_interaction(
        self,
        *,
        user_id: str,
        prompt: str,
        response: str,
        conversation_id: int | None,
        supporting_notes: Sequence[str] | None = None,
    ) -> KnowledgeDocument | None:
        """Persist a combined prompt/response pair for future retrieval."""

        material = self._compose_material(prompt, response, supporting_notes)
        vector = _normalize(_tokenize(material))
        if not vector:
            return None

        if self._is_duplicate(user_id=user_id, vector=vector):
            return None

        document = KnowledgeDocument(
            user_id=user_id,
            conversation_id=conversation_id,
            content=material,
            embedding=vector,
            payload={"source": "orchestration", "tokens": len(vector)},
        )
        self.session.add(document)
        return document

    def search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 3,
    ) -> List[KnowledgeHit]:
        """Return the most relevant snippets for the supplied query."""

        query_vector = _normalize(_tokenize(query))
        if not query_vector:
            return []

        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.user_id == user_id)
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(250)
        )
        documents = self.session.scalars(stmt)

        scored: List[KnowledgeHit] = []
        for document in documents:
            score = _cosine_similarity(query_vector, document.embedding or {})
            if score <= 0:
                continue
            scored.append(
                KnowledgeHit(
                    content=document.content,
                    metadata=document.payload or {},
                    score=round(float(score), 4),
                )
            )

        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:limit]

    @staticmethod
    def to_prompt_block(hits: Sequence[KnowledgeHit]) -> str | None:
        """Render retrieved hits into a prompt-friendly block of text."""

        if not hits:
            return None
        lines = ["Grounding knowledge retrieved from long-term memory:"]
        for idx, hit in enumerate(hits, start=1):
            snippet = hit.content.strip().replace("\n", " ")
            snippet = snippet[:360] + ("…" if len(snippet) > 360 else "")
            lines.append(f"[Memory {idx}] {snippet}")
        return "\n".join(lines)

    @staticmethod
    def snippets(hits: Sequence[KnowledgeHit]) -> List[str]:
        return [hit.content.strip() for hit in hits]

    def _is_duplicate(self, *, user_id: str, vector: dict[str, float]) -> bool:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.user_id == user_id)
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(25)
        )
        recent = list(self.session.scalars(stmt))
        for document in recent:
            if _cosine_similarity(vector, document.embedding or {}) > 0.95:
                return True
        return False

    def _compose_material(
        self,
        prompt: str,
        response: str,
        supporting_notes: Sequence[str] | None,
    ) -> str:
        lines = [f"Question: {prompt.strip()}", f"Answer: {response.strip()}"]
        for note in (supporting_notes or []):
            if not note:
                continue
            lines.append(f"Note: {note.strip()}")
        return "\n".join(lines)
