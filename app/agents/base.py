"""
Base classes and interfaces for all LLM agents.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator
from ..models.llm_provider import LLMProvider, get_provider_for_model

class Agent(ABC):
    """
    Abstract base class for all LLM agents.
    """
    def __init__(self, model_id: str, role: str):
        self.model_id = model_id
        self.role = role
        self.provider: LLMProvider = get_provider_for_model(model_id)

    @abstractmethod
    async def execute(self, prompt: str, context: str = "") -> str:
        """Executes the agent's task and returns the full response."""
        pass

    async def execute_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """Executes the agent's task and streams the response."""
        full_prompt = f"{context}\n\nTask: {prompt}"
        async for token in self.provider.generate_stream(prompt=full_prompt, model=self.model_id):
            yield token
