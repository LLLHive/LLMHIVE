"""Helper functions for agents to use MCP tools."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .client import MCPClient
from .permissions import ToolPermission

logger = logging.getLogger(__name__)


class AgentToolHelper:
    """Helper class for agents to use MCP tools with permission checking."""

    def __init__(
        self,
        mcp_client: Optional[MCPClient],
        agent_role: str,
    ) -> None:
        """Initialize agent tool helper.

        Args:
            mcp_client: MCP client instance
            agent_role: Agent role name (for permission checking)
        """
        self.mcp_client = mcp_client
        self.agent_role = agent_role

    async def use_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Use a tool with permission checking.

        Args:
            tool_name: Name of the tool to use
            arguments: Tool arguments

        Returns:
            Tool result or error if not permitted
        """
        if not self.mcp_client:
            return {
                "tool": tool_name,
                "error": "MCP client not available",
                "success": False,
            }

        # Check permissions
        if not ToolPermission.can_use_tool(self.agent_role, tool_name):
            return {
                "tool": tool_name,
                "error": f"Agent role '{self.agent_role}' is not permitted to use tool '{tool_name}'",
                "success": False,
            }

        # Call the tool
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            return result
        except Exception as exc:
            logger.error(f"Tool '{tool_name}' call failed: {exc}", exc_info=True)
            return {
                "tool": tool_name,
                "error": str(exc),
                "success": False,
            }

    def get_available_tools(self) -> list[Dict[str, Any]]:
        """Get list of tools available to this agent role.

        Returns:
            List of available tools
        """
        if not self.mcp_client:
            return []

        all_tools = self.mcp_client.list_tools()
        return ToolPermission.filter_tools(self.agent_role, all_tools)

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if agent can use a specific tool.

        Args:
            tool_name: Tool name to check

        Returns:
            True if agent can use the tool
        """
        return ToolPermission.can_use_tool(self.agent_role, tool_name)

