"""Pinecone Quick Test - Semantic Search with Reranking"""
import os
import time

from pinecone import Pinecone

# Initialize Pinecone client
api_key = os.getenv("PINECONE_API_KEY")
if not api_key:
    raise ValueError("PINECONE_API_KEY environment variable not set")

pc = Pinecone(api_key=api_key)

# Sample dataset of factual statements
records = [
    {"_id": "rec1", "content": "The Eiffel Tower was completed in 1889 and stands in Paris, France.", "category": "history"},
    {"_id": "rec2", "content": "Photosynthesis allows plants to convert sunlight into energy.", "category": "science"},
    {"_id": "rec5", "content": "Shakespeare wrote many famous plays, including Hamlet and Macbeth.", "category": "literature"},
    {"_id": "rec7", "content": "The Great Wall of China was built to protect against invasions.", "category": "history"},
    {"_id": "rec15", "content": "Leonardo da Vinci painted the Mona Lisa.", "category": "art"},
    {"_id": "rec17", "content": "The Pyramids of Giza are among the Seven Wonders of the Ancient World.", "category": "history"},
    {"_id": "rec21", "content": "The Statue of Liberty was a gift from France to the United States.", "category": "history"},
    {"_id": "rec26", "content": "Rome was once the center of a vast empire.", "category": "history"},
    {"_id": "rec33", "content": "The violin is a string instrument commonly used in orchestras.", "category": "music"},
    {"_id": "rec38", "content": "The Taj Mahal is a mausoleum built by Emperor Shah Jahan.", "category": "history"},
    {"_id": "rec48", "content": "Vincent van Gogh painted Starry Night.", "category": "art"},
    {"_id": "rec50", "content": "Renewable energy sources include wind, solar, and hydroelectric power.", "category": "energy"},
]

# Target the index
print("🔌 Connecting to index: agentic-quickstart-test")
index = pc.Index("agentic-quickstart-test")

# Upsert records into a namespace
print(f"📤 Upserting {len(records)} records into 'example-namespace'...")
index.upsert_records("example-namespace", records)

# Wait for indexing
print("⏳ Waiting 10 seconds for indexing...")
time.sleep(10)

# View stats
stats = index.describe_index_stats()
print(f"📊 Index stats: {stats.total_record_count} total records")

# Define the query
query = "Famous historical structures and monuments"
print(f"\n🔍 SEARCH 1: Semantic search (without reranking)")
print(f"   Query: '{query}'")

# Search without reranking
results = index.search(
    namespace="example-namespace",
    query={
        "top_k": 10,
        "inputs": {"text": query}
    }
)

print("\n   Results:")
for i, hit in enumerate(results["result"]["hits"][:5], 1):
    print(f"   {i}. [{hit['_score']:.3f}] {hit['fields']['category']}: {hit['fields']['content'][:60]}...")

# Search with reranking
print(f"\n🎯 SEARCH 2: Semantic search WITH reranking (bge-reranker-v2-m3)")
print(f"   Query: '{query}'")

reranked_results = index.search(
    namespace="example-namespace",
    query={
        "top_k": 10,
        "inputs": {"text": query}
    },
    rerank={
        "model": "bge-reranker-v2-m3",
        "top_n": 10,
        "rank_fields": ["content"]
    }
)

print("\n   Results (reranked):")
for i, hit in enumerate(reranked_results["result"]["hits"][:5], 1):
    print(f"   {i}. [{hit['_score']:.3f}] {hit['fields']['category']}: {hit['fields']['content'][:60]}...")

print("\n✅ Quick test completed!")
print("\n📝 Key observation: With reranking, historical structures (Eiffel Tower,")
print("   Pyramids, Taj Mahal, etc.) should rank higher than unrelated content.")
