"""Best-effort live web research integration used by the orchestrator."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List

import httpx

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WebDocument:
    """Normalized representation of a web search result."""

    title: str
    url: str
    snippet: str


class WebResearchClient:
    """Client wrapper around the Tavily API with graceful fallbacks."""

    def __init__(self, api_key: str | None = None, *, timeout: float = 8.0) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.timeout = timeout

    async def search(self, query: str, *, max_results: int = 3) -> List[WebDocument]:
        """Return at most ``max_results`` web documents relevant to ``query``."""

        if not query.strip():
            return []

        if not self.api_key:
            logger.debug("Web search disabled because TAVILY_API_KEY is not configured.")
            return [
                WebDocument(
                    title="Live search disabled",
                    url="",
                    snippet="Configure TAVILY_API_KEY to enable internet-grounded research.",
                )
            ]

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # pragma: no cover - network variability
            logger.warning("Live web search failed: %s", exc)
            return [
                WebDocument(
                    title="Live search unavailable",
                    url="",
                    snippet=str(exc),
                )
            ]

        documents: List[WebDocument] = []
        for item in data.get("results", [])[:max_results]:
            snippet = (item.get("content") or item.get("snippet") or "").strip()
            documents.append(
                WebDocument(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=snippet,
                )
            )

        if not documents and data.get("answer"):
            documents.append(
                WebDocument(title="Search summary", url="", snippet=str(data["answer"]))
            )

        return documents
