"""
The Lead Agent.

This is a general-purpose agent that handles primary tasks like providing
a direct answer, performing analysis, or generating a first draft.
"""

from .base import Agent

class LeadAgent(Agent):
    """
    A general-purpose agent for generating comprehensive initial responses.
    """
    def __init__(self, model_id: str):
        super().__init__(model_id, role="lead")

    async def execute(self, prompt: str, context: str = "") -> str:
        """
        Generates a direct response using the provided context and prompt.
        """
        full_prompt = f"{context}\n\nBased on the information above, please perform the following task: {prompt}"
        
        response = await self.provider.generate(
            prompt=full_prompt,
            model=self.model_id
        )
        return response
