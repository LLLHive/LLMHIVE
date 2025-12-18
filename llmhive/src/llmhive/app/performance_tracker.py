"""In-memory performance tracker used for adaptive model routing.

This implementation is intentionally lightweight and process-local. It can be
extended to persist metrics via the existing SQLAlchemy models if long-term
history is required.

Performance feedback update: Now includes persistent storage to disk (JSON)
and loading on startup to enable learning from past runs.

Strategy Memory update (PR2): Extended with:
- Strategy outcome tracking
- Model team composition tracking
- Query-strategy-outcome associations
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Mapping, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ModelUsage:
    """Usage statistics for a single model."""
    tokens: int = 0
    cost: float = 0.0
    responses: int = 0


@dataclass
class UsageSummary:
    """Summary of usage across all models in a request."""
    total_tokens: int = 0
    total_cost: float = 0.0
    response_count: int = 0
    per_model: Dict[str, ModelUsage] = field(default_factory=dict)


# =============================================================================
# Strategy Memory: Track strategy outcomes for learning
# =============================================================================

@dataclass
class StrategyOutcome:
    """Record of a strategy execution outcome.
    
    Captures what strategy was used, which models participated,
    and whether it succeeded for future learning.
    """
    # Identification
    timestamp: str  # ISO format
    query_hash: str  # Hash of the query for deduplication
    
    # Strategy details
    strategy: str  # e.g., "single_best", "expert_panel", "challenge_and_refine"
    task_type: str  # e.g., "coding", "research", "general"
    domain: str  # e.g., "coding", "medical", "legal"
    
    # Model team composition
    primary_model: str
    secondary_models: List[str] = field(default_factory=list)
    all_models_used: List[str] = field(default_factory=list)
    model_roles: Dict[str, str] = field(default_factory=dict)  # model -> role
    
    # Outcome metrics
    success: bool = False
    quality_score: float = 0.0
    confidence: float = 0.0
    latency_ms: float = 0.0
    total_tokens: int = 0
    
    # Context
    query_complexity: str = "medium"  # "simple", "medium", "complex"
    ensemble_size: int = 1
    refinement_iterations: int = 0
    
    # Notes
    performance_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "query_hash": self.query_hash,
            "strategy": self.strategy,
            "task_type": self.task_type,
            "domain": self.domain,
            "primary_model": self.primary_model,
            "secondary_models": self.secondary_models,
            "all_models_used": self.all_models_used,
            "model_roles": self.model_roles,
            "success": self.success,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "total_tokens": self.total_tokens,
            "query_complexity": self.query_complexity,
            "ensemble_size": self.ensemble_size,
            "refinement_iterations": self.refinement_iterations,
            "performance_notes": self.performance_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyOutcome":
        """Create from dictionary."""
        return cls(
            timestamp=data.get("timestamp", ""),
            query_hash=data.get("query_hash", ""),
            strategy=data.get("strategy", "unknown"),
            task_type=data.get("task_type", "general"),
            domain=data.get("domain", "general"),
            primary_model=data.get("primary_model", ""),
            secondary_models=data.get("secondary_models", []),
            all_models_used=data.get("all_models_used", []),
            model_roles=data.get("model_roles", {}),
            success=data.get("success", False),
            quality_score=data.get("quality_score", 0.0),
            confidence=data.get("confidence", 0.0),
            latency_ms=data.get("latency_ms", 0.0),
            total_tokens=data.get("total_tokens", 0),
            query_complexity=data.get("query_complexity", "medium"),
            ensemble_size=data.get("ensemble_size", 1),
            refinement_iterations=data.get("refinement_iterations", 0),
            performance_notes=data.get("performance_notes", []),
        )


@dataclass
class StrategyStats:
    """Aggregated statistics for a strategy.
    
    Used for quick lookups without scanning all outcomes.
    """
    strategy: str
    total_runs: int = 0
    successful_runs: int = 0
    avg_quality: float = 0.0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    
    # Domain breakdown
    domain_success_rates: Dict[str, float] = field(default_factory=dict)
    
    # Task type breakdown
    task_type_success_rates: Dict[str, float] = field(default_factory=dict)
    
    # Best model teams (by success rate)
    top_model_teams: List[Tuple[List[str], float]] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "success_rate": self.success_rate,
            "avg_quality": self.avg_quality,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_confidence": self.avg_confidence,
            "domain_success_rates": self.domain_success_rates,
            "task_type_success_rates": self.task_type_success_rates,
            "top_model_teams": self.top_model_teams,
        }


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
    
    Strategy Memory (PR2): Extended with strategy outcome tracking for learning
    which strategies work best for different query types and domains.
    """

    def __init__(self, metrics_file: Optional[str] = None) -> None:
        self._lock = RLock()
        self._models: Dict[str, ModelPerformance] = {}
        
        # Strategy Memory (PR2): Strategy outcome tracking
        self._strategy_outcomes: List[StrategyOutcome] = []
        self._strategy_stats: Dict[str, StrategyStats] = {}
        self._domain_strategy_counts: Dict[str, Dict[str, Dict[str, int]]] = {}
        self._task_strategy_counts: Dict[str, Dict[str, Dict[str, int]]] = {}
        
        # Performance feedback update: Persistent storage path
        self.metrics_file = metrics_file or os.getenv(
            "PERFORMANCE_METRICS_FILE",
            str(Path.home() / ".llmhive" / "performance_metrics.json")
        )
        # Strategy Memory (PR2): Separate file for strategy outcomes
        self.strategy_file = metrics_file.replace(".json", "_strategies.json") if metrics_file else os.getenv(
            "STRATEGY_METRICS_FILE",
            str(Path.home() / ".llmhive" / "strategy_metrics.json")
        )
        
        # Performance feedback update: Load existing metrics on startup
        self._load_metrics()
        self._load_strategy_metrics()

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
    
    # Performance feedback update: Log run outcome
    def log_run(
        self,
        models_used: List[str],
        success_flag: bool,
        latency_ms: Optional[float] = None,
        domain: Optional[str] = None,
        *,
        # Strategy Memory (PR2): Extended parameters
        strategy: Optional[str] = None,
        task_type: Optional[str] = None,
        primary_model: Optional[str] = None,
        model_roles: Optional[Dict[str, str]] = None,
        quality_score: Optional[float] = None,
        confidence: Optional[float] = None,
        total_tokens: Optional[int] = None,
        query_hash: Optional[str] = None,
        query_complexity: Optional[str] = None,
        ensemble_size: Optional[int] = None,
        refinement_iterations: Optional[int] = None,
        performance_notes: Optional[List[str]] = None,
    ) -> None:
        """Performance feedback update: Log outcome of a query run.
        
        This updates model profiles with query-level metrics and triggers
        profile updates for adaptive usage.
        
        Strategy Memory (PR2): Now also logs strategy outcomes for learning
        which strategies work best for different query types.
        
        Args:
            models_used: List of model names used in this query
            success_flag: Whether the query passed verification (True) or failed (False)
            latency_ms: Optional latency in milliseconds
            domain: Optional domain classification
            
            # Strategy Memory (PR2) parameters:
            strategy: Strategy used (e.g., "single_best", "expert_panel")
            task_type: Task type (e.g., "coding", "research")
            primary_model: Primary model in the team
            model_roles: Mapping of model to role (e.g., {"gpt-4o": "primary"})
            quality_score: Quality score of the response (0.0-1.0)
            confidence: Confidence score (0.0-1.0)
            total_tokens: Total tokens used
            query_hash: Hash of the query for deduplication
            query_complexity: Query complexity ("simple", "medium", "complex")
            ensemble_size: Number of models in the ensemble
            refinement_iterations: Number of refinement iterations
            performance_notes: List of performance notes
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
            
            # Strategy Memory (PR2): Log strategy outcome if strategy provided
            if strategy:
                outcome = StrategyOutcome(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    query_hash=query_hash or self._generate_query_hash(str(models_used)),
                    strategy=strategy,
                    task_type=task_type or "general",
                    domain=domain or "general",
                    primary_model=primary_model or (models_used[0] if models_used else ""),
                    secondary_models=models_used[1:] if len(models_used) > 1 else [],
                    all_models_used=models_used,
                    model_roles=model_roles or {},
                    success=success_flag,
                    quality_score=quality_score or (0.8 if success_flag else 0.4),
                    confidence=confidence or 0.0,
                    latency_ms=latency_ms or 0.0,
                    total_tokens=total_tokens or 0,
                    query_complexity=query_complexity or "medium",
                    ensemble_size=ensemble_size or len(models_used),
                    refinement_iterations=refinement_iterations or 0,
                    performance_notes=performance_notes or [],
                )
                self._strategy_outcomes.append(outcome)
                self._update_strategy_stats(outcome)
            
            # Performance feedback update: Auto-save after each run
            # (In production, might want to batch saves)
            self.save_metrics()
    
    def _generate_query_hash(self, content: str) -> str:
        """Generate a simple hash for query deduplication."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _update_strategy_stats(self, outcome: StrategyOutcome) -> None:
        """Update aggregated strategy statistics."""
        strategy = outcome.strategy
        
        if strategy not in self._strategy_stats:
            self._strategy_stats[strategy] = StrategyStats(strategy=strategy)
        
        stats = self._strategy_stats[strategy]
        stats.total_runs += 1
        if outcome.success:
            stats.successful_runs += 1
        
        # Update rolling averages
        n = stats.total_runs
        stats.avg_quality = ((stats.avg_quality * (n - 1)) + outcome.quality_score) / n
        stats.avg_latency_ms = ((stats.avg_latency_ms * (n - 1)) + outcome.latency_ms) / n
        stats.avg_confidence = ((stats.avg_confidence * (n - 1)) + outcome.confidence) / n
        
        # Update domain success rates
        domain = outcome.domain
        if domain not in self._domain_strategy_counts:
            self._domain_strategy_counts[domain] = {}
        if strategy not in self._domain_strategy_counts[domain]:
            self._domain_strategy_counts[domain][strategy] = {"success": 0, "total": 0}
        
        self._domain_strategy_counts[domain][strategy]["total"] += 1
        if outcome.success:
            self._domain_strategy_counts[domain][strategy]["success"] += 1
        
        # Calculate domain success rate
        counts = self._domain_strategy_counts[domain][strategy]
        stats.domain_success_rates[domain] = counts["success"] / counts["total"]
        
        # Update task type success rates similarly
        task_type = outcome.task_type
        if task_type not in self._task_strategy_counts:
            self._task_strategy_counts[task_type] = {}
        if strategy not in self._task_strategy_counts[task_type]:
            self._task_strategy_counts[task_type][strategy] = {"success": 0, "total": 0}
        
        self._task_strategy_counts[task_type][strategy]["total"] += 1
        if outcome.success:
            self._task_strategy_counts[task_type][strategy]["success"] += 1
        
        counts = self._task_strategy_counts[task_type][strategy]
        stats.task_type_success_rates[task_type] = counts["success"] / counts["total"]


    # ==========================================================================
    # Strategy Memory (PR2): Load/Save strategy metrics
    # ==========================================================================
    
    def _load_strategy_metrics(self) -> None:
        """Strategy Memory (PR2): Load strategy metrics from disk."""
        if not os.path.exists(self.strategy_file):
            logger.debug("Strategy Memory: No existing strategy file found at %s", self.strategy_file)
            return
        
        try:
            with open(self.strategy_file, "r") as f:
                data = json.load(f)
            
            with self._lock:
                # Load strategy outcomes (keep last 1000)
                outcomes_data = data.get("outcomes", [])
                for outcome_data in outcomes_data[-1000:]:
                    self._strategy_outcomes.append(StrategyOutcome.from_dict(outcome_data))
                
                # Load strategy stats
                stats_data = data.get("stats", {})
                for strategy_name, stats_dict in stats_data.items():
                    stats = StrategyStats(
                        strategy=strategy_name,
                        total_runs=stats_dict.get("total_runs", 0),
                        successful_runs=stats_dict.get("successful_runs", 0),
                        avg_quality=stats_dict.get("avg_quality", 0.0),
                        avg_latency_ms=stats_dict.get("avg_latency_ms", 0.0),
                        avg_confidence=stats_dict.get("avg_confidence", 0.0),
                        domain_success_rates=stats_dict.get("domain_success_rates", {}),
                        task_type_success_rates=stats_dict.get("task_type_success_rates", {}),
                        top_model_teams=stats_dict.get("top_model_teams", []),
                    )
                    self._strategy_stats[strategy_name] = stats
                
                # Load counts
                self._domain_strategy_counts = data.get("domain_counts", {})
                self._task_strategy_counts = data.get("task_counts", {})
            
            logger.info(
                "Strategy Memory: Loaded %d outcomes and %d strategy stats from %s",
                len(self._strategy_outcomes),
                len(self._strategy_stats),
                self.strategy_file,
            )
        except Exception as exc:
            logger.warning(
                "Strategy Memory: Failed to load strategy metrics from %s: %s",
                self.strategy_file,
                exc,
            )
    
    def save_strategy_metrics(self) -> None:
        """Strategy Memory (PR2): Save strategy metrics to disk."""
        try:
            # Create directory if it doesn't exist
            strategy_path = Path(self.strategy_file)
            strategy_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                data = {
                    "outcomes": [o.to_dict() for o in self._strategy_outcomes[-1000:]],
                    "stats": {name: stats.to_dict() for name, stats in self._strategy_stats.items()},
                    "domain_counts": self._domain_strategy_counts,
                    "task_counts": self._task_strategy_counts,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }
            
            with open(self.strategy_file, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(
                "Strategy Memory: Saved %d outcomes and %d strategy stats to %s",
                len(self._strategy_outcomes),
                len(self._strategy_stats),
                self.strategy_file,
            )
        except Exception as exc:
            logger.warning(
                "Strategy Memory: Failed to save strategy metrics to %s: %s",
                self.strategy_file,
                exc,
            )
    
    def save_metrics(self) -> None:
        """Performance feedback update: Save metrics to disk.
        
        This should be called after each query session to persist learning.
        Thread-safe.
        
        Strategy Memory (PR2): Also saves strategy metrics.
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
            
            # Strategy Memory (PR2): Also save strategy metrics
            self.save_strategy_metrics()
            
        except Exception as exc:
            logger.warning(
                "Performance feedback: Failed to save metrics to %s: %s",
                self.metrics_file,
                exc
            )
    
    # ==========================================================================
    # Strategy Memory (PR2): Query methods for strategy recommendations
    # ==========================================================================
    
    def get_best_strategy_for_domain(self, domain: str) -> Optional[str]:
        """Strategy Memory (PR2): Get the best performing strategy for a domain.
        
        Args:
            domain: Domain classification (e.g., "coding", "research")
            
        Returns:
            Strategy name with highest success rate for this domain, or None
        """
        with self._lock:
            if domain not in self._domain_strategy_counts:
                return None
            
            best_strategy = None
            best_rate = 0.0
            
            for strategy, counts in self._domain_strategy_counts[domain].items():
                total = counts.get("total", 0)
                if total < 3:  # Require minimum samples
                    continue
                
                rate = counts.get("success", 0) / total
                if rate > best_rate:
                    best_rate = rate
                    best_strategy = strategy
            
            return best_strategy
    
    def get_best_strategy_for_task_type(self, task_type: str) -> Optional[str]:
        """Strategy Memory (PR2): Get the best performing strategy for a task type.
        
        Args:
            task_type: Task type (e.g., "coding", "research_analysis")
            
        Returns:
            Strategy name with highest success rate for this task type, or None
        """
        with self._lock:
            if task_type not in self._task_strategy_counts:
                return None
            
            best_strategy = None
            best_rate = 0.0
            
            for strategy, counts in self._task_strategy_counts[task_type].items():
                total = counts.get("total", 0)
                if total < 3:  # Require minimum samples
                    continue
                
                rate = counts.get("success", 0) / total
                if rate > best_rate:
                    best_rate = rate
                    best_strategy = strategy
            
            return best_strategy
    
    def get_strategy_stats(self, strategy: str) -> Optional[StrategyStats]:
        """Strategy Memory (PR2): Get statistics for a specific strategy.
        
        Args:
            strategy: Strategy name
            
        Returns:
            StrategyStats or None if no data
        """
        with self._lock:
            return self._strategy_stats.get(strategy)
    
    def get_all_strategy_stats(self) -> Dict[str, StrategyStats]:
        """Strategy Memory (PR2): Get statistics for all strategies.
        
        Returns:
            Dictionary of strategy name to StrategyStats
        """
        with self._lock:
            return dict(self._strategy_stats)
    
    def get_recent_outcomes(
        self,
        limit: int = 100,
        strategy: Optional[str] = None,
        domain: Optional[str] = None,
        success_only: bool = False,
    ) -> List[StrategyOutcome]:
        """Strategy Memory (PR2): Get recent strategy outcomes with optional filtering.
        
        Args:
            limit: Maximum number of outcomes to return
            strategy: Filter by strategy name
            domain: Filter by domain
            success_only: Only return successful outcomes
            
        Returns:
            List of StrategyOutcome objects
        """
        with self._lock:
            outcomes = self._strategy_outcomes[-limit * 10:]  # Get more for filtering
            
            if strategy:
                outcomes = [o for o in outcomes if o.strategy == strategy]
            if domain:
                outcomes = [o for o in outcomes if o.domain == domain]
            if success_only:
                outcomes = [o for o in outcomes if o.success]
            
            return outcomes[-limit:]
    
    def recommend_strategy(
        self,
        task_type: str,
        domain: str,
        complexity: str = "medium",
        available_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Strategy Memory (PR2): Recommend a strategy based on historical performance.
        
        Args:
            task_type: Type of task
            domain: Domain classification
            complexity: Query complexity ("simple", "medium", "complex")
            available_models: Available models to consider
            
        Returns:
            Dictionary with recommended strategy and confidence
        """
        with self._lock:
            # Get strategy candidates
            domain_best = self.get_best_strategy_for_domain(domain)
            task_best = self.get_best_strategy_for_task_type(task_type)
            
            # Get stats for candidates
            candidates: List[Tuple[str, float, int]] = []  # (strategy, success_rate, samples)
            
            for strategy in set(filter(None, [domain_best, task_best])):
                stats = self._strategy_stats.get(strategy)
                if stats and stats.total_runs >= 3:
                    candidates.append((strategy, stats.success_rate, stats.total_runs))
            
            # Add fallback strategies based on complexity
            complexity_defaults = {
                "simple": "single_best",
                "medium": "quality_weighted_fusion",
                "complex": "expert_panel",
            }
            default = complexity_defaults.get(complexity, "single_best")
            
            if not candidates:
                return {
                    "strategy": default,
                    "confidence": 0.5,
                    "reason": f"No historical data, using default for {complexity} complexity",
                    "alternatives": [],
                }
            
            # Sort by success rate * log(samples) to balance exploration/exploitation
            import math
            candidates.sort(key=lambda x: x[1] * math.log(x[2] + 1), reverse=True)
            
            best = candidates[0]
            
            return {
                "strategy": best[0],
                "confidence": min(0.95, best[1] * 0.9 + 0.1 * min(1.0, best[2] / 50)),
                "reason": f"Best for {domain}/{task_type}: {best[1]:.0%} success rate ({best[2]} samples)",
                "alternatives": [c[0] for c in candidates[1:3]],
                "domain_best": domain_best,
                "task_type_best": task_best,
            }


# Shared singleton used across the application.
performance_tracker = PerformanceTracker()


class ModelUsageLike(Protocol):
    tokens: int
    cost: float
    responses: int


class UsageSummaryLike(Protocol):
    per_model: Mapping[str, ModelUsageLike]


