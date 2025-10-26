from typing import AsyncGenerator
from .blackboard import Blackboard
from agents import LeadAgent
from config import settings

class Synthesizer:
    async def synthesize_stream(self, blackboard: Blackboard) -> AsyncGenerator[str, None]:
        final_draft = blackboard.get("results.final_draft")
        if final_draft:
            for char in final_draft:
                yield char
            return

        original_prompt = blackboard.get("original_prompt")
        synthesis_prompt = self._build_synthesis_prompt(blackboard, original_prompt)
        
        synthesizer_agent = LeadAgent(model_id=settings.SYNTHESIS_MODEL)
        
        async for token in synthesizer_agent.execute_stream(synthesis_prompt):
            yield token

    def _build_synthesis_prompt(self, blackboard: Blackboard, original_prompt: str) -> str:
        context = blackboard.get_full_context()
        return (
            "You are a master editor. Synthesize the information in the context below into a single, high-quality answer for the user's original prompt.\n\n"
            f"USER'S ORIGINAL PROMPT:\n---\n{original_prompt}\n---\n\n"
            f"AVAILABLE CONTEXT FROM AGENT WORK:\n---\n{context}\n---\n\n"
            "INSTRUCTIONS:\n"
            "1. Read all contributions carefully.\n"
            "2. Construct a single, comprehensive response.\n"
            "3. Ensure the tone is consistent and helpful. Do NOT mention the internal agents or synthesis process.\n\n"
            "FINAL SYNTHESIZED ANSWER:"
        )