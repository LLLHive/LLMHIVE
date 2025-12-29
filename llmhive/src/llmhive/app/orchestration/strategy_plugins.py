"""Strategy Plugin System for LLMHive Orchestrator.

Q4 2025: Enables data-driven strategy configuration and custom strategy plugins
without modifying core orchestrator code.

Features:
- JSON/dict-based strategy definitions
- Plugin registration and discovery
- Dynamic strategy loading
- Built-in example: Majority Vote strategy

Usage:
    from llmhive.app.orchestration.strategy_plugins import (
        StrategyRegistry,
        get_strategy_registry,
        register_strategy,
        StrategyDefinition,
    )
    
    # Register a custom strategy
    register_strategy(StrategyDefinition(
        name="my_strategy",
        description="Custom ensemble strategy",
        execution_plan=[
            {"action": "parallel_query", "models": 3},
            {"action": "aggregate", "method": "vote"},
        ],
    ))
    
    # Get available strategies
    registry = get_strategy_registry()
    strategies = registry.list_strategies()
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Configuration path for custom strategies
STRATEGIES_CONFIG_PATH = Path(__file__).parent / "strategies_config.json"


# =============================================================================
# Strategy Definition Schema
# =============================================================================

class ExecutionAction(str, Enum):
    """Available actions in a strategy execution plan."""
    SINGLE_QUERY = "single_query"       # Query one model
    PARALLEL_QUERY = "parallel_query"   # Query multiple models in parallel
    SEQUENTIAL_QUERY = "sequential_query"  # Query models sequentially
    AGGREGATE = "aggregate"             # Aggregate multiple responses
    VALIDATE = "validate"               # Validate response quality
    REFINE = "refine"                   # Refine/improve a response
    LOOP = "loop"                       # Repeat steps until condition met
    BRANCH = "branch"                   # Conditional branching


class AggregationMethod(str, Enum):
    """Methods for aggregating multiple model responses."""
    VOTE = "vote"                       # Majority voting
    CONSENSUS = "consensus"             # Find consensus
    BEST_QUALITY = "best_quality"       # Select highest quality
    FIRST_SUCCESS = "first_success"     # First successful response
    WEIGHTED_FUSION = "weighted_fusion" # Weighted merge
    SYNTHESIS = "synthesis"             # LLM-based synthesis


@dataclass
class ExecutionStep:
    """A single step in strategy execution."""
    action: ExecutionAction
    params: Dict[str, Any] = field(default_factory=dict)
    on_success: Optional[str] = None  # Next step ID on success
    on_failure: Optional[str] = None  # Next step ID on failure


@dataclass
class StrategyDefinition:
    """Definition of an orchestration strategy.
    
    Strategies can be defined in code or loaded from JSON configuration.
    Each strategy specifies how to execute queries using available models.
    """
    name: str
    description: str
    execution_plan: List[Dict[str, Any]]  # List of step definitions
    
    # Strategy metadata
    ideal_complexity: List[str] = field(default_factory=lambda: ["simple", "medium"])
    ideal_task_types: List[str] = field(default_factory=list)
    min_models_needed: int = 1
    cost_multiplier: float = 1.0
    speed_rating: float = 0.5  # 0-1, higher is faster
    quality_potential: float = 0.7  # 0-1, higher is better quality
    
    # Plugin metadata
    plugin_source: str = "builtin"  # "builtin", "config", "runtime"
    created_at: Optional[str] = None
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "execution_plan": self.execution_plan,
            "ideal_complexity": self.ideal_complexity,
            "ideal_task_types": self.ideal_task_types,
            "min_models_needed": self.min_models_needed,
            "cost_multiplier": self.cost_multiplier,
            "speed_rating": self.speed_rating,
            "quality_potential": self.quality_potential,
            "plugin_source": self.plugin_source,
            "version": self.version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyDefinition":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "unknown"),
            description=data.get("description", ""),
            execution_plan=data.get("execution_plan", []),
            ideal_complexity=data.get("ideal_complexity", ["simple", "medium"]),
            ideal_task_types=data.get("ideal_task_types", []),
            min_models_needed=data.get("min_models_needed", 1),
            cost_multiplier=data.get("cost_multiplier", 1.0),
            speed_rating=data.get("speed_rating", 0.5),
            quality_potential=data.get("quality_potential", 0.7),
            plugin_source=data.get("plugin_source", "config"),
            version=data.get("version", "1.0"),
        )


# =============================================================================
# Built-in Strategy Definitions
# =============================================================================

BUILTIN_STRATEGIES: List[StrategyDefinition] = [
    # Majority Vote - New Q4 2025 strategy
    StrategyDefinition(
        name="majority_vote",
        description="Query N models and select the most common answer by voting",
        execution_plan=[
            {
                "action": "parallel_query",
                "params": {"model_count": 3, "same_prompt": True},
            },
            {
                "action": "aggregate",
                "params": {"method": "vote", "min_agreement": 2},
            },
        ],
        ideal_complexity=["simple", "medium"],
        ideal_task_types=["factual", "classification", "yes_no"],
        min_models_needed=3,
        cost_multiplier=3.0,
        speed_rating=0.7,
        quality_potential=0.85,
        plugin_source="builtin",
    ),
    
    # Cascade with Fallback
    StrategyDefinition(
        name="cascade_fallback",
        description="Try fast model first, escalate to stronger model if quality is low",
        execution_plan=[
            {
                "action": "single_query",
                "params": {"model_preference": "fast"},
            },
            {
                "action": "validate",
                "params": {"min_quality": 0.7},
            },
            {
                "action": "branch",
                "params": {
                    "condition": "validation_passed",
                    "on_true": "return",
                    "on_false": "escalate",
                },
            },
            {
                "action": "single_query",
                "params": {"model_preference": "quality"},
                "step_id": "escalate",
            },
        ],
        ideal_complexity=["simple", "medium", "complex"],
        ideal_task_types=["general"],
        min_models_needed=2,
        cost_multiplier=1.5,  # Average case
        speed_rating=0.8,
        quality_potential=0.85,
        plugin_source="builtin",
    ),
    
    # Multi-Perspective Ensemble
    StrategyDefinition(
        name="multi_perspective",
        description="Get responses from models with different perspectives, then synthesize",
        execution_plan=[
            {
                "action": "parallel_query",
                "params": {
                    "model_roles": ["analytical", "creative", "critical"],
                    "role_prompts": True,
                },
            },
            {
                "action": "aggregate",
                "params": {"method": "synthesis", "synthesis_model": "best"},
            },
        ],
        ideal_complexity=["medium", "complex"],
        ideal_task_types=["analysis", "creative", "planning"],
        min_models_needed=3,
        cost_multiplier=4.0,
        speed_rating=0.4,
        quality_potential=0.92,
        plugin_source="builtin",
    ),
]


# =============================================================================
# Strategy Registry
# =============================================================================

class StrategyRegistry:
    """Registry for orchestration strategies.
    
    Manages both built-in and custom plugin strategies.
    Supports dynamic loading from configuration files.
    """
    
    def __init__(self):
        """Initialize the registry with built-in strategies."""
        self._strategies: Dict[str, StrategyDefinition] = {}
        self._executors: Dict[str, Callable] = {}
        self._load_builtin_strategies()
        self._load_config_strategies()
    
    def _load_builtin_strategies(self):
        """Load built-in strategy definitions."""
        for strategy in BUILTIN_STRATEGIES:
            self._strategies[strategy.name] = strategy
        logger.info("Loaded %d built-in strategies", len(BUILTIN_STRATEGIES))
    
    def _load_config_strategies(self):
        """Load strategies from configuration file."""
        if not STRATEGIES_CONFIG_PATH.exists():
            return
        
        try:
            with open(STRATEGIES_CONFIG_PATH, "r") as f:
                config = json.load(f)
            
            strategies_data = config.get("strategies", [])
            for strategy_data in strategies_data:
                strategy = StrategyDefinition.from_dict(strategy_data)
                strategy.plugin_source = "config"
                self._strategies[strategy.name] = strategy
            
            logger.info("Loaded %d strategies from config", len(strategies_data))
        except Exception as e:
            logger.warning("Failed to load strategies config: %s", e)
    
    def register(
        self,
        strategy: StrategyDefinition,
        executor: Optional[Callable] = None,
    ):
        """Register a custom strategy.
        
        Args:
            strategy: Strategy definition
            executor: Optional custom executor function
        """
        strategy.plugin_source = "runtime"
        strategy.created_at = datetime.now(timezone.utc).isoformat()
        self._strategies[strategy.name] = strategy
        
        if executor:
            self._executors[strategy.name] = executor
        
        logger.info("Registered strategy: %s", strategy.name)
    
    def unregister(self, name: str) -> bool:
        """Unregister a strategy.
        
        Args:
            name: Strategy name
            
        Returns:
            True if removed, False if not found
        """
        if name in self._strategies:
            del self._strategies[name]
            self._executors.pop(name, None)
            return True
        return False
    
    def get(self, name: str) -> Optional[StrategyDefinition]:
        """Get a strategy by name."""
        return self._strategies.get(name)
    
    def list_strategies(self) -> List[StrategyDefinition]:
        """List all registered strategies."""
        return list(self._strategies.values())
    
    def list_strategy_names(self) -> List[str]:
        """List all strategy names."""
        return list(self._strategies.keys())
    
    def get_executor(self, name: str) -> Optional[Callable]:
        """Get custom executor for a strategy."""
        return self._executors.get(name)
    
    def get_strategies_for_task(
        self,
        task_type: str,
        complexity: str = "medium",
        available_models: int = 3,
    ) -> List[StrategyDefinition]:
        """Get strategies suitable for a task.
        
        Args:
            task_type: Type of task
            complexity: Query complexity
            available_models: Number of available models
            
        Returns:
            List of suitable strategies, sorted by quality potential
        """
        suitable = []
        
        for strategy in self._strategies.values():
            # Check model count
            if strategy.min_models_needed > available_models:
                continue
            
            # Check complexity match
            if complexity not in strategy.ideal_complexity:
                continue
            
            # Check task type (if specified)
            if strategy.ideal_task_types and task_type not in strategy.ideal_task_types:
                continue
            
            suitable.append(strategy)
        
        # Sort by quality potential
        suitable.sort(key=lambda s: s.quality_potential, reverse=True)
        
        return suitable
    
    def export_config(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Export all strategies to config format.
        
        Args:
            path: Optional path to save JSON file
            
        Returns:
            Configuration dictionary
        """
        config = {
            "version": "1.0",
            "strategies": [s.to_dict() for s in self._strategies.values()],
        }
        
        if path:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
        
        return config


# =============================================================================
# Global Registry
# =============================================================================

_registry: Optional[StrategyRegistry] = None


def get_strategy_registry() -> StrategyRegistry:
    """Get the global strategy registry."""
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
    return _registry


def register_strategy(
    strategy: StrategyDefinition,
    executor: Optional[Callable] = None,
):
    """Register a custom strategy globally."""
    registry = get_strategy_registry()
    registry.register(strategy, executor)


def get_strategy(name: str) -> Optional[StrategyDefinition]:
    """Get a strategy by name."""
    registry = get_strategy_registry()
    return registry.get(name)


def list_all_strategies() -> List[str]:
    """List all available strategy names."""
    registry = get_strategy_registry()
    return registry.list_strategy_names()
