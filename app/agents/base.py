"""
Base classes and interfaces for all LLM agents.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict
from ..services.model_gateway import model_gateway

class Agent(ABC):
    """
    Abstract base class for all LLM agents.
    Agents now use the central ModelGateway for all LLM interactions.
    """
    def __init__(self, model_id: str, role: str):
        self.model_id = model_id
        self.role = role
        from ..models.llm_provider import MODEL_PROVIDER_MAP # Avoid circular import
        self.provider_name = MODEL_PROVIDER_MAP.get(model_id, "openai")

    @abstractmethod
    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        """Creates the specific list of messages for the agent's task."""
        pass

    async def execute(self, task: str, context: str = "") -> str:
        """Executes the agent's task and returns the full response."""
        messages = self._create_prompt(task, context)
        response = await model_gateway.call(
            provider_name=self.provider_name,
            model=self.model_id,
            messages=messages
        )
        return response.content

    async def execute_stream(self, task: str, context: str = "") -> AsyncGenerator[str, None]:
        """Executes the agent's task and streams the response."""
        messages = self._create_prompt(task, context)
        async for token in model_gateway.call(
            provider_name=self.provider_name,
            model=self.model_id,
            messages=messages,
            stream=True
        ):
            yield token
