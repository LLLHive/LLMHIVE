#!/usr/bin/env python3
"""
Gap-fill Firestore model_catalog with OpenRouter models that are missing.

- Compares: GET https://openrouter.ai/api/v1/models (public) vs Firestore collection model_catalog.
- Writes ONLY new documents (merge on deterministic doc id). Does not delete or rewrite existing rows.
- Does NOT touch: orchestration code, Next.js, SQLite, Pinecone ModelDB index.

Requirements:
  pip install google-cloud-firestore
  GOOGLE_APPLICATION_CREDENTIALS or gcloud application-default login
  GOOGLE_CLOUD_PROJECT or GCP_PROJECT (defaults to llmhive-orchestrator)

Usage:
  python scripts/firestore_catalog_add_missing_openrouter.py          # dry-run, print summary
  python scripts/firestore_catalog_add_missing_openrouter.py --apply  # write to Firestore
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.request import Request, urlopen

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("gap_fill")

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
COLLECTION = "model_catalog"
UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # same as ModelDB pipeline


def generate_model_id(openrouter_slug: str) -> str:
    doc_uuid = uuid.uuid5(UUID_NAMESPACE, openrouter_slug)
    return str(doc_uuid).replace("-", "")


def fetch_openrouter_ids() -> List[Dict[str, Any]]:
    req = Request(OPENROUTER_MODELS_URL, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data") or []
    return data


def existing_slugs_from_firestore(db) -> Set[str]:
    found: Set[str] = set()
    for doc in db.collection(COLLECTION).stream():
        d = doc.to_dict() or {}
        slug = (d.get("openrouter_slug") or doc.id or "").strip()
        if slug and "/" in slug:
            found.add(slug)
        elif slug:
            found.add(slug)
    return found


def _bool_arch_multimodal(architecture: Optional[Dict[str, Any]]) -> bool:
    if not architecture:
        return False
    inputs = architecture.get("input_modalities") or []
    if not isinstance(inputs, list):
        return False
    return any(str(m).lower() != "text" for m in inputs)


def _supports_tools(model: Dict[str, Any]) -> bool:
    params = model.get("supported_parameters")
    if isinstance(params, list):
        return "tools" in params
    return False


def build_gap_document(or_model: Dict[str, Any]) -> Dict[str, Any]:
    slug = str(or_model.get("id") or "").strip()
    if not slug:
        raise ValueError("missing id")
    pricing = or_model.get("pricing") or {}
    try:
        pin = float(pricing.get("prompt") or 0)
    except (TypeError, ValueError):
        pin = 0.0
    try:
        pout = float(pricing.get("completion") or 0)
    except (TypeError, ValueError):
        pout = 0.0
    arch = or_model.get("architecture") if isinstance(or_model.get("architecture"), dict) else {}
    ctx = or_model.get("context_length")
    try:
        max_ctx = int(ctx) if ctx is not None else 8192
    except (TypeError, ValueError):
        max_ctx = 8192
    provider = slug.split("/", 1)[0] if "/" in slug else "unknown"
    name = str(or_model.get("name") or slug.split("/")[-1])
    now = datetime.now(timezone.utc)
    mid = generate_model_id(slug)
    return {
        "model_id": mid,
        "openrouter_slug": slug,
        "model_name": name,
        "provider_name": provider,
        "max_context_tokens": max_ctx,
        "price_input_usd_per_1m": pin * 1_000_000,
        "price_output_usd_per_1m": pout * 1_000_000,
        "supports_function_calling": _supports_tools(or_model),
        "supports_vision": _bool_arch_multimodal(arch),
        "modalities": "text,image" if _bool_arch_multimodal(arch) else "text",
        "orchestration_roles": "",
        "strengths": "",
        "weaknesses": "",
        "best_use_cases": "",
        "in_openrouter": True,
        "last_ingested_at": now,
        "source_excel_path": "scripts/firestore_catalog_add_missing_openrouter.py",
        "schema_version": "1.0.0",
        "catalog_gap_fill": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Add missing OpenRouter slugs to Firestore model_catalog.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to Firestore (default is dry-run).",
    )
    args = parser.parse_args()

    try:
        from google.cloud import firestore
    except ImportError:
        logger.error("Install google-cloud-firestore: pip install google-cloud-firestore")
        return 1

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "llmhive-orchestrator"
    logger.info("Project=%s apply=%s", project, args.apply)

    or_models = fetch_openrouter_ids()
    or_slugs = [str(m.get("id")) for m in or_models if m.get("id")]
    logger.info("OpenRouter models: %d", len(or_slugs))

    db = firestore.Client(project=project)
    have = existing_slugs_from_firestore(db)
    logger.info("Firestore slugs indexed: %d", len(have))

    by_slug = {str(m["id"]): m for m in or_models if m.get("id")}
    missing = [s for s in or_slugs if s and s not in have]
    logger.info("Missing count: %d", len(missing))
    if not missing:
        return 0

    preview = missing[:25]
    logger.info("Sample missing: %s", preview)

    if not args.apply:
        logger.info("Dry-run only. Re-run with --apply to write %d documents.", len(missing))
        return 0

    batch = db.batch()
    count = 0
    for slug in missing:
        doc_id = generate_model_id(slug)
        body = build_gap_document(by_slug[slug])
        batch.set(db.collection(COLLECTION).document(doc_id), body, merge=True)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            logger.info("Committed %d ...", count)
    if count % 400 != 0:
        batch.commit()
    logger.info("Wrote %d new catalog documents (merge).", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
