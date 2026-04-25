#!/usr/bin/env python3
"""
Targeted Firestore benchmark enrichment for a small set of OpenRouter slugs.

Why this exists:
- The ModelDB pipeline normally enriches the full Excel → Firestore catalog.
- For urgent go-to-market fixes, we sometimes need to enrich just a handful of
  newly-added models without running the full refresh runner.

What it does:
- Reads the existing Firestore `model_catalog` documents for the given slugs.
- Runs ModelDB enrichers locally (LMSYS Arena + HF Open LLM Leaderboard).
- Writes ONLY the benchmark-related columns back to Firestore (merge=True).

Safety:
- No deletes. Only writes a narrow set of keys (arena_* and hf_ollb_* families).
- Uses deterministic doc ids (uuid5) consistent with ModelDB pipeline.

Usage:
  python scripts/enrich_firestore_benchmarks_for_slugs.py --slugs "a/b,c/d"        # dry-run
  python scripts/enrich_firestore_benchmarks_for_slugs.py --apply --slugs "a/b"   # write
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("targeted_benchmark_enrich")

COLLECTION = "model_catalog"
UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # same as ModelDB pipeline

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELDB_DIR = os.path.join(REPO_ROOT, "data", "modeldb")


def generate_model_id(openrouter_slug: str) -> str:
    doc_uuid = uuid.uuid5(UUID_NAMESPACE, openrouter_slug)
    return str(doc_uuid).replace("-", "")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_value(v: Any) -> Any:
    # Firestore dislikes NaN; convert to None.
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    # Pandas sometimes gives numpy scalar types
    if hasattr(v, "item") and callable(getattr(v, "item")):
        try:
            return v.item()
        except Exception:
            return v
    return v


def _extract_benchmark_updates(row: pd.Series) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    for k, v in row.to_dict().items():
        if k.startswith("arena_") or k.startswith("hf_ollb_"):
            updates[k] = _clean_value(v)
    # Ensure match semantics are present even when unmatched.
    for k in ("arena_match_status", "arena_match_score", "hf_ollb_match_status", "hf_ollb_match_score"):
        if k in row.index:
            updates[k] = _clean_value(row.get(k))
    # Provenance: allow operators to see this was targeted.
    updates["benchmarks_targeted_enriched_at"] = _utc_now_iso()
    updates["benchmarks_targeted_enricher"] = "scripts/enrich_firestore_benchmarks_for_slugs.py"
    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Targeted Firestore benchmark enrichment for specific slugs.")
    parser.add_argument("--apply", action="store_true", help="Write updates to Firestore (default dry-run).")
    parser.add_argument("--slugs", required=True, help="Comma-separated OpenRouter slugs to enrich.")
    args = parser.parse_args()

    slugs = [s.strip() for s in (args.slugs or "").split(",") if s.strip()]
    if not slugs:
        logger.error("No slugs provided.")
        return 2

    try:
        from google.cloud import firestore
    except ImportError:
        logger.error("Install google-cloud-firestore: pip install google-cloud-firestore")
        return 1

    # Import enrichers from the repo.
    try:
        # `data/` isn't a Python package; import ModelDB modules by path.
        if MODELDB_DIR not in sys.path:
            sys.path.insert(0, MODELDB_DIR)
        from enrichers.lmsys_arena import LMSYSArenaEnricher  # type: ignore
        from enrichers.hf_open_llm_leaderboard import HFLeaderboardEnricher  # type: ignore
    except Exception as e:
        logger.error("Failed to import ModelDB enrichers: %s", e)
        return 1

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "llmhive-orchestrator"
    logger.info("Project=%s apply=%s slugs=%d", project, args.apply, len(slugs))

    db = firestore.Client(project=project)

    # Fetch existing docs and build a minimal DataFrame for matching.
    rows: List[Dict[str, Any]] = []
    missing_docs: List[str] = []
    doc_refs_by_slug: Dict[str, Any] = {}
    for slug in slugs:
        doc_id = generate_model_id(slug)
        doc_ref = db.collection(COLLECTION).document(doc_id)
        snap = doc_ref.get()
        if not snap.exists:
            missing_docs.append(slug)
            continue
        d = snap.to_dict() or {}
        doc_refs_by_slug[slug] = doc_ref
        rows.append(
            {
                "openrouter_slug": slug,
                "model_name": d.get("model_name") or slug.split("/")[-1],
                "provider_name": d.get("provider_name") or (slug.split("/", 1)[0] if "/" in slug else "unknown"),
                # These help some matchers; safe if empty.
                "display_name": d.get("display_name") or d.get("payload", {}).get("display_name") or "",
                "description": d.get("description") or d.get("payload", {}).get("description") or "",
            }
        )

    if missing_docs:
        logger.warning("These slugs were not found in Firestore (skip): %s", missing_docs)
    if not rows:
        logger.error("No existing Firestore documents found for provided slugs.")
        return 3

    df = pd.DataFrame(rows)

    # Run enrichers (they will cache locally under .cache/llmhive_modeldb/*).
    # Enrichment should run even in dry-run mode; we just won't persist writes.
    arena = LMSYSArenaEnricher(dry_run=False)
    df, arena_result = arena.enrich(df)
    logger.info("LMSYS Arena: %s", "✓" if arena_result.success else "✗")

    hf = HFLeaderboardEnricher(dry_run=False)
    df, hf_result = hf.enrich(df)
    logger.info("HF Open LLM Leaderboard: %s", "✓" if hf_result.success else "✗")

    # Write back only benchmark-related columns.
    writes = 0
    for _, r in df.iterrows():
        slug = str(r.get("openrouter_slug") or "").strip()
        if not slug:
            continue
        doc_ref = doc_refs_by_slug.get(slug)
        if not doc_ref:
            continue
        updates = _extract_benchmark_updates(r)
        if not args.apply:
            logger.info("[DRY RUN] Would update %s keys=%d arena_match=%s hf_match=%s", slug, len(updates), updates.get("arena_match_status"), updates.get("hf_ollb_match_status"))
            continue
        doc_ref.set(updates, merge=True)
        writes += 1

    if args.apply:
        logger.info("Wrote benchmark updates for %d document(s).", writes)
    return 0


if __name__ == "__main__":
    sys.exit(main())

