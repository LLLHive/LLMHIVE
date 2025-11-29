"""Custom tool registration and management."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .tool_registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class CustomToolManager:
    """Manages custom user-defined tools."""

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        """Initialize custom tool manager.

        Args:
            registry: Tool registry instance (optional)
        """
        self.registry = registry or get_tool_registry()
        self._custom_tools: Dict[str, Dict[str, Any]] = {}

    def register_custom_tool(
        self,
        tool_name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a custom tool.

        Args:
            tool_name: Unique tool name
            description: Tool description
            parameters: Tool parameters schema
            handler: Tool handler function
            user_id: Optional user ID for ownership

        Returns:
            Registration result
        """
        # Validate tool name
        if not tool_name or not tool_name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Tool name must be alphanumeric with underscores or hyphens")

        # Check if tool already exists
        if self.registry.get(tool_name):
            raise ValueError(f"Tool '{tool_name}' already exists")

        # Validate parameters schema
        self._validate_parameters(parameters)

        # Register tool using tool_registry's register_tool function
        try:
            from .tool_registry import register_tool
            register_tool(
                name=tool_name,
                description=description,
                parameters=parameters,
                handler=handler,
            )

            # Track custom tool
            self._custom_tools[tool_name] = {
                "name": tool_name,
                "description": description,
                "user_id": user_id,
                "registered_at": None,  # Would use datetime in production
            }

            logger.info(f"Custom tool registered: {tool_name} by user {user_id}")
            return {
                "success": True,
                "tool_name": tool_name,
                "message": f"Tool '{tool_name}' registered successfully",
            }
        except Exception as exc:
            logger.error(f"Failed to register custom tool: {exc}", exc_info=True)
            raise

    def unregister_custom_tool(self, tool_name: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Unregister a custom tool.

        Args:
            tool_name: Tool name to unregister
            user_id: Optional user ID for ownership check

        Returns:
            Unregistration result
        """
        if tool_name not in self._custom_tools:
            raise ValueError(f"Custom tool '{tool_name}' not found")

        # Check ownership if user_id provided
        tool_info = self._custom_tools[tool_name]
        if user_id and tool_info.get("user_id") != user_id:
            raise ValueError(f"Tool '{tool_name}' does not belong to user {user_id}")

        # Remove from registry
        # Note: This would require registry to support removal
        # For now, we just track it
        del self._custom_tools[tool_name]

        logger.info(f"Custom tool unregistered: {tool_name}")
        return {
            "success": True,
            "tool_name": tool_name,
            "message": f"Tool '{tool_name}' unregistered successfully",
        }

    def list_custom_tools(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """List custom tools.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of custom tools
        """
        if user_id:
            tools = {
                name: info
                for name, info in self._custom_tools.items()
                if info.get("user_id") == user_id
            }
        else:
            tools = self._custom_tools.copy()

        return {
            "count": len(tools),
            "tools": list(tools.values()),
        }

    def _validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate tool parameters schema.

        Args:
            parameters: Parameters schema

        Raises:
            ValueError: If schema is invalid
        """
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be a dictionary")

        for param_name, param_spec in parameters.items():
            if not isinstance(param_spec, dict):
                raise ValueError(f"Parameter '{param_name}' must be a dictionary")

            # Check required fields
            if "type" not in param_spec:
                raise ValueError(f"Parameter '{param_name}' must have a 'type' field")

            # Validate type
            valid_types = ["string", "integer", "number", "boolean", "array", "object"]
            if param_spec["type"] not in valid_types:
                raise ValueError(
                    f"Parameter '{param_name}' has invalid type '{param_spec['type']}'. "
                    f"Valid types: {valid_types}"
                )


# Global custom tool manager instance
_custom_tool_manager: Optional[CustomToolManager] = None


def get_custom_tool_manager() -> CustomToolManager:
    """Get the global custom tool manager instance."""
    global _custom_tool_manager
    if _custom_tool_manager is None:
        _custom_tool_manager = CustomToolManager()
    return _custom_tool_manager

