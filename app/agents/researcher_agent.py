from typing import List, Dict
from .base import Agent
from tavily import TavilyClient
from ..config import settings

class ResearcherAgent(Agent):
    def __init__(self, model_id: str):
        super().__init__(model_id, role="researcher")
        self.search_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        return [{"role": "user", "content": f"You are an expert researcher. Your goal is to provide a detailed, factual, and unbiased summary of the topic: '{task}'. Use the provided search results as your primary source of information. Cite your sources where possible.\n\nSEARCH RESULTS:\n---\n{context}\n---"}]

    async def execute(self, task: str, context: str = "") -> str:
        try:
            search_results = self.search_client.search(query=task, search_depth="advanced", max_results=5)
            search_context = "\n\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in search_results['results']])
            messages = self._create_prompt(task, search_context)
            response = await self.gateway.call(model_id=self.model_id, messages=messages)
            return response.content
        except Exception as e:
            return f"Error during research for '{task}': {e}"