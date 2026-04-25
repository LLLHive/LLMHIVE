#!/usr/bin/env python3
"""
Gap-fill Firestore model_catalog with OpenRouter models that are missing.

- Compares: GET https://openrouter.ai/api/v1/models (public) vs Firestore collection model_catalog.
- Writes ONLY new documents (merge on deterministic doc id). Does not delete unrelated rows.
- Does **not** set reasoning/coding/creative/accuracy capability scores (those come from ModelDB/LMSYS).
  Merge writes delete those four fields if present so old heuristic placeholders are removed.
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

# ModelDB / LMSYS pipeline owns these; gap-fill must not persist fake values.
_CAPABILITY_SCORE_FIELDS = ("reasoning_score", "coding_score", "creative_score", "accuracy_score")


def firestore_write_body(firestore_mod: Any, body: Dict[str, Any]) -> Dict[str, Any]:
    """Merge payload with DELETE_FIELD for ModelDB-owned scores so stale placeholders are removed."""
    merged = dict(body)
    for k in _CAPABILITY_SCORE_FIELDS:
        merged[k] = firestore_mod.DELETE_FIELD
    return merged


def resolve_merge_body(firestore_mod: Any, doc_ref: Any, body: Dict[str, Any]) -> Dict[str, Any]:
    """Apply score-field deletes only for new docs or existing gap-fill rows; never strip ModelDB scores."""
    snap = doc_ref.get()
    if not snap.exists:
        return firestore_write_body(firestore_mod, body)
    existing = snap.to_dict() or {}
    if existing.get("catalog_gap_fill") is True:
        return firestore_write_body(firestore_mod, body)
    return body


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
        if slug:
            found.add(slug.lower())
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


def _tool_score(model: Dict[str, Any]) -> int:
    params = model.get("supported_parameters")
    if not isinstance(params, list):
        return 0
    if "structured_outputs" in params and "tools" in params:
        return 2
    if "tools" in params:
        return 1
    return 0


def _multimodal_score(architecture: Optional[Dict[str, Any]]) -> int:
    if not architecture:
        return 0
    inputs = architecture.get("input_modalities") or []
    if not isinstance(inputs, list):
        return 0
    has_non_text = any(str(m).lower() != "text" for m in inputs)
    has_audio = any("audio" in str(m).lower() for m in inputs)
    if has_audio and has_non_text:
        return 2
    return 1 if has_non_text else 0


def _architecture_modality_string(architecture: Optional[Dict[str, Any]]) -> str:
    if not architecture:
        return "text->text"
    mod = architecture.get("modality")
    return str(mod) if mod else "text->text"


def compute_openrouter_snapshot_ranks(or_models: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Competition ranks over the live OpenRouter list only (same universe as pin/pout)."""
    ids: List[str] = []
    ctx: List[int] = []
    pin: List[float] = []
    pout: List[float] = []
    tscore: List[int] = []
    mscore: List[int] = []
    for m in or_models:
        sid = str(m.get("id") or "").strip()
        if not sid:
            continue
        pr = m.get("pricing") or {}
        try:
            p_in = float(pr.get("prompt") or 0)
        except (TypeError, ValueError):
            p_in = 0.0
        try:
            p_out = float(pr.get("completion") or 0)
        except (TypeError, ValueError):
            p_out = 0.0
        try:
            c = int(m.get("context_length") or 0)
        except (TypeError, ValueError):
            c = 0
        arch = m.get("architecture") if isinstance(m.get("architecture"), dict) else {}
        ids.append(sid)
        ctx.append(c)
        pin.append(p_in)
        pout.append(p_out)
        tscore.append(_tool_score(m))
        mscore.append(_multimodal_score(arch))

    def rank_desc(values: List[int]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for i, sid in enumerate(ids):
            v = values[i]
            out[sid] = 1 + sum(1 for x in values if x > v)
        return out

    def rank_asc(values: List[float]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for i, sid in enumerate(ids):
            v = values[i]
            out[sid] = 1 + sum(1 for x in values if x < v)
        return out

    def rank_tool_desc(values: List[int]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for i, sid in enumerate(ids):
            v = values[i]
            out[sid] = 1 + sum(1 for x in values if x > v)
        return out

    def rank_mm_desc(values: List[int]) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for i, sid in enumerate(ids):
            v = values[i]
            out[sid] = 1 + sum(1 for x in values if x > v)
        return out

    r_ctx = rank_desc(ctx)
    r_pin = rank_asc(pin)
    r_pout = rank_asc(pout)
    r_tool = rank_tool_desc(tscore)
    r_mm = rank_mm_desc(mscore)
    merged: Dict[str, Dict[str, int]] = {}
    for sid in ids:
        merged[sid] = {
            "rank_context_length_desc": r_ctx[sid],
            "openrouter_rank_context_length": r_ctx[sid],
            "rank_cost_input_asc": r_pin[sid],
            "openrouter_rank_price_input": r_pin[sid],
            "rank_cost_output_asc": r_pout[sid],
            "openrouter_rank_price_output": r_pout[sid],
            "rank_tool_support": r_tool[sid],
            "rank_multimodal_support": r_mm[sid],
        }
    return merged


def build_gap_document(
    or_model: Dict[str, Any],
    rank_by_slug: Dict[str, Dict[str, int]],
    total_or: int,
) -> Dict[str, Any]:
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
    display_name = str(or_model.get("name") or slug.split("/")[-1])
    short_name = slug.split("/")[-1] if "/" in slug else display_name
    now = datetime.now(timezone.utc)
    mid = generate_model_id(slug)
    ranks = rank_by_slug.get(slug, {})
    tool_sc = _tool_score(or_model)
    mm_sc = _multimodal_score(arch)
    desc = str(or_model.get("description") or "")[:8000]
    arch_s = _architecture_modality_string(arch)

    rankings_json = json.dumps(
        {
            "is_moderated": bool((or_model.get("top_provider") or {}).get("is_moderated"))
            if isinstance(or_model.get("top_provider"), dict)
            else False,
            "context_length": max_ctx,
            "price_prompt": pin,
            "price_completion": pout,
            "rank_context": ranks.get("openrouter_rank_context_length"),
            "rank_price_input": ranks.get("openrouter_rank_price_input"),
            "rank_price_output": ranks.get("openrouter_rank_price_output"),
        },
        default=str,
    )

    payload: Dict[str, Any] = {
        "openrouter_slug": slug,
        "display_name": display_name,
        "model_name": short_name,
        "provider_name": provider,
        "provider_id": provider,
        "description": desc,
        "architecture": arch_s,
        "max_context_tokens": max_ctx,
        "price_input_usd_per_1m": pin * 1_000_000,
        "price_output_usd_per_1m": pout * 1_000_000,
        "supports_function_calling": 1.0 if _supports_tools(or_model) else 0.0,
        "supports_vision": 1.0 if _bool_arch_multimodal(arch) else 0.0,
        "supports_streaming": 1.0,
        "multimodal_score": mm_sc,
        "tool_score": tool_sc,
        "in_openrouter": True,
        "openrouter_total_models": total_or,
        "openrouter_rankings_source_name": "OpenRouter API",
        "openrouter_rankings_source_url": OPENROUTER_MODELS_URL,
        "openrouter_rankings_retrieved_at": now.isoformat(),
        "openrouter_rankings_json_full": rankings_json,
        "openrouter_slug_source_name": "OpenRouter API",
        "openrouter_slug_source_url": OPENROUTER_MODELS_URL,
        "openrouter_slug_retrieved_at": now.isoformat(),
        "_openrouter_raw": json.dumps(or_model, default=str)[:120000],
        "rank_context_length_desc": ranks.get("rank_context_length_desc"),
        "rank_cost_input_asc": ranks.get("rank_cost_input_asc"),
        "rank_cost_output_asc": ranks.get("rank_cost_output_asc"),
        "openrouter_rank_context_length": ranks.get("openrouter_rank_context_length"),
        "openrouter_rank_price_input": ranks.get("openrouter_rank_price_input"),
        "openrouter_rank_price_output": ranks.get("openrouter_rank_price_output"),
        "rank_tool_support": ranks.get("rank_tool_support"),
        "rank_multimodal_support": ranks.get("rank_multimodal_support"),
        "derived_rank_source_name": "Derived from live OpenRouter snapshot (gap-fill)",
        "derived_rank_retrieved_at": now.isoformat(),
        "arena_match_status": "unmatched",
        "arena_match_score": 0.0,
        "catalog_gap_fill": True,
        "catalog_gap_fill_note": (
            "OpenRouter snapshot only. Top-level reasoning/coding/creative/accuracy scores are unset here; "
            "ModelDB/LMSYS enrichment adds them. Clients use neutral defaults when absent."
        ),
        "capability_scores_status": "pending_modeldb",
    }

    return {
        "model_id": mid,
        "openrouter_slug": slug,
        "model_name": short_name,
        "provider_id": provider,
        "provider_name": provider,
        "max_context_tokens": max_ctx,
        "price_input_usd_per_1m": pin * 1_000_000,
        "price_output_usd_per_1m": pout * 1_000_000,
        "supports_function_calling": 1.0 if _supports_tools(or_model) else 0.0,
        "supports_streaming": 1.0,
        "supports_vision": 1.0 if _bool_arch_multimodal(arch) else 0.0,
        "modalities": "text,image" if _bool_arch_multimodal(arch) else "text",
        "architecture": arch_s,
        "orchestration_roles": "",
        "strengths": "",
        "weaknesses": "",
        "best_use_cases": "",
        "in_openrouter": True,
        "last_ingested_at": now,
        "source_excel_path": "scripts/firestore_catalog_add_missing_openrouter.py",
        "schema_version": "1.0.0",
        "catalog_gap_fill": True,
        "payload": payload,
        "payload_overflow": len(json.dumps(payload, default=str)) > 850000,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Add missing OpenRouter slugs to Firestore model_catalog.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to Firestore (default is dry-run).",
    )
    parser.add_argument(
        "--enrich-slugs",
        default="",
        help=(
            "Comma-separated OpenRouter slugs: merge-update existing model_catalog docs "
            "with OpenRouter-derived ranks (removes any stale top-level capability score fields). "
            "Use with --apply."
        ),
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
    rank_by_slug = compute_openrouter_snapshot_ranks(or_models)

    db = firestore.Client(project=project)
    have = existing_slugs_from_firestore(db)
    logger.info("Firestore slugs indexed: %d", len(have))

    by_slug = {str(m["id"]): m for m in or_models if m.get("id")}
    missing = [s for s in or_slugs if s and s.lower() not in have]
    logger.info("Missing count: %d", len(missing))
    preview = missing[:25]
    if missing:
        logger.info("Sample missing: %s", preview)
        if not args.apply:
            logger.info("Dry-run only. Re-run with --apply to write %d new documents.", len(missing))
        else:
            batch = db.batch()
            count = 0
            for slug in missing:
                doc_id = generate_model_id(slug)
                body = build_gap_document(by_slug[slug], rank_by_slug, len(or_models))
                doc_ref = db.collection(COLLECTION).document(doc_id)
                batch.set(doc_ref, resolve_merge_body(firestore, doc_ref, body), merge=True)
                count += 1
                if count % 400 == 0:
                    batch.commit()
                    batch = db.batch()
                    logger.info("Committed %d ...", count)
            if count % 400 != 0:
                batch.commit()
            logger.info("Wrote %d new catalog documents (merge).", count)

    enrich_slugs = [s.strip() for s in (args.enrich_slugs or "").split(",") if s.strip()]
    if enrich_slugs:
        logger.info("Enrich merge requested for %d slug(s): %s", len(enrich_slugs), enrich_slugs)
        if not args.apply:
            logger.info("Dry-run: would merge-enrich those slugs; add --apply to persist.")
        else:
            batch = db.batch()
            n_en = 0
            for slug in enrich_slugs:
                om = by_slug.get(slug)
                if not om:
                    logger.warning("Slug not on current OpenRouter list, skip: %s", slug)
                    continue
                doc_id = generate_model_id(slug)
                body = build_gap_document(om, rank_by_slug, len(or_models))
                doc_ref = db.collection(COLLECTION).document(doc_id)
                batch.set(doc_ref, resolve_merge_body(firestore, doc_ref, body), merge=True)
                n_en += 1
            batch.commit()
            logger.info("Merge-enriched %d existing catalog document(s).", n_en)

    if not missing and not enrich_slugs:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
