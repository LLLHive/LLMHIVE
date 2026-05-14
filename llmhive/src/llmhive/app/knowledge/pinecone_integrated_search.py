"""Helpers for Pinecone integrated embedding search (SDK version differences).

Some deployments had older clients where ``Index.search(..., query=...)`` failed
with ``unexpected keyword argument 'query'``. We probe the signature and fall
back gracefully so RAG paths degrade to FAISS/local without error-level noise.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def integrated_search_to_dict(
    index: Any,
    *,
    namespace: str,
    search_query: Dict[str, Any],
    rerank: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Call ``index.search`` for integrated-record indexes when supported.

    Returns:
        Parsed dict (OpenAPI ``to_dict()`` shape) on success,
        ``{}`` when the search returns an empty/unexpected body,
        or ``None`` when the SDK does not support this call (caller should fall back).
    """
    if index is None or not hasattr(index, "search"):
        return None
    try:
        sig = inspect.signature(index.search)
    except (TypeError, ValueError):
        return None
    if "query" not in sig.parameters:
        logger.debug(
            "Pinecone index.search has no query= parameter; skipping integrated search"
        )
        return None
    try:
        if rerank:
            raw = index.search(
                namespace=namespace,
                query=search_query,
                rerank=rerank,
            )
        else:
            raw = index.search(namespace=namespace, query=search_query)
    except TypeError as exc:
        if "query" in str(exc) or "unexpected keyword" in str(exc).lower():
            logger.warning(
                "Pinecone integrated search API mismatch (%s); using fallback retrieval",
                exc,
            )
            return None
        raise
    except Exception as exc:
        logger.warning("Pinecone integrated search failed (%s); using fallback", exc)
        return None

    if hasattr(raw, "to_dict"):
        return raw.to_dict()
    if isinstance(raw, dict):
        return raw
    logger.warning("Unexpected Pinecone search response type: %s", type(raw))
    return None


def hits_from_search_payload(payload: Optional[Dict[str, Any]]) -> list:
    """Extract ``hits`` list from a search response dict."""
    if not payload:
        return []
    result_block = payload.get("result") or {}
    if hasattr(result_block, "to_dict"):
        result_block = result_block.to_dict()
    if not isinstance(result_block, dict):
        return []
    return list(result_block.get("hits") or [])
