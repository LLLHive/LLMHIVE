from typing import Any
import requests
import os

TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT_S = 20

class TavilyInvalidRequest(Exception):
    pass

class TavilyClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY", "").strip()
        if not self.api_key:
            raise TavilyInvalidRequest("Missing TAVILY_API_KEY")

    def run(self, query: str) -> Any:
        if not isinstance(query, str) or not query.strip():
            return {"error": "empty query"}
        payload = {
            "query": query.strip(),
            "search_depth": "advanced",
            "max_results": 5,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(TAVILY_URL, json=payload, headers=headers, timeout=TIMEOUT_S)
            if resp.status_code == 400:
                retry_payload = {
                    "query": payload["query"],
                    "search_depth": "basic",
                    "max_results": 3,
                }
                resp = requests.post(TAVILY_URL, json=retry_payload, headers=headers, timeout=TIMEOUT_S)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": f"Tavily search failed: {str(e)}"}
