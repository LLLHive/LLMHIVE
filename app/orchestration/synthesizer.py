"""
The Synthesizer component of the Orchestrator Engine.

Responsible for aggregating the outputs from multiple LLM agents and
merging them into a single, coherent, and polished final answer.
"""

from typing import Dict
from .planner import Plan
from ..agents import LeadAgent
from ..config import settings

class Synthesizer:
    """
    Combines partial results from different agents into a final response.
    """
    async def synthesize(self, partial_results: Dict[str, str], plan: Plan, original_prompt: str) -> str:
        """
        Synthesizes the final answer using an LLM to ensure coherence.
        """
        print(f"Synthesizing results with strategy: '{plan.synthesis_strategy}'")

        if not partial_results:
            return "I'm sorry, but I was unable to generate a response."

        # For simple plans, just return the lead's answer
        if len(partial_results) == 1 and "lead" in partial_results:
            return partial_results["lead"]

        # For complex plans, use an LLM to synthesize a final answer
        synthesis_prompt = self._build_synthesis_prompt(partial_results, original_prompt)
        
        # Use a powerful model for the final synthesis
        synthesizer_agent = LeadAgent(model_id=settings.DEFAULT_MODEL)
        
        print("Calling synthesizer LLM to merge results...")
        final_answer = await synthesizer_agent.execute(synthesis_prompt)
        
        return final_answer

    def _build_synthesis_prompt(self, partial_results: Dict[str, str], original_prompt: str) -> str:
        """Constructs a prompt for the synthesizer LLM."""
        prompt = f"You are a master editor. Your task is to synthesize the following partial results from different AI agents into a single, high-quality, and coherent final answer that directly addresses the user's original prompt.\n\n"
        prompt += f"USER'S ORIGINAL PROMPT:\n---\n{original_prompt}\n---\n\n"
        prompt += "PARTIAL RESULTS FROM AGENTS:\n---\n"

        for role, result in partial_results.items():
            prompt += f"## Contribution from {role.capitalize()} Agent:\n{result}\n\n"

        prompt += "---\nINSTRUCTIONS:\n"
        prompt += "1. Combine all the information into a single, well-structured response.\n"
        prompt += "2. Ensure the tone is consistent, helpful, and clear.\n"
        prompt += "3. Do not mention the different agents or the synthesis process in the final output.\n"
        prompt += "4. Make sure the final answer directly and completely answers the user's original prompt.\n\n"
        prompt += "FINAL SYNTHESIZED ANSWER:"

        return prompt
