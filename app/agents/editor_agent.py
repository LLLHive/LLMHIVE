"""
The Editor Agent.

This agent specializes in refining, formatting, and synthesizing text.
It takes drafts and other inputs and polishes them into a final,
high-quality response.
"""

from .base import Agent

class EditorAgent(Agent):
    """
    An agent that refines and synthesizes text into a final response.
    """
    def __init__(self, model_id: str = "gpt-4"):
        super().__init__(model_id, role="editor")

    async def execute(self, prompt: str, context: str = "") -> str:
        """
        Refines the provided context into a polished final answer.
        """
        full_prompt = (
            f"You are an expert editor. Your task is to refine the following text based on the provided context and instructions.\n\n"
            f"CONTEXT:\n---\n{context}\n---\n\n"
            f"EDITING TASK: {prompt}\n\n"
            f"Please produce the final, polished text. Ensure it is well-written, coherent, and meets all instructions."
        )
        
        final_text = await self.provider.generate(
            prompt=full_prompt,
            model=self.model_id
        )
        return final_text
