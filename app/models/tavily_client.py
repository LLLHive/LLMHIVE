"""
TavilyClient: A wrapper for the Tavily search API using direct HTTP calls.

This implementation uses the Authorization: Bearer header and retries once
with a basic search if the initial request returns 400 Bad Request.
"""
from typing import Any
import requests

TAVILY_URL = "https://api.tavily.com/search"
TIMEOUT_S = 20

class TavilyInvalidRequest(Exception):
    pass

class TavilyClient:
    def __init__(self, api_key: str):
        """
        Initialize the Tavily client using the direct HTTP API.
        Args:
            api_key: Tavily API key
        """
        self.api_key = api_key

    def run(self, query: str) -> Any:
        """
        Execute a search query using Tavily's HTTP API.
        Args:
            query: The search query string
        Returns:
            Search results from Tavily or an error dict.
        """
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
                # Retry once with a simpler request if Tavily rejects the original shape
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
