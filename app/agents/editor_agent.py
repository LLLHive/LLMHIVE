from typing import List, Dict
from .base import Agent

class EditorAgent(Agent):
    def __init__(self, model_id: str):
        super().__init__(model_id, role="editor")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        system_prompt = "You are an expert editor. Your task is to refine and synthesize the provided text into a final, high-quality response based on the given instructions."
        user_prompt = f"CONTEXT:\n---\n{context}\n---\n\nEDITING TASK: {task}\n\nPlease produce the final, polished text. Ensure it is well-written, coherent, and meets all instructions."
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]