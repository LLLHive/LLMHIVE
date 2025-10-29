import pytest

from llmhive.app.services.web_research import WebResearchClient


@pytest.mark.asyncio
async def test_web_research_returns_fallback_when_disabled(monkeypatch):
    client = WebResearchClient(api_key=None)
    results = await client.search("LLMHive architecture")
    assert results
    assert "search" in results[0].title.lower()
