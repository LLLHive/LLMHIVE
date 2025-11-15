from typing import Dict, List

from .base import Agent


class LeadAgent(Agent):
    def __init__(self, model_id: str):
        super().__init__(model_id, role="lead")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        system_prompt = (
            "You are the lead responder in a collaborative team of AI experts."
            " Provide a clear, structured, and thorough answer using the"
            " supplied context."
        )
        user_prompt = (
            f"CONTEXT FROM TEAM:\n---\n{context}\n---\n\nTASK:\n{task}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
