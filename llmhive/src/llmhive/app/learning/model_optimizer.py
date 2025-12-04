"""Model Optimizer for Continuous Learning.

This module analyzes historical performance data and optimizes model selection:
- Adjusts model weights based on success rates
- Prefers faster models for simple queries
- Routes complex queries to best-performing models
- Considers domain-specific performance
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .performance_logger import get_performance_logger, PerformanceLogger

logger = logging.getLogger(__name__)


class OptimizationStrategy(str, Enum):
    """Strategy for model weight optimization."""
    BALANCED = "balanced"           # Balance quality and speed
    QUALITY_FIRST = "quality_first"  # Prioritize quality over speed
    SPEED_FIRST = "speed_first"      # Prioritize speed over quality
    COST_OPTIMIZED = "cost_optimized"  # Minimize token usage


@dataclass
class ModelWeight:
    """Optimized weight for a model."""
    model_name: str
    base_weight: float = 1.0
    quality_factor: float = 1.0
    speed_factor: float = 1.0
    success_factor: float = 1.0
    domain_factor: float = 1.0
    recency_factor: float = 1.0  # Recent performance matters more
    
    # Computed total weight
    total_weight: float = 1.0
    
    # Metadata
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def compute_total(self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED) -> float:
        """Compute total weight based on strategy."""
        if strategy == OptimizationStrategy.QUALITY_FIRST:
            self.total_weight = (
                self.base_weight *
                (self.quality_factor ** 2) *
                self.success_factor *
                self.domain_factor *
                self.recency_factor
            )
        elif strategy == OptimizationStrategy.SPEED_FIRST:
            self.total_weight = (
                self.base_weight *
                (self.speed_factor ** 2) *
                self.quality_factor *
                self.success_factor *
                self.recency_factor
            )
        elif strategy == OptimizationStrategy.COST_OPTIMIZED:
            self.total_weight = (
                self.base_weight *
                self.speed_factor *
                self.success_factor *
                self.recency_factor
            )
        else:  # BALANCED
            self.total_weight = (
                self.base_weight *
                self.quality_factor *
                self.speed_factor *
                self.success_factor *
                self.domain_factor *
                self.recency_factor
            )
        return self.total_weight
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_weight": self.base_weight,
            "quality_factor": self.quality_factor,
            "speed_factor": self.speed_factor,
            "success_factor": self.success_factor,
            "domain_factor": self.domain_factor,
            "recency_factor": self.recency_factor,
            "total_weight": self.total_weight,
            "last_updated": self.last_updated,
        }


@dataclass
class QueryClassification:
    """Classification of a query for routing."""
    complexity: str  # "simple", "moderate", "complex"
    domain: str  # "coding", "research", "general", etc.
    estimated_tokens: int
    requires_reasoning: bool = False
    requires_tools: bool = False
    requires_knowledge: bool = False
    
    @property
    def is_simple(self) -> bool:
        return self.complexity == "simple"
    
    @property
    def is_complex(self) -> bool:
        return self.complexity == "complex"


class ModelOptimizer:
    """Optimizes model selection based on historical performance.
    
    Key features:
    - Analyzes historical success rates and latencies
    - Adjusts weights dynamically based on recent performance
    - Considers domain-specific performance
    - Supports multiple optimization strategies
    """
    
    # Default model capabilities
    MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
        "gpt-4o": {
            "speed_rating": 0.7,
            "quality_rating": 0.95,
            "cost_per_1k": 0.03,
            "strengths": ["reasoning", "coding", "general"],
        },
        "gpt-4o-mini": {
            "speed_rating": 0.95,
            "quality_rating": 0.8,
            "cost_per_1k": 0.003,
            "strengths": ["general", "quick-tasks"],
        },
        "claude-3-5-sonnet-20241022": {
            "speed_rating": 0.8,
            "quality_rating": 0.92,
            "cost_per_1k": 0.015,
            "strengths": ["coding", "analysis", "writing"],
        },
        "claude-3-5-haiku-20241022": {
            "speed_rating": 0.95,
            "quality_rating": 0.75,
            "cost_per_1k": 0.001,
            "strengths": ["general", "quick-tasks"],
        },
        "deepseek-chat": {
            "speed_rating": 0.85,
            "quality_rating": 0.85,
            "cost_per_1k": 0.001,
            "strengths": ["coding", "math"],
        },
        "deepseek-reasoner": {
            "speed_rating": 0.6,
            "quality_rating": 0.9,
            "cost_per_1k": 0.003,
            "strengths": ["reasoning", "math", "analysis"],
        },
        "grok-beta": {
            "speed_rating": 0.8,
            "quality_rating": 0.85,
            "cost_per_1k": 0.01,
            "strengths": ["general", "real-time"],
        },
    }
    
    def __init__(
        self,
        perf_logger: Optional[PerformanceLogger] = None,
        learning_rate: float = 0.1,
        recency_decay: float = 0.95,
    ):
        self.perf_logger = perf_logger or get_performance_logger()
        self.learning_rate = learning_rate
        self.recency_decay = recency_decay
        self._weights: Dict[str, ModelWeight] = {}
        self._domain_weights: Dict[str, Dict[str, ModelWeight]] = {}
        self._last_optimization: Optional[str] = None
        
        logger.info(
            "ModelOptimizer initialized (learning_rate=%.2f, recency_decay=%.2f)",
            learning_rate, recency_decay
        )
    
    def classify_query(self, query: str) -> QueryClassification:
        """Classify a query for optimal model routing."""
        query_lower = query.lower()
        
        # Estimate complexity
        word_count = len(query.split())
        has_code_request = any(kw in query_lower for kw in [
            "code", "program", "function", "implement", "debug", "fix"
        ])
        has_research_request = any(kw in query_lower for kw in [
            "research", "analyze", "compare", "explain in detail", "comprehensive"
        ])
        has_reasoning_request = any(kw in query_lower for kw in [
            "think", "reason", "solve", "prove", "calculate", "derive"
        ])
        
        # Complexity classification
        if word_count < 20 and not has_code_request and not has_research_request:
            complexity = "simple"
        elif word_count > 100 or has_research_request or has_reasoning_request:
            complexity = "complex"
        else:
            complexity = "moderate"
        
        # Domain classification
        if has_code_request:
            domain = "coding"
        elif has_research_request:
            domain = "research"
        elif has_reasoning_request:
            domain = "reasoning"
        elif any(kw in query_lower for kw in ["math", "calculate", "equation"]):
            domain = "math"
        else:
            domain = "general"
        
        # Estimate token usage
        estimated_tokens = word_count * 2  # Rough estimate
        
        return QueryClassification(
            complexity=complexity,
            domain=domain,
            estimated_tokens=estimated_tokens,
            requires_reasoning=has_reasoning_request,
            requires_tools="search" in query_lower or "look up" in query_lower,
            requires_knowledge=has_research_request,
        )
    
    def get_model_weights(
        self,
        domain: Optional[str] = None,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        days: int = 30,
    ) -> Dict[str, ModelWeight]:
        """Get optimized weights for all models.
        
        Args:
            domain: Optional domain filter for domain-specific weights
            strategy: Optimization strategy to use
            days: Number of days of history to consider
            
        Returns:
            Dict mapping model names to their optimized weights
        """
        # Get historical stats
        all_stats = self.perf_logger.get_all_model_stats(days=days)
        stats_by_model = {s["model_name"]: s for s in all_stats}
        
        weights = {}
        
        for model_name, capabilities in self.MODEL_CAPABILITIES.items():
            stats = stats_by_model.get(model_name, {})
            
            # Base weight from capabilities
            base_weight = 1.0
            
            # Quality factor from historical data or defaults
            if stats.get("avg_quality") is not None and stats["avg_quality"] > 0:
                quality_factor = 0.5 + (stats["avg_quality"] * 0.5)
            else:
                quality_factor = capabilities.get("quality_rating", 0.8)
            
            # Speed factor from historical latency
            if stats.get("avg_latency_ms") is not None and stats["avg_latency_ms"] > 0:
                # Normalize latency to 0-1 scale (faster is better)
                # Assume 10000ms is very slow, 100ms is very fast
                latency_score = 1.0 - min(stats["avg_latency_ms"] / 10000, 1.0)
                speed_factor = 0.3 + (latency_score * 0.7)
            else:
                speed_factor = capabilities.get("speed_rating", 0.8)
            
            # Success factor from historical success rate
            if stats.get("total_queries", 0) > 0 and stats.get("successful_calls"):
                success_rate = stats["successful_calls"] / stats["total_queries"]
                success_factor = 0.5 + (success_rate * 0.5)
            else:
                success_factor = 1.0
            
            # Domain factor (check if model is good at this domain)
            domain_factor = 1.0
            if domain:
                strengths = capabilities.get("strengths", [])
                if domain in strengths:
                    domain_factor = 1.3  # Boost for domain expertise
                elif "general" not in strengths:
                    domain_factor = 0.7  # Penalty for specialists outside domain
            
            # Recency factor (prefer models with recent successful usage)
            recency_factor = 1.0
            if stats.get("total_queries", 0) > 10:
                recency_factor = 1.1
            elif stats.get("total_queries", 0) == 0:
                recency_factor = 0.9  # Slight penalty for unused models
            
            weight = ModelWeight(
                model_name=model_name,
                base_weight=base_weight,
                quality_factor=quality_factor,
                speed_factor=speed_factor,
                success_factor=success_factor,
                domain_factor=domain_factor,
                recency_factor=recency_factor,
            )
            weight.compute_total(strategy)
            weights[model_name] = weight
        
        return weights
    
    def select_models(
        self,
        query: str,
        max_models: int = 3,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        required_models: Optional[List[str]] = None,
        excluded_models: Optional[List[str]] = None,
    ) -> List[str]:
        """Select optimal models for a query.
        
        Args:
            query: The user query
            max_models: Maximum number of models to select
            strategy: Optimization strategy
            required_models: Models that must be included
            excluded_models: Models to exclude
            
        Returns:
            Ordered list of model names (best first)
        """
        classification = self.classify_query(query)
        
        # Adjust strategy based on query complexity
        if classification.is_simple and strategy == OptimizationStrategy.BALANCED:
            strategy = OptimizationStrategy.SPEED_FIRST
        elif classification.is_complex and strategy == OptimizationStrategy.BALANCED:
            strategy = OptimizationStrategy.QUALITY_FIRST
        
        # Get weights
        weights = self.get_model_weights(
            domain=classification.domain,
            strategy=strategy,
        )
        
        # Filter and sort
        excluded = set(excluded_models or [])
        required = set(required_models or [])
        
        candidates = [
            (model, weight)
            for model, weight in weights.items()
            if model not in excluded
        ]
        
        # Sort by weight
        candidates.sort(key=lambda x: x[1].total_weight, reverse=True)
        
        # Build selection
        selected = []
        
        # Add required models first
        for model in required:
            if model in weights:
                selected.append(model)
        
        # Add top weighted models
        for model, weight in candidates:
            if len(selected) >= max_models:
                break
            if model not in selected:
                selected.append(model)
        
        logger.info(
            "Selected models for '%s...' (complexity=%s, domain=%s): %s",
            query[:30], classification.complexity, classification.domain,
            selected
        )
        
        return selected
    
    def select_single_model(
        self,
        query: str,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    ) -> str:
        """Select the single best model for a query."""
        models = self.select_models(query, max_models=1, strategy=strategy)
        return models[0] if models else "gpt-4o-mini"
    
    def update_weights_from_feedback(
        self,
        model_name: str,
        positive: bool,
        domain: Optional[str] = None,
    ) -> None:
        """Update model weights based on user feedback.
        
        Args:
            model_name: Model that received feedback
            positive: Whether feedback was positive
            domain: Optional domain for domain-specific updates
        """
        if model_name not in self._weights:
            self._weights[model_name] = ModelWeight(model_name=model_name)
        
        weight = self._weights[model_name]
        
        # Apply learning rate
        adjustment = self.learning_rate if positive else -self.learning_rate
        
        # Update success factor
        weight.success_factor = max(0.1, min(2.0, weight.success_factor + adjustment))
        
        # Update quality factor
        if positive:
            weight.quality_factor = min(2.0, weight.quality_factor + adjustment * 0.5)
        else:
            weight.quality_factor = max(0.1, weight.quality_factor + adjustment * 0.5)
        
        weight.last_updated = datetime.now(timezone.utc).isoformat()
        weight.compute_total()
        
        logger.info(
            "Updated weights for %s: success=%.2f, quality=%.2f (positive=%s)",
            model_name, weight.success_factor, weight.quality_factor, positive
        )
    
    def get_optimization_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate a report on model optimization.
        
        Returns a summary of model performance and recommendations.
        """
        all_stats = self.perf_logger.get_all_model_stats(days=days)
        regeneration_rate = self.perf_logger.get_regeneration_rate(days=days)
        
        # Calculate rankings
        by_quality = sorted(
            all_stats,
            key=lambda x: x.get("avg_quality") or 0,
            reverse=True
        )
        by_speed = sorted(
            all_stats,
            key=lambda x: x.get("avg_latency_ms") or float("inf")
        )
        by_usage = sorted(
            all_stats,
            key=lambda x: x.get("total_queries") or 0,
            reverse=True
        )
        
        # Generate recommendations
        recommendations = []
        
        if regeneration_rate > 0.2:
            recommendations.append(
                "High regeneration rate (%.1f%%) suggests quality issues. "
                "Consider routing more queries to higher-quality models." % (regeneration_rate * 100)
            )
        
        if by_quality and by_quality[0].get("avg_quality", 0) < 0.7:
            recommendations.append(
                "Overall quality is low. Consider enabling more verification steps."
            )
        
        return {
            "period_days": days,
            "total_queries": sum(s.get("total_queries", 0) for s in all_stats),
            "regeneration_rate": regeneration_rate,
            "model_rankings": {
                "by_quality": [s["model_name"] for s in by_quality[:5]],
                "by_speed": [s["model_name"] for s in by_speed[:5]],
                "by_usage": [s["model_name"] for s in by_usage[:5]],
            },
            "model_stats": {s["model_name"]: s for s in all_stats},
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Global instance
_model_optimizer: Optional[ModelOptimizer] = None


def get_model_optimizer() -> ModelOptimizer:
    """Get the global model optimizer instance."""
    global _model_optimizer
    if _model_optimizer is None:
        _model_optimizer = ModelOptimizer()
    return _model_optimizer
