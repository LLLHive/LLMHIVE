#!/usr/bin/env python3
"""
Sync enriched model research to the Model Knowledge Store.

This script loads the researched model characteristics and updates
the orchestrator's knowledge base with the latest information about
free models and their capabilities.

Usage:
    python scripts/sync_model_research.py
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "llmhive" / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Try to import model knowledge store
try:
    from llmhive.app.knowledge.model_knowledge_store import (
        ModelKnowledgeStore,
        ModelProfile,
        get_model_knowledge_store,
    )
    KNOWLEDGE_STORE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_STORE_AVAILABLE = False
    logger.warning("Model knowledge store not available locally")


async def sync_research_to_knowledge_store() -> dict:
    """Sync the enriched model research to the knowledge store."""
    
    # Load the research file
    research_file = Path(__file__).parent.parent / "model_cache" / "enriched" / "FREE_MODELS_RESEARCH_20260127.json"
    
    if not research_file.exists():
        logger.error(f"Research file not found: {research_file}")
        return {"success": False, "error": "Research file not found"}
    
    with open(research_file) as f:
        research_data = json.load(f)
    
    models_research = research_data.get("free_models_research", {})
    logger.info(f"Loaded research for {len(models_research)} free models")
    
    if not KNOWLEDGE_STORE_AVAILABLE:
        # Save to local file for production sync
        output_file = Path(__file__).parent.parent / "model_cache" / "model_profiles_for_sync.json"
        
        profiles = []
        for model_id, data in models_research.items():
            profile = {
                "model_id": model_id,
                "model_name": data.get("display_name", model_id),
                "provider": data.get("provider", model_id.split("/")[0] if "/" in model_id else "unknown"),
                "context_length": data.get("context_length", 128000),
                "parameters_total": data.get("parameters_total", "unknown"),
                "parameters_active": data.get("parameters_active", "unknown"),
                "architecture": data.get("architecture", "transformer"),
                "is_reasoning_model": "reasoning" in data.get("best_for", []),
                "is_coding_model": "coding" in data.get("best_for", []),
                "multimodal": data.get("multimodal", False),
                "open_source": data.get("open_source", True),
                "strengths": data.get("strengths", []),
                "best_for": data.get("best_for", []),
                "orchestrator_notes": data.get("orchestrator_notes", ""),
                "benchmark_estimates": data.get("benchmark_estimates", {}),
                "updated_at": datetime.now().isoformat(),
            }
            profiles.append(profile)
        
        with open(output_file, "w") as f:
            json.dump({
                "sync_date": datetime.now().isoformat(),
                "profiles_count": len(profiles),
                "profiles": profiles,
            }, f, indent=2)
        
        logger.info(f"Saved {len(profiles)} model profiles to {output_file}")
        return {
            "success": True,
            "profiles_saved": len(profiles),
            "output_file": str(output_file),
        }
    
    # If knowledge store is available, sync directly
    store = get_model_knowledge_store()
    synced_count = 0
    errors = []
    
    for model_id, data in models_research.items():
        try:
            profile = ModelProfile(
                model_id=model_id,
                model_name=data.get("display_name", model_id),
                provider=data.get("provider", model_id.split("/")[0] if "/" in model_id else "unknown"),
                context_length=data.get("context_length", 128000),
                is_reasoning_model="reasoning" in data.get("best_for", []),
                chain_of_thought="reasoning" in data.get("best_for", []),
                supports_vision=data.get("multimodal", False) or data.get("vision", False),
                strengths=data.get("strengths", []),
                best_for=data.get("best_for", []),
                source="weekly_research",
            )
            
            await store.store_model_profile(profile)
            synced_count += 1
            logger.info(f"  ✓ Synced: {model_id}")
            
        except Exception as e:
            errors.append(f"{model_id}: {e}")
            logger.error(f"  ✗ Failed to sync {model_id}: {e}")
    
    return {
        "success": len(errors) == 0,
        "synced_count": synced_count,
        "errors": errors,
    }


async def main():
    """Main entry point."""
    print("=" * 60)
    print("🔄 SYNCING MODEL RESEARCH TO KNOWLEDGE STORE")
    print("=" * 60)
    print()
    
    result = await sync_research_to_knowledge_store()
    
    print()
    print("=" * 60)
    if result.get("success"):
        print("✅ SYNC COMPLETE")
        print(f"   Profiles processed: {result.get('synced_count', result.get('profiles_saved', 0))}")
    else:
        print("⚠️ SYNC COMPLETED WITH ISSUES")
        for error in result.get("errors", []):
            print(f"   - {error}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
