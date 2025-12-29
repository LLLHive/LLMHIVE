"""Meta-Learning Strategy Optimizer for LLMHive Orchestration.

This module implements an adaptive strategy selection system that learns from
past orchestration outcomes to recommend the optimal strategy for new queries.

Key Features:
- Uses telemetry and strategy_memory to learn patterns
- Lightweight ML model (gradient-boosted decision rules) for predictions
- Continuous learning: updates with each outcome
- Fallback to rule-based selection when data is sparse
- Integration with QueryAnalyzer and EliteOrchestrator

References:
- Patent vision: Multi-expert synergy with adaptive strategy
- PR2: Extended Strategy Memory
- PR8: Testing & Telemetry

Usage:
    from llmhive.app.orchestration.strategy_optimizer import (
        StrategyOptimizer,
        get_strategy_optimizer,
    )
    
    optimizer = get_strategy_optimizer()
    
    # Get recommendation
    result = optimizer.recommend_strategy(
        query_analysis={
            "task_type": "coding",
            "domain": "coding",
            "complexity": "complex",
            "tokens_estimate": 500,
        }
    )
    print(f"Recommended: {result.strategy} (confidence: {result.confidence:.0%})")
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .strategy_memory import (
    StrategyMemory,
    StrategyProfile,
    get_strategy_memory,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# Path for persisting learned weights
OPTIMIZER_WEIGHTS_PATH = Path(os.path.expanduser("~/.llmhive/strategy_optimizer_weights.json"))

# Minimum samples needed before ML predictions are trusted
MIN_SAMPLES_FOR_ML = 20

# Learning rate for weight updates
LEARNING_RATE = 0.1

# Decay factor for older outcomes (per day)
TIME_DECAY_FACTOR = 0.95

# Feature names for the model
FEATURE_NAMES = [
    "complexity_simple",
    "complexity_medium", 
    "complexity_complex",
    "task_type_coding",
    "task_type_reasoning",
    "task_type_factual",
    "task_type_creative",
    "task_type_analysis",
    "task_type_math",
    "domain_coding",
    "domain_technical",
    "domain_general",
    "domain_creative",
    "domain_business",
    "tokens_low",
    "tokens_medium",
    "tokens_high",
    "prefer_speed",
    "prefer_quality",
    "budget_constrained",
]

# Strategy names (must match StrategyProfile.PROFILES)
STRATEGY_NAMES = [
    "single_best",
    "parallel_race",
    "best_of_n",
    "quality_weighted_fusion",
    "expert_panel",
    "challenge_and_refine",
    "dynamic",
]


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class QueryFeatures:
    """Extracted features from a query analysis."""
    complexity: str = "medium"
    task_type: str = "general"
    domain: str = "general"
    tokens_estimate: int = 100
    prefer_speed: bool = False
    prefer_quality: bool = False
    budget_constrained: bool = False
    available_models: List[str] = field(default_factory=list)
    
    def to_vector(self) -> List[float]:
        """Convert features to a numeric vector for ML model."""
        vec = []
        
        # Complexity one-hot
        vec.append(1.0 if self.complexity == "simple" else 0.0)
        vec.append(1.0 if self.complexity == "medium" else 0.0)
        vec.append(1.0 if self.complexity == "complex" else 0.0)
        
        # Task type one-hot
        vec.append(1.0 if self.task_type == "coding" else 0.0)
        vec.append(1.0 if self.task_type in ("reasoning", "procedural") else 0.0)
        vec.append(1.0 if self.task_type == "factual" else 0.0)
        vec.append(1.0 if self.task_type == "creative" else 0.0)
        vec.append(1.0 if self.task_type == "analysis" else 0.0)
        vec.append(1.0 if self.task_type == "math" else 0.0)
        
        # Domain one-hot
        vec.append(1.0 if self.domain == "coding" else 0.0)
        vec.append(1.0 if self.domain == "technical" else 0.0)
        vec.append(1.0 if self.domain == "general" else 0.0)
        vec.append(1.0 if self.domain == "creative" else 0.0)
        vec.append(1.0 if self.domain == "business" else 0.0)
        
        # Token buckets
        vec.append(1.0 if self.tokens_estimate < 100 else 0.0)
        vec.append(1.0 if 100 <= self.tokens_estimate < 500 else 0.0)
        vec.append(1.0 if self.tokens_estimate >= 500 else 0.0)
        
        # Preferences
        vec.append(1.0 if self.prefer_speed else 0.0)
        vec.append(1.0 if self.prefer_quality else 0.0)
        vec.append(1.0 if self.budget_constrained else 0.0)
        
        return vec


@dataclass
class StrategyRecommendation:
    """Result of strategy optimization."""
    strategy: str
    confidence: float
    reason: str
    alternatives: List[str]
    method: str  # "ml", "rule_based", "fallback"
    scores: Dict[str, float]  # Score for each strategy
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Lightweight ML Model
# =============================================================================

class LinearStrategyModel:
    """Simple linear model for strategy prediction.
    
    Uses a weight matrix (features x strategies) to predict the best strategy.
    Trained online with simple gradient updates.
    """
    
    def __init__(self):
        """Initialize with default weights."""
        self.weights: Dict[str, List[float]] = {}
        self.biases: Dict[str, float] = {}
        self.total_samples = 0
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize weights with domain knowledge priors."""
        num_features = len(FEATURE_NAMES)
        
        for strategy in STRATEGY_NAMES:
            # Initialize with small random-like values based on strategy profile
            profile = StrategyProfile.get_profile(strategy)
            base_weight = profile.get("quality_potential", 0.5)
            
            self.weights[strategy] = [0.0] * num_features
            self.biases[strategy] = base_weight
            
            # Set some initial domain knowledge weights
            self._apply_prior_knowledge(strategy, profile)
    
    def _apply_prior_knowledge(self, strategy: str, profile: Dict[str, Any]):
        """Apply domain knowledge as initial weight biases."""
        ideal_complexity = profile.get("ideal_complexity", [])
        
        # Complexity weights
        if "simple" in ideal_complexity:
            self.weights[strategy][0] = 0.2  # complexity_simple
        if "medium" in ideal_complexity:
            self.weights[strategy][1] = 0.2  # complexity_medium
        if "complex" in ideal_complexity:
            self.weights[strategy][2] = 0.2  # complexity_complex
        
        # Strategy-specific priors
        if strategy == "expert_panel":
            # Expert panel is best for complex, multi-domain
            self.weights[strategy][2] = 0.4  # complexity_complex
            self.weights[strategy][4] = 0.2  # reasoning
            self.weights[strategy][8] = 0.2  # analysis
        elif strategy == "challenge_and_refine":
            # Challenge & refine for quality-focused complex tasks
            self.weights[strategy][2] = 0.3  # complexity_complex
            self.weights[strategy][19] = 0.3  # prefer_quality
        elif strategy == "parallel_race":
            # Parallel race for speed
            self.weights[strategy][18] = 0.4  # prefer_speed
        elif strategy == "single_best":
            # Single best for simple tasks
            self.weights[strategy][0] = 0.4  # complexity_simple
            self.weights[strategy][18] = 0.3  # prefer_speed
    
    def predict(self, features: List[float]) -> Dict[str, float]:
        """Predict scores for each strategy.
        
        Args:
            features: Feature vector from QueryFeatures.to_vector()
            
        Returns:
            Dictionary mapping strategy name to predicted score
        """
        scores = {}
        
        for strategy in STRATEGY_NAMES:
            # Linear combination of weights and features
            weights = self.weights.get(strategy, [0.0] * len(features))
            bias = self.biases.get(strategy, 0.5)
            
            score = bias
            for i, (w, f) in enumerate(zip(weights, features)):
                score += w * f
            
            # Apply sigmoid to bound score between 0 and 1
            scores[strategy] = 1 / (1 + math.exp(-score))
        
        return scores
    
    def update(
        self,
        features: List[float],
        strategy: str,
        reward: float,
        learning_rate: float = LEARNING_RATE,
    ):
        """Update weights based on outcome.
        
        Args:
            features: Feature vector used for this prediction
            strategy: Strategy that was used
            reward: Outcome reward (0-1, based on quality_score * success)
            learning_rate: Learning rate for update
        """
        if strategy not in self.weights:
            return
        
        # Get current prediction
        predicted = self.predict(features)
        current_score = predicted.get(strategy, 0.5)
        
        # Calculate error
        error = reward - current_score
        
        # Update weights for this strategy
        for i, f in enumerate(features):
            self.weights[strategy][i] += learning_rate * error * f
        
        # Update bias
        self.biases[strategy] += learning_rate * error * 0.1
        
        self.total_samples += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary."""
        return {
            "weights": self.weights,
            "biases": self.biases,
            "total_samples": self.total_samples,
            "version": "1.0",
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinearStrategyModel":
        """Deserialize model from dictionary."""
        model = cls()
        model.weights = data.get("weights", model.weights)
        model.biases = data.get("biases", model.biases)
        model.total_samples = data.get("total_samples", 0)
        return model


# =============================================================================
# Strategy Optimizer
# =============================================================================

class StrategyOptimizer:
    """Meta-learning optimizer for orchestration strategy selection.
    
    This class combines:
    1. Rule-based recommendations from StrategyMemory
    2. ML predictions from LinearStrategyModel
    3. Continuous learning from outcomes
    
    The optimizer automatically falls back to rule-based selection when
    there isn't enough data for reliable ML predictions.
    """
    
    def __init__(self, memory: Optional[StrategyMemory] = None):
        """Initialize the optimizer.
        
        Args:
            memory: StrategyMemory instance (uses global singleton if not provided)
        """
        self.memory = memory or get_strategy_memory()
        self.model = LinearStrategyModel()
        self._load_model()
    
    def _load_model(self):
        """Load persisted model weights if available."""
        try:
            if OPTIMIZER_WEIGHTS_PATH.exists():
                with open(OPTIMIZER_WEIGHTS_PATH, "r") as f:
                    data = json.load(f)
                self.model = LinearStrategyModel.from_dict(data)
                logger.info(
                    "Loaded strategy optimizer model with %d samples",
                    self.model.total_samples
                )
        except Exception as e:
            logger.warning("Failed to load optimizer weights: %s", e)
    
    def _save_model(self):
        """Persist model weights."""
        try:
            OPTIMIZER_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OPTIMIZER_WEIGHTS_PATH, "w") as f:
                json.dump(self.model.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning("Failed to save optimizer weights: %s", e)
    
    def _extract_features(self, query_analysis: Dict[str, Any]) -> QueryFeatures:
        """Extract features from query analysis."""
        return QueryFeatures(
            complexity=query_analysis.get("complexity", "medium"),
            task_type=query_analysis.get("task_type", "general"),
            domain=query_analysis.get("domain", "general"),
            tokens_estimate=query_analysis.get("tokens_estimate", 100),
            prefer_speed=query_analysis.get("prefer_speed", False),
            prefer_quality=query_analysis.get("prefer_quality", False),
            budget_constrained=query_analysis.get("budget_constrained", False),
            available_models=query_analysis.get("available_models", []),
        )
    
    def recommend_strategy(
        self,
        query_analysis: Dict[str, Any],
        override_method: Optional[str] = None,
    ) -> StrategyRecommendation:
        """Recommend the best strategy for a query.
        
        This method combines ML predictions with rule-based fallbacks:
        1. If enough data exists (>MIN_SAMPLES_FOR_ML), use ML predictions
        2. Otherwise, use rule-based recommendations from StrategyMemory
        3. Apply any constraints (budget, available models, etc.)
        
        Args:
            query_analysis: Dictionary with query analysis results
            override_method: Force a specific method ("ml", "rule_based")
            
        Returns:
            StrategyRecommendation with the optimal strategy
        """
        features = self._extract_features(query_analysis)
        feature_vector = features.to_vector()
        
        # Determine which method to use
        use_ml = (
            override_method == "ml" or
            (override_method is None and self.model.total_samples >= MIN_SAMPLES_FOR_ML)
        )
        
        if use_ml:
            return self._recommend_with_ml(features, feature_vector, query_analysis)
        else:
            return self._recommend_with_rules(features, query_analysis)
    
    def _recommend_with_ml(
        self,
        features: QueryFeatures,
        feature_vector: List[float],
        query_analysis: Dict[str, Any],
    ) -> StrategyRecommendation:
        """Use ML model for recommendation."""
        # Get ML predictions
        scores = self.model.predict(feature_vector)
        
        # Apply constraints
        available_models = features.available_models
        filtered_scores = {}
        
        for strategy, score in scores.items():
            profile = StrategyProfile.get_profile(strategy)
            min_models = profile.get("min_models_needed", 1)
            
            # Check if we have enough models
            if available_models and len(available_models) < min_models:
                filtered_scores[strategy] = score * 0.1  # Heavily penalize
            else:
                filtered_scores[strategy] = score
        
        # Sort by score
        sorted_strategies = sorted(
            filtered_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        best = sorted_strategies[0]
        alternatives = [s[0] for s in sorted_strategies[1:4]]
        
        return StrategyRecommendation(
            strategy=best[0],
            confidence=min(0.95, best[1]),
            reason=f"ML model prediction (trained on {self.model.total_samples} samples)",
            alternatives=alternatives,
            method="ml",
            scores=filtered_scores,
            metadata={
                "features": {
                    "complexity": features.complexity,
                    "task_type": features.task_type,
                    "domain": features.domain,
                },
            },
        )
    
    def _recommend_with_rules(
        self,
        features: QueryFeatures,
        query_analysis: Dict[str, Any],
    ) -> StrategyRecommendation:
        """Use rule-based recommendation from StrategyMemory."""
        rec = self.memory.recommend_strategy(
            task_type=features.task_type,
            domain=features.domain,
            complexity=features.complexity,
            available_models=features.available_models if features.available_models else None,
            prefer_speed=features.prefer_speed,
            prefer_quality=features.prefer_quality,
        )
        
        # Get scores based on profile characteristics
        scores = {}
        for strategy in STRATEGY_NAMES:
            profile = StrategyProfile.get_profile(strategy)
            score = 0.5
            
            if features.complexity in profile.get("ideal_complexity", []):
                score += 0.2
            if features.prefer_speed:
                score += profile.get("speed", 0.5) * 0.2
            if features.prefer_quality:
                score += profile.get("quality_potential", 0.5) * 0.2
                
            scores[strategy] = score
        
        return StrategyRecommendation(
            strategy=rec.get("strategy", "single_best"),
            confidence=rec.get("confidence", 0.5),
            reason=rec.get("reason", "Rule-based selection (insufficient ML data)"),
            alternatives=rec.get("alternatives", []),
            method="rule_based",
            scores=scores,
            metadata={
                "historical_data": rec.get("historical_data", {}),
                "samples_needed": MIN_SAMPLES_FOR_ML - self.model.total_samples,
            },
        )
    
    def record_outcome(
        self,
        query_analysis: Dict[str, Any],
        strategy: str,
        success: bool,
        quality_score: float = 0.0,
        latency_ms: float = 0.0,
    ):
        """Record an outcome to learn from.
        
        This method:
        1. Updates the ML model weights
        2. Records to StrategyMemory for persistence
        3. Saves the model periodically
        
        Args:
            query_analysis: Query analysis used for the recommendation
            strategy: Strategy that was used
            success: Whether the outcome was successful
            quality_score: Quality score (0-1)
            latency_ms: Latency in milliseconds
        """
        features = self._extract_features(query_analysis)
        feature_vector = features.to_vector()
        
        # Calculate reward (combination of success and quality)
        reward = 0.0
        if success:
            reward = 0.5 + (quality_score * 0.5)
        else:
            reward = quality_score * 0.3
        
        # Update ML model
        self.model.update(
            features=feature_vector,
            strategy=strategy,
            reward=reward,
        )
        
        # Also record to StrategyMemory for persistence
        self.memory.record_outcome(
            strategy=strategy,
            task_type=features.task_type,
            domain=features.domain,
            models_used=features.available_models or ["unknown"],
            success=success,
            quality_score=quality_score,
            latency_ms=latency_ms,
            query_complexity=features.complexity,
        )
        
        # Save model periodically (every 10 updates)
        if self.model.total_samples % 10 == 0:
            self._save_model()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "ml_samples": self.model.total_samples,
            "ml_ready": self.model.total_samples >= MIN_SAMPLES_FOR_ML,
            "samples_needed": max(0, MIN_SAMPLES_FOR_ML - self.model.total_samples),
            "strategy_profiles": {
                s: StrategyProfile.get_profile(s)
                for s in STRATEGY_NAMES
            },
            "current_weights": self.model.weights,
        }


# =============================================================================
# Global Singleton
# =============================================================================

_optimizer: Optional[StrategyOptimizer] = None


def get_strategy_optimizer() -> StrategyOptimizer:
    """Get the global strategy optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = StrategyOptimizer()
    return _optimizer


# =============================================================================
# Integration Functions
# =============================================================================

def optimize_strategy_selection(
    query_analysis: Dict[str, Any],
    current_strategy: str = "automatic",
) -> Tuple[str, Dict[str, Any]]:
    """Optimize strategy selection for the orchestrator.
    
    This function is designed to be called by EliteOrchestrator when
    eliteStrategy == "automatic" to get the optimal strategy.
    
    Args:
        query_analysis: Dictionary with query analysis results
        current_strategy: Current strategy setting ("automatic" triggers optimization)
        
    Returns:
        Tuple of (selected_strategy, metadata)
    """
    if current_strategy != "automatic":
        return current_strategy, {"reason": "User override", "method": "manual"}
    
    optimizer = get_strategy_optimizer()
    rec = optimizer.recommend_strategy(query_analysis)
    
    return rec.strategy, {
        "reason": rec.reason,
        "method": rec.method,
        "confidence": rec.confidence,
        "alternatives": rec.alternatives,
        "scores": rec.scores,
    }


def record_orchestration_outcome(
    query_analysis: Dict[str, Any],
    strategy: str,
    success: bool,
    quality_score: float = 0.0,
    latency_ms: float = 0.0,
):
    """Record an orchestration outcome for learning.
    
    This function should be called after each orchestration completes
    to enable continuous learning.
    
    Args:
        query_analysis: Query analysis used
        strategy: Strategy that was executed
        success: Whether it was successful
        quality_score: Quality score (0-1)
        latency_ms: Latency in milliseconds
    """
    optimizer = get_strategy_optimizer()
    optimizer.record_outcome(
        query_analysis=query_analysis,
        strategy=strategy,
        success=success,
        quality_score=quality_score,
        latency_ms=latency_ms,
    )
