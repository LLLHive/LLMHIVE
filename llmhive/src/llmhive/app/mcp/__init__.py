"""MCP (Model Context Protocol) integration for LLMHive agents."""
from __future__ import annotations

from .client import MCPClient
from .tool_registry import ToolRegistry, register_tool, get_tool_registry
from .permissions import ToolPermission
from .tool_parser import ToolCallParser
from .tool_usage_tracker import ToolUsageTracker, get_tool_usage_tracker
from .agent_helper import AgentToolHelper

__all__ = [
    "MCPClient",
    "ToolRegistry",
    "register_tool",
    "get_tool_registry",
    "ToolPermission",
    "ToolCallParser",
    "ToolUsageTracker",
    "get_tool_usage_tracker",
    "AgentToolHelper",
]
