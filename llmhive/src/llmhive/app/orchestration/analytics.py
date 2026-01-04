"""Adaptive Learning & Analytics for LLMHive Stage 4.

This module implements Section 10 of Stage 4 upgrades:
- User interface for model insights
- Auto-tuning via reinforcement signals
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# PERFORMANCE METRICS
# ==============================================================================

@dataclass
class ModelMetrics:
    """Performance metrics for a model."""
    model_id: str
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_retries: int = 0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    user_approvals: int = 0
    user_rejections: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_queries == 0:
            return 0.0
        return self.successful_queries / self.total_queries
    
    @property
    def approval_rate(self) -> float:
        """Calculate user approval rate."""
        total_feedback = self.user_approvals + self.user_rejections
        if total_feedback == 0:
            return 0.5  # Neutral when no feedback
        return self.user_approvals / total_feedback


@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    query_id: str
    query_text: str
    model_used: str
    latency_ms: float
    confidence: float
    success: bool
    retries: int
    sources_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_feedback: Optional[str] = None  # "approve", "reject", None


# ==============================================================================
# METRICS COLLECTOR
# ==============================================================================

class MetricsCollector:
    """Collects and aggregates performance metrics.
    
    Implements Stage 4 Section 10: Analytics and insights.
    """
    
    def __init__(self, persistence_path: Optional[str] = None):
        self._model_metrics: Dict[str, ModelMetrics] = {}
        self._query_history: List[QueryMetrics] = []
        self._max_history = 10000
        self._persistence_path = persistence_path
        self._load_metrics()
    
    def _load_metrics(self):
        """Load metrics from persistence."""
        if not self._persistence_path:
            return
        
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, 'r') as f:
                    data = json.load(f)
                    
                for model_id, m in data.get('models', {}).items():
                    self._model_metrics[model_id] = ModelMetrics(
                        model_id=model_id,
                        total_queries=m.get('total_queries', 0),
                        successful_queries=m.get('successful_queries', 0),
                        failed_queries=m.get('failed_queries', 0),
                        total_retries=m.get('total_retries', 0),
                        avg_latency_ms=m.get('avg_latency_ms', 0.0),
                        avg_confidence=m.get('avg_confidence', 0.0),
                        user_approvals=m.get('user_approvals', 0),
                        user_rejections=m.get('user_rejections', 0),
                    )
                
                logger.info("Loaded metrics for %d models", len(self._model_metrics))
        except Exception as e:
            logger.warning("Failed to load metrics: %s", e)
    
    def _save_metrics(self):
        """Save metrics to persistence."""
        if not self._persistence_path:
            return
        
        try:
            data = {
                'models': {
                    model_id: {
                        'total_queries': m.total_queries,
                        'successful_queries': m.successful_queries,
                        'failed_queries': m.failed_queries,
                        'total_retries': m.total_retries,
                        'avg_latency_ms': m.avg_latency_ms,
                        'avg_confidence': m.avg_confidence,
                        'user_approvals': m.user_approvals,
                        'user_rejections': m.user_rejections,
                    }
                    for model_id, m in self._model_metrics.items()
                },
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            
            with open(self._persistence_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning("Failed to save metrics: %s", e)
    
    def record_query(
        self,
        query_id: str,
        query_text: str,
        model_used: str,
        latency_ms: float,
        confidence: float,
        success: bool,
        retries: int = 0,
        sources_count: int = 0,
    ):
        """Record metrics for a query."""
        # Update model metrics
        if model_used not in self._model_metrics:
            self._model_metrics[model_used] = ModelMetrics(model_id=model_used)
        
        metrics = self._model_metrics[model_used]
        metrics.total_queries += 1
        metrics.total_retries += retries
        
        if success:
            metrics.successful_queries += 1
        else:
            metrics.failed_queries += 1
        
        # Update running averages
        n = metrics.total_queries
        metrics.avg_latency_ms = (
            (metrics.avg_latency_ms * (n - 1) + latency_ms) / n
        )
        metrics.avg_confidence = (
            (metrics.avg_confidence * (n - 1) + confidence) / n
        )
        metrics.last_updated = datetime.now(timezone.utc)
        
        # Record query history
        query_metrics = QueryMetrics(
            query_id=query_id,
            query_text=query_text[:200],
            model_used=model_used,
            latency_ms=latency_ms,
            confidence=confidence,
            success=success,
            retries=retries,
            sources_count=sources_count,
        )
        
        self._query_history.append(query_metrics)
        
        # Trim history if needed
        if len(self._query_history) > self._max_history:
            self._query_history = self._query_history[-self._max_history:]
        
        self._save_metrics()
        
        logger.debug(
            "Recorded query %s: model=%s, latency=%.1fms, confidence=%.2f",
            query_id[:8], model_used, latency_ms, confidence
        )
    
    def record_user_feedback(
        self,
        query_id: str,
        feedback: str,  # "approve" or "reject"
    ):
        """Record user feedback for a query."""
        # Find query in history
        for query in reversed(self._query_history):
            if query.query_id == query_id:
                query.user_feedback = feedback
                
                # Update model metrics
                model_id = query.model_used
                if model_id in self._model_metrics:
                    metrics = self._model_metrics[model_id]
                    if feedback == "approve":
                        metrics.user_approvals += 1
                    elif feedback == "reject":
                        metrics.user_rejections += 1
                    
                    self._save_metrics()
                
                logger.info("Recorded %s feedback for query %s", feedback, query_id[:8])
                return
        
        logger.warning("Query %s not found for feedback", query_id[:8])
    
    def get_model_metrics(self, model_id: str) -> Optional[ModelMetrics]:
        """Get metrics for a specific model."""
        return self._model_metrics.get(model_id)
    
    def get_all_metrics(self) -> Dict[str, ModelMetrics]:
        """Get all model metrics."""
        return self._model_metrics.copy()
    
    def get_recent_queries(self, limit: int = 100) -> List[QueryMetrics]:
        """Get recent query history."""
        return self._query_history[-limit:]
    
    def reset_metrics(self):
        """Reset all metrics."""
        self._model_metrics.clear()
        self._query_history.clear()
        self._save_metrics()
        logger.info("Metrics reset")


# ==============================================================================
# ADAPTIVE TUNER
# ==============================================================================

class AdaptiveTuner:
    """Auto-tunes parameters based on performance signals.
    
    Implements Stage 4 Section 10: Auto-tuning via reinforcement signals.
    """
    
    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        min_samples: int = 50,
    ):
        self._metrics = metrics_collector or MetricsCollector()
        self._min_samples = min_samples
        
        # Tunable parameters
        self._confidence_threshold = 0.7
        self._retry_threshold = 0.6
        self._ensemble_weights: Dict[str, float] = {}
    
    def tune(self) -> Dict[str, Any]:
        """
        Perform auto-tuning based on collected metrics.
        
        Returns:
            Dict of tuned parameters
        """
        all_metrics = self._metrics.get_all_metrics()
        
        if not all_metrics:
            logger.info("No metrics available for tuning")
            return self._get_current_params()
        
        # Calculate optimal confidence threshold
        self._tune_confidence_threshold(all_metrics)
        
        # Update ensemble weights
        self._tune_ensemble_weights(all_metrics)
        
        # Tune retry behavior
        self._tune_retry_threshold(all_metrics)
        
        params = self._get_current_params()
        logger.info("Auto-tuning complete: %s", params)
        
        return params
    
    def _tune_confidence_threshold(self, metrics: Dict[str, ModelMetrics]):
        """Tune the confidence threshold."""
        # Collect all confidence values weighted by success
        weighted_confidences = []
        
        for m in metrics.values():
            if m.total_queries >= self._min_samples:
                # Higher success rate = more influence
                weight = m.success_rate * m.total_queries
                weighted_confidences.append((m.avg_confidence, weight))
        
        if not weighted_confidences:
            return
        
        # Calculate weighted average
        total_weight = sum(w for _, w in weighted_confidences)
        if total_weight > 0:
            new_threshold = sum(c * w for c, w in weighted_confidences) / total_weight
            
            # Smooth transition
            self._confidence_threshold = (
                0.8 * self._confidence_threshold + 0.2 * new_threshold
            )
            
            # Keep in bounds
            self._confidence_threshold = max(0.5, min(0.9, self._confidence_threshold))
    
    def _tune_ensemble_weights(self, metrics: Dict[str, ModelMetrics]):
        """Tune weights for ensemble models."""
        for model_id, m in metrics.items():
            if m.total_queries < self._min_samples:
                continue
            
            # Calculate score based on success rate and approval rate
            score = 0.7 * m.success_rate + 0.3 * m.approval_rate
            
            # Convert to weight
            weight = max(0.5, min(2.0, 0.5 + score * 1.5))
            
            old_weight = self._ensemble_weights.get(model_id, 1.0)
            # Smooth transition
            self._ensemble_weights[model_id] = 0.8 * old_weight + 0.2 * weight
    
    def _tune_retry_threshold(self, metrics: Dict[str, ModelMetrics]):
        """Tune the retry threshold."""
        # Calculate retry effectiveness
        total_retries = sum(m.total_retries for m in metrics.values())
        total_queries = sum(m.total_queries for m in metrics.values())
        
        if total_queries < self._min_samples:
            return
        
        retry_rate = total_retries / total_queries
        
        # If retries are frequent but success is high, lower threshold
        avg_success = sum(m.success_rate * m.total_queries for m in metrics.values()) / total_queries
        
        if avg_success > 0.8 and retry_rate > 0.3:
            # Retries are helping, lower threshold to trigger more
            self._retry_threshold = max(0.5, self._retry_threshold - 0.02)
        elif avg_success < 0.6 and retry_rate > 0.5:
            # Retries aren't helping much, raise threshold
            self._retry_threshold = min(0.8, self._retry_threshold + 0.02)
    
    def _get_current_params(self) -> Dict[str, Any]:
        """Get current tuned parameters."""
        return {
            'confidence_threshold': self._confidence_threshold,
            'retry_threshold': self._retry_threshold,
            'ensemble_weights': self._ensemble_weights.copy(),
        }
    
    def get_confidence_threshold(self) -> float:
        """Get current confidence threshold."""
        return self._confidence_threshold
    
    def get_retry_threshold(self) -> float:
        """Get current retry threshold."""
        return self._retry_threshold
    
    def get_ensemble_weight(self, model_id: str) -> float:
        """Get weight for a specific model."""
        return self._ensemble_weights.get(model_id, 1.0)


# ==============================================================================
# INSIGHTS DASHBOARD
# ==============================================================================

@dataclass
class ModelInsight:
    """Insight about a model's performance."""
    model_id: str
    success_rate: float
    approval_rate: float
    avg_latency_ms: float
    avg_confidence: float
    total_queries: int
    weight: float
    recommendation: str


class InsightsDashboard:
    """Dashboard for viewing model insights.
    
    Implements Stage 4 Section 10: UI for model insights.
    """
    
    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        adaptive_tuner: Optional[AdaptiveTuner] = None,
    ):
        self._metrics = metrics_collector or MetricsCollector()
        self._tuner = adaptive_tuner or AdaptiveTuner(self._metrics)
    
    def get_model_insights(self) -> List[ModelInsight]:
        """Get insights for all models."""
        insights = []
        all_metrics = self._metrics.get_all_metrics()
        
        for model_id, m in all_metrics.items():
            recommendation = self._generate_recommendation(m)
            
            insight = ModelInsight(
                model_id=model_id,
                success_rate=m.success_rate,
                approval_rate=m.approval_rate,
                avg_latency_ms=m.avg_latency_ms,
                avg_confidence=m.avg_confidence,
                total_queries=m.total_queries,
                weight=self._tuner.get_ensemble_weight(model_id),
                recommendation=recommendation,
            )
            insights.append(insight)
        
        # Sort by success rate descending
        insights.sort(key=lambda i: i.success_rate, reverse=True)
        
        return insights
    
    def _generate_recommendation(self, metrics: ModelMetrics) -> str:
        """Generate a recommendation based on metrics."""
        if metrics.total_queries < 10:
            return "Needs more data for reliable assessment"
        
        if metrics.success_rate >= 0.9 and metrics.approval_rate >= 0.8:
            return "⭐ Excellent - consider increasing weight"
        elif metrics.success_rate >= 0.7:
            return "✅ Good - performing well"
        elif metrics.success_rate >= 0.5:
            return "⚠️ Moderate - may need configuration tuning"
        else:
            return "❌ Poor - consider reducing usage or investigating issues"
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        all_metrics = self._metrics.get_all_metrics()
        recent = self._metrics.get_recent_queries(100)
        
        if not all_metrics:
            return {'status': 'No data'}
        
        total_queries = sum(m.total_queries for m in all_metrics.values())
        total_success = sum(m.successful_queries for m in all_metrics.values())
        total_retries = sum(m.total_retries for m in all_metrics.values())
        
        return {
            'total_queries': total_queries,
            'overall_success_rate': total_success / total_queries if total_queries > 0 else 0,
            'total_retries': total_retries,
            'retry_rate': total_retries / total_queries if total_queries > 0 else 0,
            'active_models': len(all_metrics),
            'recent_avg_latency': (
                sum(q.latency_ms for q in recent) / len(recent) if recent else 0
            ),
            'recent_avg_confidence': (
                sum(q.confidence for q in recent) / len(recent) if recent else 0
            ),
            'tuned_confidence_threshold': self._tuner.get_confidence_threshold(),
            'tuned_retry_threshold': self._tuner.get_retry_threshold(),
        }
    
    def get_performance_history(
        self,
        model_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get performance history for visualization."""
        recent = self._metrics.get_recent_queries(limit)
        
        if model_id:
            recent = [q for q in recent if q.model_used == model_id]
        
        return [
            {
                'timestamp': q.timestamp.isoformat(),
                'model': q.model_used,
                'latency_ms': q.latency_ms,
                'confidence': q.confidence,
                'success': q.success,
                'feedback': q.user_feedback,
            }
            for q in recent
        ]
    
    def render_text_report(self) -> str:
        """Render a text-based report."""
        insights = self.get_model_insights()
        stats = self.get_summary_stats()
        
        lines = [
            "=" * 60,
            "LLMHive Model Performance Report",
            "=" * 60,
            "",
            "📊 Summary Statistics:",
            f"  Total Queries: {stats.get('total_queries', 0):,}",
            f"  Overall Success Rate: {stats.get('overall_success_rate', 0):.1%}",
            f"  Retry Rate: {stats.get('retry_rate', 0):.1%}",
            f"  Active Models: {stats.get('active_models', 0)}",
            f"  Avg Latency (recent): {stats.get('recent_avg_latency', 0):.0f}ms",
            f"  Avg Confidence (recent): {stats.get('recent_avg_confidence', 0):.2f}",
            "",
            "⚙️ Tuned Parameters:",
            f"  Confidence Threshold: {stats.get('tuned_confidence_threshold', 0.7):.2f}",
            f"  Retry Threshold: {stats.get('tuned_retry_threshold', 0.6):.2f}",
            "",
            "🤖 Model Insights:",
            "-" * 60,
        ]
        
        for insight in insights:
            lines.extend([
                f"  {insight.model_id}:",
                f"    Success Rate: {insight.success_rate:.1%}",
                f"    Approval Rate: {insight.approval_rate:.1%}",
                f"    Avg Latency: {insight.avg_latency_ms:.0f}ms",
                f"    Weight: {insight.weight:.2f}",
                f"    {insight.recommendation}",
                "",
            ])
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================

def create_metrics_collector(
    persistence_path: Optional[str] = None,
) -> MetricsCollector:
    """Create a metrics collector."""
    return MetricsCollector(persistence_path)


def create_adaptive_tuner(
    metrics_collector: Optional[MetricsCollector] = None,
) -> AdaptiveTuner:
    """Create an adaptive tuner."""
    return AdaptiveTuner(metrics_collector)


def create_insights_dashboard(
    metrics_collector: Optional[MetricsCollector] = None,
) -> InsightsDashboard:
    """Create an insights dashboard."""
    return InsightsDashboard(metrics_collector)

