from typing import Dict, Any, List
from threading import Lock

class Blackboard:
    def __init__(self, original_prompt: str):
        self._data: Dict[str, Any] = {"original_prompt": original_prompt, "logs": {"errors": [], "execution": []}}
        self._lock = Lock()

    def set(self, key: str, value: Any):
        with self._lock:
            keys = key.split('.')
            d = self._data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
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
        with self._lock:
            current_list = self.get(key, [])
            if not isinstance(current_list, list):
                raise TypeError(f"Key '{key}' does not point to a list.")
            current_list.append(value)
            self.set(key, current_list)

    def get_full_context(self) -> str:
        with self._lock:
            context = f"Original Prompt: {self._data.get('original_prompt')}\n\n"
            results = self._data.get('results', {})
            for key, result in results.items():
                context += f"--- Result from {key} ---\n{str(result)}\n\n"
            return context