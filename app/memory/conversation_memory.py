"""
Short-Term Conversation Memory.

This module handles the storage and retrieval of recent conversation history
for a given user session. This context is crucial for maintaining continuity
and relevance in multi-turn dialogues.
"""

from typing import List, Dict

# In-memory store for demonstration purposes. A real application would use
# a database like Redis or PostgreSQL for persistence.
_memory_store: Dict[str, List[Dict[str, str]]] = {}

class ConversationMemory:
    """
    Manages the conversation history for a user.
    """
    def __init__(self, user_id: str):
        self.user_id = user_id
        if self.user_id not in _memory_store:
            _memory_store[self.user_id] = []

    def store_interaction(self, prompt: str, response: str):
        """
        Saves a user prompt and AI response to the history.
        """
        print(f"Storing interaction for user '{self.user_id}'")
        _memory_store[self.user_id].append({"user": prompt, "ai": response})

    def retrieve_history(self, limit: int = 5) -> List[str]:
        """
        Retrieves the recent conversation history.
        """
        history = _memory_store.get(self.user_id, [])
        # Simple formatting for context. A real system might use summarization.
        formatted_history = []
        for turn in history[-limit:]:
            formatted_history.append(f"User: {turn['user']}")
            formatted_history.append(f"AI: {turn['ai']}")
        return formatted_history
