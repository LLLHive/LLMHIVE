"""Simple shared scratchpad for orchestrator coordination tests."""

from __future__ import annotations

from typing import Any, Dict


class Scratchpad:
    """Stores intermediate agent results in a dictionary."""

    def __init__(self) -> None:
        self._context: Dict[str, Any] = {}

    def add_entry(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_entry(self, key: str) -> Any:
        return self._context.get(key)

    def clear(self) -> None:
        self._context.clear()

    def snapshot(self) -> Dict[str, Any]:
        """Return a shallow copy of the stored context."""

        return dict(self._context)
