"""Base interfaces for LLM provider adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GenerationParams:
    """Parameters controlling a generation request."""

    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 512
    n_samples: int = 1
    stop: Optional[list[str]] = None
    system_role: Optional[str] = None
    json_mode: bool = False


@dataclass
class LLMResult:
    """Container for a single LLM generation outcome."""

    text: str
    tokens: int
    latency_ms: float
    cost_usd: float
    model_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMAdapter:
    """Abstract base class for all LLM adapters."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def is_available(self) -> bool:
        """Whether the adapter can currently be used."""

        return True

    async def generate(self, prompt: str, params: GenerationParams) -> LLMResult:
        """Execute a generation request and return the result."""

        raise NotImplementedError

    def adapter_type(self) -> str:
        """Return a short identifier used for telemetry."""

        return self.name.split(":", 1)[0]
