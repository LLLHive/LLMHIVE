from typing import List, Dict
from .base import Agent
from app.config import settings

try:
    from tavily import TavilyClient
    if settings.TAVILY_API_KEY:
        tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    else:
        tavily_client = None
except ImportError:
    tavily_client = None

class ResearcherAgent(Agent):
    def __init__(self, model_id: str):
        super().__init__(model_id, role="researcher")

    def _create_search_synthesis_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        return [{"role": "user", "content": f"You are an expert researcher. Synthesize the provided search results into a detailed, factual, and unbiased summary for the topic: '{task}'. Cite your sources where possible.\n\nSEARCH RESULTS:\n---\n{context}\n---"}]

    def _create_internal_knowledge_prompt(self, task: str) -> List[Dict[str, str]]:
        return [{"role": "user", "content": f"You are an expert researcher. Although you cannot access the live internet right now, provide the most detailed and accurate summary you can about the topic '{task}' based on your internal knowledge up to your last training cut-off."}]

    async def execute(self, task: str, context: str = "") -> str:
        if tavily_client:
            try:
                search_results = tavily_client.search(query=task, search_depth="advanced", max_results=5)
                search_context = "\n\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in search_results['results']])
                messages = self._create_search_synthesis_prompt(task, search_context)
            except Exception as e:
                messages = self._create_internal_knowledge_prompt(task)
        else:
            messages = self._create_internal_knowledge_prompt(task)

        response = await self.gateway.call(model_id=self.model_id, messages=messages)
        return response.content
