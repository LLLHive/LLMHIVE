"""In-memory performance tracker used for adaptive model routing.

This implementation is intentionally lightweight and process-local. It can be
extended to persist metrics via the existing SQLAlchemy models if long-term
history is required.

Performance feedback update: Now includes persistent storage to disk (JSON)
and loading on startup to enable learning from past runs.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Dict, List, Mapping, Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ModelPerformance:
    """Aggregated performance statistics for a single model.
    
    Performance feedback update: Extended with persistent metrics for learning.
    """

    model: str
    total_tokens: int = 0
    total_cost: float = 0.0
    calls: int = 0
    avg_latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    quality_scores: List[float] = field(default_factory=list)
    # Adaptive Ensemble: Domain-specific performance tracking
    domain_performance: Dict[str, Dict[str, int]] = field(default_factory=dict)  # domain -> {success: int, failure: int}
    # Performance feedback update: Additional persistent metrics
    total_queries: int = 0  # Total queries this model was used in
    successful_queries: int = 0  # Queries where model's answer passed verification
    latency_history: List[float] = field(default_factory=list)  # History of latencies for moving average

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total

    @property
    def avg_quality(self) -> float:
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)
    
    # Performance feedback update: Query-level accuracy
    @property
    def query_accuracy(self) -> float:
        """Performance feedback update: Accuracy based on successful queries."""
        if self.total_queries == 0:
            return 0.0
        return self.successful_queries / self.total_queries
    
    def get_domain_success_rate(self, domain: str) -> float:
        """Adaptive Ensemble: Get success rate for a specific domain."""
        domain_perf = self.domain_performance.get(domain, {})
        success = domain_perf.get("success", 0)
        failure = domain_perf.get("failure", 0)
        total = success + failure
        if total == 0:
            return 0.5  # Default to 0.5 if no domain data
        return success / total
    
    def update_latency(self, latency_ms: float) -> None:
        """Performance feedback update: Update latency with moving average."""
        self.latency_history.append(latency_ms)
        # Keep only last 100 latencies for moving average
        if len(self.latency_history) > 100:
            self.latency_history = self.latency_history[-100:]
        # Calculate moving average
        self.avg_latency_ms = sum(self.latency_history) / len(self.latency_history)


class PerformanceTracker:
    """Tracks per-model performance statistics for routing heuristics.
    
    Performance feedback update: Now includes persistent storage to disk (JSON)
    and automatic loading on startup to enable learning from past runs.
    """

    def __init__(self, metrics_file: Optional[str] = None) -> None:
        self._lock = RLock()
        self._models: Dict[str, ModelPerformance] = {}
        # Performance feedback update: Persistent storage path
        self.metrics_file = metrics_file or os.getenv(
            "PERFORMANCE_METRICS_FILE",
            str(Path.home() / ".llmhive" / "performance_metrics.json")
        )
        # Performance feedback update: Load existing metrics on startup
        self._load_metrics()

    def record_usage(
        self,
        usage: "UsageSummaryLike",
        *,
        quality_by_model: Mapping[str, float] | None = None,
    ) -> None:
        """
        Update metrics based on a UsageSummary-like object and optional quality scores.

        We intentionally depend only on the *shape* of the orchestration usage
        object (via the UsageSummaryLike protocol below) to avoid a hard
        import-time dependency on the orchestrator module and its dataclasses.
        This keeps the tracker usable in isolation and prevents circular imports.
        """

        quality_by_model = quality_by_model or {}
        with self._lock:
            for model, metrics in usage.per_model.items():
                perf = self._models.get(model)
                if perf is None:
                    perf = ModelPerformance(model=model)
                    self._models[model] = perf
                perf.total_tokens += metrics.tokens
                perf.total_cost += metrics.cost
                perf.calls += max(metrics.responses, 1)
                score = quality_by_model.get(model)
                if score is not None:
                    perf.quality_scores.append(score)

    def mark_outcome(self, model: str, *, success: bool, domain: str | None = None) -> None:
        """Record success/failure for a particular model call.
        
        Adaptive Ensemble: Also tracks domain-specific outcomes for adaptive routing.
        """

        with self._lock:
            perf = self._models.get(model)
            if perf is None:
                perf = ModelPerformance(model=model)
                self._models[model] = perf
            if success:
                perf.success_count += 1
            else:
                perf.failure_count += 1
            
            # Adaptive Ensemble: Track domain-specific performance
            if domain:
                if domain not in perf.domain_performance:
                    perf.domain_performance[domain] = {"success": 0, "failure": 0}
                if success:
                    perf.domain_performance[domain]["success"] += 1
                else:
                    perf.domain_performance[domain]["failure"] += 1

    def snapshot(self) -> Mapping[str, ModelPerformance]:
        """Return a shallow copy of the current metrics."""

        with self._lock:
            return dict(self._models)
    
    # Performance feedback update: Persistent storage methods
    def _load_metrics(self) -> None:
        """Performance feedback update: Load metrics from disk on startup."""
        if not os.path.exists(self.metrics_file):
            logger.debug("Performance feedback: No existing metrics file found at %s", self.metrics_file)
            return
        
        try:
            with open(self.metrics_file, "r") as f:
                data = json.load(f)
            
            with self._lock:
                for model_name, metrics_data in data.items():
                    perf = ModelPerformance(
                        model=model_name,
                        total_tokens=metrics_data.get("total_tokens", 0),
                        total_cost=metrics_data.get("total_cost", 0.0),
                        calls=metrics_data.get("calls", 0),
                        avg_latency_ms=metrics_data.get("avg_latency_ms", 0.0),
                        success_count=metrics_data.get("success_count", 0),
                        failure_count=metrics_data.get("failure_count", 0),
                        quality_scores=metrics_data.get("quality_scores", []),
                        domain_performance=metrics_data.get("domain_performance", {}),
                        total_queries=metrics_data.get("total_queries", 0),
                        successful_queries=metrics_data.get("successful_queries", 0),
                        latency_history=metrics_data.get("latency_history", []),
                    )
                    self._models[model_name] = perf
            
            logger.info(
                "Performance feedback: Loaded metrics for %d models from %s",
                len(self._models),
                self.metrics_file
            )
        except Exception as exc:
            logger.warning(
                "Performance feedback: Failed to load metrics from %s: %s",
                self.metrics_file,
                exc
            )
    
    def save_metrics(self) -> None:
        """Performance feedback update: Save metrics to disk.
        
        This should be called after each query session to persist learning.
        Thread-safe.
        """
        try:
            # Create directory if it doesn't exist
            metrics_path = Path(self.metrics_file)
            metrics_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                data = {}
                for model_name, perf in self._models.items():
                    data[model_name] = {
                        "total_tokens": perf.total_tokens,
                        "total_cost": perf.total_cost,
                        "calls": perf.calls,
                        "avg_latency_ms": perf.avg_latency_ms,
                        "success_count": perf.success_count,
                        "failure_count": perf.failure_count,
                        "quality_scores": perf.quality_scores[-100:],  # Keep last 100 scores
                        "domain_performance": perf.domain_performance,
                        "total_queries": perf.total_queries,
                        "successful_queries": perf.successful_queries,
                        "latency_history": perf.latency_history[-100:],  # Keep last 100 latencies
                    }
            
            with open(self.metrics_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(
                "Performance feedback: Saved metrics for %d models to %s",
                len(self._models),
                self.metrics_file
            )
        except Exception as exc:
            logger.warning(
                "Performance feedback: Failed to save metrics to %s: %s",
                self.metrics_file,
                exc
            )
    
    # Performance feedback update: Log run outcome
    def log_run(
        self,
        models_used: List[str],
        success_flag: bool,
        latency_ms: Optional[float] = None,
        domain: Optional[str] = None,
    ) -> None:
        """Performance feedback update: Log outcome of a query run.
        
        This updates model profiles with query-level metrics and triggers
        profile updates for adaptive usage.
        
        Args:
            models_used: List of model names used in this query
            success_flag: Whether the query passed verification (True) or failed (False)
            latency_ms: Optional latency in milliseconds
            domain: Optional domain classification
        """
        with self._lock:
            for model_name in models_used:
                perf = self._models.get(model_name)
                if perf is None:
                    perf = ModelPerformance(model=model_name)
                    self._models[model_name] = perf
                
                # Performance feedback update: Update query-level metrics
                perf.total_queries += 1
                if success_flag:
                    perf.successful_queries += 1
                
                # Performance feedback update: Update latency if provided
                if latency_ms is not None:
                    perf.update_latency(latency_ms)
                
                # Performance feedback update: Update domain-specific metrics
                if domain:
                    if domain not in perf.domain_performance:
                        perf.domain_performance[domain] = {"success": 0, "failure": 0}
                    if success_flag:
                        perf.domain_performance[domain]["success"] += 1
                    else:
                        perf.domain_performance[domain]["failure"] += 1
            
            # Performance feedback update: Auto-save after each run
            # (In production, might want to batch saves)
            self.save_metrics()


# Shared singleton used across the application.
performance_tracker = PerformanceTracker()


class ModelUsageLike(Protocol):
    tokens: int
    cost: float
    responses: int


class UsageSummaryLike(Protocol):
    per_model: Mapping[str, ModelUsageLike]


