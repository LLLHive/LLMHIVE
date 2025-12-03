"""Model Configuration Module for LLMHive Orchestrator.

This module handles loading and managing model capabilities from configuration,
enabling data-driven model selection and easy updates without code changes.

Features:
- Load capabilities from JSON config file
- Dynamic capability updates based on performance tracking
- Cost-aware model selection
- Strategy threshold configuration
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ModelCapability(str, Enum):
    """Model capabilities for specialized routing."""
    CODING = "coding"
    REASONING = "reasoning"
    MATH = "math"
    CREATIVE = "creative"
    FACTUAL = "factual"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    INSTRUCTION_FOLLOWING = "instruction_following"
    SPEED = "speed"
    QUALITY = "quality"


@dataclass
class ModelProfile:
    """Complete profile for a model."""
    model_id: str
    capabilities: Dict[ModelCapability, float]
    cost_per_1k_tokens: float = 0.001
    success_rate: float = 1.0  # Updated from performance tracking
    avg_latency_ms: float = 1000.0
    total_calls: int = 0


@dataclass
class StrategyConfig:
    """Configuration for an orchestration strategy."""
    min_models: int = 1
    max_models: int = 5
    accuracy_level_min: int = 1
    accuracy_level_max: int = 5
    task_types: List[str] = field(default_factory=list)
    complexity: List[str] = field(default_factory=list)
    speed_priority: bool = False
    n: int = 3  # For best_of_n
    samples: int = 5  # For self_consistency


class ModelConfigManager:
    """Manages model configurations with dynamic updates.
    
    Loads from JSON config file and can be updated based on
    performance tracking data for data-driven optimization.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with optional config file path."""
        self._config_path = config_path or self._default_config_path()
        self._models: Dict[str, ModelProfile] = {}
        self._task_capabilities: Dict[str, List[ModelCapability]] = {}
        self._strategy_configs: Dict[str, StrategyConfig] = {}
        self._loaded = False
        
        self._load_config()
    
    def _default_config_path(self) -> str:
        """Get default config file path."""
        return str(Path(__file__).parent / "model_capabilities.json")
    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r') as f:
                    config = json.load(f)
                
                # Load models
                for model_id, caps in config.get("models", {}).items():
                    capabilities = {}
                    for cap_name, score in caps.items():
                        if cap_name == "cost_per_1k_tokens":
                            continue
                        try:
                            cap = ModelCapability(cap_name)
                            capabilities[cap] = score
                        except ValueError:
                            pass
                    
                    self._models[model_id] = ModelProfile(
                        model_id=model_id,
                        capabilities=capabilities,
                        cost_per_1k_tokens=caps.get("cost_per_1k_tokens", 0.001),
                    )
                
                # Load task capabilities
                for task, caps in config.get("task_capabilities", {}).items():
                    self._task_capabilities[task] = [
                        ModelCapability(c) for c in caps
                        if c in [e.value for e in ModelCapability]
                    ]
                
                # Load strategy configs
                for strategy, cfg in config.get("strategy_thresholds", {}).items():
                    self._strategy_configs[strategy] = StrategyConfig(
                        min_models=cfg.get("min_models", 1),
                        max_models=cfg.get("max_models", 5),
                        accuracy_level_min=cfg.get("accuracy_level_min", 1),
                        accuracy_level_max=cfg.get("accuracy_level_max", 5),
                        task_types=cfg.get("task_types", []),
                        complexity=cfg.get("complexity", []),
                        speed_priority=cfg.get("speed_priority", False),
                        n=cfg.get("n", 3),
                        samples=cfg.get("samples", 5),
                    )
                
                self._loaded = True
                logger.info("Loaded model config with %d models", len(self._models))
            else:
                logger.warning("Config file not found: %s", self._config_path)
                self._load_defaults()
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            self._load_defaults()
    
    def _load_defaults(self) -> None:
        """Load default configurations."""
        # Default model capabilities
        default_models = {
            "gpt-4o": {
                ModelCapability.CODING: 0.95,
                ModelCapability.REASONING: 0.95,
                ModelCapability.MATH: 0.90,
                ModelCapability.QUALITY: 0.95,
            },
            "claude-sonnet-4": {
                ModelCapability.CODING: 0.96,
                ModelCapability.REASONING: 0.94,
                ModelCapability.QUALITY: 0.94,
            },
            "deepseek-chat": {
                ModelCapability.CODING: 0.94,
                ModelCapability.MATH: 0.93,
                ModelCapability.SPEED: 0.80,
            },
        }
        
        for model_id, caps in default_models.items():
            self._models[model_id] = ModelProfile(
                model_id=model_id,
                capabilities=caps,
            )
        
        self._loaded = True
    
    def get_model_profile(self, model_id: str) -> Optional[ModelProfile]:
        """Get profile for a model."""
        # Handle model name variations
        if model_id in self._models:
            return self._models[model_id]
        
        # Try to find by prefix
        for stored_id, profile in self._models.items():
            if model_id.startswith(stored_id.split('-')[0]):
                return profile
        
        return None
    
    def get_capabilities(self, model_id: str) -> Dict[ModelCapability, float]:
        """Get capabilities for a model."""
        profile = self.get_model_profile(model_id)
        if profile:
            return profile.capabilities
        return {}
    
    def get_task_requirements(self, task_type: str) -> List[ModelCapability]:
        """Get required capabilities for a task type."""
        return self._task_capabilities.get(task_type, [ModelCapability.QUALITY])
    
    def get_strategy_config(self, strategy: str) -> StrategyConfig:
        """Get configuration for a strategy."""
        return self._strategy_configs.get(strategy, StrategyConfig())
    
    def get_best_models_for_task(
        self,
        task_type: str,
        available_models: List[str],
        n: int = 3,
        prefer_speed: bool = False,
        prefer_cheap: bool = False,
    ) -> List[str]:
        """Get best models for a task type.
        
        Args:
            task_type: Type of task
            available_models: List of available model IDs
            n: Number of models to return
            prefer_speed: Prioritize faster models
            prefer_cheap: Prioritize cheaper models
            
        Returns:
            List of model IDs ranked by suitability
        """
        required_caps = self.get_task_requirements(task_type)
        
        scored_models = []
        for model_id in available_models:
            profile = self.get_model_profile(model_id)
            if not profile:
                continue
            
            # Calculate base score from required capabilities
            cap_scores = [
                profile.capabilities.get(cap, 0.5)
                for cap in required_caps
            ]
            base_score = sum(cap_scores) / len(cap_scores) if cap_scores else 0.5
            
            # Adjust for preferences
            if prefer_speed:
                speed_bonus = profile.capabilities.get(ModelCapability.SPEED, 0.5) * 0.2
                base_score += speed_bonus
            
            if prefer_cheap:
                # Normalize cost (lower is better)
                cost_factor = 1.0 - min(profile.cost_per_1k_tokens * 10, 1.0)
                base_score += cost_factor * 0.1
            
            # Adjust for historical success rate
            if profile.total_calls > 10:
                base_score = base_score * 0.7 + profile.success_rate * 0.3
            
            scored_models.append((model_id, base_score))
        
        # Sort by score descending
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        return [m[0] for m in scored_models[:n]]
    
    def update_model_performance(
        self,
        model_id: str,
        success: bool,
        latency_ms: float,
        task_type: Optional[str] = None,
    ) -> None:
        """Update model performance metrics.
        
        This enables data-driven capability adjustments over time.
        """
        profile = self.get_model_profile(model_id)
        if not profile:
            return
        
        # Update call count
        profile.total_calls += 1
        
        # Update success rate (exponential moving average)
        alpha = 0.1
        new_success = 1.0 if success else 0.0
        profile.success_rate = (1 - alpha) * profile.success_rate + alpha * new_success
        
        # Update latency
        profile.avg_latency_ms = (1 - alpha) * profile.avg_latency_ms + alpha * latency_ms
        
        # Optionally adjust capability scores based on task-specific performance
        if task_type and task_type in self._task_capabilities:
            required_caps = self._task_capabilities[task_type]
            adjustment = 0.01 if success else -0.01
            
            for cap in required_caps:
                if cap in profile.capabilities:
                    current = profile.capabilities[cap]
                    profile.capabilities[cap] = max(0.1, min(1.0, current + adjustment))
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        config = {
            "version": "1.0.0",
            "models": {},
            "task_capabilities": {},
            "strategy_thresholds": {},
        }
        
        for model_id, profile in self._models.items():
            config["models"][model_id] = {
                cap.value: score
                for cap, score in profile.capabilities.items()
            }
            config["models"][model_id]["cost_per_1k_tokens"] = profile.cost_per_1k_tokens
        
        for task, caps in self._task_capabilities.items():
            config["task_capabilities"][task] = [cap.value for cap in caps]
        
        for strategy, cfg in self._strategy_configs.items():
            config["strategy_thresholds"][strategy] = {
                "min_models": cfg.min_models,
                "max_models": cfg.max_models,
                "accuracy_level_min": cfg.accuracy_level_min,
                "accuracy_level_max": cfg.accuracy_level_max,
                "task_types": cfg.task_types,
                "complexity": cfg.complexity,
                "speed_priority": cfg.speed_priority,
                "n": cfg.n,
                "samples": cfg.samples,
            }
        
        try:
            with open(self._config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Saved model config to %s", self._config_path)
        except Exception as e:
            logger.error("Failed to save config: %s", e)


# Global instance
_config_manager: Optional[ModelConfigManager] = None


def get_config_manager() -> ModelConfigManager:
    """Get or create the global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ModelConfigManager()
    return _config_manager


def get_model_capabilities(model_id: str) -> Dict[ModelCapability, float]:
    """Convenience function to get model capabilities."""
    return get_config_manager().get_capabilities(model_id)


def get_best_models_for_task(
    task_type: str,
    available_models: List[str],
    n: int = 3,
    criteria: Optional[Dict[str, int]] = None,
) -> List[str]:
    """Convenience function for task-based model selection."""
    prefer_speed = False
    prefer_cheap = False
    
    if criteria:
        # Speed > accuracy means prefer fast models
        if criteria.get("speed", 50) > criteria.get("accuracy", 50):
            prefer_speed = True
        # If speed is very high (>80), also prefer cheap models
        if criteria.get("speed", 50) > 80:
            prefer_cheap = True
    
    return get_config_manager().get_best_models_for_task(
        task_type,
        available_models,
        n=n,
        prefer_speed=prefer_speed,
        prefer_cheap=prefer_cheap,
    )

