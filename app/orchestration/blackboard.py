from __future__ import annotations

from threading import Lock
from typing import Any, Dict


class Blackboard:
    def __init__(self, original_prompt: str):
        self._data: Dict[str, Any] = {
            "original_prompt": original_prompt,
            "logs": {"errors": [], "execution": []},
        }
        self._lock = Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            container, final_key = self._traverse_to_parent(key)
            container[final_key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._get_nested_value(key, default)

    def append_to_list(self, key: str, value: Any) -> None:
        with self._lock:
            container, final_key = self._traverse_to_parent(key)
            current_value = container.get(final_key)
            if current_value is None:
                container[final_key] = [value]
            elif isinstance(current_value, list):
                current_value.append(value)
            else:
                raise TypeError(f"Key '{key}' does not point to a list.")

    def get_full_context(self) -> str:
        with self._lock:
            lines = [f"Original Prompt: {self._data.get('original_prompt', '')}"]

            results = self._data.get("results", {})
            if results:
                lines.append("")
                for key, result in results.items():
                    lines.append(f"--- Result from {key} ---")
                    lines.append(str(result))
                    lines.append("")

            return "\n".join(lines).strip()

    def _traverse_to_parent(self, key: str) -> tuple[Dict[str, Any], str]:
        keys = key.split(".")
        if not keys:
            raise ValueError("Key must not be empty")

        container: Dict[str, Any] = self._data
        for part in keys[:-1]:
            next_value = container.setdefault(part, {})
            if not isinstance(next_value, dict):
                raise TypeError(f"Key '{part}' does not map to a dictionary.")
            container = next_value
        return container, keys[-1]

    def _get_nested_value(self, key: str, default: Any) -> Any:
        keys = key.split(".")
        value: Any = self._data
        for part in keys:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value