"""
The Lead Agent. A general-purpose agent for primary tasks.
"""

from typing import AsyncGenerator, List, Dict
from .base import Agent

class LeadAgent(Agent):
    """A general-purpose agent for generating comprehensive responses."""
    def __init__(self, model_id: str):
        # The role can be lead, analyst, etc.
        super().__init__(model_id, role="lead")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        """Creates the prompt messages for the lead agent."""
        full_prompt = f"{context}\n\nBased on the information above, please perform the following task: {task}"
        return [{"role": "user", "content": full_prompt}]
