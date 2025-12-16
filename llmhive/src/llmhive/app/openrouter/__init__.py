"""OpenRouter Integration for LLMHive.

Complete OpenRouter integration providing:
- Model Catalog Sync (database)
- Inference Gateway (provider adapter)
- Telemetry & Rankings
- API endpoints for UI

Usage:
    from llmhive.app.openrouter import (
        OpenRouterClient,
        OpenRouterModelSync,
        OpenRouterInferenceGateway,
    )
"""
from __future__ import annotations

from .client import OpenRouterClient
from .models import (
    OpenRouterModel,
    OpenRouterEndpoint,
    OpenRouterUsageTelemetry,
    PromptTemplate,
    SavedRun,
)
from .sync import OpenRouterModelSync
from .gateway import OpenRouterInferenceGateway
from .rankings import RankingsAggregator

__all__ = [
    "OpenRouterClient",
    "OpenRouterModel",
    "OpenRouterEndpoint", 
    "OpenRouterUsageTelemetry",
    "PromptTemplate",
    "SavedRun",
    "OpenRouterModelSync",
    "OpenRouterInferenceGateway",
    "RankingsAggregator",
]

