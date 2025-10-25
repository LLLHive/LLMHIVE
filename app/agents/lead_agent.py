from typing import List, Dict
from .base import Agent

class LeadAgent(Agent):
    def __init__(self, model_id: str):
        super().__init__(model_id, role="lead")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        return [{"role": "user", "content": f"{context}\n\nBased on the information above, please perform the following task: {task}"}]