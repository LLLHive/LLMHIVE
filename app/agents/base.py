"""
Base classes and interfaces for all LLM agents.

This module defines the abstract `Agent` class, ensuring that all agents
adhere to a common interface for execution and role management.
"""

from abc import ABC, abstractmethod

class Agent(ABC):
    """
    Abstract base class for all LLM agents.
    """
    def __init__(self, model_id: str, role: str):
        self.model_id = model_id
        self.role = role

    @abstractmethod
    async def execute(self, prompt: str, context: str = "") -> str:
        """
        Executes the agent's task.

        Args:
            prompt: The specific instruction or task for the agent.
            context: Any relevant information or partial results from previous steps.

        Returns:
            The output of the agent as a string.
        """
        pass
