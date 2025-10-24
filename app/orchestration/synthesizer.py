"""
The Synthesizer component of the Orchestrator Engine.

Responsible for aggregating the outputs from multiple LLM agents and
merging them into a single, coherent, and polished final answer.
"""

from typing import Dict
from .planner import Plan

class Synthesizer:
    """
    Combines partial results from different agents into a final response.
    """
    def synthesize(self, partial_results: Dict[str, str], plan: Plan) -> str:
        """
        Synthesizes the final answer based on the provided strategy.

        A real implementation would use an LLM to perform the synthesis for
        complex merging tasks, ensuring a consistent tone and high quality.
        """
        print(f"Synthesizing results with strategy: '{plan.synthesis_strategy}'")

        if not partial_results:
            return "I'm sorry, but I was unable to generate a response."

        # Simple synthesis strategy: concatenate results
        if plan.synthesis_strategy == "merge" or plan.synthesis_strategy == "hybrid":
            final_answer = "Here is a synthesized response based on the work of multiple agents:\n\n"
            for role, result in partial_results.items():
                final_answer += f"--- Contribution from {role.capitalize()} Agent ---\n{result}\n\n"
            return final_answer.strip()
        else: # Default to the lead's answer
            return partial_results.get("lead", "No primary answer was generated.")
