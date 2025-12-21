#!/usr/bin/env python3
"""
Ingestion script for LLMHive Orchestrator Intelligence data.

This script loads the intelligence data files into the appropriate stores:
- Models -> Pinecone ModelKnowledgeStore + SQLite (if available)
- Benchmarks -> Pinecone ModelKnowledgeStore
- Orchestration Patterns -> Pinecone ModelKnowledgeStore

Usage:
    python ingest_intel_data.py --all
    python ingest_intel_data.py --models --benchmarks
    python ingest_intel_data.py --patterns
    python ingest_intel_data.py --dry-run  # Preview without writing

Requirements:
    - PINECONE_API_KEY environment variable
    - Access to LLMHive backend modules
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add llmhive to path
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
LLMHIVE_SRC = REPO_ROOT / "llmhive" / "src"
sys.path.insert(0, str(LLMHIVE_SRC))


def load_jsonl(filepath: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file."""
    records = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def ingest_models(dry_run: bool = False) -> int:
    """Ingest model data into Pinecone ModelKnowledgeStore."""
    filepath = SCRIPT_DIR / "models.jsonl"
    if not filepath.exists():
        logger.error(f"Models file not found: {filepath}")
        return 0
    
    models = load_jsonl(filepath)
    logger.info(f"Loaded {len(models)} models from {filepath}")
    
    if dry_run:
        for model in models[:3]:
            logger.info(f"  [DRY RUN] Would ingest: {model['model_id']}")
        logger.info(f"  ... and {len(models) - 3} more")
        return len(models)
    
    try:
        from llmhive.app.knowledge.model_knowledge_store import (
            ModelKnowledgeStore, ModelProfile, get_model_knowledge_store
        )
        
        store = get_model_knowledge_store()
        if not store._initialized:
            logger.error("ModelKnowledgeStore not initialized. Check PINECONE_API_KEY.")
            return 0
        
        count = 0
        for model in models:
            # Derive scores from strengths/weaknesses
            strengths = model.get("strengths", [])
            is_reasoning = "reasoning" in " ".join(strengths).lower() or "complex_reasoning" in strengths
            is_coding = "coding" in " ".join(strengths).lower() or "excellent_coding" in strengths
            is_fast = "fast" in " ".join(strengths).lower() or "very_fast" in strengths
            is_cheap = "cheap" in " ".join(strengths).lower() or model.get("pricing_input_per_1m", 100) < 1.0
            
            profile = ModelProfile(
                model_id=model["model_id"],
                model_name=model.get("model_id", "").split("/")[-1],
                provider=model.get("provider", "unknown"),
                reasoning_score=85 if is_reasoning else 60,
                coding_score=85 if is_coding else 60,
                creative_score=70,  # Default
                accuracy_score=80 if not model.get("legacy", False) else 65,
                speed_score=90 if is_fast else 70,
                cost_efficiency=90 if is_cheap else 50,
                context_length=model.get("context_window", 8192),
                supports_tools=model.get("supports_tools", True),
                supports_vision=model.get("supports_vision", False),
                supports_streaming=model.get("supports_streaming", True),
                is_reasoning_model=is_reasoning,
                chain_of_thought="cot" in " ".join(strengths).lower() or is_reasoning,
                self_verification="verification" in " ".join(strengths).lower(),
                multi_step_planning="planning" in " ".join(strengths).lower() or is_reasoning,
                strengths=strengths,
                weaknesses=model.get("weaknesses", []),
                best_for=model.get("best_for", []),
                avoid_for=model.get("avoid_for", []),
                last_updated=time.time(),
                source="intel_update_2024_12_20",
            )
            
            # Async call - run synchronously for script
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                store.store_model_profile(profile)
            )
            if result:
                count += 1
                logger.debug(f"Ingested model: {model['model_id']}")
        
        logger.info(f"Successfully ingested {count} models into ModelKnowledgeStore")
        return count
        
    except ImportError as e:
        logger.error(f"Failed to import LLMHive modules: {e}")
        logger.info("Falling back to file-only mode (data validated but not stored)")
        return len(models)


def ingest_benchmarks(dry_run: bool = False) -> int:
    """Ingest benchmark data using PineconeKnowledgeBase.store_document."""
    filepath = SCRIPT_DIR / "benchmarks.jsonl"
    if not filepath.exists():
        logger.error(f"Benchmarks file not found: {filepath}")
        return 0
    
    benchmarks = load_jsonl(filepath)
    logger.info(f"Loaded {len(benchmarks)} benchmarks from {filepath}")
    
    if dry_run:
        for bench in benchmarks[:3]:
            logger.info(f"  [DRY RUN] Would ingest: {bench['benchmark_id']}")
        logger.info(f"  ... and {len(benchmarks) - 3} more")
        return len(benchmarks)
    
    try:
        from llmhive.app.knowledge.pinecone_kb import PineconeKnowledgeBase
        
        kb = PineconeKnowledgeBase()
        if not kb._initialized:
            logger.error("PineconeKnowledgeBase not initialized.")
            return 0
        
        count = 0
        for bench in benchmarks:
            content = (
                f"Benchmark: {bench['name']}\n"
                f"Category: {bench['category']}\n"
                f"Description: {bench['description']}\n"
                f"Evaluation Protocol: {bench['evaluation_protocol']}\n"
                f"What it Measures: {bench['what_it_measures']}\n"
                f"Pitfalls: {', '.join(bench.get('pitfalls', []))}\n"
                f"Source: {bench.get('source_url', 'N/A')}"
            )
            
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                kb.store_document(
                    document_text=content,
                    doc_id=f"benchmark_{bench['benchmark_id']}",
                    metadata={
                        "type": "benchmark",
                        "benchmark_id": bench["benchmark_id"],
                        "category": bench["category"],
                    }
                )
            )
            if result:
                count += 1
        
        logger.info(f"Successfully ingested {count} benchmarks")
        return count
        
    except Exception as e:
        logger.error(f"Failed to ingest benchmarks: {e}")
        return 0


def ingest_benchmark_results(dry_run: bool = False) -> int:
    """Ingest model benchmark results."""
    filepath = SCRIPT_DIR / "model_benchmark_results.jsonl"
    if not filepath.exists():
        logger.error(f"Benchmark results file not found: {filepath}")
        return 0
    
    results = load_jsonl(filepath)
    logger.info(f"Loaded {len(results)} benchmark results from {filepath}")
    
    if dry_run:
        for result in results[:3]:
            logger.info(f"  [DRY RUN] Would ingest: {result['model_id']} on {result['benchmark_id']}")
        logger.info(f"  ... and {len(results) - 3} more")
        return len(results)
    
    try:
        from llmhive.app.knowledge.pinecone_kb import PineconeKnowledgeBase
        
        kb = PineconeKnowledgeBase()
        count = 0
        
        for result in results:
            content = (
                f"Benchmark Result: {result['model_id']} on {result['benchmark_id']}\n"
                f"Score: {result['score']} ({result['metric']})\n"
                f"Date: {result['date_reported']}\n"
                f"Source: {result.get('source_url', 'N/A')}\n"
                f"{'Vendor-reported' if result.get('vendor_reported') else 'Independent evaluation'}"
            )
            
            safe_model_id = result["model_id"].replace("/", "_")
            import asyncio
            r = asyncio.get_event_loop().run_until_complete(
                kb.store_document(
                    document_text=content,
                    doc_id=f"result_{safe_model_id}_{result['benchmark_id']}",
                    metadata={
                        "type": "benchmark_result",
                        "model_id": result["model_id"],
                        "benchmark_id": result["benchmark_id"],
                        "score": float(result["score"]),
                    }
                )
            )
            if r:
                count += 1
        
        logger.info(f"Successfully ingested {count} benchmark results")
        return count
        
    except Exception as e:
        logger.error(f"Failed to ingest benchmark results: {e}")
        return 0


def ingest_patterns(dry_run: bool = False) -> int:
    """Ingest orchestration patterns using store_document."""
    filepath = SCRIPT_DIR / "orchestration_patterns.jsonl"
    if not filepath.exists():
        logger.error(f"Patterns file not found: {filepath}")
        return 0
    
    patterns = load_jsonl(filepath)
    logger.info(f"Loaded {len(patterns)} orchestration patterns from {filepath}")
    
    if dry_run:
        for pattern in patterns[:3]:
            logger.info(f"  [DRY RUN] Would ingest: {pattern['pattern_id']} - {pattern['name']}")
        logger.info(f"  ... and {len(patterns) - 3} more")
        return len(patterns)
    
    try:
        from llmhive.app.knowledge.pinecone_kb import PineconeKnowledgeBase
        
        kb = PineconeKnowledgeBase()
        count = 0
        
        for pattern in patterns:
            content = (
                f"Orchestration Pattern: {pattern['name']}\n"
                f"Category: {pattern['category']}\n"
                f"Description: {pattern['description']}\n"
                f"When to use: {', '.join(pattern.get('when_to_use', []))}\n"
                f"Failure modes: {', '.join(pattern.get('failure_modes', []))}\n"
                f"Cost impact: {pattern.get('cost_impact', 'N/A')}\n"
                f"Latency impact: {pattern.get('latency_impact', 'N/A')}\n"
                f"Complexity: {pattern.get('complexity', 'N/A')}\n"
                f"Source: {pattern.get('source_url', 'N/A')}"
            )
            
            import asyncio
            r = asyncio.get_event_loop().run_until_complete(
                kb.store_document(
                    document_text=content,
                    doc_id=f"pattern_{pattern['pattern_id']}",
                    metadata={
                        "type": "orchestration_pattern",
                        "pattern_id": pattern["pattern_id"],
                        "name": pattern["name"],
                        "category": pattern["category"],
                    }
                )
            )
            if r:
                count += 1
        
        logger.info(f"Successfully ingested {count} orchestration patterns")
        return count
        
    except Exception as e:
        logger.error(f"Failed to ingest patterns: {e}")
        return 0


def ingest_capabilities(dry_run: bool = False) -> int:
    """Ingest tool and capability data using store_document."""
    filepath = SCRIPT_DIR / "tools_and_capabilities.jsonl"
    if not filepath.exists():
        logger.error(f"Capabilities file not found: {filepath}")
        return 0
    
    capabilities = load_jsonl(filepath)
    logger.info(f"Loaded {len(capabilities)} capabilities from {filepath}")
    
    if dry_run:
        for cap in capabilities[:3]:
            logger.info(f"  [DRY RUN] Would ingest: {cap['capability_id']} - {cap['name']}")
        return len(capabilities)
    
    try:
        from llmhive.app.knowledge.pinecone_kb import PineconeKnowledgeBase
        
        kb = PineconeKnowledgeBase()
        count = 0
        
        for cap in capabilities:
            content = (
                f"Capability: {cap['name']}\n"
                f"Description: {cap['description']}\n"
                f"Best models: {', '.join(cap.get('best_models', []))}\n"
                f"Common issues: {', '.join(cap.get('common_issues', []))}\n"
                f"Best practices: {', '.join(cap.get('best_practices', []))}\n"
                f"Providers: {', '.join(cap.get('providers_supporting', []))}\n"
                f"Source: {cap.get('source_url', 'N/A')}"
            )
            
            import asyncio
            r = asyncio.get_event_loop().run_until_complete(
                kb.store_document(
                    document_text=content,
                    doc_id=f"capability_{cap['capability_id']}",
                    metadata={
                        "type": "capability",
                        "capability_id": cap["capability_id"],
                        "name": cap["name"],
                    }
                )
            )
            if r:
                count += 1
        
        logger.info(f"Successfully ingested {count} capabilities")
        return count
        
    except Exception as e:
        logger.error(f"Failed to ingest capabilities: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Ingest LLMHive orchestrator intelligence data"
    )
    parser.add_argument("--models", action="store_true", help="Ingest model data")
    parser.add_argument("--benchmarks", action="store_true", help="Ingest benchmark data")
    parser.add_argument("--results", action="store_true", help="Ingest benchmark results")
    parser.add_argument("--patterns", action="store_true", help="Ingest orchestration patterns")
    parser.add_argument("--capabilities", action="store_true", help="Ingest capability data")
    parser.add_argument("--all", action="store_true", help="Ingest all data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not (args.models or args.benchmarks or args.results or 
            args.patterns or args.capabilities or args.all):
        parser.print_help()
        return
    
    total = 0
    
    if args.all or args.models:
        total += ingest_models(dry_run=args.dry_run)
    
    if args.all or args.benchmarks:
        total += ingest_benchmarks(dry_run=args.dry_run)
    
    if args.all or args.results:
        total += ingest_benchmark_results(dry_run=args.dry_run)
    
    if args.all or args.patterns:
        total += ingest_patterns(dry_run=args.dry_run)
    
    if args.all or args.capabilities:
        total += ingest_capabilities(dry_run=args.dry_run)
    
    logger.info(f"Total records processed: {total}")
    
    if args.dry_run:
        logger.info("DRY RUN complete - no data was written")


if __name__ == "__main__":
    main()

