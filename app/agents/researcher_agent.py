"""
The Researcher Agent.

This agent is responsible for gathering information, fetching data from
external sources (like web search or databases), and providing supporting
evidence for other agents.
"""

from .base import Agent
import asyncio

class ResearcherAgent(Agent):
    """
    An agent that gathers information. In a real system, this agent would
    be augmented with tools like web search.
    """
    def __init__(self, model_id: str = "claude-3-opus"):
        super().__init__(model_id, role="researcher")

    async def _search_web(self, query: str) -> str:
        """Simulates a web search tool."""
        print(f"Simulating web search for: '{query}'")
        await asyncio.sleep(1) # Simulate network latency
        return f"Simulated search results show that '{query}' is tied to recent AI advancements and has significant economic implications."

    async def execute(self, prompt: str, context: str = "") -> str:
        """
        Performs research on the given topic, using a simulated web search.
        """
        # A real agent might first use an LLM to determine what to search for.
        search_query = prompt
        
        search_results = await self._search_web(search_query)

        synthesis_prompt = (
            f"You are a research analyst. Based on the following search results, synthesize the key findings and provide a summary for the topic: '{prompt}'.\n\n"
            f"SEARCH RESULTS:\n---\n{search_results}\n---\n\n"
            f"Please provide a concise summary of your findings."
        )
        
        research_summary = await self.provider.generate(
            prompt=synthesis_prompt,
            model=self.model_id
        )
        return research_summary
