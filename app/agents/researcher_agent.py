"""
The Researcher Agent - Now with real web search capabilities.

This agent is responsible for gathering information using Tavily AI
for web search and providing supporting evidence for other agents.
"""

from typing import List, Dict
from .base import Agent
from tavily import TavilyClient
from ..config import settings

class ResearcherAgent(Agent):
    """
    An agent that uses Tavily search tool to gather up-to-date information
    from the web.
    """
    def __init__(self, model_id: str = "claude-3-opus"):
        super().__init__(model_id, role="researcher")
        self.search_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        """The 'task' for a researcher is the topic to research."""
        return [{"role": "user", "content": f"You are an expert researcher. Your goal is to provide a detailed, factual, and unbiased summary of the topic: '{task}'. Use the provided search results as your primary source of information. Cite your sources where possible.\n\nSEARCH RESULTS:\n---\n{context}\n---"}]

    async def execute(self, task: str, context: str = "") -> str:
        """
        Performs research by first using the search tool, then using an LLM
        to synthesize the findings.
        """
        print(f"Researcher Agent searching for: '{task}'")
        try:
            # 1. Use the search tool to get real-world information
            search_results = self.search_client.search(query=task, search_depth="advanced", max_results=5)
            # Format the results into a clean context string
            search_context = "\n\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in search_results['results']])
            
            # 2. Use the LLM to synthesize the findings into a high-quality answer
            # We pass the search results as the 'context' for the LLM prompt.
            messages = self._create_prompt(task, search_context)
            from ..services.model_gateway import model_gateway
            response = await model_gateway.call(model_id=self.model_id, messages=messages)
            return response.content

        except Exception as e:
            error_msg = f"Error during research for '{task}': {e}"
            print(f"ERROR: {error_msg}")
            return error_msg
