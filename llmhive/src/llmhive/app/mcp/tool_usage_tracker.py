"""Tool usage tracking and metrics for MCP."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ToolUsageTracker:
    """Tracks tool usage for metrics and monitoring."""

    def __init__(self) -> None:
        self._usage_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_time": 0.0,
                "last_used": None,
                "errors": [],
            }
        )
        self._agent_tool_usage: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_tool_call(
        self,
        tool_name: str,
        agent_role: str,
        success: bool,
        duration: float = 0.0,
        error: str | None = None,
    ) -> None:
        """Record a tool call.

        Args:
            tool_name: Name of the tool
            agent_role: Agent role that used the tool
            success: Whether the call was successful
            duration: Call duration in seconds
            error: Error message if failed
        """
        stats = self._usage_stats[tool_name]
        stats["calls"] += 1
        stats["last_used"] = datetime.utcnow().isoformat()
        stats["total_time"] += duration

        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            if error:
                stats["errors"].append(error)
                # Keep only last 10 errors
                if len(stats["errors"]) > 10:
                    stats["errors"] = stats["errors"][-10:]

        # Record agent-specific usage
        self._agent_tool_usage[agent_role].append({
            "tool": tool_name,
            "success": success,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
        })

        logger.debug(
            f"Tool usage recorded: {tool_name} by {agent_role} - "
            f"success={success}, duration={duration:.3f}s"
        )

    def get_tool_stats(self, tool_name: str) -> Dict[str, Any]:
        """Get statistics for a specific tool.

        Args:
            tool_name: Tool name

        Returns:
            Tool statistics
        """
        stats = self._usage_stats.get(tool_name, {})
        if not stats:
            return {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
            }

        calls = stats["calls"]
        successes = stats["successes"]
        avg_duration = stats["total_time"] / calls if calls > 0 else 0.0
        success_rate = successes / calls if calls > 0 else 0.0

        return {
            "calls": calls,
            "successes": successes,
            "failures": stats["failures"],
            "success_rate": round(success_rate, 3),
            "avg_duration": round(avg_duration, 3),
            "total_time": round(stats["total_time"], 3),
            "last_used": stats["last_used"],
            "recent_errors": stats["errors"][-5:],  # Last 5 errors
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tools.

        Returns:
            Dictionary of tool statistics
        """
        return {
            tool_name: self.get_tool_stats(tool_name)
            for tool_name in self._usage_stats.keys()
        }

    def get_agent_stats(self, agent_role: str) -> Dict[str, Any]:
        """Get tool usage statistics for an agent role.

        Args:
            agent_role: Agent role name

        Returns:
            Agent tool usage statistics
        """
        usage = self._agent_tool_usage.get(agent_role, [])
        if not usage:
            return {
                "total_calls": 0,
                "tools_used": [],
                "success_rate": 0.0,
            }

        total_calls = len(usage)
        successful_calls = sum(1 for u in usage if u["success"])
        tools_used = list(set(u["tool"] for u in usage))
        success_rate = successful_calls / total_calls if total_calls > 0 else 0.0

        return {
            "total_calls": total_calls,
            "tools_used": tools_used,
            "success_rate": round(success_rate, 3),
            "recent_calls": usage[-10:],  # Last 10 calls
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get overall tool usage summary.

        Returns:
            Summary statistics
        """
        all_stats = self.get_all_stats()
        total_calls = sum(s["calls"] for s in all_stats.values())
        total_successes = sum(s["successes"] for s in all_stats.values())
        overall_success_rate = total_successes / total_calls if total_calls > 0 else 0.0

        return {
            "total_tool_calls": total_calls,
            "tools_available": len(all_stats),
            "overall_success_rate": round(overall_success_rate, 3),
            "most_used_tools": sorted(
                all_stats.items(),
                key=lambda x: x[1]["calls"],
                reverse=True,
            )[:5],
            "agent_usage": {
                role: self.get_agent_stats(role)
                for role in self._agent_tool_usage.keys()
            },
        }


# Global tracker instance
_tool_usage_tracker: ToolUsageTracker | None = None


def get_tool_usage_tracker() -> ToolUsageTracker:
    """Get the global tool usage tracker instance."""
    global _tool_usage_tracker
    if _tool_usage_tracker is None:
        _tool_usage_tracker = ToolUsageTracker()
    return _tool_usage_tracker

