"""Database query tool for MCP."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def database_query_tool(
    query: str,
    user_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Query the database (knowledge base or user data).

    Args:
        query: SQL-like query or search query
        user_id: Optional user ID for scoped queries
        limit: Maximum number of results

    Returns:
        Query results
    """
    try:
        from ...knowledge import KnowledgeBase
        from ...database import SessionLocal

        # For now, use knowledge base search
        # In production, this could support SQL queries with proper sanitization
        with SessionLocal() as session:
            kb = KnowledgeBase(session)

            # Simple text search in knowledge base
            if user_id:
                results = kb.search(user_id, query, limit=limit)
            else:
                # Search all knowledge (admin only in production)
                results = kb.search("system", query, limit=limit)

            return {
                "query": query,
                "results": [
                    {
                        "content": result.content[:500],  # Truncate for safety
                        "score": result.score if hasattr(result, "score") else 0.0,
                        "metadata": result.metadata if hasattr(result, "metadata") else {},
                    }
                    for result in results[:limit]
                ],
                "count": len(results),
            }
    except ImportError:
        logger.warning("KnowledgeBase not available")
        return {
            "query": query,
            "error": "Database service not available",
            "results": [],
            "count": 0,
        }
    except Exception as exc:
        logger.error(f"Database query failed: {exc}", exc_info=True)
        return {
            "query": query,
            "error": str(exc),
            "results": [],
            "count": 0,
        }


# Register the tool
from ..tool_registry import register_tool

register_tool(
    name="database_query",
    description="Query the knowledge base or database for information",
    parameters={
        "query": {
            "type": "string",
            "description": "Search query or SQL query (sanitized)",
            "required": True,
        },
        "user_id": {
            "type": "string",
            "description": "Optional user ID for scoped queries",
            "required": False,
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results",
            "default": 100,
            "required": False,
        },
    },
    handler=database_query_tool,
)

