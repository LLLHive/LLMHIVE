"""Adapter registry exposed to orchestration modules."""
from __future__ import annotations

from typing import Dict, Iterable, List

from .anthropic_adapter import AnthropicAdapter
from .azure_adapter import AzureAdapter
from .base import BaseLLMAdapter
from .google_adapter import GoogleAdapter
from .local_llm_adapter import LocalLLMAdapter
from .openai_adapter import OpenAIAdapter


class AdapterRegistry:
    """Central registry containing all configured adapters."""

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseLLMAdapter] = {}
        for adapter in [
            OpenAIAdapter(),
            AnthropicAdapter(),
            GoogleAdapter(),
            AzureAdapter(),
            LocalLLMAdapter(),
        ]:
            self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BaseLLMAdapter | None:
        return self._adapters.get(name)

    def available(self) -> List[BaseLLMAdapter]:
        return [adapter for adapter in self._adapters.values() if adapter.is_available]

    def all(self) -> Iterable[BaseLLMAdapter]:
        return self._adapters.values()


__all__ = ["AdapterRegistry", "BaseLLMAdapter"]
