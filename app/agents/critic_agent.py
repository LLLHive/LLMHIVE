"""
The Critic Agent.

This agent is responsible for evaluating and critiquing the outputs
of other agents. It helps ensure quality, accuracy, and adherence
to instructions.
"""

from .base import Agent

class CriticAgent(Agent):
    """
    An agent that critiques or evaluates the outputs of others.
    """
    def __init__(self, model_id: str = "gpt-4"):
        super().__init__(model_id, role="critic")

    async def execute(self, prompt: str, context: str = "") -> str:
        """
        Evaluates the provided content based on a task prompt.
        """
        full_prompt = (
            f"You are a meticulous critic. Your task is to review the following content based on the user's original request and the work of other agents. Provide constructive feedback.\n\n"
            f"CONTEXT:\n---\n{context}\n---\n\n"
            f"TASK FOR REVIEW: {prompt}\n\n"
            f"Please provide your critique. Focus on accuracy, completeness, and clarity. Be specific in your feedback."
        )

        critique = await self.provider.generate(
            prompt=full_prompt,
            model=self.model_id
        )
        return critique
