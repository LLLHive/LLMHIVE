"""
The Blackboard (Shared Scratchpad) for LLMHive.

This module provides a centralized, structured workspace for agents to share
intermediate results, reasoning steps, and other artifacts during the
execution of a plan. It acts as the shared memory for the multi-agent team.
"""

from typing import Dict, Any, List
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class Blackboard:
    """
    A thread-safe object for storing and retrieving shared state among agents.
    """
    def __init__(self, original_prompt: str):
        self._data: Dict[str, Any] = {"original_prompt": original_prompt, "results": {}}
        self._lock = Lock()

    def set(self, key: str, value: Any):
        """
        Writes a value to the blackboard.
        Example: blackboard.set("research_findings", "Quantum computing is...")
        """
        with self._lock:
            keys = key.split('.')
            d = self._data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value
            logger.debug(f"Blackboard SET: {key} = {str(value)[:80]}...")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Reads a value from the blackboard.
        Example: findings = blackboard.get("research_findings")
        """
        with self._lock:
            keys = key.split('.')
            d = self._data
            for k in keys:
                if isinstance(d, dict) and k in d:
                    d = d[k]
                else:
                    return default
            return d

    def append_to_list(self, key: str, value: Any):
        """
        Appends a value to a list on the blackboard. Creates the list if it doesn't exist.
        """
        with self._lock:
            current_list = self.get(key, [])
            if not isinstance(current_list, list):
                raise TypeError(f"Key '{key}' does not point to a list.")
            current_list.append(value)
            self.set(key, current_list)

    def get_full_context(self) -> str:
        """
        Generates a string representation of the current state for an agent's context.
        """
        with self._lock:
            context = f"Original Prompt: {self._data.get('original_prompt')}\n\n"
            results = self._data.get('results', {})
            for role, result in results.items():
                context += f"--- Result from {role} ---\n{str(result)}\n\n"
            return context
