from typing import Dict, List

from .base import Agent


class CriticAgent(Agent):
    def __init__(self, model_id: str):
        super().__init__(model_id, role="critic")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        system_prompt = (
            "You are a meticulous and constructive AI critic. Your task is to"
            " review a provided text and identify potential flaws, inaccuracies,"
            " or areas for improvement. Be specific and provide actionable"
            " feedback."
        )
        user_prompt = (
            "Please critique the following text. Focus on factual accuracy,"
            " logical consistency, clarity, and completeness. Do not be overly"
            " positive; your goal is to help improve the text.\n\nTEXT TO"
            f" CRITIQUE:\n---\n{task}\n---\n\nADDITIONAL CONTEXT (for"
            f" fact-checking and relevance):\n---\n{context}\n---"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
