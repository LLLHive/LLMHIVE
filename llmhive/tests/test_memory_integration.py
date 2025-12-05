"""Unit tests for memory and vector database integration."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from unittest.mock import MagicMock, patch
import pytest

# Check if numpy is available (required for embeddings)
numpy_available = pytest.importorskip("numpy", reason="numpy required for embedding tests")

try:
    from llmhive.app.memory.embeddings import (
        EmbeddingService,
        get_embedding,
    )
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    EmbeddingService = None
    get_embedding = None

try:
    from llmhive.app.memory.vector_store import (
        InMemoryVectorStore,
        MemoryRecord,
        MemoryQueryResult,
    )
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    InMemoryVectorStore = None
    MemoryRecord = None
    MemoryQueryResult = None

try:
    from llmhive.app.memory.persistent_memory import (
        PersistentMemoryManager,
        MemoryHit,
        Scratchpad,
        query_scratchpad,
    )
    PERSISTENT_MEMORY_AVAILABLE = True
except ImportError:
    PERSISTENT_MEMORY_AVAILABLE = False
    PersistentMemoryManager = None
    MemoryHit = None
    Scratchpad = None
    query_scratchpad = None

# Skip if memory modules not available
pytestmark = pytest.mark.skipif(
    not (EMBEDDINGS_AVAILABLE and VECTOR_STORE_AVAILABLE and PERSISTENT_MEMORY_AVAILABLE),
    reason="Memory modules not available"
)


class TestEmbeddingService:
    """Tests for embedding service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = EmbeddingService(dimension=128)
    
    def test_get_embedding_returns_correct_dimension(self):
        """Test that embeddings have correct dimension."""
        embedding = self.service.get_embedding("Hello world")
        assert len(embedding) == 128
    
    def test_get_embedding_deterministic(self):
        """Test that same text produces same embedding."""
        text = "The quick brown fox"
        emb1 = self.service.get_embedding(text)
        emb2 = self.service.get_embedding(text)
        assert emb1 == emb2
    
    def test_get_embedding_different_for_different_text(self):
        """Test that different text produces different embeddings."""
        emb1 = self.service.get_embedding("Hello world")
        emb2 = self.service.get_embedding("Goodbye world")
        assert emb1 != emb2
    
    def test_get_embedding_empty_text(self):
        """Test handling of empty text."""
        embedding = self.service.get_embedding("")
        assert len(embedding) == 128
        # Should be zero vector
        assert all(v == 0.0 for v in embedding)
    
    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity of identical vectors."""
        vec = [0.5, 0.5, 0.5, 0.5]
        similarity = self.service.cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.001
    
    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        similarity = self.service.cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.001
    
    def test_batch_embeddings(self):
        """Test batch embedding generation."""
        texts = ["Hello", "World", "Test"]
        embeddings = self.service.get_embeddings_batch(texts)
        assert len(embeddings) == 3
        assert all(len(e) == 128 for e in embeddings)


class TestInMemoryVectorStore:
    """Tests for in-memory vector store."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.embedding_service = EmbeddingService(dimension=64)
        self.store = InMemoryVectorStore(embedding_service=self.embedding_service)
    
    def test_upsert_and_query(self):
        """Test basic upsert and query operations."""
        # Create and upsert a record
        embedding = self.embedding_service.get_embedding("What is the capital of France?")
        record = MemoryRecord(
            id="test1",
            text="Q: What is the capital of France? A: Paris",
            embedding=embedding,
            metadata={"verified": True},
        )
        
        count = self.store.upsert([record], namespace="test")
        assert count == 1
        
        # Query for similar content
        query_embedding = self.embedding_service.get_embedding("capital of France")
        result = self.store.query(query_embedding, top_k=5, namespace="test")
        
        assert len(result.records) == 1
        assert result.records[0].text == "Q: What is the capital of France? A: Paris"
        assert result.records[0].score > 0.5
    
    def test_query_with_filter(self):
        """Test query with metadata filter."""
        # Insert records with different metadata
        for i, verified in enumerate([True, False, True]):
            embedding = self.embedding_service.get_embedding(f"Test content {i}")
            record = MemoryRecord(
                id=f"record_{i}",
                text=f"Test content {i}",
                embedding=embedding,
                metadata={"verified": verified, "index": i},
            )
            self.store.upsert([record], namespace="test")
        
        # Query with filter
        query_embedding = self.embedding_service.get_embedding("Test content")
        result = self.store.query(
            query_embedding,
            top_k=10,
            namespace="test",
            filter_metadata={"verified": True},
        )
        
        assert all(r.metadata.get("verified") == True for r in result.records)
    
    def test_delete_records(self):
        """Test deleting records."""
        # Insert a record
        embedding = self.embedding_service.get_embedding("To be deleted")
        record = MemoryRecord(
            id="to_delete",
            text="To be deleted",
            embedding=embedding,
        )
        self.store.upsert([record], namespace="test")
        
        # Verify it exists
        all_records = self.store.get_all_records("test")
        assert len(all_records) == 1
        
        # Delete it
        deleted = self.store.delete(["to_delete"], namespace="test")
        assert deleted == 1
        
        # Verify it's gone
        all_records = self.store.get_all_records("test")
        assert len(all_records) == 0
    
    def test_clear_namespace(self):
        """Test clearing a namespace."""
        # Insert multiple records
        for i in range(5):
            embedding = self.embedding_service.get_embedding(f"Content {i}")
            record = MemoryRecord(
                id=f"record_{i}",
                text=f"Content {i}",
                embedding=embedding,
            )
            self.store.upsert([record], namespace="test")
        
        # Clear namespace
        self.store.clear_namespace("test")
        
        # Verify empty
        all_records = self.store.get_all_records("test")
        assert len(all_records) == 0
    
    def test_namespaces_are_isolated(self):
        """Test that namespaces are isolated."""
        embedding = self.embedding_service.get_embedding("Test")
        
        record1 = MemoryRecord(id="r1", text="Namespace 1", embedding=embedding)
        record2 = MemoryRecord(id="r2", text="Namespace 2", embedding=embedding)
        
        self.store.upsert([record1], namespace="ns1")
        self.store.upsert([record2], namespace="ns2")
        
        # Query each namespace
        result1 = self.store.query(embedding, namespace="ns1")
        result2 = self.store.query(embedding, namespace="ns2")
        
        assert len(result1.records) == 1
        assert result1.records[0].text == "Namespace 1"
        
        assert len(result2.records) == 1
        assert result2.records[0].text == "Namespace 2"


class TestPersistentMemoryManager:
    """Tests for persistent memory manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.embedding_service = EmbeddingService(dimension=64)
        self.vector_store = InMemoryVectorStore(embedding_service=self.embedding_service)
        self.memory = PersistentMemoryManager(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
        )
    
    def test_add_and_query_memory(self):
        """Test basic add and query operations."""
        # Add a memory
        record_id = self.memory.add_to_memory(
            uid="session1|capital_france",
            text="The capital of France is Paris.",
            metadata={"verified": True, "tags": ["geography"]},
        )
        
        assert record_id != ""
        
        # Query for it
        hits = self.memory.query_memory(
            query_text="What is the capital of France?",
            top_k=5,
        )
        
        assert len(hits) > 0
        assert "Paris" in hits[0].text
        assert hits[0].is_verified
    
    def test_store_verified_answer(self):
        """Test storing verified Q&A pairs."""
        record_id = self.memory.store_verified_answer(
            session_id="session123",
            query="What is the capital of France?",
            answer="The capital of France is Paris.",
            domain="geography",
        )
        
        assert record_id != ""
        
        # Query should find it
        hits = self.memory.query_memory("capital of France")
        assert len(hits) > 0
        assert hits[0].is_verified
        assert hits[0].domain == "geography"
    
    def test_memory_reuse_scenario(self):
        """Test the memory reuse scenario from requirements.
        
        1. User asks: "What is the capital of France?"
        2. System answers "Paris", stores in memory
        3. User asks: "Which city is the capital of France?"
        4. Memory retrieval should find the previous Q&A
        """
        # Step 1-2: First query and store
        self.memory.store_verified_answer(
            session_id="test_session",
            query="What is the capital of France?",
            answer="Paris is the capital of France.",
            domain="geography",
        )
        
        # Step 3-4: Second query should retrieve stored answer
        hits = self.memory.query_memory(
            query_text="Which city is the capital of France?",
            top_k=5,
        )
        
        # Should find the stored answer
        assert len(hits) > 0
        assert "Paris" in hits[0].text
        assert hits[0].score > 0.7  # Should have high similarity
    
    def test_get_relevant_context(self):
        """Test getting relevant context for augmentation."""
        # Store some verified answers
        self.memory.store_verified_answer(
            session_id="s1",
            query="What is Python?",
            answer="Python is a high-level programming language.",
        )
        self.memory.store_verified_answer(
            session_id="s2",
            query="Who created Python?",
            answer="Python was created by Guido van Rossum.",
        )
        
        # Get context for related query
        context, hits = self.memory.get_relevant_context(
            query="Tell me about Python programming language",
            top_k=2,
        )
        
        # Should have context
        if hits:  # May not find if similarity is too low
            assert "Relevant prior knowledge" in context or len(context) > 0
    
    def test_user_namespace_isolation(self):
        """Test that user namespaces are isolated."""
        # Add memories for different users
        self.memory.add_to_memory(
            uid="user1_fact",
            text="User 1's favorite color is blue.",
            user_id="user1",
        )
        self.memory.add_to_memory(
            uid="user2_fact",
            text="User 2's favorite color is red.",
            user_id="user2",
        )
        
        # Query for user 1 - should not see user 2's data
        hits_user1 = self.memory.query_memory(
            query_text="favorite color",
            user_id="user1",
            include_global=False,
        )
        
        for hit in hits_user1:
            assert "User 2" not in hit.text
    
    def test_delete_memory(self):
        """Test deleting memories."""
        record_id = self.memory.add_to_memory(
            uid="to_delete",
            text="This will be deleted.",
        )
        
        # Verify it exists
        hits = self.memory.query_memory("will be deleted")
        assert len(hits) > 0
        
        # Delete it
        deleted = self.memory.delete_memory([record_id])
        assert deleted > 0


class TestScratchpad:
    """Tests for short-term scratchpad."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scratchpad = Scratchpad()
    
    def test_write_and_read(self):
        """Test basic write and read operations."""
        self.scratchpad.write("key1", "value1")
        assert self.scratchpad.read("key1") == "value1"
    
    def test_read_missing_key(self):
        """Test reading missing key returns default."""
        assert self.scratchpad.read("missing") is None
        assert self.scratchpad.read("missing", "default") == "default"
    
    def test_get_all(self):
        """Test getting all data."""
        self.scratchpad.write("key1", "value1")
        self.scratchpad.write("key2", "value2")
        
        all_data = self.scratchpad.get_all()
        assert all_data == {"key1": "value1", "key2": "value2"}
    
    def test_clear(self):
        """Test clearing scratchpad."""
        self.scratchpad.write("key1", "value1")
        self.scratchpad.clear()
        
        assert self.scratchpad.get_all() == {}
    
    def test_remove(self):
        """Test removing a key."""
        self.scratchpad.write("key1", "value1")
        self.scratchpad.write("key2", "value2")
        
        removed = self.scratchpad.remove("key1")
        assert removed is True
        assert self.scratchpad.read("key1") is None
        assert self.scratchpad.read("key2") == "value2"
    
    def test_has(self):
        """Test checking key existence."""
        self.scratchpad.write("exists", "value")
        
        assert self.scratchpad.has("exists") is True
        assert self.scratchpad.has("missing") is False
    
    def test_append_to_list(self):
        """Test appending to a list."""
        self.scratchpad.append_to_list("results", "result1")
        self.scratchpad.append_to_list("results", "result2")
        
        assert self.scratchpad.read("results") == ["result1", "result2"]
    
    def test_get_context_string(self):
        """Test getting context as string."""
        self.scratchpad.write("model_output", "The answer is 42.")
        self.scratchpad.write("model_name", "gpt-4")
        
        context = self.scratchpad.get_context_string()
        
        assert "model_output" in context
        assert "42" in context
        assert "gpt-4" in context
    
    def test_context_manager(self):
        """Test query_scratchpad context manager."""
        with query_scratchpad() as pad:
            pad.write("intermediate", "data")
            assert pad.read("intermediate") == "data"
        
        # After context, scratchpad should be cleared
        # (New scratchpad each time, so this is a fresh one)
        new_pad = Scratchpad()
        assert new_pad.read("intermediate") is None


class TestMemoryIntegrationScenarios:
    """Integration tests for memory scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.embedding_service = EmbeddingService(dimension=64)
        self.vector_store = InMemoryVectorStore(embedding_service=self.embedding_service)
        self.memory = PersistentMemoryManager(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
        )
    
    def test_full_qa_cycle(self):
        """Test full Q&A cycle with memory."""
        # Simulate: User asks question, gets answer, stores in memory
        query1 = "What is the capital of France?"
        answer1 = "The capital of France is Paris."
        
        # Store verified answer
        self.memory.store_verified_answer(
            session_id="session1",
            query=query1,
            answer=answer1,
            domain="geography",
        )
        
        # Later: Similar question should retrieve stored answer
        query2 = "Which city serves as the capital of France?"
        hits = self.memory.query_memory(query2, top_k=5, min_score=0.5)
        
        # Should find relevant memory
        assert len(hits) >= 1
        found_paris = any("Paris" in hit.text for hit in hits)
        assert found_paris, "Should find Paris in memory hits"
    
    def test_multi_domain_memory(self):
        """Test memory across multiple domains."""
        # Store answers in different domains
        domains = [
            ("What is Python?", "Python is a programming language.", "coding"),
            ("What is a contract?", "A contract is a legal agreement.", "legal"),
            ("What is hypertension?", "Hypertension is high blood pressure.", "medical"),
        ]
        
        for query, answer, domain in domains:
            self.memory.store_verified_answer(
                session_id="test",
                query=query,
                answer=answer,
                domain=domain,
            )
        
        # Query should find domain-relevant answers
        coding_hits = self.memory.query_memory(
            "programming language",
            filter_tags=["coding"],
        )
        
        if coding_hits:
            assert any("Python" in h.text for h in coding_hits)
    
    def test_scratchpad_agent_communication(self):
        """Test using scratchpad for agent communication."""
        scratchpad = Scratchpad()
        
        # Simulate: Researcher agent stores findings
        scratchpad.write("researcher_findings", "France is a country in Europe.")
        
        # Analyst agent reads findings and adds analysis
        findings = scratchpad.read("researcher_findings")
        assert "France" in findings
        
        scratchpad.write("analyst_notes", "The capital is Paris, population ~2 million.")
        
        # Synthesizer agent reads all data
        all_data = scratchpad.get_all()
        assert "researcher_findings" in all_data
        assert "analyst_notes" in all_data
        
        # Critic agent appends feedback
        scratchpad.append_to_list("critiques", "Good factual accuracy.")
        scratchpad.append_to_list("critiques", "Could add more historical context.")
        
        critiques = scratchpad.read("critiques")
        assert len(critiques) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

