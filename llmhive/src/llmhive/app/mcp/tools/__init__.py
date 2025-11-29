"""Embedded tool implementations for MCP."""
from __future__ import annotations

import logging

from ..tool_registry import register_tool

logger = logging.getLogger(__name__)


async def load_embedded_tools() -> None:
    """Load all embedded tools into the registry."""
    # Import tool modules to register them
    try:
        from . import web_search
        from . import database
        from . import file_system
        from . import api_client
        from . import knowledge_base
        from . import email
        from . import calendar

        # Tools are auto-registered on import
        logger.info("Loaded embedded MCP tools")
    except ImportError as exc:
        logger.warning(f"Failed to load some MCP tools: {exc}")

