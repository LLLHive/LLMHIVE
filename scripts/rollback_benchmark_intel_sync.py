#!/usr/bin/env python3
"""Rollback the narrow March 29 benchmark-intel remote sync.

This script restores the exact Firestore `model_catalog` documents captured in
the pre-sync snapshot, rebuilds the paired `modeldb-embeddings` Pinecone
records from that snapshot, and removes the extra `frontier-2026-03-29`
knowledge-store ranking slice plus the benchmark refresh AI-development note.

Important:
- Firestore rollback is exact for the captured documents.
- `modeldb-embeddings` rollback is exact enough for the captured documents.
- `llmhive-model-knowledge` model profiles were overwritten in-place during the
  sync and are not exactly recoverable from the snapshot alone, so this script
  does not delete them by default.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data" / "modeldb"))

from google.cloud import firestore  # type: ignore
from pinecone import Pinecone  # type: ignore

from llmhive_modeldb_pipeline import generate_model_id, build_embedding_text


DEFAULT_SNAPSHOT = ROOT / "artifacts" / "snapshots" / "benchmark_intel_presync_20260329T234759Z.json"
MODELDB_INDEX = "modeldb-embeddings"
KNOWLEDGE_INDEX = "llmhive-model-knowledge"
KNOWLEDGE_VIEW = "frontier-2026-03-29"
AI_DEVELOPMENT_TITLE = "Frontier benchmark leaders refreshed 2026-03-29"
TARGET_SLUGS = [
    "openai/o3",
    "anthropic/claude-opus-4.5",
    "deepseek/deepseek-r1",
    "openai/gpt-5.2",
    "google/gemini-3-pro",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rollback narrow benchmark-intel remote sync.")
    parser.add_argument(
        "--snapshot",
        default=str(DEFAULT_SNAPSHOT),
        help="Path to the pre-sync snapshot JSON.",
    )
    parser.add_argument(
        "--project",
        default="llmhive-orchestrator",
        help="Firestore GCP project ID.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without modifying remote stores.",
    )
    return parser.parse_args()


def _load_snapshot(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Snapshot not found: {path}")
    return json.loads(path.read_text())


def _extract_embedding_record(doc_id: str, doc_data: Dict[str, Any]) -> Dict[str, Any]:
    payload = doc_data.get("payload", {}) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Snapshot payload for {doc_id} is not an object.")

    record = {
        "_id": doc_id,
        "content": build_embedding_text(payload),
        "model_id": doc_id,
        "openrouter_slug": doc_data.get("openrouter_slug", payload.get("openrouter_slug", "")),
        "provider_name": doc_data.get("provider_name", payload.get("provider_name", "")),
        "model_family": doc_data.get("provider_id", payload.get("provider_id", "")),
        "in_openrouter": bool(doc_data.get("in_openrouter", True)),
        "max_context_tokens": int(doc_data.get("max_context_tokens", payload.get("max_context_tokens", 0)) or 0),
    }
    orchestration_roles = doc_data.get("orchestration_roles") or payload.get("orchestration_roles")
    if orchestration_roles is not None:
        record["orchestration_roles"] = str(orchestration_roles)
    return record


def _restore_firestore(snapshot: Dict[str, Any], db: firestore.Client, dry_run: bool) -> List[str]:
    actions: List[str] = []
    docs = snapshot.get("firestore_model_catalog", {})
    collection = db.collection("model_catalog")
    overflow_collection = db.collection("model_catalog_payloads")

    for slug in TARGET_SLUGS:
        snap = docs.get(slug, {})
        doc_id = snap.get("doc_id") or generate_model_id(slug)
        exists = bool(snap.get("exists"))
        if not exists:
            actions.append(f"delete firestore model_catalog/{doc_id} ({slug})")
            if not dry_run:
                collection.document(doc_id).delete()
                overflow_collection.document(doc_id).delete()
            continue

        doc_data = snap.get("data", {})
        if not isinstance(doc_data, dict):
            raise ValueError(f"Snapshot data for {slug} is not an object.")
        actions.append(f"restore firestore model_catalog/{doc_id} ({slug})")
        if not dry_run:
            collection.document(doc_id).set(doc_data)
    return actions


def _restore_modeldb_embeddings(snapshot: Dict[str, Any], pc: Pinecone, dry_run: bool) -> List[str]:
    actions: List[str] = []
    idx = pc.Index(MODELDB_INDEX)
    docs = snapshot.get("firestore_model_catalog", {})
    upserts: List[Dict[str, Any]] = []
    deletes: List[str] = []

    for slug in TARGET_SLUGS:
        snap = docs.get(slug, {})
        doc_id = snap.get("doc_id") or generate_model_id(slug)
        if bool(snap.get("exists")):
            upserts.append(_extract_embedding_record(doc_id, snap["data"]))
            actions.append(f"restore pinecone {MODELDB_INDEX}/model_catalog {doc_id} ({slug})")
        else:
            deletes.append(doc_id)
            actions.append(f"delete pinecone {MODELDB_INDEX}/model_catalog {doc_id} ({slug})")

    if not dry_run:
        if upserts:
            idx.upsert_records("model_catalog", upserts)
        if deletes:
            idx.delete(namespace="model_catalog", ids=deletes)
    return actions


def _search_ids(idx: Any, namespace: str, query_text: str, flt: Dict[str, Any], top_k: int = 100) -> List[str]:
    res = idx.search(namespace=namespace, query={"top_k": top_k, "inputs": {"text": query_text}, "filter": flt})
    hits = res.get("result", {}).get("hits", []) if isinstance(res, dict) else res.result.hits
    ids: List[str] = []
    for hit in hits:
        if isinstance(hit, dict):
            rec_id = hit.get("_id")
        else:
            rec_id = getattr(hit, "_id", None)
        if rec_id:
            ids.append(rec_id)
    return ids


def _cleanup_knowledge_store(pc: Pinecone, dry_run: bool) -> List[str]:
    actions: List[str] = []
    idx = pc.Index(KNOWLEDGE_INDEX)

    ranking_ids = _search_ids(
        idx,
        namespace="category_rankings",
        query_text="frontier benchmark leaderboard",
        flt={"view": {"$eq": KNOWLEDGE_VIEW}},
        top_k=100,
    )
    if ranking_ids:
        actions.append(f"delete {len(ranking_ids)} knowledge ranking records for view {KNOWLEDGE_VIEW}")
        if not dry_run:
            idx.delete(namespace="category_rankings", ids=ranking_ids)

    ai_dev_ids = _search_ids(
        idx,
        namespace="ai_developments",
        query_text="Frontier benchmark leaders refreshed",
        flt={"title": {"$eq": AI_DEVELOPMENT_TITLE}},
        top_k=20,
    )
    if ai_dev_ids:
        actions.append(f"delete {len(ai_dev_ids)} ai_developments records for benchmark refresh note")
        if not dry_run:
            idx.delete(namespace="ai_developments", ids=ai_dev_ids)

    actions.append("leave model_profiles untouched (exact pre-sync versions not present in snapshot)")
    return actions


def main() -> int:
    args = _parse_args()
    snapshot = _load_snapshot(Path(args.snapshot).expanduser())
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise RuntimeError("PINECONE_API_KEY is required.")

    db = firestore.Client(project=args.project)
    pc = Pinecone(api_key=api_key)

    firestore_actions = _restore_firestore(snapshot, db, args.dry_run)
    modeldb_actions = _restore_modeldb_embeddings(snapshot, pc, args.dry_run)
    knowledge_actions = _cleanup_knowledge_store(pc, args.dry_run)

    summary = {
        "snapshot": str(Path(args.snapshot).expanduser()),
        "dry_run": args.dry_run,
        "firestore_actions": firestore_actions,
        "modeldb_actions": modeldb_actions,
        "knowledge_actions": knowledge_actions,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
