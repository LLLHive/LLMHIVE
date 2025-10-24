"""
The Lead Agent. A general-purpose agent for primary tasks.
"""

from typing import AsyncGenerator
from .base import Agent

class LeadAgent(Agent):
    """A general-purpose agent for generating comprehensive responses."""
    def __init__(self, model_id: str):
        # The role can be lead, analyst, etc.
        super().__init__(model_id, role="lead")

    async def execute(self, prompt: str, context: str = "") -> str:
        """Generates a direct response using the provided context and prompt."""
        full_prompt = f"{context}\n\nBased on the information above, please perform the following task: {prompt}"
        
        response = await self.provider.generate(
            prompt=full_prompt,
            model=self.model_id
        )
        return response

    async def execute_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
        """Streams a direct response."""
        full_prompt = f"{context}\n\nBased on the information above, please perform the following task: {prompt}"
        async for token in self.provider.generate_stream(prompt=full_prompt, model=self.model_id):
            yield token
