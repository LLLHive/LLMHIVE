"""Tests for RAG system optimizations.

This module tests:
1. Hybrid semantic + lexical retrieval
2. Cross-encoder reranking
3. HyDE fallback
4. Query caching
5. Context validation
6. Factoid fast-path
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBM25Index:
    """Tests for BM25 lexical search index."""
    
    def test_add_documents(self):
        """Test adding documents to BM25 index."""
        from llmhive.app.knowledge.retrieval_engine import BM25Index
        
        index = BM25Index()
        documents = [
            ("doc1", "Python is a programming language"),
            ("doc2", "Java is also a programming language"),
            ("doc3", "Machine learning uses Python"),
        ]
        
        index.add_documents(documents)
        
        assert index.total_docs == 3
        assert "doc1" in index.doc_contents
        assert index.avg_doc_length > 0
    
    def test_search(self):
        """Test BM25 search returns relevant documents."""
        from llmhive.app.knowledge.retrieval_engine import BM25Index
        
        index = BM25Index()
        documents = [
            ("doc1", "Python is a programming language"),
            ("doc2", "Java is also a programming language"),
            ("doc3", "Machine learning uses Python heavily"),
        ]
        index.add_documents(documents)
        
        results = index.search("Python programming", top_k=2)
        
        assert len(results) > 0
        # Python document should rank higher
        doc_ids = [doc_id for doc_id, _ in results]
        assert "doc1" in doc_ids or "doc3" in doc_ids


class TestCrossEncoderReranker:
    """Tests for cross-encoder reranking."""
    
    def test_rerank_fallback_without_model(self):
        """Test reranking falls back gracefully without sentence-transformers."""
        from llmhive.app.knowledge.retrieval_engine import CrossEncoderReranker, RetrievedDocument
        
        reranker = CrossEncoderReranker()
        
        docs = [
            RetrievedDocument(content="Python programming", score=0.8, doc_id="1"),
            RetrievedDocument(content="Java programming", score=0.9, doc_id="2"),
        ]
        
        # Should return original order if model not available
        result = reranker.rerank("Python code", docs, top_k=2)
        
        assert len(result) == 2


class TestHyDEGenerator:
    """Tests for HyDE hypothetical document generation."""
    
    @pytest.mark.asyncio
    async def test_generate_without_llm(self):
        """Test HyDE returns empty without LLM provider."""
        from llmhive.app.knowledge.retrieval_engine import HyDEGenerator
        
        generator = HyDEGenerator(llm_provider=None)
        
        result = await generator.generate_hypothetical_document("test query")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_generate_with_mock_llm(self):
        """Test HyDE generates hypothetical documents with LLM."""
        from llmhive.app.knowledge.retrieval_engine import HyDEGenerator
        
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value=MagicMock(content="Hypothetical answer about the topic"))
        
        generator = HyDEGenerator(llm_provider=mock_llm)
        
        result = await generator.generate_hypothetical_document("What is machine learning?")
        
        assert len(result) == 1
        assert "Hypothetical" in result[0]


class TestQueryCache:
    """Tests for query caching."""
    
    def test_memory_cache_set_get(self):
        """Test in-memory cache works correctly."""
        from llmhive.app.knowledge.retrieval_engine import QueryCache, RetrievedDocument
        
        cache = QueryCache(redis_url=None, ttl_seconds=3600)
        
        docs = [
            RetrievedDocument(content="Test content", score=0.9, doc_id="1"),
        ]
        
        cache.set("test query", docs, config_hash="abc")
        result = cache.get("test query", config_hash="abc")
        
        assert result is not None
        assert len(result) == 1
        assert result[0].content == "Test content"
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        from llmhive.app.knowledge.retrieval_engine import QueryCache
        
        cache = QueryCache(redis_url=None)
        
        result = cache.get("nonexistent query", config_hash="abc")
        
        assert result is None


class TestContextValidation:
    """Tests for RAG context validation."""
    
    def test_validate_relevant_context(self):
        """Test validation passes for relevant context."""
        from llmhive.app.knowledge.retrieval_engine import validate_rag_context, RetrievedDocument
        
        docs = [
            RetrievedDocument(content="Machine learning is a subset of artificial intelligence", score=0.9, doc_id="1"),
        ]
        
        is_valid, filtered, message = validate_rag_context(
            "What is machine learning?",
            docs,
            min_term_overlap=0.2,
        )
        
        assert is_valid
        assert len(filtered) == 1
    
    def test_validate_irrelevant_context(self):
        """Test validation filters irrelevant context."""
        from llmhive.app.knowledge.retrieval_engine import validate_rag_context, RetrievedDocument
        
        docs = [
            RetrievedDocument(content="The weather is sunny today", score=0.9, doc_id="1"),
        ]
        
        is_valid, filtered, message = validate_rag_context(
            "What is machine learning?",
            docs,
            min_term_overlap=0.5,  # High threshold
        )
        
        assert not is_valid or len(filtered) < len(docs)


class TestQueryRouter:
    """Tests for query routing."""
    
    def test_factoid_routing(self):
        """Test factoid questions are routed correctly."""
        from llmhive.app.knowledge.query_router import QueryRouter, QueryRoute
        
        router = QueryRouter()
        
        decision = router.route("Who discovered penicillin?")
        
        assert decision.route == QueryRoute.FACTOID_FAST
        assert decision.skip_clarification
    
    def test_tool_required_routing(self):
        """Test tool-requiring queries are detected."""
        from llmhive.app.knowledge.query_router import QueryRouter, QueryRoute
        
        router = QueryRouter()
        
        decision = router.route("What is the current price of Bitcoin?")
        
        assert decision.route == QueryRoute.TOOL_REQUIRED
        assert "web_search" in decision.suggested_tools
    
    def test_complex_routing(self):
        """Test complex queries trigger multi-hop."""
        from llmhive.app.knowledge.query_router import QueryRouter, QueryRoute
        
        router = QueryRouter()
        
        decision = router.route(
            "Analyze the pros and cons of remote work, "
            "considering productivity, mental health, and cost."
        )
        
        assert decision.route == QueryRoute.COMPLEX_MULTIHOP
        assert decision.use_multihop
    
    def test_ambiguous_routing(self):
        """Test ambiguous queries request clarification."""
        from llmhive.app.knowledge.query_router import QueryRouter, QueryRoute
        
        router = QueryRouter()
        
        decision = router.route("Tell me about it")
        
        assert decision.route == QueryRoute.CLARIFICATION
        assert not decision.skip_clarification


class TestRetrievalEngine:
    """Integration tests for the full retrieval engine."""
    
    @pytest.mark.asyncio
    async def test_retrieve_with_semantic_search(self):
        """Test retrieval with semantic search function."""
        from llmhive.app.knowledge.retrieval_engine import RetrievalEngine, RetrievalConfig
        
        mock_search = AsyncMock(return_value=[
            {"content": "Test document", "score": 0.9, "id": "1"},
        ])
        
        config = RetrievalConfig(enable_reranking=False, enable_hyde=False)
        engine = RetrievalEngine(
            semantic_search_fn=mock_search,
            config=config,
        )
        
        result = await engine.retrieve("test query", user_id="user1")
        
        assert len(result.documents) > 0
        mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retrieve_uses_cache(self):
        """Test that repeated queries use cache."""
        from llmhive.app.knowledge.retrieval_engine import RetrievalEngine, RetrievalConfig
        
        mock_search = AsyncMock(return_value=[
            {"content": "Test document", "score": 0.9, "id": "1"},
        ])
        
        config = RetrievalConfig(enable_cache=True, enable_reranking=False, enable_hyde=False)
        engine = RetrievalEngine(semantic_search_fn=mock_search, config=config)
        
        # First call
        result1 = await engine.retrieve("test query", user_id="user1")
        assert not result1.cache_hit
        
        # Second call should hit cache
        result2 = await engine.retrieve("test query", user_id="user1")
        assert result2.cache_hit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

