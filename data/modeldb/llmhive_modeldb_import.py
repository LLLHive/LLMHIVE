#!/usr/bin/env python3
"""
LLMHive ModelDB Importer

Purpose
-------
Take the single-sheet LLMHive Excel and upsert it into a SQL database.

Why this exists
---------------
- Your orchestrator can query by cost/context/modality quickly via SQL
- Your RAG can also ingest a JSONL export derived from the same table

Supported DBs
-------------
Anything SQLAlchemy supports, e.g.:
- sqlite:///llmhive_modeldb.sqlite
- postgresql+psycopg2://user:pass@host:5432/dbname

Usage
-----
pip install -r requirements.txt

python llmhive_modeldb_import.py \
  --excel ./LLMHive_ModelDB.xlsx \
  --sheet LLMHive_ModelDB \
  --db sqlite:///llmhive_modeldb.sqlite \
  --table ai_models
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd
from sqlalchemy import create_engine, text


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", required=True)
    ap.add_argument("--sheet", default="LLMHive_ModelDB")
    ap.add_argument("--db", required=True, help="SQLAlchemy URL")
    ap.add_argument("--table", default="ai_models")
    ap.add_argument("--chunksize", type=int, default=500)
    args = ap.parse_args()

    df = pd.read_excel(args.excel, sheet_name=args.sheet)
    df["imported_at"] = utc_now_iso()

    # Create a JSON payload column for flexible RAG/analytics use
    # (keeps every column even if schema evolves)
    df["payload_json"] = df.apply(lambda r: json.dumps({k: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in r.items()}, ensure_ascii=False), axis=1)

    engine = create_engine(args.db)

    # Create table if not exists (simple schema, flexible JSON payload)
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {args.table} (
        model_id INTEGER,
        openrouter_slug TEXT,
        provider_name TEXT,
        model_name TEXT,
        max_context_tokens INTEGER,
        modalities TEXT,
        price_input_usd_per_1m REAL,
        price_output_usd_per_1m REAL,
        parameter_count REAL,
        release_date TEXT,
        openrouter_rankings_json TEXT,
        benchmark_results_json_merged TEXT,
        payload_json TEXT,
        imported_at TEXT,
        PRIMARY KEY (openrouter_slug)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))

    # Upsert strategy: replace on PK conflict.
    # For SQLite this is easy; for Postgres we do a DELETE+INSERT per chunk (portable but slower).
    # You can upgrade to native ON CONFLICT for Postgres if desired.
    with engine.begin() as conn:
        # delete existing slugs in chunks, then append
        slugs = df["openrouter_slug"].dropna().astype(str).tolist()
        for i in range(0, len(slugs), args.chunksize):
            batch = slugs[i : i + args.chunksize]
            conn.execute(text(f"DELETE FROM {args.table} WHERE openrouter_slug IN :batch").bindparams(batch=tuple(batch)))

    df_to_load = df[
        [
            "model_id",
            "openrouter_slug",
            "provider_name",
            "model_name",
            "max_context_tokens",
            "modalities",
            "price_input_usd_per_1m",
            "price_output_usd_per_1m",
            "parameter_count",
            "release_date",
            "openrouter_rankings_json",
            "benchmark_results_json_merged",
            "payload_json",
            "imported_at",
        ]
    ].copy()

    df_to_load.to_sql(args.table, engine, if_exists="append", index=False, chunksize=args.chunksize)

    print(f"[OK] Imported rows={len(df_to_load)} into {args.db} table={args.table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
