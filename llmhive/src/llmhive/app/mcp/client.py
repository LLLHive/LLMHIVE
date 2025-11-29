"""MCP client for agent tool usage."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .tool_registry import get_tool_registry

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with MCP servers and tools."""

    def __init__(self, server_url: Optional[str] = None) -> None:
        """Initialize MCP client.

        Args:
            server_url: Optional MCP server URL. If None, uses embedded tools.
        """
        self.server_url = server_url
        self.registry = get_tool_registry()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize client and discover available tools."""
        if self._initialized:
            return

        if self.server_url:
            # Connect to external MCP server
            await self._connect_to_server()
        else:
            # Use embedded tools
            await self._load_embedded_tools()

        self._initialized = True
        tool_count = len(self.registry.list())
        logger.info(f"MCP client initialized with {tool_count} tools")

    async def _load_embedded_tools(self) -> None:
        """Load embedded tool implementations."""
        # Import tools to register them
        try:
            from .tools import load_embedded_tools
            await load_embedded_tools()
        except ImportError as exc:
            logger.warning(f"Failed to load embedded tools: {exc}")

    async def _connect_to_server(self) -> None:
        """Connect to external MCP server.

        TODO: Implement MCP protocol client
        This would use stdio or HTTP transport per MCP spec
        """
        logger.warning("External MCP server connection not yet implemented")
        # Fall back to embedded tools
        await self._load_embedded_tools()

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call a tool by name.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result with success/error status
        """
        if not self._initialized:
            await self.initialize()

        tool = self.registry.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        handler = tool.get("handler")
        if not handler:
            raise ValueError(f"Tool '{tool_name}' has no handler")

        try:
            # Validate arguments against parameter schema
            validated_args = self._validate_arguments(tool["parameters"], arguments)

            # Call the tool handler
            if hasattr(handler, "__call__"):
                if hasattr(handler, "__code__") and "async" in str(handler.__code__.co_flags):
                    result = await handler(**validated_args)
                else:
                    result = handler(**validated_args)
            else:
                result = await handler(**validated_args)

            return {
                "tool": tool_name,
                "result": result,
                "success": True,
            }
        except Exception as exc:
            logger.error(f"Tool '{tool_name}' failed: {exc}", exc_info=True)
            return {
                "tool": tool_name,
                "error": str(exc),
                "success": False,
            }

    def _validate_arguments(
        self,
        parameters: Dict[str, Any],
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate and extract arguments based on parameter schema.

        Args:
            parameters: Parameter schema
            arguments: Provided arguments

        Returns:
            Validated arguments
        """
        validated: Dict[str, Any] = {}

        for param_name, param_spec in parameters.items():
            if isinstance(param_spec, dict):
                param_type = param_spec.get("type", "string")
                default = param_spec.get("default")
                required = param_spec.get("required", True)

                if param_name in arguments:
                    value = arguments[param_name]
                    # Basic type validation
                    if param_type == "integer" and not isinstance(value, int):
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            raise ValueError(f"Parameter '{param_name}' must be an integer")
                    elif param_type == "number" and not isinstance(value, (int, float)):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            raise ValueError(f"Parameter '{param_name}' must be a number")
                    elif param_type == "boolean" and not isinstance(value, bool):
                        if isinstance(value, str):
                            value = value.lower() in ("true", "1", "yes")
                        else:
                            value = bool(value)

                    validated[param_name] = value
                elif required and default is None:
                    raise ValueError(f"Required parameter '{param_name}' is missing")
                elif default is not None:
                    validated[param_name] = default
            else:
                # Simple parameter (just name)
                if param_name in arguments:
                    validated[param_name] = arguments[param_name]

        return validated

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return self.registry.list()

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        return self.registry.has_tool(tool_name)

