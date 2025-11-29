"""Admin endpoints for tool analytics and management."""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query, status

from ...mcp.tool_registry import get_tool_registry
from ...mcp.tool_usage_tracker import get_tool_usage_tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tools/analytics", status_code=status.HTTP_200_OK)
def get_tool_analytics(
    tool_name: str | None = Query(default=None, description="Filter by specific tool"),
    agent_role: str | None = Query(default=None, description="Filter by agent role"),
) -> Dict[str, Any]:
    """Get comprehensive tool usage analytics.

    Final path: /api/v1/admin/tools/analytics?tool_name={name}&agent_role={role}
    """
    try:
        tracker = get_tool_usage_tracker()
        
        if tool_name:
            # Get stats for specific tool
            stats = tracker.get_tool_stats(tool_name)
            return {
                "tool_name": tool_name,
                "statistics": stats,
            }
        elif agent_role:
            # Get stats for specific agent
            stats = tracker.get_agent_stats(agent_role)
            return {
                "agent_role": agent_role,
                "statistics": stats,
            }
        else:
            # Get overall summary
            summary = tracker.get_summary()
            all_stats = tracker.get_all_stats()
            return {
                "summary": summary,
                "all_tools": all_stats,
            }
    except Exception as exc:
        logger.exception("Failed to get tool analytics: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool analytics",
        ) from exc


@router.get("/tools/performance", status_code=status.HTTP_200_OK)
def get_tool_performance() -> Dict[str, Any]:
    """Get tool performance metrics.

    Final path: /api/v1/admin/tools/performance
    """
    try:
        tracker = get_tool_usage_tracker()
        all_stats = tracker.get_all_stats()
        
        # Calculate performance metrics
        performance_metrics = {}
        for tool_name, stats in all_stats.items():
            performance_metrics[tool_name] = {
                "success_rate": stats.get("success_rate", 0.0),
                "avg_duration": stats.get("avg_duration", 0.0),
                "total_calls": stats.get("calls", 0),
                "reliability_score": round(
                    stats.get("success_rate", 0.0) * (1.0 / max(stats.get("avg_duration", 1.0), 0.1)),
                    3
                ),
            }
        
        # Sort by reliability score
        sorted_tools = sorted(
            performance_metrics.items(),
            key=lambda x: x[1]["reliability_score"],
            reverse=True,
        )
        
        return {
            "performance_metrics": dict(performance_metrics),
            "top_performers": [
                {"tool": name, **metrics}
                for name, metrics in sorted_tools[:10]
            ],
            "needs_attention": [
                {"tool": name, **metrics}
                for name, metrics in sorted_tools
                if metrics["success_rate"] < 0.8 or metrics["avg_duration"] > 5.0
            ],
        }
    except Exception as exc:
        logger.exception("Failed to get tool performance: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool performance",
        ) from exc


@router.get("/tools/health", status_code=status.HTTP_200_OK)
def get_tools_health() -> Dict[str, Any]:
    """Get health status of all tools.

    Final path: /api/v1/admin/tools/health
    """
    try:
        registry = get_tool_registry()
        tracker = get_tool_usage_tracker()
        
        all_tools = registry.list()
        all_stats = tracker.get_all_stats()
        
        health_status = {}
        for tool in all_tools:
            tool_name = tool["name"]
            stats = all_stats.get(tool_name, {})
            
            # Determine health status
            success_rate = stats.get("success_rate", 1.0)
            calls = stats.get("calls", 0)
            
            if calls == 0:
                health = "unknown"
            elif success_rate >= 0.95:
                health = "healthy"
            elif success_rate >= 0.80:
                health = "degraded"
            else:
                health = "unhealthy"
            
            health_status[tool_name] = {
                "health": health,
                "success_rate": success_rate,
                "total_calls": calls,
                "last_used": stats.get("last_used"),
            }
        
        # Count health statuses
        health_counts = {
            "healthy": sum(1 for h in health_status.values() if h["health"] == "healthy"),
            "degraded": sum(1 for h in health_status.values() if h["health"] == "degraded"),
            "unhealthy": sum(1 for h in health_status.values() if h["health"] == "unhealthy"),
            "unknown": sum(1 for h in health_status.values() if h["health"] == "unknown"),
        }
        
        return {
            "overall_health": "healthy" if health_counts["unhealthy"] == 0 else "degraded",
            "health_counts": health_counts,
            "tools": health_status,
        }
    except Exception as exc:
        logger.exception("Failed to get tools health: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tools health",
        ) from exc

