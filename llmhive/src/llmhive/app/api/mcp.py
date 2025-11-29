"""MCP tool usage API endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..mcp.tool_usage_tracker import get_tool_usage_tracker

logger = logging.getLogger(__name__)

router = APIRouter()

# Include custom tool registration endpoints
try:
    # Import from mcp package (directory), not mcp.py module
    import sys
    import os
    mcp_dir = os.path.join(os.path.dirname(__file__), "mcp")
    if os.path.isdir(mcp_dir):
        sys.path.insert(0, os.path.dirname(__file__))
        from api.mcp.tools import router as register_router
        router.include_router(register_router, prefix="/tools", tags=["mcp-tools"])
except (ImportError, Exception) as exc:
    logger.warning(f"Custom tool registration endpoints not available: {exc}")


@router.get("/tools", status_code=status.HTTP_200_OK)
def list_tools():
    """List all available MCP tools.

    Final path: /api/v1/mcp/tools
    """
    try:
        from ..mcp.client import MCPClient
        from ..orchestrator import _orchestrator

        if not _orchestrator.mcp_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP client not available",
            )

        import asyncio
        asyncio.run(_orchestrator.mcp_client.initialize())
        tools = _orchestrator.mcp_client.list_tools()

        return {
            "tools": tools,
            "count": len(tools),
        }
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP modules not available",
        )
    except Exception as exc:
        logger.exception("Failed to list tools: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tools",
        ) from exc


@router.get("/tools/stats", status_code=status.HTTP_200_OK)
def get_tool_stats():
    """Get tool usage statistics.

    Final path: /api/v1/mcp/tools/stats
    """
    try:
        tracker = get_tool_usage_tracker()
        if not tracker:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tool usage tracker not available",
            )

        summary = tracker.get_summary()
        return summary
    except Exception as exc:
        logger.exception("Failed to get tool stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool stats",
        ) from exc


@router.get("/tools/{tool_name}/stats", status_code=status.HTTP_200_OK)
def get_tool_stat(tool_name: str):
    """Get statistics for a specific tool.

    Final path: /api/v1/mcp/tools/{tool_name}/stats
    """
    try:
        tracker = get_tool_usage_tracker()
        if not tracker:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tool usage tracker not available",
            )

        stats = tracker.get_tool_stats(tool_name)
        return stats
    except Exception as exc:
        logger.exception("Failed to get tool stat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool stat",
        ) from exc


@router.get("/agents/{agent_role}/stats", status_code=status.HTTP_200_OK)
def get_agent_tool_stats(agent_role: str):
    """Get tool usage statistics for an agent role.

    Final path: /api/v1/mcp/agents/{agent_role}/stats
    """
    try:
        tracker = get_tool_usage_tracker()
        if not tracker:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Tool usage tracker not available",
            )

        stats = tracker.get_agent_stats(agent_role)
        return stats
    except Exception as exc:
        logger.exception("Failed to get agent tool stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent tool stats",
        ) from exc

