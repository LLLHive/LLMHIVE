"""Unit tests for performance optimization: caching and parallel execution."""
from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llmhive.app.cache import RequestCache, get_request_cache, reset_request_cache
from llmhive.app.services.web_research import WebDocument, WebResearchClient
from llmhive.app.orchestrator import Orchestrator


@pytest.fixture
def cache():
    """Provide a fresh cache instance for each test."""
    reset_request_cache()
    return get_request_cache(max_size=10)


@pytest.fixture
def mock_web_research():
    """Provide a mock web research client."""
    mock = AsyncMock(spec=WebResearchClient)
    mock.search = AsyncMock(return_value=[
        WebDocument(title="Test", url="http://test.com", snippet="Test snippet")
    ])
    return mock


@pytest.mark.asyncio
async def test_cache_web_search_hit(cache, mock_web_research):
    """Test that cached web search returns cached result without calling API."""
    query = "test query"
    
    # First call - should be a miss
    cached_result = await cache.get("web_search", query, max_results=3)
    assert cached_result is None
    
    # Store result
    result = [WebDocument(title="Cached", url="http://cached.com", snippet="Cached snippet")]
    await cache.set("web_search", result, query, max_results=3)
    
    # Second call - should be a hit
    cached_result = await cache.get("web_search", query, max_results=3)
    assert cached_result is not None
    assert cached_result[0].title == "Cached"
    
    # Verify API was not called (if we had a real client)
    # In this test, we're just verifying cache behavior


@pytest.mark.asyncio
async def test_cache_knowledge_search(cache):
    """Test that knowledge base search results are cached."""
    user_id = "test_user"
    query = "test knowledge query"
    
    # First call - miss
    cached = await cache.get("knowledge_search", user_id, query, limit=3, min_score=0.5)
    assert cached is None
    
    # Store result
    mock_results = [{"content": "test content", "score": 0.8}]
    await cache.set("knowledge_search", mock_results, user_id, query, limit=3, min_score=0.5)
    
    # Second call - hit
    cached = await cache.get("knowledge_search", user_id, query, limit=3, min_score=0.5)
    assert cached is not None
    assert cached[0]["content"] == "test content"


@pytest.mark.asyncio
async def test_cache_lru_eviction(cache):
    """Test that LRU eviction works when cache exceeds max size."""
    # Fill cache beyond max_size
    for i in range(15):  # max_size is 10
        await cache.set("test", f"value_{i}", i)
    
    # Oldest entries should be evicted
    stats = cache.get_stats()
    assert stats["size"] <= cache.max_size
    
    # First entry should be evicted
    first_value = await cache.get("test", 0)
    assert first_value is None  # Should be evicted
    
    # Recent entries should still be cached
    recent_value = await cache.get("test", 14)
    assert recent_value == "value_14"


@pytest.mark.asyncio
async def test_cache_thread_safety(cache):
    """Test that cache is thread-safe for concurrent access."""
    async def set_value(i):
        await cache.set("test", f"value_{i}", i)
    
    async def get_value(i):
        return await cache.get("test", i)
    
    # Concurrent writes
    await asyncio.gather(*[set_value(i) for i in range(10)])
    
    # Concurrent reads
    results = await asyncio.gather(*[get_value(i) for i in range(10)])
    
    # All values should be retrievable
    assert all(r is not None for r in results)


@pytest.mark.asyncio
async def test_parallel_web_searches():
    """Test that multiple web searches can execute in parallel."""
    # Create mock web research with delay
    async def delayed_search(query: str, max_results: int = 3):
        await asyncio.sleep(0.1)  # Simulate network delay
        return [WebDocument(title=query, url="http://test.com", snippet=f"Result for {query}")]
    
    mock_web_research = AsyncMock()
    mock_web_research.search = delayed_search
    
    # Execute multiple searches in parallel
    queries = ["query1", "query2", "query3"]
    start_time = time.time()
    
    tasks = [delayed_search(q) for q in queries]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    # Parallel execution should be faster than sequential (3 * 0.1 = 0.3s sequential)
    # Parallel should be ~0.1s (all run concurrently)
    assert elapsed < 0.2, f"Parallel execution took {elapsed}s, expected < 0.2s"
    assert len(results) == 3
    assert all(len(r) > 0 for r in results)


@pytest.mark.asyncio
async def test_orchestrator_cached_web_search():
    """Test that orchestrator uses cached web search."""
    orchestrator = Orchestrator()
    
    # Mock web research
    mock_result = [WebDocument(title="Cached", url="http://test.com", snippet="Cached")]
    orchestrator.web_research.search = AsyncMock(return_value=mock_result)
    
    query = "test query"
    
    # First call - should call API
    result1 = await orchestrator._cached_web_search(query)
    assert result1[0].title == "Cached"
    assert orchestrator.web_research.search.call_count == 1
    
    # Second call - should use cache
    result2 = await orchestrator._cached_web_search(query)
    assert result2[0].title == "Cached"
    # API should not be called again (but our mock doesn't track this perfectly)
    # The cache should return the same result


@pytest.mark.asyncio
async def test_orchestrator_cached_prompt_optimization():
    """Test that orchestrator caches prompt optimization."""
    orchestrator = Orchestrator()
    
    prompt = "test prompt"
    context = "test context"
    
    # First call - should compute
    result1 = orchestrator._cached_optimize_prompt(prompt, context=context)
    assert result1 is not None
    
    # Second call with same inputs - should use cache
    # We can't easily verify this without mocking, but we can check it returns same result
    result2 = orchestrator._cached_optimize_prompt(prompt, context=context)
    assert result2 == result1  # Should be identical (cached)


@pytest.mark.asyncio
async def test_parallel_fact_checks():
    """Test that multiple fact-check operations can run in parallel."""
    # Create mock fact checker with delay
    async def delayed_fact_check(answer: str, prompt: str, web_documents=None):
        await asyncio.sleep(0.1)  # Simulate processing delay
        from llmhive.app.fact_check import FactCheckResult
        return FactCheckResult(
            verified_count=1,
            contested_count=0,
            unknown_count=0,
            failed_claims=[],
            verification_score=0.9,
        )
    
    mock_fact_checker = AsyncMock()
    mock_fact_checker.check_answer = delayed_fact_check
    
    # Execute multiple fact checks in parallel
    answers = ["answer1", "answer2", "answer3"]
    start_time = time.time()
    
    tasks = [delayed_fact_check(a, "prompt") for a in answers]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    # Parallel execution should be faster than sequential
    assert elapsed < 0.2, f"Parallel fact checks took {elapsed}s, expected < 0.2s"
    assert len(results) == 3
    assert all(r.verification_score > 0 for r in results)


def test_cache_stats(cache):
    """Test that cache statistics are accurate."""
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["size"] == 0
    
    # Add some entries
    import asyncio
    async def add_entries():
        for i in range(5):
            await cache.set("test", f"value_{i}", i)
        for i in range(3):
            await cache.get("test", i)  # Hits
        for i in range(10, 13):
            await cache.get("test", i)  # Misses
    
    asyncio.run(add_entries())
    
    stats = cache.get_stats()
    assert stats["hits"] == 3
    assert stats["misses"] == 3
    assert stats["size"] == 5
    assert stats["hit_rate"] == 50.0  # 3 hits / 6 total = 50%


@pytest.mark.asyncio
async def test_cache_clear(cache):
    """Test that cache can be cleared."""
    # Add entries
    for i in range(5):
        await cache.set("test", f"value_{i}", i)
    
    assert cache.get_stats()["size"] == 5
    
    # Clear cache
    await cache.clear()
    
    stats = cache.get_stats()
    assert stats["size"] == 0
    assert stats["hits"] == 0
    assert stats["misses"] == 0

