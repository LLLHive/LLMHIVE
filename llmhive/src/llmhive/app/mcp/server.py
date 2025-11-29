"""MCP server implementation for external connections."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP server for external connections (stdio transport)."""

    def __init__(self, tool_registry=None) -> None:
        """Initialize MCP server.

        Args:
            tool_registry: Tool registry instance (optional)
        """
        from .tool_registry import get_tool_registry

        self.registry = tool_registry or get_tool_registry()
        self.running = False

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP protocol request.

        Args:
            request: MCP request dictionary

        Returns:
            MCP response dictionary
        """
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return await self._handle_tools_list()
        elif method == "tools/call":
            return await self._handle_tools_call(params)
        elif method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": "llmhive-mcp-server",
                        "version": "1.0.0",
                    },
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    async def _handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self.registry.list()
        mcp_tools = []
        for tool in tools:
            mcp_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": {
                    "type": "object",
                    "properties": tool.get("parameters", {}),
                },
            })

        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": mcp_tools,
            },
        }

    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Missing tool name",
                },
            }

        tool = self.registry.get(tool_name)
        if not tool:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Tool '{tool_name}' not found",
                },
            }

        try:
            handler = tool.get("handler")
            if not handler:
                raise ValueError(f"Tool '{tool_name}' has no handler")

            # Call the tool
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ],
                },
            }
        except Exception as exc:
            logger.error(f"Tool call failed: {exc}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": str(exc),
                },
            }

    async def run_stdio(self) -> None:
        """Run MCP server using stdio transport."""
        self.running = True
        logger.info("MCP server starting (stdio transport)")

        try:
            while self.running:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)
                    # Write response to stdout
                    print(json.dumps(response), flush=True)
                except json.JSONDecodeError as exc:
                    logger.error(f"Invalid JSON request: {exc}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error",
                        },
                    }
                    print(json.dumps(error_response), flush=True)
                except Exception as exc:
                    logger.error(f"Request handling error: {exc}", exc_info=True)

        except KeyboardInterrupt:
            logger.info("MCP server stopping")
        finally:
            self.running = False


async def run_mcp_server() -> None:
    """Run the MCP server (entry point)."""
    from .tool_registry import get_tool_registry
    from .tools import load_embedded_tools

    # Load tools
    await load_embedded_tools()

    # Create and run server
    server = MCPServer(get_tool_registry())
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(run_mcp_server())

