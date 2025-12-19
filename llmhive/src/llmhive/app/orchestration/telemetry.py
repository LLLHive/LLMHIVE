"""PR8: Orchestrator Telemetry Module

Tracks and aggregates orchestration metrics:
- Strategy usage and outcomes
- Model performance per role
- Tool usage statistics
- Cost and latency metrics
- Verification and refinement triggers

This module provides in-memory storage with optional database persistence.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StrategyType(str, Enum):
    """Orchestration strategy types."""
    AUTOMATIC = "automatic"
    SINGLE_BEST = "single_best"
    PARALLEL_RACE = "parallel_race"
    BEST_OF_N = "best_of_n"
    QUALITY_WEIGHTED_FUSION = "quality_weighted_fusion"
    EXPERT_PANEL = "expert_panel"
    CHALLENGE_AND_REFINE = "challenge_and_refine"


class ModelRole(str, Enum):
    """Model role in orchestration."""
    PRIMARY = "primary"
    VALIDATOR = "validator"
    FALLBACK = "fallback"
    SPECIALIST = "specialist"


class ToolType(str, Enum):
    """Tool types used in orchestration."""
    WEB_SEARCH = "web_search"
    CALCULATOR = "calculator"
    CODE_EXECUTION = "code_execution"
    RAG_RETRIEVAL = "rag_retrieval"
    IMAGE_GENERATION = "image_generation"


@dataclass
class OrchestrationEvent:
    """Single orchestration event for telemetry."""
    timestamp: datetime
    strategy: str
    models_used: List[str]
    model_roles: Dict[str, str]  # model_id -> role
    tools_used: List[str]
    success: bool
    latency_ms: int
    tokens_used: int
    cost_usd: float
    quality_score: Optional[float] = None
    verification_triggered: bool = False
    refinement_loops: int = 0
    budget_exceeded: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyMetrics:
    """Aggregated metrics for a strategy."""
    strategy: str
    total_count: int = 0
    success_count: int = 0
    total_latency_ms: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_quality: float = 0.0
    quality_count: int = 0  # Count of events with quality scores
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def avg_quality(self) -> float:
        return self.total_quality / self.quality_count if self.quality_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "count": self.total_count,
            "successRate": self.success_rate,
            "avgLatencyMs": self.avg_latency_ms,
            "avgCost": self.avg_cost,
            "avgQuality": self.avg_quality,
        }


@dataclass
class ModelMetrics:
    """Aggregated metrics for a model."""
    model_id: str
    total_count: int = 0
    success_count: int = 0
    total_latency_ms: int = 0
    total_cost: float = 0.0
    roles: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def avg_cost(self) -> float:
        return self.total_cost / self.total_count if self.total_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "modelId": self.model_id,
            "count": self.total_count,
            "successRate": self.success_rate,
            "avgLatencyMs": self.avg_latency_ms,
            "avgCost": self.avg_cost,
            "roles": list(self.roles.keys()),
        }


@dataclass
class ToolMetrics:
    """Aggregated metrics for a tool."""
    tool: str
    total_count: int = 0
    success_count: int = 0
    total_latency_ms: int = 0
    
    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_count if self.total_count > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_count if self.total_count > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "count": self.total_count,
            "successRate": self.success_rate,
            "avgLatencyMs": self.avg_latency_ms,
        }


class OrchestratorTelemetry:
    """
    In-memory telemetry storage for orchestrator metrics.
    
    Thread-safe implementation with optional database persistence.
    
    Usage:
        telemetry = OrchestratorTelemetry()
        
        # Record an event
        telemetry.record_event(
            strategy="parallel_race",
            models_used=["gpt-4o", "claude-sonnet-4"],
            model_roles={"gpt-4o": "primary", "claude-sonnet-4": "validator"},
            success=True,
            latency_ms=2500,
            tokens_used=1500,
            cost_usd=0.025,
        )
        
        # Get aggregated metrics
        metrics = telemetry.get_metrics(time_range_hours=24)
    """
    
    def __init__(
        self,
        max_events: int = 10000,
        retention_hours: int = 168,  # 7 days
    ) -> None:
        """
        Initialize telemetry store.
        
        Args:
            max_events: Maximum events to keep in memory
            retention_hours: Hours to retain events
        """
        self._events: List[OrchestrationEvent] = []
        self._lock = Lock()
        self._max_events = max_events
        self._retention_hours = retention_hours
        
        # Cached aggregations
        self._strategy_cache: Dict[str, StrategyMetrics] = {}
        self._model_cache: Dict[str, ModelMetrics] = {}
        self._tool_cache: Dict[str, ToolMetrics] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Refresh cache every minute
        
        logger.info(
            "PR8: OrchestratorTelemetry initialized (max_events=%d, retention=%dh)",
            max_events, retention_hours
        )
    
    def record_event(
        self,
        strategy: str,
        models_used: List[str],
        *,
        model_roles: Optional[Dict[str, str]] = None,
        tools_used: Optional[List[str]] = None,
        success: bool = True,
        latency_ms: int = 0,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        quality_score: Optional[float] = None,
        verification_triggered: bool = False,
        refinement_loops: int = 0,
        budget_exceeded: bool = False,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an orchestration event.
        
        Args:
            strategy: Orchestration strategy used
            models_used: List of model IDs used
            model_roles: Map of model_id -> role
            tools_used: List of tools used
            success: Whether orchestration succeeded
            latency_ms: Total latency in milliseconds
            tokens_used: Total tokens consumed
            cost_usd: Total cost in USD
            quality_score: Optional quality score (0-1)
            verification_triggered: Whether verification was run
            refinement_loops: Number of refinement iterations
            budget_exceeded: Whether budget was exceeded
            error_message: Error message if failed
            metadata: Additional metadata
        """
        event = OrchestrationEvent(
            timestamp=datetime.utcnow(),
            strategy=strategy,
            models_used=models_used,
            model_roles=model_roles or {},
            tools_used=tools_used or [],
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            quality_score=quality_score,
            verification_triggered=verification_triggered,
            refinement_loops=refinement_loops,
            budget_exceeded=budget_exceeded,
            error_message=error_message,
            metadata=metadata or {},
        )
        
        with self._lock:
            self._events.append(event)
            
            # Prune old events
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
            
            # Invalidate cache
            self._cache_timestamp = None
        
        logger.debug(
            "PR8: Recorded telemetry event: strategy=%s, models=%s, success=%s, latency=%dms",
            strategy, models_used, success, latency_ms
        )
    
    def _prune_old_events(self) -> None:
        """Remove events older than retention period."""
        cutoff = datetime.utcnow() - timedelta(hours=self._retention_hours)
        self._events = [e for e in self._events if e.timestamp > cutoff]
    
    def _refresh_cache(self, time_range_hours: int = 24) -> None:
        """Refresh aggregation caches."""
        now = datetime.utcnow()
        
        # Check if cache is still valid
        if (
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds
        ):
            return
        
        cutoff = now - timedelta(hours=time_range_hours)
        
        # Reset caches
        strategy_metrics: Dict[str, StrategyMetrics] = {}
        model_metrics: Dict[str, ModelMetrics] = {}
        tool_metrics: Dict[str, ToolMetrics] = {}
        
        for event in self._events:
            if event.timestamp < cutoff:
                continue
            
            # Aggregate strategy metrics
            if event.strategy not in strategy_metrics:
                strategy_metrics[event.strategy] = StrategyMetrics(strategy=event.strategy)
            
            sm = strategy_metrics[event.strategy]
            sm.total_count += 1
            if event.success:
                sm.success_count += 1
            sm.total_latency_ms += event.latency_ms
            sm.total_tokens += event.tokens_used
            sm.total_cost += event.cost_usd
            if event.quality_score is not None:
                sm.total_quality += event.quality_score
                sm.quality_count += 1
            
            # Aggregate model metrics
            for model_id in event.models_used:
                if model_id not in model_metrics:
                    model_metrics[model_id] = ModelMetrics(model_id=model_id)
                
                mm = model_metrics[model_id]
                mm.total_count += 1
                if event.success:
                    mm.success_count += 1
                mm.total_latency_ms += event.latency_ms
                mm.total_cost += event.cost_usd / len(event.models_used)  # Split cost
                
                role = event.model_roles.get(model_id, "unknown")
                mm.roles[role] += 1
            
            # Aggregate tool metrics
            for tool in event.tools_used:
                if tool not in tool_metrics:
                    tool_metrics[tool] = ToolMetrics(tool=tool)
                
                tm = tool_metrics[tool]
                tm.total_count += 1
                if event.success:
                    tm.success_count += 1
                # Note: tool-specific latency not tracked, using total
        
        self._strategy_cache = strategy_metrics
        self._model_cache = model_metrics
        self._tool_cache = tool_metrics
        self._cache_timestamp = now
    
    def get_metrics(
        self,
        time_range_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for the specified time range.
        
        Args:
            time_range_hours: Hours to look back
            
        Returns:
            Dictionary with aggregated metrics
        """
        with self._lock:
            self._prune_old_events()
            self._refresh_cache(time_range_hours)
            
            cutoff = datetime.utcnow() - timedelta(hours=time_range_hours)
            recent_events = [e for e in self._events if e.timestamp > cutoff]
            
            if not recent_events:
                return {
                    "totalRequests": 0,
                    "successfulRequests": 0,
                    "failedRequests": 0,
                    "avgLatencyMs": 0,
                    "avgCost": 0,
                    "totalCost": 0,
                    "avgTokens": 0,
                    "totalTokens": 0,
                    "strategies": [],
                    "models": [],
                    "tools": [],
                    "verificationTriggers": 0,
                    "refinementLoops": 0,
                    "budgetExceeded": 0,
                    "lastUpdated": datetime.utcnow().isoformat(),
                }
            
            total_requests = len(recent_events)
            successful = sum(1 for e in recent_events if e.success)
            failed = total_requests - successful
            total_latency = sum(e.latency_ms for e in recent_events)
            total_cost = sum(e.cost_usd for e in recent_events)
            total_tokens = sum(e.tokens_used for e in recent_events)
            verification_triggers = sum(1 for e in recent_events if e.verification_triggered)
            refinement_loops = sum(e.refinement_loops for e in recent_events)
            budget_exceeded = sum(1 for e in recent_events if e.budget_exceeded)
            
            return {
                "totalRequests": total_requests,
                "successfulRequests": successful,
                "failedRequests": failed,
                "avgLatencyMs": total_latency / total_requests if total_requests > 0 else 0,
                "avgCost": total_cost / total_requests if total_requests > 0 else 0,
                "totalCost": total_cost,
                "avgTokens": total_tokens / total_requests if total_requests > 0 else 0,
                "totalTokens": total_tokens,
                "strategies": sorted(
                    [sm.to_dict() for sm in self._strategy_cache.values()],
                    key=lambda x: x["count"],
                    reverse=True,
                ),
                "models": sorted(
                    [mm.to_dict() for mm in self._model_cache.values()],
                    key=lambda x: x["count"],
                    reverse=True,
                ),
                "tools": sorted(
                    [tm.to_dict() for tm in self._tool_cache.values()],
                    key=lambda x: x["count"],
                    reverse=True,
                ),
                "verificationTriggers": verification_triggers,
                "refinementLoops": refinement_loops,
                "budgetExceeded": budget_exceeded,
                "lastUpdated": datetime.utcnow().isoformat(),
            }
    
    def get_strategy_ranking(
        self,
        time_range_hours: int = 24,
        sort_by: str = "count",
    ) -> List[Dict[str, Any]]:
        """
        Get strategies ranked by the specified metric.
        
        Args:
            time_range_hours: Hours to look back
            sort_by: Metric to sort by (count, success_rate, avg_quality, avg_cost)
            
        Returns:
            List of strategy metrics, sorted
        """
        with self._lock:
            self._refresh_cache(time_range_hours)
            
            strategies = [sm.to_dict() for sm in self._strategy_cache.values()]
            
            sort_key = {
                "count": lambda x: x["count"],
                "success_rate": lambda x: x["successRate"],
                "avg_quality": lambda x: x["avgQuality"],
                "avg_cost": lambda x: -x["avgCost"],  # Lower is better
                "avg_latency": lambda x: -x["avgLatencyMs"],  # Lower is better
            }.get(sort_by, lambda x: x["count"])
            
            return sorted(strategies, key=sort_key, reverse=True)
    
    def get_model_ranking(
        self,
        time_range_hours: int = 24,
        role: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get models ranked by usage, optionally filtered by role.
        
        Args:
            time_range_hours: Hours to look back
            role: Optional role filter
            
        Returns:
            List of model metrics, sorted by count
        """
        with self._lock:
            self._refresh_cache(time_range_hours)
            
            models = [mm.to_dict() for mm in self._model_cache.values()]
            
            if role:
                models = [m for m in models if role in m["roles"]]
            
            return sorted(models, key=lambda x: x["count"], reverse=True)
    
    def clear(self) -> None:
        """Clear all telemetry data."""
        with self._lock:
            self._events.clear()
            self._strategy_cache.clear()
            self._model_cache.clear()
            self._tool_cache.clear()
            self._cache_timestamp = None
        
        logger.info("PR8: Telemetry data cleared")


# Global singleton instance
_telemetry: Optional[OrchestratorTelemetry] = None
_telemetry_lock = Lock()


def get_telemetry() -> OrchestratorTelemetry:
    """Get or create the global telemetry instance."""
    global _telemetry
    
    if _telemetry is None:
        with _telemetry_lock:
            if _telemetry is None:
                _telemetry = OrchestratorTelemetry()
    
    return _telemetry


def record_orchestration_event(
    strategy: str,
    models_used: List[str],
    **kwargs,
) -> None:
    """Convenience function to record an event to global telemetry."""
    get_telemetry().record_event(strategy, models_used, **kwargs)

