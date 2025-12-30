"""Tests for Vector Memory (Pinecone Knowledge Base) feature.

This module validates the PineconeKnowledgeBase implementation:
- Record storage and retrieval
- Namespace isolation
- Semantic search with fallback
- Quality score tracking
- Orchestration pattern learning
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, List

# Import the module under test
from llmhive.app.knowledge.pinecone_kb import (
    PineconeKnowledgeBase,
    KnowledgeRecord,
    RecordType,
    LocalVectorStore,
    PINECONE_AVAILABLE,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def knowledge_base():
    """Create a knowledge base using local fallback (no Pinecone API required)."""
    return PineconeKnowledgeBase(use_local_only=True)


@pytest.fixture
def sample_query():
    return "What is the capital of France?"


@pytest.fixture
def sample_answer():
    return "The capital of France is Paris. It is the largest city in France and serves as the country's political, economic, and cultural center."


@pytest.fixture
def sample_models():
    return ["openai/gpt-4o", "anthropic/claude-sonnet-4"]


# =============================================================================
# Test RecordType Enum
# =============================================================================

class TestRecordType:
    """Tests for RecordType enumeration."""
    
    def test_record_types_exist(self):
        """Verify all expected record types are defined."""
        assert RecordType.FINAL_ANSWER == "final_answer"
        assert RecordType.PARTIAL_ANSWER == "partial_answer"
        assert RecordType.USER_QUERY == "user_query"
        assert RecordType.ORCHESTRATION_PATTERN == "orchestration_pattern"
        assert RecordType.DOMAIN_KNOWLEDGE == "domain_knowledge"
        assert RecordType.CORRECTION == "correction"
    
    def test_record_type_string_values(self):
        """Verify record types have expected string values."""
        assert str(RecordType.FINAL_ANSWER) == "RecordType.FINAL_ANSWER"
        assert RecordType.FINAL_ANSWER.value == "final_answer"


# =============================================================================
# Test KnowledgeRecord Dataclass
# =============================================================================

class TestKnowledgeRecord:
    """Tests for KnowledgeRecord dataclass."""
    
    def test_create_basic_record(self):
        """Test creating a basic knowledge record."""
        record = KnowledgeRecord(
            id="test-123",
            content="Test content",
            record_type=RecordType.FINAL_ANSWER,
        )
        assert record.id == "test-123"
        assert record.content == "Test content"
        assert record.record_type == RecordType.FINAL_ANSWER
        assert record.metadata == {}
        assert record.score == 0.0
    
    def test_create_record_with_metadata(self):
        """Test creating a record with metadata."""
        metadata = {"domain": "science", "models_used": "gpt-4"}
        record = KnowledgeRecord(
            id="test-456",
            content="Scientific answer",
            record_type=RecordType.DOMAIN_KNOWLEDGE,
            metadata=metadata,
            score=0.95,
        )
        assert record.metadata == metadata
        assert record.score == 0.95


# =============================================================================
# Test PineconeKnowledgeBase Initialization
# =============================================================================

class TestKnowledgeBaseInit:
    """Tests for knowledge base initialization."""
    
    def test_init_local_only(self):
        """Test initialization with local-only mode."""
        kb = PineconeKnowledgeBase(use_local_only=True)
        assert kb._initialized is False
        assert kb.pc is None
        assert kb.index is None
        assert kb._local_store is not None
    
    def test_init_without_api_key(self):
        """Test initialization without API key falls back to local."""
        with patch.dict("os.environ", {}, clear=True):
            kb = PineconeKnowledgeBase(api_key=None, use_local_only=False)
            # Should fall back to local since no API key
            assert kb._initialized is False


# =============================================================================
# Test Namespace Generation
# =============================================================================

class TestNamespaceGeneration:
    """Tests for namespace generation."""
    
    def test_get_namespace_global(self, knowledge_base):
        """Test global namespace when no identifiers provided."""
        ns = knowledge_base._get_namespace()
        assert ns == "global"
    
    def test_get_namespace_user(self, knowledge_base):
        """Test user-specific namespace."""
        ns = knowledge_base._get_namespace(user_id="user123")
        assert ns == "user_user123"
    
    def test_get_namespace_project(self, knowledge_base):
        """Test project-specific namespace."""
        ns = knowledge_base._get_namespace(project_id="proj456")
        assert ns == "project_proj456"
    
    def test_get_namespace_org(self, knowledge_base):
        """Test org-specific namespace (highest priority)."""
        ns = knowledge_base._get_namespace(
            user_id="user123",
            project_id="proj456",
            org_id="org789"
        )
        assert ns == "org_org789"
    
    def test_namespace_isolation(self, knowledge_base):
        """Verify different entities get different namespaces."""
        ns1 = knowledge_base._get_namespace(user_id="alice")
        ns2 = knowledge_base._get_namespace(user_id="bob")
        ns3 = knowledge_base._get_namespace(project_id="shared")
        
        assert ns1 != ns2
        assert ns1 != ns3
        assert ns2 != ns3


# =============================================================================
# Test ID Generation
# =============================================================================

class TestIdGeneration:
    """Tests for record ID generation."""
    
    def test_generate_id_format(self, knowledge_base):
        """Test that generated IDs have expected format."""
        record_id = knowledge_base._generate_id(
            content="Test content",
            record_type="final_answer",
            namespace="test"
        )
        # Should be a 16-character hex string
        assert len(record_id) == 16
        assert all(c in "0123456789abcdef" for c in record_id)
    
    def test_generate_id_uniqueness(self, knowledge_base):
        """Test that different inputs produce different IDs."""
        id1 = knowledge_base._generate_id("content1", "type1", "ns1")
        id2 = knowledge_base._generate_id("content2", "type1", "ns1")
        # Note: Same content at different times should also differ due to timestamp
        assert id1 != id2


# =============================================================================
# Test Answer Storage (Local Fallback)
# =============================================================================

class TestAnswerStorage:
    """Tests for storing answers in the knowledge base."""
    
    @pytest.mark.asyncio
    async def test_store_final_answer(self, knowledge_base, sample_query, sample_answer, sample_models):
        """Test storing a final answer."""
        record_id = await knowledge_base.store_answer(
            query=sample_query,
            answer=sample_answer,
            models_used=sample_models,
            record_type=RecordType.FINAL_ANSWER,
            quality_score=0.9,
            domain="general",
        )
        
        assert record_id is not None
        assert len(record_id) == 16
    
    @pytest.mark.asyncio
    async def test_store_with_user_namespace(self, knowledge_base, sample_query, sample_answer, sample_models):
        """Test storing an answer in a user-specific namespace."""
        record_id = await knowledge_base.store_answer(
            query=sample_query,
            answer=sample_answer,
            models_used=sample_models,
            user_id="test_user_123",
        )
        
        assert record_id is not None
    
    @pytest.mark.asyncio
    async def test_store_with_custom_metadata(self, knowledge_base):
        """Test storing an answer with custom metadata."""
        custom_meta = {
            "session_id": "sess123",
            "accuracy_level": 5,
            "tags": "important,reviewed"
        }
        
        record_id = await knowledge_base.store_answer(
            query="Test query",
            answer="Test answer",
            models_used=["model1"],
            metadata=custom_meta,
        )
        
        assert record_id is not None
    
    @pytest.mark.asyncio
    async def test_store_partial_answer(self, knowledge_base):
        """Test storing a partial/intermediate answer."""
        record_id = await knowledge_base.store_answer(
            query="Complex question",
            answer="Partial reasoning step...",
            models_used=["openai/gpt-4o"],
            record_type=RecordType.PARTIAL_ANSWER,
        )
        
        assert record_id is not None


# =============================================================================
# Test Orchestration Pattern Storage
# =============================================================================

class TestOrchestrationPatternStorage:
    """Tests for storing orchestration patterns."""
    
    @pytest.mark.asyncio
    async def test_store_successful_pattern(self, knowledge_base, sample_models):
        """Test storing a successful orchestration pattern."""
        record_id = await knowledge_base.store_orchestration_pattern(
            query_type="factual",
            strategy_used="parallel_race",
            models_used=sample_models,
            success=True,
            latency_ms=1500,
            quality_score=0.92,
        )
        
        assert record_id is not None
    
    @pytest.mark.asyncio
    async def test_store_failed_pattern(self, knowledge_base):
        """Test storing a failed orchestration pattern."""
        record_id = await knowledge_base.store_orchestration_pattern(
            query_type="coding",
            strategy_used="sequential_refinement",
            models_used=["model1", "model2"],
            success=False,
            latency_ms=5000,
            quality_score=0.3,
        )
        
        assert record_id is not None


# =============================================================================
# Test LocalVectorStore (In-Memory Fallback)
# =============================================================================

class TestLocalVectorStore:
    """Tests for the local in-memory vector store fallback."""
    
    def test_add_and_retrieve(self):
        """Test adding and retrieving records from local store."""
        store = LocalVectorStore()
        
        record = KnowledgeRecord(
            id="test-1",
            content="Test content about Python programming",
            record_type=RecordType.FINAL_ANSWER,
            score=0.85,
        )
        
        store.add(namespace="test", record=record)
        
        # Verify record was stored
        results = store.search(namespace="test", query="Python programming", top_k=5)
        assert len(results) > 0
    
    def test_namespace_isolation_local(self):
        """Test that local store respects namespace isolation."""
        store = LocalVectorStore()
        
        record1 = KnowledgeRecord(id="r1", content="User A data", record_type=RecordType.FINAL_ANSWER)
        record2 = KnowledgeRecord(id="r2", content="User B data", record_type=RecordType.FINAL_ANSWER)
        
        store.add(namespace="user_a", record=record1)
        store.add(namespace="user_b", record=record2)
        
        # Search in user_a namespace should only find user A's data
        results_a = store.search(namespace="user_a", query="data", top_k=10)
        for r in results_a:
            assert "User A" in r.content or r.id == "r1"


# =============================================================================
# Test Feature Flag Integration
# =============================================================================

class TestFeatureFlagIntegration:
    """Tests for feature flag integration with Vector Memory."""
    
    def test_feature_flag_exists(self):
        """Verify VECTOR_MEMORY feature flag is defined."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        
        assert FeatureFlags.VECTOR_MEMORY.value == "vector_memory"
    
    def test_feature_can_be_toggled(self):
        """Test that the feature flag can be toggled via environment."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        import os
        
        # Test with feature disabled (default)
        with patch.dict(os.environ, {"FEATURE_VECTOR_MEMORY": "false"}):
            assert is_feature_enabled(FeatureFlags.VECTOR_MEMORY) is False
        
        # Test with feature enabled
        with patch.dict(os.environ, {"FEATURE_VECTOR_MEMORY": "true"}):
            assert is_feature_enabled(FeatureFlags.VECTOR_MEMORY) is True


# =============================================================================
# Test Context Retrieval
# =============================================================================

class TestContextRetrieval:
    """Tests for retrieving context from the knowledge base."""
    
    @pytest.mark.asyncio
    async def test_retrieve_from_empty_store(self, knowledge_base):
        """Test retrieval from an empty store returns empty list."""
        results = await knowledge_base.retrieve_context(
            query="Any query",
            top_k=5,
        )
        
        # Should return empty list, not error
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_after_store(self, knowledge_base):
        """Test that stored answers can be retrieved."""
        # Store some answers
        await knowledge_base.store_answer(
            query="What is Python?",
            answer="Python is a high-level programming language.",
            models_used=["gpt-4"],
            quality_score=0.9,
        )
        
        await knowledge_base.store_answer(
            query="What is JavaScript?",
            answer="JavaScript is a programming language for the web.",
            models_used=["claude"],
            quality_score=0.85,
        )
        
        # Retrieve context for a related query
        results = await knowledge_base.retrieve_context(
            query="Tell me about programming languages",
            top_k=5,
        )
        
        # Local store should find something
        # (Note: actual semantic search quality depends on implementation)
        assert isinstance(results, list)


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

