"""API client tool for MCP."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


async def api_call_tool(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Make an HTTP API call.

    Args:
        url: API URL
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional HTTP headers
        body: Optional request body (for POST/PUT)
        timeout: Request timeout in seconds

    Returns:
        API response
    """
    try:
        # Security: Only allow HTTPS for external calls
        if url.startswith("http://") and not url.startswith("http://localhost"):
            return {
                "url": url,
                "error": "Only HTTPS URLs are allowed (except localhost)",
                "success": False,
            }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body if body else None,
            )

            # Try to parse JSON response
            try:
                response_data = response.json()
            except Exception:
                response_data = response.text[:1000]  # Limit text response

            return {
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response_data,
                "success": response.is_success,
            }
    except httpx.TimeoutException:
        return {
            "url": url,
            "error": f"Request timed out after {timeout} seconds",
            "success": False,
        }
    except Exception as exc:
        logger.error(f"API call failed: {exc}", exc_info=True)
        return {
            "url": url,
            "error": str(exc),
            "success": False,
        }


# Register the tool
from ..tool_registry import register_tool

register_tool(
    name="api_call",
    description="Make an HTTP API call (HTTPS only for external URLs)",
    parameters={
        "url": {
            "type": "string",
            "description": "API URL",
            "required": True,
        },
        "method": {
            "type": "string",
            "description": "HTTP method (GET, POST, PUT, DELETE, etc.)",
            "default": "GET",
            "required": False,
        },
        "headers": {
            "type": "object",
            "description": "Optional HTTP headers",
            "default": {},
            "required": False,
        },
        "body": {
            "type": "object",
            "description": "Optional request body (for POST/PUT)",
            "required": False,
        },
        "timeout": {
            "type": "integer",
            "description": "Request timeout in seconds",
            "default": 30,
            "required": False,
        },
    },
    handler=api_call_tool,
)

