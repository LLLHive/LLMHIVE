"""LLM Providers for LLMHive.

This module provides various LLM provider implementations:
- LocalModelProvider: HuggingFace/local models
- OpenAIProvider: OpenAI API models
- AnthropicProvider: Anthropic Claude models
- Custom fine-tuned model support
"""
from __future__ import annotations

# Local model provider
try:
    from .local_model import (
        LocalModelProvider,
        LocalModelConfig,
        ModelLoadError,
        get_local_provider,
    )
    LOCAL_MODEL_AVAILABLE = True
except ImportError:
    LOCAL_MODEL_AVAILABLE = False
    LocalModelProvider = None  # type: ignore
    LocalModelConfig = None  # type: ignore

# Fine-tuning module
try:
    from .fine_tuning import (
        FineTuner,
        FineTuneConfig,
        FineTuneResult,
        fine_tune_model,
    )
    FINE_TUNING_AVAILABLE = True
except ImportError:
    FINE_TUNING_AVAILABLE = False
    FineTuner = None  # type: ignore
    FineTuneConfig = None  # type: ignore

# Model registry
try:
    from .model_registry import (
        ModelRegistry,
        ModelInfo,
        register_model,
        get_model_registry,
    )
    MODEL_REGISTRY_AVAILABLE = True
except ImportError:
    MODEL_REGISTRY_AVAILABLE = False
    ModelRegistry = None  # type: ignore
    ModelInfo = None  # type: ignore


__all__ = [
    "LOCAL_MODEL_AVAILABLE",
    "FINE_TUNING_AVAILABLE",
    "MODEL_REGISTRY_AVAILABLE",
]

if LOCAL_MODEL_AVAILABLE:
    __all__.extend([
        "LocalModelProvider",
        "LocalModelConfig",
        "ModelLoadError",
        "get_local_provider",
    ])

if FINE_TUNING_AVAILABLE:
    __all__.extend([
        "FineTuner",
        "FineTuneConfig",
        "FineTuneResult",
        "fine_tune_model",
    ])

if MODEL_REGISTRY_AVAILABLE:
    __all__.extend([
        "ModelRegistry",
        "ModelInfo",
        "register_model",
        "get_model_registry",
    ])

