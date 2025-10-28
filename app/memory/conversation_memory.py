from __future__ import annotations

from typing import Dict, List

_memory_store: Dict[str, List[Dict[str, str]]] = {}


class ConversationMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id
        if self.user_id not in _memory_store:
            _memory_store[self.user_id] = []

    def store_interaction(self, prompt: str, response: str) -> None:
        _memory_store[self.user_id].append({"user": prompt, "ai": response})

    def retrieve_history(self, limit: int = 5) -> List[str]:
        history = _memory_store.get(self.user_id, [])
        formatted_history: List[str] = []
        for turn in history[-limit:]:
            formatted_history.append(f"User: {turn['user']}")
            formatted_history.append(f"AI: {turn['ai']}")
        return formatted_history