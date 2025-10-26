"""
TavilyClient: A wrapper for the Tavily search API.
"""
from typing import Any

try:
    from tavily import TavilyClient as TavilyAPIClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

class TavilyClient:
    def __init__(self, api_key: str):
        """
        Initialize the Tavily client.
        
        Args:
            api_key: Tavily API key
        """
        if not TAVILY_AVAILABLE:
            raise ImportError("Tavily library not available. Install with: pip install tavily-python")
        self.client = TavilyAPIClient(api_key=api_key)

    def run(self, query: str) -> Any:
        """
        Execute a search query using Tavily.
        
        Args:
            query: The search query string
            
        Returns:
            Search results from Tavily
        """
        try:
            results = self.client.search(query=query, search_depth="basic", max_results=5)
            return results
        except Exception as e:
            return {"error": f"Tavily search failed: {str(e)}"}
