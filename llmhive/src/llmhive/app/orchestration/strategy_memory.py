"""Strategy Memory Module for LLMHive Orchestration.

This module provides a high-level interface for storing, retrieving, and learning
from past orchestration strategy outcomes. It builds on top of the performance_tracker
to provide strategy-specific insights.

Key Features:
- Strategy outcome recording with full context
- Best strategy recommendations based on historical performance
- Model team success tracking
- Domain and task-type specific learning
- Time-decay for recency weighting

Usage:
    from llmhive.app.orchestration.strategy_memory import StrategyMemory, get_strategy_memory
    
    memory = get_strategy_memory()
    
    # Record an outcome
    memory.record_outcome(
        strategy="expert_panel",
        task_type="coding",
        domain="coding",
        models_used=["gpt-4o", "claude-3.5-sonnet"],
        success=True,
        quality_score=0.92,
    )
    
    # Get recommendation
    recommendation = memory.recommend_strategy(
        task_type="coding",
        domain="coding",
        complexity="complex",
    )
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..performance_tracker import (
    performance_tracker,
    StrategyOutcome,
    StrategyStats,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Strategy Definitions
# =============================================================================

class StrategyProfile:
    """Profile of an orchestration strategy with metadata."""
    
    # Strategy profiles with characteristics
    PROFILES: Dict[str, Dict[str, Any]] = {
        "single_best": {
            "description": "Route to single best model for task",
            "speed": 1.0,  # 1.0 = fastest
            "quality_potential": 0.7,  # 0-1 quality ceiling
            "cost_multiplier": 1.0,  # Base cost
            "ideal_complexity": ["simple", "medium"],
            "min_models_needed": 1,
        },
        "parallel_race": {
            "description": "Race multiple models, take fastest good answer",
            "speed": 0.9,
            "quality_potential": 0.8,
            "cost_multiplier": 2.0,
            "ideal_complexity": ["simple", "medium"],
            "min_models_needed": 2,
        },
        "best_of_n": {
            "description": "Generate N responses, judge selects best",
            "speed": 0.5,
            "quality_potential": 0.9,
            "cost_multiplier": 3.5,
            "ideal_complexity": ["medium", "complex"],
            "min_models_needed": 2,
        },
        "quality_weighted_fusion": {
            "description": "Combine responses weighted by model quality",
            "speed": 0.6,
            "quality_potential": 0.88,
            "cost_multiplier": 2.5,
            "ideal_complexity": ["medium", "complex"],
            "min_models_needed": 2,
        },
        "expert_panel": {
            "description": "Different models for different aspects, then synthesize",
            "speed": 0.4,
            "quality_potential": 0.95,
            "cost_multiplier": 4.0,
            "ideal_complexity": ["complex"],
            "min_models_needed": 3,
        },
        "challenge_and_refine": {
            "description": "Generate, challenge, improve iteratively",
            "speed": 0.3,
            "quality_potential": 0.93,
            "cost_multiplier": 3.0,
            "ideal_complexity": ["complex"],
            "min_models_needed": 2,
        },
        "dynamic": {
            "description": "Use real-time OpenRouter rankings for selection",
            "speed": 0.7,
            "quality_potential": 0.85,
            "cost_multiplier": 1.5,
            "ideal_complexity": ["simple", "medium", "complex"],
            "min_models_needed": 1,
        },
    }
    
    @classmethod
    def get_profile(cls, strategy: str) -> Dict[str, Any]:
        """Get profile for a strategy."""
        return cls.PROFILES.get(strategy, cls.PROFILES["single_best"])
    
    @classmethod
    def all_strategies(cls) -> List[str]:
        """Get all available strategy names."""
        return list(cls.PROFILES.keys())


# =============================================================================
# Model Team Tracking
# =============================================================================

@dataclass
class ModelTeamRecord:
    """Record of a model team's performance."""
    team_hash: str  # Hash of sorted model IDs
    models: List[str]
    total_runs: int = 0
    successful_runs: int = 0
    avg_quality: float = 0.0
    avg_latency_ms: float = 0.0
    
    # Strategy breakdown
    strategy_success: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # strategy -> (success, total)
    
    # Domain breakdown
    domain_success: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # domain -> (success, total)
    
    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs
    
    def best_strategy(self) -> Optional[str]:
        """Get the best performing strategy for this team."""
        best = None
        best_rate = 0.0
        
        for strategy, (success, total) in self.strategy_success.items():
            if total < 2:
                continue
            rate = success / total
            if rate > best_rate:
                best_rate = rate
                best = strategy
        
        return best


# =============================================================================
# Strategy Memory
# =============================================================================

class StrategyMemory:
    """High-level interface for strategy learning and recommendations.
    
    This class wraps the performance_tracker to provide strategy-specific
    insights and recommendations. It maintains additional state for:
    - Model team tracking
    - Time-decay weighted recommendations
    - Strategy-model compatibility
    
    Usage:
        memory = StrategyMemory()
        
        # Record an outcome
        memory.record_outcome(
            strategy="expert_panel",
            task_type="coding",
            domain="coding",
            models_used=["gpt-4o", "claude-3.5-sonnet"],
            success=True,
            quality_score=0.92,
            latency_ms=5000,
        )
        
        # Get recommendation for a new query
        rec = memory.recommend_strategy(
            task_type="coding",
            domain="coding",
            complexity="complex",
            available_models=["gpt-4o", "claude-3.5-sonnet", "gpt-4o-mini"],
        )
        print(f"Recommended: {rec['strategy']} with confidence {rec['confidence']:.0%}")
    """
    
    def __init__(self) -> None:
        """Initialize strategy memory."""
        self._tracker = performance_tracker
        self._model_teams: Dict[str, ModelTeamRecord] = {}
        self._load_model_teams()
    
    def _load_model_teams(self) -> None:
        """Load model team records from past outcomes."""
        outcomes = self._tracker.get_recent_outcomes(limit=1000)
        
        for outcome in outcomes:
            self._update_model_team(outcome)
    
    def _generate_team_hash(self, models: List[str]) -> str:
        """Generate a hash for a model team."""
        import hashlib
        sorted_models = sorted(models)
        return hashlib.md5("|".join(sorted_models).encode()).hexdigest()[:12]
    
    def _update_model_team(self, outcome: StrategyOutcome) -> None:
        """Update model team records from an outcome."""
        if not outcome.all_models_used:
            return
        
        team_hash = self._generate_team_hash(outcome.all_models_used)
        
        if team_hash not in self._model_teams:
            self._model_teams[team_hash] = ModelTeamRecord(
                team_hash=team_hash,
                models=outcome.all_models_used,
            )
        
        team = self._model_teams[team_hash]
        team.total_runs += 1
        if outcome.success:
            team.successful_runs += 1
        
        # Update rolling averages
        n = team.total_runs
        team.avg_quality = ((team.avg_quality * (n - 1)) + outcome.quality_score) / n
        team.avg_latency_ms = ((team.avg_latency_ms * (n - 1)) + outcome.latency_ms) / n
        
        # Update strategy breakdown
        strategy = outcome.strategy
        if strategy not in team.strategy_success:
            team.strategy_success[strategy] = (0, 0)
        success, total = team.strategy_success[strategy]
        team.strategy_success[strategy] = (success + (1 if outcome.success else 0), total + 1)
        
        # Update domain breakdown
        domain = outcome.domain
        if domain not in team.domain_success:
            team.domain_success[domain] = (0, 0)
        success, total = team.domain_success[domain]
        team.domain_success[domain] = (success + (1 if outcome.success else 0), total + 1)
    
    def record_outcome(
        self,
        strategy: str,
        task_type: str,
        domain: str,
        models_used: List[str],
        success: bool,
        *,
        primary_model: Optional[str] = None,
        model_roles: Optional[Dict[str, str]] = None,
        quality_score: float = 0.0,
        confidence: float = 0.0,
        latency_ms: float = 0.0,
        total_tokens: int = 0,
        query_hash: Optional[str] = None,
        query_complexity: str = "medium",
        ensemble_size: Optional[int] = None,
        refinement_iterations: int = 0,
        performance_notes: Optional[List[str]] = None,
    ) -> None:
        """Record a strategy outcome.
        
        This wraps performance_tracker.log_run with strategy-specific handling.
        
        Args:
            strategy: Strategy used
            task_type: Type of task
            domain: Domain classification
            models_used: List of models used
            success: Whether the outcome was successful
            primary_model: Primary model (defaults to first in list)
            model_roles: Mapping of model to role
            quality_score: Quality score (0-1)
            confidence: Confidence score (0-1)
            latency_ms: Latency in milliseconds
            total_tokens: Total tokens used
            query_hash: Hash of the query
            query_complexity: Query complexity
            ensemble_size: Number of models in ensemble
            refinement_iterations: Number of refinement iterations
            performance_notes: Performance notes
        """
        # Log to performance tracker
        self._tracker.log_run(
            models_used=models_used,
            success_flag=success,
            latency_ms=latency_ms,
            domain=domain,
            strategy=strategy,
            task_type=task_type,
            primary_model=primary_model or (models_used[0] if models_used else None),
            model_roles=model_roles,
            quality_score=quality_score,
            confidence=confidence,
            total_tokens=total_tokens,
            query_hash=query_hash,
            query_complexity=query_complexity,
            ensemble_size=ensemble_size or len(models_used),
            refinement_iterations=refinement_iterations,
            performance_notes=performance_notes,
        )
        
        # Also update local model team tracking
        outcome = StrategyOutcome(
            timestamp=datetime.now(timezone.utc).isoformat(),
            query_hash=query_hash or "",
            strategy=strategy,
            task_type=task_type,
            domain=domain,
            primary_model=primary_model or (models_used[0] if models_used else ""),
            secondary_models=models_used[1:] if len(models_used) > 1 else [],
            all_models_used=models_used,
            model_roles=model_roles or {},
            success=success,
            quality_score=quality_score,
            confidence=confidence,
            latency_ms=latency_ms,
            total_tokens=total_tokens,
            query_complexity=query_complexity,
            ensemble_size=ensemble_size or len(models_used),
            refinement_iterations=refinement_iterations,
            performance_notes=performance_notes or [],
        )
        self._update_model_team(outcome)
    
    def recommend_strategy(
        self,
        task_type: str,
        domain: str,
        complexity: str = "medium",
        *,
        available_models: Optional[List[str]] = None,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        max_cost_multiplier: float = 4.0,
    ) -> Dict[str, Any]:
        """Recommend a strategy based on historical performance.
        
        Uses a combination of:
        1. Historical success rates from performance_tracker
        2. Strategy profiles (speed/quality characteristics)
        3. Available models and their capabilities
        4. Time-decay weighting for recent outcomes
        
        Args:
            task_type: Type of task
            domain: Domain classification
            complexity: Query complexity ("simple", "medium", "complex")
            available_models: Available models to consider
            prefer_speed: Prefer faster strategies
            prefer_quality: Prefer higher quality strategies
            max_cost_multiplier: Maximum acceptable cost multiplier
            
        Returns:
            Dictionary with recommended strategy and metadata
        """
        # Get base recommendation from performance tracker
        base_rec = self._tracker.recommend_strategy(
            task_type=task_type,
            domain=domain,
            complexity=complexity,
            available_models=available_models,
        )
        
        # Filter by complexity and cost
        suitable_strategies: List[Tuple[str, float]] = []
        
        for strategy_name in StrategyProfile.all_strategies():
            profile = StrategyProfile.get_profile(strategy_name)
            
            # Check complexity match
            if complexity not in profile["ideal_complexity"]:
                continue
            
            # Check cost constraint
            if profile["cost_multiplier"] > max_cost_multiplier:
                continue
            
            # Check model availability
            min_models = profile["min_models_needed"]
            if available_models and len(available_models) < min_models:
                continue
            
            # Calculate score
            score = 0.5  # Base score
            
            # Add historical performance
            stats = self._tracker.get_strategy_stats(strategy_name)
            if stats and stats.total_runs >= 3:
                score += stats.success_rate * 0.3
                
                # Domain-specific boost
                if domain in stats.domain_success_rates:
                    score += stats.domain_success_rates[domain] * 0.2
            
            # Preference adjustments
            if prefer_speed:
                score += profile["speed"] * 0.2
            if prefer_quality:
                score += profile["quality_potential"] * 0.2
            
            # Complexity match bonus
            if complexity in profile["ideal_complexity"]:
                score += 0.1
            
            suitable_strategies.append((strategy_name, score))
        
        if not suitable_strategies:
            # Fall back to base recommendation
            return base_rec
        
        # Sort by score
        suitable_strategies.sort(key=lambda x: x[1], reverse=True)
        
        best = suitable_strategies[0]
        best_profile = StrategyProfile.get_profile(best[0])
        
        return {
            "strategy": best[0],
            "confidence": min(0.95, best[1]),
            "reason": f"Best for {complexity} {domain}/{task_type} tasks",
            "alternatives": [s[0] for s in suitable_strategies[1:3]],
            "profile": {
                "description": best_profile["description"],
                "speed": best_profile["speed"],
                "quality_potential": best_profile["quality_potential"],
                "cost_multiplier": best_profile["cost_multiplier"],
            },
            "historical_data": {
                "domain_best": base_rec.get("domain_best"),
                "task_type_best": base_rec.get("task_type_best"),
            },
        }
    
    def recommend_model_team(
        self,
        strategy: str,
        domain: str,
        available_models: List[str],
        team_size: int = 3,
    ) -> Dict[str, Any]:
        """Recommend a model team based on historical performance.
        
        Args:
            strategy: Strategy to use
            domain: Domain classification
            available_models: Available models to choose from
            team_size: Desired team size
            
        Returns:
            Dictionary with recommended models and metadata
        """
        # Find teams that have worked well for this strategy+domain
        best_teams: List[Tuple[List[str], float, int]] = []
        
        for team in self._model_teams.values():
            # Check if team uses available models
            if not all(m in available_models for m in team.models):
                continue
            
            # Check if team has used this strategy
            if strategy not in team.strategy_success:
                continue
            
            success, total = team.strategy_success[strategy]
            if total < 2:
                continue
            
            rate = success / total
            best_teams.append((team.models, rate, total))
        
        if not best_teams:
            # No historical data, return first N available models
            return {
                "models": available_models[:team_size],
                "confidence": 0.5,
                "reason": "No historical data, using default selection",
                "historical_teams": [],
            }
        
        # Sort by success rate * log(samples)
        best_teams.sort(key=lambda x: x[1] * math.log(x[2] + 1), reverse=True)
        
        best = best_teams[0]
        
        return {
            "models": best[0][:team_size],
            "confidence": min(0.95, best[1] * 0.9 + 0.1 * min(1.0, best[2] / 20)),
            "reason": f"Historical success rate: {best[1]:.0%} ({best[2]} samples)",
            "historical_teams": [
                {"models": t[0], "success_rate": t[1], "samples": t[2]}
                for t in best_teams[:5]
            ],
        }
    
    def get_strategy_stats(self, strategy: str) -> Optional[StrategyStats]:
        """Get statistics for a strategy."""
        return self._tracker.get_strategy_stats(strategy)
    
    def get_all_strategy_stats(self) -> Dict[str, StrategyStats]:
        """Get statistics for all strategies."""
        return self._tracker.get_all_strategy_stats()
    
    def get_model_team_stats(self, models: List[str]) -> Optional[ModelTeamRecord]:
        """Get statistics for a model team."""
        team_hash = self._generate_team_hash(models)
        return self._model_teams.get(team_hash)
    
    def get_recent_outcomes(
        self,
        limit: int = 100,
        strategy: Optional[str] = None,
        domain: Optional[str] = None,
        success_only: bool = False,
    ) -> List[StrategyOutcome]:
        """Get recent strategy outcomes."""
        return self._tracker.get_recent_outcomes(
            limit=limit,
            strategy=strategy,
            domain=domain,
            success_only=success_only,
        )


# Global singleton
_strategy_memory: Optional[StrategyMemory] = None


def get_strategy_memory() -> StrategyMemory:
    """Get the global strategy memory instance."""
    global _strategy_memory
    if _strategy_memory is None:
        _strategy_memory = StrategyMemory()
    return _strategy_memory


# =============================================================================
# Convenience Functions
# =============================================================================

def record_strategy_outcome(
    strategy: str,
    task_type: str,
    domain: str,
    models_used: List[str],
    success: bool,
    **kwargs: Any,
) -> None:
    """Convenience function to record a strategy outcome."""
    memory = get_strategy_memory()
    memory.record_outcome(
        strategy=strategy,
        task_type=task_type,
        domain=domain,
        models_used=models_used,
        success=success,
        **kwargs,
    )


def recommend_strategy(
    task_type: str,
    domain: str,
    complexity: str = "medium",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Convenience function to get a strategy recommendation."""
    memory = get_strategy_memory()
    return memory.recommend_strategy(
        task_type=task_type,
        domain=domain,
        complexity=complexity,
        **kwargs,
    )

