"""Tool permissions system for MCP agents."""
from __future__ import annotations

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class ToolPermission:
    """Tool permission system for agent role-based access."""

    # Define which tools each agent role can use
    AGENT_PERMISSIONS: Dict[str, List[str]] = {
        "researcher": [
            "web_search",
            "database_query",
            "api_call",
            "knowledge_search",
        ],
        "critic": [
            "database_query",
            "read_file",
            "knowledge_search",
        ],
        "editor": [
            "read_file",
            "write_file",
            "list_files",
            "knowledge_search",
        ],
        "fact_checker": [
            "web_search",
            "database_query",
            "api_call",
            "knowledge_search",
        ],
        "analyst": [
            "database_query",
            "api_call",
            "read_file",
            "knowledge_search",
        ],
        "lead": [
            "web_search",
            "database_query",
            "api_call",
            "read_file",
            "write_file",
            "knowledge_search",
            "knowledge_add",
            "send_email",
            "create_calendar_event",
            "list_calendar_events",
        ],
        # Default permissions for unknown roles
        "default": [
            "knowledge_search",
        ],
    }

    @classmethod
    def can_use_tool(cls, agent_role: str, tool_name: str) -> bool:
        """Check if an agent role can use a tool.

        Args:
            agent_role: Agent role name
            tool_name: Tool name

        Returns:
            True if agent can use the tool
        """
        role_lower = agent_role.lower()
        allowed_tools = cls.AGENT_PERMISSIONS.get(role_lower, cls.AGENT_PERMISSIONS["default"])

        # Also check if any parent role has permission
        # (e.g., "lead" can use all tools)
        if "lead" in role_lower or "manager" in role_lower:
            return True

        return tool_name in allowed_tools

    @classmethod
    def get_allowed_tools(cls, agent_role: str) -> List[str]:
        """Get list of tools allowed for an agent role.

        Args:
            agent_role: Agent role name

        Returns:
            List of allowed tool names
        """
        role_lower = agent_role.lower()
        allowed = cls.AGENT_PERMISSIONS.get(role_lower, cls.AGENT_PERMISSIONS["default"])

        # Lead/manager roles get all tools
        if "lead" in role_lower or "manager" in role_lower:
            from .tool_registry import get_tool_registry
            registry = get_tool_registry()
            return [tool["name"] for tool in registry.list()]

        return allowed

    @classmethod
    def filter_tools(cls, agent_role: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter tools list to only include allowed tools for agent role.

        Args:
            agent_role: Agent role name
            tools: List of tool dictionaries

        Returns:
            Filtered list of tools
        """
        allowed_tool_names = set(cls.get_allowed_tools(agent_role))
        return [tool for tool in tools if tool.get("name") in allowed_tool_names]

