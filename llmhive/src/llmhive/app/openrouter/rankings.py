"""Rankings Aggregator for OpenRouter Models.

Builds rankings from internal telemetry data:
- Trending models (usage growth)
- Most used (usage volume)
- Best value (cost-adjusted)
- Best for long context
- Best for tools/agents
- Multimodal leaders

Compliance: Rankings are derived ONLY from our internal telemetry.
No scraping or use of undocumented OpenRouter ranking data.

Data Provenance:
- Usage metrics: Our inference gateway telemetry
- Model attributes: OpenRouter official API
- Cost calculations: OpenRouter pricing from API
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from .models import OpenRouterModel, OpenRouterUsageTelemetry

logger = logging.getLogger(__name__)


class RankingDimension(str, Enum):
    """Ranking dimensions."""
    TRENDING = "trending"
    MOST_USED = "most_used"
    BEST_VALUE = "best_value"
    LONG_CONTEXT = "long_context"
    TOOLS_AGENTS = "tools_agents"
    MULTIMODAL = "multimodal"
    FASTEST = "fastest"
    MOST_RELIABLE = "most_reliable"
    LOWEST_COST = "lowest_cost"


class TimeRange(str, Enum):
    """Time range for rankings."""
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    ALL_TIME = "all"


@dataclass
class RankedModel:
    """A model with ranking data."""
    model: OpenRouterModel
    rank: int
    score: float
    
    # Dimension-specific metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    data_source: str = "internal_telemetry"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model.to_dict(),
            "rank": self.rank,
            "score": self.score,
            "metrics": self.metrics,
            "data_source": self.data_source,
        }


@dataclass 
class RankingResult:
    """Result of a ranking query."""
    dimension: RankingDimension
    time_range: TimeRange
    models: List[RankedModel]
    
    # Metadata
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = "internal_telemetry"
    metric_definitions: Dict[str, str] = field(default_factory=dict)
    
    @property
    def count(self) -> int:
        return len(self.models)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dimension": self.dimension.value,
            "time_range": self.time_range.value,
            "count": self.count,
            "models": [m.to_dict() for m in self.models],
            "generated_at": self.generated_at.isoformat(),
            "data_source": self.data_source,
            "metric_definitions": self.metric_definitions,
        }


class RankingsAggregator:
    """Aggregates telemetry data to build rankings.
    
    Usage:
        agg = RankingsAggregator(db_session)
        
        # Get trending models
        result = agg.get_ranking(
            dimension=RankingDimension.TRENDING,
            time_range=TimeRange.LAST_7D,
            limit=10,
        )
        
        # Get with filters
        result = agg.get_ranking(
            dimension=RankingDimension.BEST_VALUE,
            time_range=TimeRange.LAST_30D,
            filters={
                "min_context": 32000,
                "supports_tools": True,
            },
        )
    """
    
    # Metric definitions for transparency
    METRIC_DEFINITIONS = {
        "usage_count": "Total number of requests through our gateway",
        "usage_growth_pct": "Percentage growth in usage compared to previous period",
        "avg_latency_ms": "Average response time in milliseconds",
        "success_rate": "Percentage of successful requests (no errors)",
        "cost_per_1m_tokens": "Cost in USD per 1 million input tokens",
        "value_score": "Composite score: success_rate / cost_per_1m_tokens",
        "tool_success_rate": "Percentage of successful tool/function calls",
    }
    
    def __init__(self, db_session: Session):
        """Initialize aggregator.
        
        Args:
            db_session: SQLAlchemy session
        """
        self.db = db_session
    
    def _get_time_bounds(self, time_range: TimeRange) -> Tuple[datetime, datetime]:
        """Get time bounds for range."""
        now = datetime.now(timezone.utc)
        
        if time_range == TimeRange.LAST_24H:
            start = now - timedelta(hours=24)
        elif time_range == TimeRange.LAST_7D:
            start = now - timedelta(days=7)
        elif time_range == TimeRange.LAST_30D:
            start = now - timedelta(days=30)
        else:  # ALL_TIME
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        
        return start, now
    
    def _apply_filters(
        self,
        query,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """Apply filters to model query."""
        if not filters:
            return query
        
        # Context length
        if filters.get("min_context"):
            query = query.filter(OpenRouterModel.context_length >= filters["min_context"])
        if filters.get("max_context"):
            query = query.filter(OpenRouterModel.context_length <= filters["max_context"])
        
        # Pricing
        if filters.get("max_price_per_1m"):
            query = query.filter(OpenRouterModel.price_per_1m_prompt <= filters["max_price_per_1m"])
        if filters.get("is_free") is True:
            query = query.filter(OpenRouterModel.is_free == True)
        
        # Capabilities
        if filters.get("supports_tools") is True:
            query = query.filter(OpenRouterModel.supports_tools == True)
        if filters.get("supports_structured") is True:
            query = query.filter(OpenRouterModel.supports_structured == True)
        if filters.get("multimodal_input") is True:
            query = query.filter(OpenRouterModel.multimodal_input == True)
        if filters.get("multimodal_output") is True:
            query = query.filter(OpenRouterModel.multimodal_output == True)
        
        # Categories
        if filters.get("category"):
            # JSON contains check (may vary by DB)
            pass  # TODO: Implement for specific DB
        
        return query
    
    def get_ranking(
        self,
        dimension: RankingDimension,
        time_range: TimeRange = TimeRange.LAST_7D,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[str] = None,
    ) -> RankingResult:
        """Get ranking for a dimension.
        
        Args:
            dimension: Ranking dimension
            time_range: Time range for usage data
            limit: Maximum results
            offset: Pagination offset
            filters: Model attribute filters
            tenant_id: Filter by tenant (for per-tenant rankings)
            
        Returns:
            RankingResult with ranked models
        """
        handlers = {
            RankingDimension.TRENDING: self._rank_trending,
            RankingDimension.MOST_USED: self._rank_most_used,
            RankingDimension.BEST_VALUE: self._rank_best_value,
            RankingDimension.LONG_CONTEXT: self._rank_long_context,
            RankingDimension.TOOLS_AGENTS: self._rank_tools_agents,
            RankingDimension.MULTIMODAL: self._rank_multimodal,
            RankingDimension.FASTEST: self._rank_fastest,
            RankingDimension.MOST_RELIABLE: self._rank_most_reliable,
            RankingDimension.LOWEST_COST: self._rank_lowest_cost,
        }
        
        handler = handlers.get(dimension)
        if not handler:
            raise ValueError(f"Unknown dimension: {dimension}")
        
        return handler(
            time_range=time_range,
            limit=limit,
            offset=offset,
            filters=filters,
            tenant_id=tenant_id,
        )
    
    def _rank_trending(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by usage growth (trending).
        
        Compares current period to previous period of same length.
        """
        start, end = self._get_time_bounds(time_range)
        period_length = end - start
        prev_start = start - period_length
        
        # Get current period usage
        current_usage = self._get_usage_by_model(start, end, tenant_id)
        
        # Get previous period usage
        prev_usage = self._get_usage_by_model(prev_start, start, tenant_id)
        
        # Calculate growth
        rankings = []
        for model_id, current_count in current_usage.items():
            prev_count = prev_usage.get(model_id, 0)
            
            if prev_count > 0:
                growth_pct = ((current_count - prev_count) / prev_count) * 100
            elif current_count > 0:
                growth_pct = 100.0  # New model
            else:
                growth_pct = 0.0
            
            rankings.append((model_id, growth_pct, current_count))
        
        # Sort by growth
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        # Build result
        return self._build_ranking_result(
            dimension=RankingDimension.TRENDING,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="usage_growth_pct",
        )
    
    def _rank_most_used(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by total usage volume."""
        start, end = self._get_time_bounds(time_range)
        usage = self._get_usage_by_model(start, end, tenant_id)
        
        # Sort by usage count
        rankings = [(mid, count, count) for mid, count in usage.items()]
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return self._build_ranking_result(
            dimension=RankingDimension.MOST_USED,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="usage_count",
        )
    
    def _rank_best_value(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by value (quality/cost ratio).
        
        Value = success_rate / (cost_per_1m + 0.01)
        Higher is better.
        """
        start, end = self._get_time_bounds(time_range)
        
        # Get telemetry aggregates
        telemetry = self._get_aggregated_telemetry(start, end, tenant_id)
        
        # Get models with their costs
        models_query = self.db.query(OpenRouterModel).filter(
            OpenRouterModel.is_active == True
        )
        models_query = self._apply_filters(models_query, filters)
        models = {m.id: m for m in models_query.all()}
        
        # Calculate value scores
        rankings = []
        for model_id, stats in telemetry.items():
            if model_id not in models:
                continue
            
            model = models[model_id]
            success_rate = stats["success_rate"]
            cost = float(model.price_per_1m_prompt or 0.01) + 0.01  # Avoid div by zero
            
            value_score = success_rate / cost
            rankings.append((model_id, value_score, stats["request_count"]))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return self._build_ranking_result(
            dimension=RankingDimension.BEST_VALUE,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="value_score",
        )
    
    def _rank_long_context(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by context length."""
        query = self.db.query(OpenRouterModel).filter(
            OpenRouterModel.is_active == True,
            OpenRouterModel.context_length.isnot(None),
        ).order_by(OpenRouterModel.context_length.desc())
        
        query = self._apply_filters(query, filters)
        models = query.offset(offset).limit(limit).all()
        
        ranked = []
        for i, model in enumerate(models):
            ranked.append(RankedModel(
                model=model,
                rank=offset + i + 1,
                score=float(model.context_length or 0),
                metrics={
                    "context_length": model.context_length,
                },
            ))
        
        return RankingResult(
            dimension=RankingDimension.LONG_CONTEXT,
            time_range=time_range,
            models=ranked,
            metric_definitions={"context_length": "Maximum context window in tokens"},
        )
    
    def _rank_tools_agents(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by tool/agent capabilities and success rate."""
        start, end = self._get_time_bounds(time_range)
        
        # Get tool usage stats
        telemetry = self._get_aggregated_telemetry(start, end, tenant_id)
        
        # Get models with tool support
        query = self.db.query(OpenRouterModel).filter(
            OpenRouterModel.is_active == True,
            OpenRouterModel.supports_tools == True,
        )
        query = self._apply_filters(query, filters)
        models = {m.id: m for m in query.all()}
        
        # Score by tool success rate
        rankings = []
        for model_id, stats in telemetry.items():
            if model_id not in models:
                continue
            
            tool_count = stats.get("tool_call_count", 0)
            tool_success = stats.get("tool_success_count", 0)
            
            if tool_count > 0:
                tool_success_rate = tool_success / tool_count
            else:
                tool_success_rate = 1.0  # Default for models with no tool calls yet
            
            # Weight by usage
            score = tool_success_rate * min(1.0, tool_count / 100)
            rankings.append((model_id, score, tool_count))
        
        # Add models with no telemetry but have tool support
        for model_id, model in models.items():
            if model_id not in telemetry:
                rankings.append((model_id, 0.5, 0))  # Neutral score
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return self._build_ranking_result(
            dimension=RankingDimension.TOOLS_AGENTS,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="tool_success_rate",
        )
    
    def _rank_multimodal(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank multimodal models by capabilities and usage."""
        start, end = self._get_time_bounds(time_range)
        telemetry = self._get_aggregated_telemetry(start, end, tenant_id)
        
        # Get multimodal models
        query = self.db.query(OpenRouterModel).filter(
            OpenRouterModel.is_active == True,
            or_(
                OpenRouterModel.multimodal_input == True,
                OpenRouterModel.multimodal_output == True,
            ),
        )
        query = self._apply_filters(query, filters)
        models = {m.id: m for m in query.all()}
        
        # Score: 2 points for input+output, 1 for either, weighted by usage
        rankings = []
        for model_id, model in models.items():
            base_score = 0
            if model.multimodal_input:
                base_score += 1
            if model.multimodal_output:
                base_score += 1
            
            usage = telemetry.get(model_id, {}).get("request_count", 0)
            usage_weight = min(1.0, usage / 1000)
            
            score = base_score * (0.5 + 0.5 * usage_weight)
            rankings.append((model_id, score, usage))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return self._build_ranking_result(
            dimension=RankingDimension.MULTIMODAL,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="multimodal_score",
        )
    
    def _rank_fastest(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by average response latency (lower is better)."""
        start, end = self._get_time_bounds(time_range)
        telemetry = self._get_aggregated_telemetry(start, end, tenant_id)
        
        # Get models
        query = self.db.query(OpenRouterModel).filter(OpenRouterModel.is_active == True)
        query = self._apply_filters(query, filters)
        models = {m.id: m for m in query.all()}
        
        rankings = []
        for model_id, stats in telemetry.items():
            if model_id not in models:
                continue
            
            avg_latency = stats.get("avg_latency_ms", float("inf"))
            if avg_latency > 0:
                # Invert so lower latency = higher score
                score = 1000000 / avg_latency
                rankings.append((model_id, score, stats["request_count"]))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return self._build_ranking_result(
            dimension=RankingDimension.FASTEST,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="avg_latency_ms",
        )
    
    def _rank_most_reliable(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by success rate (higher is better)."""
        start, end = self._get_time_bounds(time_range)
        telemetry = self._get_aggregated_telemetry(start, end, tenant_id)
        
        # Get models
        query = self.db.query(OpenRouterModel).filter(OpenRouterModel.is_active == True)
        query = self._apply_filters(query, filters)
        models = {m.id: m for m in query.all()}
        
        # Require minimum sample size
        min_requests = 10
        
        rankings = []
        for model_id, stats in telemetry.items():
            if model_id not in models:
                continue
            if stats["request_count"] < min_requests:
                continue
            
            success_rate = stats["success_rate"]
            rankings.append((model_id, success_rate, stats["request_count"]))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return self._build_ranking_result(
            dimension=RankingDimension.MOST_RELIABLE,
            time_range=time_range,
            rankings=rankings[offset:offset + limit],
            filters=filters,
            metric_name="success_rate",
        )
    
    def _rank_lowest_cost(
        self,
        time_range: TimeRange,
        limit: int,
        offset: int,
        filters: Optional[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> RankingResult:
        """Rank by pricing (lower is better)."""
        query = self.db.query(OpenRouterModel).filter(
            OpenRouterModel.is_active == True,
            OpenRouterModel.price_per_1m_prompt.isnot(None),
        ).order_by(OpenRouterModel.price_per_1m_prompt.asc())
        
        query = self._apply_filters(query, filters)
        models = query.offset(offset).limit(limit).all()
        
        ranked = []
        for i, model in enumerate(models):
            ranked.append(RankedModel(
                model=model,
                rank=offset + i + 1,
                score=1.0 / (float(model.price_per_1m_prompt or 0.01) + 0.01),
                metrics={
                    "cost_per_1m_tokens": float(model.price_per_1m_prompt or 0),
                    "is_free": model.is_free,
                },
            ))
        
        return RankingResult(
            dimension=RankingDimension.LOWEST_COST,
            time_range=time_range,
            models=ranked,
            metric_definitions=self.METRIC_DEFINITIONS,
        )
    
    def _get_usage_by_model(
        self,
        start: datetime,
        end: datetime,
        tenant_id: Optional[str],
    ) -> Dict[str, int]:
        """Get request counts by model."""
        query = self.db.query(
            OpenRouterUsageTelemetry.model_id,
            func.sum(OpenRouterUsageTelemetry.request_count).label("total"),
        ).filter(
            OpenRouterUsageTelemetry.time_bucket >= start,
            OpenRouterUsageTelemetry.time_bucket < end,
        )
        
        if tenant_id:
            query = query.filter(OpenRouterUsageTelemetry.tenant_id == tenant_id)
        
        query = query.group_by(OpenRouterUsageTelemetry.model_id)
        
        return {row.model_id: row.total for row in query.all()}
    
    def _get_aggregated_telemetry(
        self,
        start: datetime,
        end: datetime,
        tenant_id: Optional[str],
    ) -> Dict[str, Dict[str, Any]]:
        """Get aggregated telemetry by model."""
        query = self.db.query(
            OpenRouterUsageTelemetry.model_id,
            func.sum(OpenRouterUsageTelemetry.request_count).label("request_count"),
            func.sum(OpenRouterUsageTelemetry.success_count).label("success_count"),
            func.sum(OpenRouterUsageTelemetry.error_count).label("error_count"),
            func.sum(OpenRouterUsageTelemetry.total_latency_ms).label("total_latency"),
            func.sum(OpenRouterUsageTelemetry.tool_call_count).label("tool_call_count"),
            func.sum(OpenRouterUsageTelemetry.tool_success_count).label("tool_success_count"),
            func.sum(OpenRouterUsageTelemetry.total_cost_usd).label("total_cost"),
        ).filter(
            OpenRouterUsageTelemetry.time_bucket >= start,
            OpenRouterUsageTelemetry.time_bucket < end,
        )
        
        if tenant_id:
            query = query.filter(OpenRouterUsageTelemetry.tenant_id == tenant_id)
        
        query = query.group_by(OpenRouterUsageTelemetry.model_id)
        
        result = {}
        for row in query.all():
            total = row.request_count or 0
            success = row.success_count or 0
            
            result[row.model_id] = {
                "request_count": total,
                "success_count": success,
                "error_count": row.error_count or 0,
                "success_rate": success / total if total > 0 else 0.0,
                "avg_latency_ms": (row.total_latency or 0) / total if total > 0 else 0,
                "tool_call_count": row.tool_call_count or 0,
                "tool_success_count": row.tool_success_count or 0,
                "total_cost": float(row.total_cost or 0),
            }
        
        return result
    
    def _build_ranking_result(
        self,
        dimension: RankingDimension,
        time_range: TimeRange,
        rankings: List[Tuple[str, float, int]],
        filters: Optional[Dict[str, Any]],
        metric_name: str,
    ) -> RankingResult:
        """Build ranking result from (model_id, score, usage) tuples."""
        # Fetch models
        model_ids = [r[0] for r in rankings]
        query = self.db.query(OpenRouterModel).filter(OpenRouterModel.id.in_(model_ids))
        query = self._apply_filters(query, filters)
        models = {m.id: m for m in query.all()}
        
        ranked = []
        for i, (model_id, score, usage) in enumerate(rankings):
            if model_id not in models:
                continue
            
            ranked.append(RankedModel(
                model=models[model_id],
                rank=i + 1,
                score=score,
                metrics={
                    metric_name: score,
                    "usage_count": usage,
                },
            ))
        
        return RankingResult(
            dimension=dimension,
            time_range=time_range,
            models=ranked,
            metric_definitions=self.METRIC_DEFINITIONS,
        )

