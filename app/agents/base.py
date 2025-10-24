"""
Base classes and interfaces for all LLM agents.

This module defines the abstract `Agent` class, ensuring that all agents
adhere to a common interface for execution and role management.
"""

from abc import ABC, abstractmethod
from ..models.llm_provider import LLMProvider, get_provider_for_model

class Agent(ABC):
    """
    Abstract base class for all LLM agents.
    It is initialized with a model_id and automatically gets the correct
    LLM provider to execute its tasks.
    """
    def __init__(self, model_id: str, role: str):
        self.model_id = model_id
        self.role = role
        self.provider: LLMProvider = get_provider_for_model(model_id)

    @abstractmethod
    async def execute(self, prompt: str, context: str = "") -> str:
        """
        Executes the agent's task by formatting a prompt and calling the LLM provider.
        """
        pass
