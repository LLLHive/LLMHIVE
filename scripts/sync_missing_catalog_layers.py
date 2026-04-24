#!/usr/bin/env python3
"""
Safe multi-layer catalog sync — adds missing OpenRouter models where automation is additive.

Runs (in order):
  1) Firestore model_catalog gap-fill (scripts/firestore_catalog_add_missing_openrouter.py)
  2) OpenRouter → SQLite catalog sync (OpenRouterModelSync), enrich_endpoints=False by default
     - On successful commit, also runs the existing knowledge-store hook inside sync (Pinecone),
       same as POST /api/v1/openrouter/sync — failures there are already non-fatal.
  3) Optional: enrich canonical ModelRegistry2026 from Firestore (updates EXISTING keys only)

Does NOT modify (by design — benchmark / product locks):
  - llmhive/.../elite_policy.py (ELITE_POLICY)
  - llmhive/.../elite_orchestration.py (ELITE_MODELS / FREE_MODELS tables)
  - llmhive/.../free_models_database.py (FREE_MODELS_DB)
  - scripts/verify-openrouter-catalog-ids.mjs
  - data/modeldb Excel / full ModelDB Pinecone embedding pipeline

Env:
  Firestore: GOOGLE_APPLICATION_CREDENTIALS or ADC; GOOGLE_CLOUD_PROJECT or GCP_PROJECT
  SQLite sync: DATABASE_URL or SQLALCHEMY_DATABASE_URI; OPENROUTER_API_KEY (required by OpenRouterConfig)

Usage:
  python scripts/sync_missing_catalog_layers.py                 # dry-run both steps
  python scripts/sync_missing_catalog_layers.py --apply         # write Firestore + DB
  python scripts/sync_missing_catalog_layers.py --apply --skip-firestore
  python scripts/sync_missing_catalog_layers.py --apply --enrich-endpoints  # slower, more API calls
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("sync_layers")

ROOT = Path(__file__).resolve().parents[1]


def _run_firestore_gap(apply: bool) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "firestore_catalog_add_missing_openrouter.py")]
    if apply:
        cmd.append("--apply")
    logger.info("Running: %s", " ".join(cmd))
    return subprocess.call(cmd)


def _run_sqlite_sync(apply: bool, enrich_endpoints: bool) -> int:
    if not os.getenv("DATABASE_URL") and not os.getenv("SQLALCHEMY_DATABASE_URI"):
        logger.warning("Skipping SQLite sync: set DATABASE_URL or SQLALCHEMY_DATABASE_URI")
        return 0
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.warning("Skipping SQLite sync: OPENROUTER_API_KEY required for OpenRouterModelSync client")
        return 0

    sys.path.insert(0, str(ROOT / "llmhive" / "src"))

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from llmhive.app.openrouter.sync import OpenRouterModelSync

    db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    engine = create_engine(db_url)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        sync = OpenRouterModelSync(session)
        report = asyncio.run(
            sync.run(
                dry_run=not apply,
                enrich_endpoints=enrich_endpoints,
            )
        )
        logger.info("OpenRouter sync report: %s", report.to_dict())
        if report.model_errors:
            for err in report.model_errors[:15]:
                logger.warning("model_error: %s", err)
        return 0 if report.success else 1
    finally:
        session.close()


def _run_registry_enrich_from_firestore() -> None:
    sys.path.insert(0, str(ROOT / "llmhive" / "src"))
    from llmhive.app.intelligence.model_registry_2026 import get_model_registry_2026

    reg = get_model_registry_2026()
    n = reg.enrich_from_firestore()
    logger.info("ModelRegistry2026.enrich_from_firestore updated %d entries (existing keys only)", n)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Persist changes (default is dry-run for SQLite; Firestore script defaults dry-run without --apply)")
    p.add_argument("--skip-firestore", action="store_true")
    p.add_argument("--skip-sqlite", action="store_true")
    p.add_argument(
        "--enrich-endpoints",
        action="store_true",
        help="Per-model endpoint fetches (slower, more OpenRouter traffic). Default off for safety.",
    )
    p.add_argument(
        "--registry-enrich",
        action="store_true",
        help="After apply, run ModelRegistry2026.enrich_from_firestore() in-process (updates existing canonical rows only).",
    )
    args = p.parse_args()

    logger.info(
        "sync_missing_catalog_layers apply=%s skip_firestore=%s skip_sqlite=%s enrich_endpoints=%s",
        args.apply,
        args.skip_firestore,
        args.skip_sqlite,
        args.enrich_endpoints,
    )

    rc = 0
    if not args.skip_firestore:
        rc = _run_firestore_gap(args.apply)
        if rc != 0:
            return rc

    if not args.skip_sqlite:
        rc = _run_sqlite_sync(args.apply, args.enrich_endpoints)
        if rc != 0:
            return rc

    if args.apply and args.registry_enrich:
        try:
            _run_registry_enrich_from_firestore()
        except Exception as e:
            logger.warning("Registry enrich failed (non-fatal): %s", e)

    logger.info(
        "Done. Curated orchestration lists (ELITE_POLICY, ELITE_MODELS, FREE_MODELS, FREE_MODELS_DB) "
        "and verify-openrouter-catalog-ids.mjs were NOT changed — update those only when you intentionally "
        "add a model to a benchmark or tier strategy."
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())
