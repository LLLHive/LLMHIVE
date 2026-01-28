"""
Sync enriched MODEL_PROFILES to Pinecone ModelKnowledgeStore.

This script takes the rich ModelProfile data from model_intelligence.py
and stores it in Pinecone for semantic search by the orchestrator.
"""
import asyncio
import os
import sys

# Add the llmhive package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'llmhive', 'src'))

async def sync_profiles():
    """Sync all MODEL_PROFILES to Pinecone."""
    from llmhive.app.knowledge.model_intelligence import MODEL_PROFILES
    from llmhive.app.knowledge.model_knowledge_store import (
        ModelKnowledgeStore,
        ModelProfile as StoreModelProfile,
    )
    
    store = ModelKnowledgeStore()
    
    if not store._initialized:
        print("⚠️  Pinecone not available - skipping sync")
        print("   This is expected in local development.")
        print("   Profiles will sync automatically when deployed.")
        return
    
    print(f"Found {len(MODEL_PROFILES)} profiles to sync...")
    
    synced = 0
    for model_id, profile in MODEL_PROFILES.items():
        # Convert to store format
        store_profile = StoreModelProfile(
            model_id=profile.model_id,
            model_name=profile.display_name,
            provider=profile.provider,
            reasoning_score=profile.reasoning_score,
            coding_score=profile.coding_score,
            creative_score=profile.creative_score,
            accuracy_score=profile.factual_score,
            speed_score=int(profile.latency.tokens_per_second) if profile.latency else 50,
            cost_efficiency=100 if profile.costs.input_per_million == 0 else int(max(0, 100 - profile.costs.input_per_million * 5)),
            context_length=profile.context_window,
            supports_tools=profile.supports_tools,
            supports_vision=profile.supports_vision,
            is_reasoning_model=bool(profile.reasoning_capabilities),
            chain_of_thought=profile.can_be_hacked_to_reason or (profile.reasoning_score > 85),
            self_verification=profile.reasoning_score > 90,
            strengths=profile.strengths,
            weaknesses=profile.weaknesses,
            best_for=profile.best_for,
            avoid_for=profile.avoid_for,
            source="model_intelligence.py",
        )
        
        result = await store.store_model_profile(store_profile)
        if result:
            synced += 1
            print(f"  ✅ {profile.display_name}")
        else:
            print(f"  ❌ Failed: {profile.display_name}")
    
    print(f"\n✅ Synced {synced}/{len(MODEL_PROFILES)} profiles to Pinecone")

if __name__ == "__main__":
    asyncio.run(sync_profiles())
