"""Tool registry for MCP tools."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for MCP tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
    ) -> None:
        """Register a tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: Tool parameter schema
            handler: Async function that handles tool calls
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")

        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }
        logger.debug(f"Registered tool: {name}")

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in self._tools.values()
        ]

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._initialized = False


# Global tool registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def register_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    handler: Callable,
) -> None:
    """Register a tool in the global registry.

    Args:
        name: Tool name
        description: Tool description
        parameters: Tool parameter schema
        handler: Async function that handles tool calls
    """
    registry = get_tool_registry()
    registry.register(name, description, parameters, handler)

