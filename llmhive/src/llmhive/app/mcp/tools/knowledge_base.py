"""Knowledge base tools for MCP."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def knowledge_search_tool(
    query: str,
    user_id: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search the knowledge base.

    Args:
        query: Search query
        user_id: User ID for scoped search
        limit: Maximum number of results

    Returns:
        Search results
    """
    try:
        from ...knowledge import KnowledgeBase
        from ...database import SessionLocal

        with SessionLocal() as session:
            kb = KnowledgeBase(session)
            results = kb.search(user_id, query, limit=limit)

            return {
                "query": query,
                "user_id": user_id,
                "results": [
                    {
                        "content": result.content[:500],
                        "score": getattr(result, "score", 0.0),
                        "metadata": getattr(result, "metadata", {}),
                    }
                    for result in results
                ],
                "count": len(results),
            }
    except Exception as exc:
        logger.error(f"Knowledge search failed: {exc}", exc_info=True)
        return {
            "query": query,
            "error": str(exc),
            "results": [],
            "count": 0,
        }


async def knowledge_add_tool(
    content: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add content to the knowledge base.

    Args:
        content: Content to add
        user_id: User ID
        metadata: Optional metadata

    Returns:
        Add result
    """
    try:
        from ...knowledge import KnowledgeBase
        from ...database import SessionLocal

        with SessionLocal() as session:
            kb = KnowledgeBase(session)
            doc_id = kb.store(user_id, content, metadata=metadata or {})

            return {
                "success": True,
                "document_id": doc_id,
                "user_id": user_id,
            }
    except Exception as exc:
        logger.error(f"Knowledge add failed: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
        }


# Register the tools
from ..tool_registry import register_tool

register_tool(
    name="knowledge_search",
    description="Search the knowledge base for stored information",
    parameters={
        "query": {
            "type": "string",
            "description": "Search query",
            "required": True,
        },
        "user_id": {
            "type": "string",
            "description": "User ID for scoped search",
            "required": True,
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results",
            "default": 10,
            "required": False,
        },
    },
    handler=knowledge_search_tool,
)

register_tool(
    name="knowledge_add",
    description="Add content to the knowledge base",
    parameters={
        "content": {
            "type": "string",
            "description": "Content to add",
            "required": True,
        },
        "user_id": {
            "type": "string",
            "description": "User ID",
            "required": True,
        },
        "metadata": {
            "type": "object",
            "description": "Optional metadata",
            "required": False,
        },
    },
    handler=knowledge_add_tool,
)

