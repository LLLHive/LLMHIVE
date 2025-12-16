"""Model Registry for LLMHive.

This module provides centralized model management:
- Register and track available models
- Model metadata and capabilities
- Domain-to-model mapping
- Performance-based selection
- Fine-tuned model integration

Usage:
    registry = get_model_registry()
    
    # Register a fine-tuned model
    registry.register(
        model_id="medical-llm-v1",
        model_path="./models/medical_v1",
        domains=["medical", "healthcare"],
    )
    
    # Get best model for a domain
    model = registry.get_model_for_domain("medical")
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class ModelType(str, Enum):
    """Types of models."""
    API = "api"  # External API (OpenAI, Anthropic, etc.)
    LOCAL = "local"  # Local HuggingFace model
    FINE_TUNED = "fine_tuned"  # Fine-tuned local model
    CUSTOM = "custom"  # Custom model


class ModelCapability(str, Enum):
    """Model capabilities."""
    CHAT = "chat"
    COMPLETION = "completion"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    EMBEDDING = "embedding"
    FUNCTION_CALLING = "function_calling"


@dataclass(slots=True)
class ModelInfo:
    """Information about a registered model."""
    model_id: str
    model_name: str  # HuggingFace ID or API model name
    model_type: ModelType
    provider: str  # "local", "openai", "anthropic", etc.
    model_path: Optional[str] = None  # Local path if applicable
    domains: List[str] = field(default_factory=list)
    capabilities: List[ModelCapability] = field(default_factory=list)
    context_length: int = 4096
    description: Optional[str] = None
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Performance metrics
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    avg_quality: float = 0.0
    # Configuration
    default_temperature: float = 0.7
    default_max_tokens: int = 512
    use_4bit: bool = False
    use_8bit: bool = False
    # Status
    is_available: bool = True
    is_default: bool = False
    priority: int = 0  # Higher = preferred
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DomainMapping:
    """Mapping of domains to preferred models."""
    domain: str
    models: List[str]  # Model IDs in order of preference
    description: Optional[str] = None


# Default API models
DEFAULT_API_MODELS = {
    "gpt-4o": ModelInfo(
        model_id="gpt-4o",
        model_name="gpt-4o",
        model_type=ModelType.API,
        provider="openai",
        domains=["general", "coding", "reasoning"],
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.CODE,
            ModelCapability.REASONING,
            ModelCapability.FUNCTION_CALLING,
        ],
        context_length=128000,
        description="OpenAI GPT-4o (Omni)",
        priority=100,
    ),
    "gpt-4o-mini": ModelInfo(
        model_id="gpt-4o-mini",
        model_name="gpt-4o-mini",
        model_type=ModelType.API,
        provider="openai",
        domains=["general", "coding"],
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
        ],
        context_length=128000,
        description="OpenAI GPT-4o Mini",
        priority=80,
    ),
    "claude-3-5-sonnet": ModelInfo(
        model_id="claude-3-5-sonnet",
        model_name="claude-3-5-sonnet-20241022",
        model_type=ModelType.API,
        provider="anthropic",
        domains=["general", "reasoning", "coding"],
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.CODE,
        ],
        context_length=200000,
        description="Anthropic Claude 3.5 Sonnet",
        priority=95,
    ),
    "claude-3-haiku": ModelInfo(
        model_id="claude-3-haiku",
        model_name="claude-3-haiku-20240307",
        model_type=ModelType.API,
        provider="anthropic",
        domains=["general"],
        capabilities=[ModelCapability.CHAT],
        context_length=200000,
        description="Anthropic Claude 3 Haiku (fast)",
        priority=70,
    ),
    "grok-2": ModelInfo(
        model_id="grok-2",
        model_name="grok-2-latest",
        model_type=ModelType.API,
        provider="grok",
        domains=["general", "reasoning"],
        capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
        context_length=131072,
        description="xAI Grok-2",
        priority=85,
    ),
    "gemini-1.5-pro": ModelInfo(
        model_id="gemini-1.5-pro",
        model_name="gemini-1.5-pro",
        model_type=ModelType.API,
        provider="gemini",
        domains=["general", "reasoning"],
        capabilities=[
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.VISION,
        ],
        context_length=2097152,
        description="Google Gemini 1.5 Pro",
        priority=90,
    ),
}

# Default local models
DEFAULT_LOCAL_MODELS = {
    "mistral-7b-instruct": ModelInfo(
        model_id="mistral-7b-instruct",
        model_name="mistralai/Mistral-7B-Instruct-v0.2",
        model_type=ModelType.LOCAL,
        provider="local",
        domains=["general", "coding"],
        capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
        context_length=32768,
        description="Mistral 7B Instruct v0.2",
        use_4bit=True,
        priority=60,
    ),
    "llama-3-8b-instruct": ModelInfo(
        model_id="llama-3-8b-instruct",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        model_type=ModelType.LOCAL,
        provider="local",
        domains=["general", "reasoning"],
        capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
        context_length=8192,
        description="Meta Llama 3 8B Instruct",
        use_4bit=True,
        priority=65,
    ),
    "phi-3-mini": ModelInfo(
        model_id="phi-3-mini",
        model_name="microsoft/Phi-3-mini-4k-instruct",
        model_type=ModelType.LOCAL,
        provider="local",
        domains=["general", "reasoning"],
        capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
        context_length=4096,
        description="Microsoft Phi-3 Mini 4K",
        use_4bit=True,
        priority=55,
    ),
    "codellama-7b": ModelInfo(
        model_id="codellama-7b",
        model_name="codellama/CodeLlama-7b-Instruct-hf",
        model_type=ModelType.LOCAL,
        provider="local",
        domains=["coding"],
        capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
        context_length=16384,
        description="Meta CodeLlama 7B",
        use_4bit=True,
        priority=60,
    ),
    "tinyllama-1b": ModelInfo(
        model_id="tinyllama-1b",
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_type=ModelType.LOCAL,
        provider="local",
        domains=["general"],
        capabilities=[ModelCapability.CHAT],
        context_length=2048,
        description="TinyLlama 1.1B (fast, lightweight)",
        use_4bit=False,  # Small enough without quantization
        priority=40,
    ),
}


# ==============================================================================
# Model Registry
# ==============================================================================

class ModelRegistry:
    """Central registry for managing LLM models.
    
    Features:
    - Register API and local models
    - Track fine-tuned models
    - Domain-based model selection
    - Performance tracking
    - Priority-based routing
    
    Usage:
        registry = ModelRegistry()
        
        # Get all available models
        models = registry.list_models()
        
        # Get models for a domain
        coding_models = registry.get_models_for_domain("coding")
        
        # Register a fine-tuned model
        registry.register(
            model_id="my-medical-model",
            model_name="./models/medical_v1",
            model_type=ModelType.FINE_TUNED,
            domains=["medical"],
        )
    """
    
    def __init__(
        self,
        *,
        include_defaults: bool = True,
        registry_path: Optional[str] = None,
    ):
        """
        Initialize the registry.
        
        Args:
            include_defaults: Include default API and local models
            registry_path: Path to persist registry
        """
        self._models: Dict[str, ModelInfo] = {}
        self._domain_mappings: Dict[str, DomainMapping] = {}
        self._registry_path = registry_path
        self._loaded_providers: Dict[str, Any] = {}
        
        if include_defaults:
            self._load_defaults()
        
        if registry_path and os.path.exists(registry_path):
            self._load_from_file(registry_path)
    
    def _load_defaults(self) -> None:
        """Load default models."""
        # Add API models
        for model_id, info in DEFAULT_API_MODELS.items():
            self._models[model_id] = info
        
        # Add local models
        for model_id, info in DEFAULT_LOCAL_MODELS.items():
            self._models[model_id] = info
        
        logger.info(
            "Loaded %d default models (%d API, %d local)",
            len(self._models),
            len(DEFAULT_API_MODELS),
            len(DEFAULT_LOCAL_MODELS),
        )
    
    def register(
        self,
        model_id: str,
        model_name: str,
        model_type: ModelType = ModelType.LOCAL,
        provider: str = "local",
        model_path: Optional[str] = None,
        domains: Optional[List[str]] = None,
        capabilities: Optional[List[ModelCapability]] = None,
        context_length: int = 4096,
        description: Optional[str] = None,
        use_4bit: bool = False,
        priority: int = 50,
        **kwargs,
    ) -> ModelInfo:
        """
        Register a new model.
        
        Args:
            model_id: Unique identifier
            model_name: HuggingFace model ID or path
            model_type: Type of model
            provider: Provider name
            model_path: Local path (for fine-tuned models)
            domains: List of domains
            capabilities: List of capabilities
            context_length: Context window size
            description: Model description
            use_4bit: Use 4-bit quantization
            priority: Selection priority
            **kwargs: Additional metadata
            
        Returns:
            ModelInfo for the registered model
        """
        info = ModelInfo(
            model_id=model_id,
            model_name=model_name,
            model_type=model_type,
            provider=provider,
            model_path=model_path or model_name,
            domains=domains or ["general"],
            capabilities=capabilities or [ModelCapability.CHAT],
            context_length=context_length,
            description=description,
            use_4bit=use_4bit,
            priority=priority,
            metadata=kwargs,
        )
        
        self._models[model_id] = info
        
        # Update domain mappings
        for domain in info.domains:
            if domain not in self._domain_mappings:
                self._domain_mappings[domain] = DomainMapping(domain=domain, models=[])
            
            if model_id not in self._domain_mappings[domain].models:
                self._domain_mappings[domain].models.append(model_id)
        
        logger.info("Registered model: %s (%s)", model_id, model_type.value)
        
        if self._registry_path:
            self._save_to_file(self._registry_path)
        
        return info
    
    def unregister(self, model_id: str) -> bool:
        """Remove a model from the registry."""
        if model_id in self._models:
            info = self._models.pop(model_id)
            
            # Update domain mappings
            for domain in info.domains:
                if domain in self._domain_mappings:
                    if model_id in self._domain_mappings[domain].models:
                        self._domain_mappings[domain].models.remove(model_id)
            
            logger.info("Unregistered model: %s", model_id)
            return True
        
        return False
    
    def get(self, model_id: str) -> Optional[ModelInfo]:
        """Get a model by ID."""
        return self._models.get(model_id)
    
    def list_models(
        self,
        model_type: Optional[ModelType] = None,
        provider: Optional[str] = None,
        domain: Optional[str] = None,
        available_only: bool = True,
    ) -> List[ModelInfo]:
        """
        List registered models with optional filters.
        
        Args:
            model_type: Filter by type
            provider: Filter by provider
            domain: Filter by domain
            available_only: Only return available models
            
        Returns:
            List of matching ModelInfo
        """
        models = list(self._models.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if domain:
            models = [m for m in models if domain in m.domains]
        
        if available_only:
            models = [m for m in models if m.is_available]
        
        # Sort by priority (descending)
        models.sort(key=lambda m: m.priority, reverse=True)
        
        return models
    
    def get_models_for_domain(
        self,
        domain: str,
        limit: int = 3,
        include_local: bool = True,
    ) -> List[ModelInfo]:
        """
        Get best models for a domain.
        
        Args:
            domain: Domain name
            limit: Maximum models to return
            include_local: Include local models
            
        Returns:
            List of ModelInfo sorted by priority
        """
        models = self.list_models(domain=domain, available_only=True)
        
        if not include_local:
            models = [m for m in models if m.model_type == ModelType.API]
        
        return models[:limit]
    
    def get_best_model(
        self,
        domain: Optional[str] = None,
        capability: Optional[ModelCapability] = None,
        prefer_local: bool = False,
    ) -> Optional[ModelInfo]:
        """
        Get the single best model for criteria.
        
        Args:
            domain: Preferred domain
            capability: Required capability
            prefer_local: Prefer local models
            
        Returns:
            Best matching ModelInfo or None
        """
        models = self.list_models(domain=domain, available_only=True)
        
        if capability:
            models = [m for m in models if capability in m.capabilities]
        
        if not models:
            return None
        
        if prefer_local:
            local_models = [m for m in models if m.model_type in (ModelType.LOCAL, ModelType.FINE_TUNED)]
            if local_models:
                return local_models[0]
        
        return models[0]
    
    def update_performance(
        self,
        model_id: str,
        latency_ms: float,
        success: bool,
        quality: Optional[float] = None,
    ) -> None:
        """Update model performance metrics."""
        if model_id not in self._models:
            return
        
        info = self._models[model_id]
        
        # Update rolling average
        total = info.total_requests
        info.avg_latency_ms = (info.avg_latency_ms * total + latency_ms) / (total + 1)
        info.success_rate = (info.success_rate * total + (1 if success else 0)) / (total + 1)
        info.total_requests = total + 1
        if quality is not None:
            prev_q = getattr(info, "avg_quality", 0.0)
            info.avg_quality = (prev_q * total + quality) / (total + 1)  # type: ignore
    
    def get_provider(self, model_id: str) -> Any:
        """
        Get or create a provider for a model.
        
        Args:
            model_id: Model ID
            
        Returns:
            Provider instance
        """
        info = self._models.get(model_id)
        if not info:
            raise ValueError(f"Model not found: {model_id}")
        
        # Check cache
        if model_id in self._loaded_providers:
            return self._loaded_providers[model_id]
        
        # Create provider
        if info.model_type in (ModelType.LOCAL, ModelType.FINE_TUNED):
            from .local_model import ChatLocalModelProvider
            
            provider = ChatLocalModelProvider(
                info.model_path or info.model_name,
                use_4bit=info.use_4bit,
                use_8bit=info.use_8bit,
            )
            
            self._loaded_providers[model_id] = provider
            return provider
        
        # For API models, return None (use orchestrator's providers)
        return None
    
    def _save_to_file(self, path: str) -> None:
        """Persist registry to file."""
        data = {
            model_id: {
                "model_name": info.model_name,
                "model_type": info.model_type.value,
                "provider": info.provider,
                "model_path": info.model_path,
                "domains": info.domains,
                "capabilities": [c.value for c in info.capabilities],
                "context_length": info.context_length,
                "description": info.description,
                "use_4bit": info.use_4bit,
                "priority": info.priority,
                "avg_latency_ms": info.avg_latency_ms,
                "success_rate": info.success_rate,
                "total_requests": info.total_requests,
                "avg_quality": getattr(info, "avg_quality", 0.0),
            }
            for model_id, info in self._models.items()
            if info.model_type in (ModelType.LOCAL, ModelType.FINE_TUNED)
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_from_file(self, path: str) -> None:
        """Load registry from file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            for model_id, info in data.items():
                if model_id not in self._models:
                    self.register(
                        model_id=model_id,
                        model_name=info["model_name"],
                        model_type=ModelType(info["model_type"]),
                        provider=info.get("provider", "local"),
                        model_path=info.get("model_path"),
                        domains=info.get("domains", []),
                        capabilities=[ModelCapability(c) for c in info.get("capabilities", [])],
                        context_length=info.get("context_length", 4096),
                        description=info.get("description"),
                        use_4bit=info.get("use_4bit", False),
                        priority=info.get("priority", 50),
                    )
                    
                    # Restore metrics
                    self._models[model_id].avg_latency_ms = info.get("avg_latency_ms", 0)
                    self._models[model_id].success_rate = info.get("success_rate", 1.0)
                    self._models[model_id].total_requests = info.get("total_requests", 0)
                    self._models[model_id].avg_quality = info.get("avg_quality", 0.0)
            
            logger.info("Loaded %d models from %s", len(data), path)
            
        except Exception as e:
            logger.warning("Failed to load registry from %s: %s", path, e)


# ==============================================================================
# Global Registry
# ==============================================================================

_registry: Optional[ModelRegistry] = None


def get_model_registry(
    registry_path: Optional[str] = None,
) -> ModelRegistry:
    """Get or create global model registry."""
    global _registry
    
    if _registry is None:
        _registry = ModelRegistry(
            include_defaults=True,
            registry_path=registry_path or os.environ.get("LLMHIVE_MODEL_REGISTRY"),
        )
    
    return _registry


def register_model(
    model_id: str,
    model_name: str,
    **kwargs,
) -> ModelInfo:
    """Quick helper to register a model."""
    registry = get_model_registry()
    return registry.register(model_id, model_name, **kwargs)


def get_model(model_id: str) -> Optional[ModelInfo]:
    """Quick helper to get a model."""
    registry = get_model_registry()
    return registry.get(model_id)

