"""
The Synthesizer component of the Orchestrator Engine.

Aggregates outputs and uses an LLM to merge them into a final, coherent answer.
"""
from typing import AsyncGenerator
from .blackboard import Blackboard
from ..agents import LeadAgent
from ..config import settings

class Synthesizer:
    """Combines results from agents into a final response."""
    async def synthesize_stream(self, blackboard: Blackboard) -> AsyncGenerator[str, None]:
        """Synthesizes the final answer and streams it token by token."""
        print(f"Synthesizing results...")
        
        original_prompt = blackboard.get("original_prompt")

        # Check for final draft or improved results from critique workflow
        final_draft = blackboard.get("results.final_draft")
        critique_workflow = blackboard.get("results.critique_workflow")
        
        if critique_workflow and "improved_drafts" in critique_workflow:
            # Use improved drafts from critique workflow
            improved_drafts = critique_workflow["improved_drafts"]
            if improved_drafts:
                # Pick the first improved draft or merge them
                first_improved = next(iter(improved_drafts.values()))
                for char in first_improved:
                    yield char
                return
        
        if final_draft:
            # If a final draft already exists (e.g., from an editor), stream it directly.
            for char in final_draft:
                yield char
            return

        # If no final draft, build a prompt to generate one
        synthesis_prompt = self._build_synthesis_prompt(blackboard, original_prompt)
        
        synthesizer_agent = LeadAgent(model_id=settings.SYNTHESIS_MODEL)
        
        print("Calling synthesizer LLM to merge results and stream...")
        async for token in synthesizer_agent.execute_stream(synthesis_prompt):
            yield token

    def _build_synthesis_prompt(self, blackboard: Blackboard, original_prompt: str) -> str:
        """Constructs a prompt for the synthesizer LLM."""
        context = blackboard.get_full_context()
        prompt = (
            "You are a master editor. Your task is to synthesize the information provided in the context below into a single, high-quality, and coherent final answer that directly addresses the user's original prompt. The context contains outputs from various specialized AI agents.\n\n"
            f"USER'S ORIGINAL PROMPT:\n---\n{original_prompt}\n---\n\n"
            f"AVAILABLE CONTEXT FROM AGENT WORK:\n---\n{context}\n---\n\n"
            "INSTRUCTIONS:\n"
            "1. Read the original prompt and all agent contributions carefully.\n"
            "2. Construct a single, comprehensive response that directly answers the user's prompt.\n"
            "3. Ensure the tone is consistent, helpful, and clear. Do NOT mention the agents or the internal synthesis process.\n"
            "4. If there are conflicting pieces of information, use your best judgment to resolve them or state the uncertainty clearly.\n\n"
            "FINAL SYNTHESIZED ANSWER:"
        )
        return prompt
