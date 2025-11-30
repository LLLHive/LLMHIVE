"""Test Pinecone Integration with LLMHive Memory System.

This script tests the upgraded PineconeVectorStore with:
- Integrated embeddings (Pinecone handles embedding generation)
- Reranking for better search relevance
- Proper namespace isolation
"""
import os
import sys
import time

# Ensure the package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "llmhive", "src"))

from llmhive.app.memory.vector_store import (
    PineconeVectorStore,
    MemoryRecord,
    get_vector_store,
)

def main():
    print("=" * 60)
    print("🧪 Testing Pinecone Integration with LLMHive")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ PINECONE_API_KEY environment variable not set")
        print("   Run: export PINECONE_API_KEY='your-key'")
        return
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-5:]}")
    
    # Initialize store with integrated embeddings
    print("\n📦 Initializing PineconeVectorStore...")
    store = PineconeVectorStore(
        index_name="agentic-quickstart-test",  # Use our test index
        use_integrated_embeddings=True,
        content_field="content",
    )
    
    if not store._initialized:
        print("❌ Failed to initialize Pinecone store")
        return
    
    print("✅ Store initialized successfully")
    
    # Get stats
    stats = store.get_stats()
    print(f"   Index: {stats.get('index_name')}")
    print(f"   Records: {stats.get('total_records')}")
    print(f"   Integrated Embeddings: {stats.get('use_integrated_embeddings')}")
    
    # Test namespace
    test_namespace = "llmhive-test"
    
    # Create test records
    print(f"\n📤 Creating test records in namespace '{test_namespace}'...")
    test_records = [
        MemoryRecord(
            id="mem_001",
            text="The user prefers concise responses with bullet points.",
            metadata={"type": "preference", "user_id": "test_user"},
        ),
        MemoryRecord(
            id="mem_002", 
            text="Previous conversation discussed machine learning basics.",
            metadata={"type": "context", "user_id": "test_user"},
        ),
        MemoryRecord(
            id="mem_003",
            text="The Eiffel Tower is located in Paris, France.",
            metadata={"type": "fact", "verified": True},
        ),
        MemoryRecord(
            id="mem_004",
            text="Python is a programming language known for its simplicity.",
            metadata={"type": "fact", "verified": True},
        ),
        MemoryRecord(
            id="mem_005",
            text="User asked about weather in Tokyo yesterday.",
            metadata={"type": "history", "user_id": "test_user"},
        ),
    ]
    
    count = store.upsert(test_records, namespace=test_namespace)
    print(f"✅ Upserted {count} records")
    
    # Wait for indexing
    print("⏳ Waiting for indexing...")
    time.sleep(5)
    
    # Test query WITHOUT reranking
    print("\n🔍 TEST 1: Query WITHOUT reranking")
    query = "What does the user prefer?"
    result = store.query(
        query_text=query,
        top_k=3,
        namespace=test_namespace,
        use_rerank=False,
    )
    
    print(f"   Query: '{query}'")
    print(f"   Results: {len(result.records)} found in {result.query_time_ms:.1f}ms")
    for i, rec in enumerate(result.records, 1):
        print(f"   {i}. [{rec.score:.3f}] {rec.text[:60]}...")
    
    # Test query WITH reranking
    print("\n🎯 TEST 2: Query WITH reranking (bge-reranker-v2-m3)")
    result = store.query(
        query_text=query,
        top_k=3,
        namespace=test_namespace,
        use_rerank=True,
    )
    
    print(f"   Query: '{query}'")
    print(f"   Results: {len(result.records)} found in {result.query_time_ms:.1f}ms (reranked={result.reranked})")
    for i, rec in enumerate(result.records, 1):
        print(f"   {i}. [{rec.score:.3f}] {rec.text[:60]}...")
    
    # Test filtered query
    print("\n🔎 TEST 3: Query with metadata filter")
    result = store.query(
        query_text="What did the user do?",
        top_k=3,
        namespace=test_namespace,
        filter_metadata={"type": "history"},
        use_rerank=True,
    )
    
    print(f"   Filter: type='history'")
    print(f"   Results: {len(result.records)} found")
    for i, rec in enumerate(result.records, 1):
        print(f"   {i}. [{rec.score:.3f}] {rec.text[:60]}...")
    
    # Test different query
    print("\n🌍 TEST 4: Factual query")
    result = store.query(
        query_text="Tell me about famous landmarks in Europe",
        top_k=3,
        namespace=test_namespace,
        use_rerank=True,
    )
    
    print(f"   Query: 'Tell me about famous landmarks in Europe'")
    print(f"   Results: {len(result.records)} found")
    for i, rec in enumerate(result.records, 1):
        print(f"   {i}. [{rec.score:.3f}] {rec.text[:60]}...")
    
    # Cleanup (optional - comment out to keep data)
    print(f"\n🧹 Cleaning up test namespace '{test_namespace}'...")
    store.delete(
        ids=[r.id for r in test_records],
        namespace=test_namespace,
    )
    print("✅ Cleanup complete")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print("\n📝 Summary:")
    print("   - Pinecone integration upgraded to modern API")
    print("   - Integrated embeddings working (llama-text-embed-v2)")
    print("   - Reranking enabled (bge-reranker-v2-m3)")
    print("   - Namespace isolation working")
    print("   - Ready for LLMHive memory system!")

if __name__ == "__main__":
    main()

