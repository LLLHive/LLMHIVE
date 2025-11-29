"""Web search tool for MCP."""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def web_search_tool(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search the web for information.

    Args:
        query: Search query
        max_results: Maximum number of results (default: 5)

    Returns:
        Search results with titles, URLs, and snippets
    """
    try:
        from ...services.web_research import WebResearchClient

        web_research = WebResearchClient()
        results = await web_research.search(query)

        return {
            "query": query,
            "results": [
                {
                    "title": doc.title,
                    "url": doc.url,
                    "snippet": doc.snippet or "",
                }
                for doc in results[:max_results]
            ],
            "count": len(results[:max_results]),
        }
    except ImportError:
        logger.warning("WebResearchClient not available")
        return {
            "query": query,
            "error": "Web search service not available",
            "results": [],
            "count": 0,
        }
    except Exception as exc:
        logger.error(f"Web search failed: {exc}", exc_info=True)
        return {
            "query": query,
            "error": str(exc),
            "results": [],
            "count": 0,
        }


# Register the tool
from ..tool_registry import register_tool

register_tool(
    name="web_search",
    description="Search the web for information using a search engine",
    parameters={
        "query": {
            "type": "string",
            "description": "The search query",
            "required": True,
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "default": 5,
            "required": False,
        },
    },
    handler=web_search_tool,
)

