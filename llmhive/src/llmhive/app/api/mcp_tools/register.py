"""API endpoints for custom tool registration."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...mcp.custom_tools import get_custom_tool_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterToolRequest(BaseModel):
    """Request to register a custom tool."""

    tool_name: str = Field(..., description="Unique tool name (alphanumeric with underscores/hyphens)")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters schema")
    handler_code: str = Field(..., description="Python code for tool handler function")
    user_id: str | None = Field(default=None, description="User ID for ownership")


class UnregisterToolRequest(BaseModel):
    """Request to unregister a custom tool."""

    tool_name: str = Field(..., description="Tool name to unregister")
    user_id: str | None = Field(default=None, description="User ID for ownership check")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_custom_tool(request: RegisterToolRequest) -> Dict[str, Any]:
    """Register a custom tool.

    Final path: /api/v1/mcp/tools/register

    Note: In production, handler_code execution should be sandboxed for security.
    """
    try:
        manager = get_custom_tool_manager()

        # Compile and validate handler code
        # WARNING: In production, this should be sandboxed!
        try:
            namespace: Dict[str, Any] = {}
            exec(request.handler_code, namespace)
            
            # Find handler function (look for function named after tool or 'handler')
            handler: Callable | None = None
            if request.tool_name in namespace:
                handler = namespace[request.tool_name]
            elif "handler" in namespace:
                handler = namespace["handler"]
            elif "tool_handler" in namespace:
                handler = namespace["tool_handler"]
            else:
                # Try to find any callable
                for value in namespace.values():
                    if callable(value) and not value.__name__.startswith("_"):
                        handler = value
                        break

            if not handler:
                raise ValueError("Handler function not found in code. Expected function named 'handler' or tool name.")

        except SyntaxError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Python code: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to compile handler: {exc}",
            ) from exc

        # Register tool
        result = manager.register_custom_tool(
            tool_name=request.tool_name,
            description=request.description,
            parameters=request.parameters,
            handler=handler,
            user_id=request.user_id,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Failed to register custom tool: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register custom tool",
        ) from exc


@router.post("/unregister", status_code=status.HTTP_200_OK)
def unregister_custom_tool(request: UnregisterToolRequest) -> Dict[str, Any]:
    """Unregister a custom tool.

    Final path: /api/v1/mcp/tools/unregister
    """
    try:
        manager = get_custom_tool_manager()
        result = manager.unregister_custom_tool(
            tool_name=request.tool_name,
            user_id=request.user_id,
        )
        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Failed to unregister custom tool: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister custom tool",
        ) from exc


@router.get("/list", status_code=status.HTTP_200_OK)
def list_custom_tools(
    user_id: str | None = Query(default=None, description="Filter by user ID"),
) -> Dict[str, Any]:
    """List custom tools.

    Final path: /api/v1/mcp/tools/list?user_id={user_id}
    """
    try:
        manager = get_custom_tool_manager()
        result = manager.list_custom_tools(user_id=user_id)
        return result

    except Exception as exc:
        logger.exception("Failed to list custom tools: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list custom tools",
        ) from exc

