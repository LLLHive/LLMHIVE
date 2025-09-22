"""Custom exceptions used throughout the service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class LLMHiveError(Exception):
    """Base exception for predictable orchestration failures."""

    message: str
    status_code: int = 400
    context: Mapping[str, Any] | None = None

    def __str__(self) -> str:  # pragma: no cover - delegated to dataclass __repr__
        return self.message


class ProviderNotConfiguredError(LLMHiveError):
    """Raised when a provider is requested but credentials are missing."""

    status_code: int = 503


class FactCheckError(LLMHiveError):
    """Raised when fact-checking infrastructure fails."""

    status_code: int = 502
