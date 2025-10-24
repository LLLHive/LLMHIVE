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
        Evaluates the provided content.

        This is a stub. A real implementation would use an LLM call with a
        specialized prompt to review the context.
        """
        print(f"Critic Agent ({self.model_id}) evaluating: '{context}'")
        critique = f"This is a good start, but consider elaborating on the key points. The section on '{prompt}' could be clearer."
        return critique
