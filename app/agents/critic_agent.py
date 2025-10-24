"""
The Critic Agent.

This agent is responsible for evaluating and critiquing the outputs
of other agents. It helps ensure quality, accuracy, and adherence
to instructions.
"""

from typing import List, Dict
from .base import Agent

class CriticAgent(Agent):
    """
    An agent that critiques or evaluates the outputs of others.
    """
    def __init__(self, model_id: str = "gpt-4"):
        super().__init__(model_id, role="critic")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        """Creates the prompt messages for critique."""
        # The 'task' for a critic is the content to be critiqued.
        system_prompt = "You are a meticulous and constructive AI critic. Your task is to review a provided text and identify potential flaws, inaccuracies, or areas for improvement. Be specific and provide actionable feedback."
        user_prompt = f"Please critique the following text. Focus on factual accuracy, logical consistency, clarity, and completeness. Do not be overly positive; your goal is to help improve the text.\n\nTEXT TO CRITIQUE:\n---\n{task}\n---\n\nADDITIONAL CONTEXT (for fact-checking and relevance):\n---\n{context}\n---"
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
