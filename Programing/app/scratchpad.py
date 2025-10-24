"""Shared scratchpad for intermediate results in LLMHive."""

from typing import Dict, Any


class Scratchpad:
    """Stores and manages shared context for agents."""

    def __init__(self):
        self.context = {}

    def add_entry(self, key: str, value: Any):
        """Add an entry to the scratchpad."""
        self.context[key] = value

    def get_entry(self, key: str) -> Any:
        """Retrieve an entry from the scratchpad."""
        return self.context.get(key)

    def clear(self):
        """Clear the scratchpad."""
        self.context.clear()
