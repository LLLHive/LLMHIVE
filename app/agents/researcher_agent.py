"""
The Researcher Agent - Now with intelligent fallback for web search.
"""
from typing import List, Dict
from .base import Agent
from ..config import settings

# Conditionally import and initialize TavilyClient
try:
    from tavily import TavilyClient
    if settings.TAVILY_API_KEY:
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    else:
        tavily_client = None
except ImportError:
    tavily_client = None

class ResearcherAgent(Agent):
    """An agent that uses a search tool if available, otherwise uses internal knowledge."""
    def __init__(self, model_id: str):
        super().__init__(model_id, role="researcher")

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        """Required abstract method - not used as execute is overridden."""
        # This is a fallback that should not normally be called
        return self._create_internal_knowledge_prompt(task)

    def _create_search_synthesis_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        """Prompt for when search results are available."""
        return [{"role": "user", "content": f"You are an expert researcher. Synthesize the provided search results into a detailed, factual, and unbiased summary for the topic: '{task}'. Cite your sources where possible.\n\nSEARCH RESULTS:\n---\n{context}\n---"}]

    def _create_internal_knowledge_prompt(self, task: str) -> List[Dict[str, str]]:
        """Prompt for when the search tool is not available."""
        return [{"role": "user", "content": f"You are an expert researcher. Although you cannot access the live internet right now, provide the most detailed and accurate summary you can about the topic '{task}' based on your internal knowledge up to your last training cut-off."}]

    async def execute(self, task: str, context: str = "") -> str:
        """
        Performs research. If Tavily API key is present, it searches the web.
        Otherwise, it falls back to using the LLM's internal knowledge.
        """
        # Intelligent Fallback Logic
        if tavily_client:
            print(f"Researcher Agent: Performing live web search for: '{task}'")
            try:
                search_results = tavily_client.search(query=task, search_depth="advanced", max_results=5)
                search_context = "\n\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in search_results['results']])
                messages = self._create_search_synthesis_prompt(task, search_context)
            except Exception as e:
                error_msg = f"Web search failed: {e}. Falling back to internal knowledge."
                print(f"WARNING: {error_msg}")
                messages = self._create_internal_knowledge_prompt(task)
        else:
            print("Researcher Agent: Tavily API key not found. Using internal knowledge.")
            messages = self._create_internal_knowledge_prompt(task)

        response = await self.gateway.call(model_id=self.model_id, messages=messages)
        return response.content