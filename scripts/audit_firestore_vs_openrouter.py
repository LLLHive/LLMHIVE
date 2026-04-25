#!/usr/bin/env python3
"""
Read-only audit: Firestore model_catalog vs live OpenRouter catalog (+ optional curated picker).

- No writes anywhere.
- Safe for CI / local: uses Application Default Credentials for Firestore.

Exit codes:
  0 always (audit is informational); inspect stdout / --json-out for gaps.

Env:
  GOOGLE_CLOUD_PROJECT or GCP_PROJECT (default: llmhive-orchestrator)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]


def _fetch_openrouter_ids() -> Set[str]:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data") or []
    out: Set[str] = set()
    for row in data:
        mid = row.get("id")
        if isinstance(mid, str) and mid.strip():
            out.add(mid.strip().lower())
    return out


def _firestore_slugs(project: str) -> Tuple[Set[str], Dict[str, Any]]:
    from google.cloud import firestore

    db = firestore.Client(project=project)
    col = db.collection("model_catalog")
    slugs: Set[str] = set()
    newest: datetime | None = None
    n = 0
    for doc in col.stream():
        n += 1
        d = doc.to_dict() or {}
        raw = d.get("openrouter_slug") or d.get("model_id") or doc.id
        if isinstance(raw, str) and raw.strip():
            slugs.add(raw.strip().lower())
        ts = d.get("last_ingested_at")
        if hasattr(ts, "timestamp"):
            ts = datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc)
        if isinstance(ts, datetime) and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if isinstance(ts, datetime):
            if newest is None or ts > newest:
                newest = ts
    meta = {"firestore_doc_count_streamed": n, "newest_last_ingested_at": newest.isoformat() if newest else None}
    return slugs, meta


def _curated_picker_ids() -> Set[str]:
    path = ROOT / "lib" / "models.ts"
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8")
    # id: "provider/model" or id: '...'
    found = set(re.findall(r"""id:\s*["']([^"']+)["']""", text))
    found.discard("automatic")
    return {x.strip().lower() for x in found if "/" in x}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--project",
        default=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "llmhive-orchestrator",
        help="GCP project id for Firestore",
    )
    p.add_argument("--json-out", type=Path, help="Write full report JSON to this path")
    p.add_argument("--max-list", type=int, default=80, help="Max IDs to print per list")
    p.add_argument("--no-curated", action="store_true", help="Skip lib/models.ts curated comparison")
    args = p.parse_args()

    print("Fetching OpenRouter public catalog…", file=sys.stderr)
    or_ids = _fetch_openrouter_ids()
    print(f"OpenRouter models: {len(or_ids)}", file=sys.stderr)

    print(f"Streaming Firestore model_catalog ({args.project})…", file=sys.stderr)
    fs_slugs, fs_meta = _firestore_slugs(args.project)
    print(f"Firestore unique slugs: {len(fs_slugs)} (docs streamed: {fs_meta['firestore_doc_count_streamed']})", file=sys.stderr)

    missing_in_firestore = sorted(or_ids - fs_slugs)
    extra_in_firestore = sorted(fs_slugs - or_ids)

    curated: Set[str] = set()
    if not args.no_curated:
        curated = _curated_picker_ids()
        print(f"Curated picker models (lib/models.ts): {len(curated)}", file=sys.stderr)

    curated_missing_fs: List[str] = []
    curated_missing_or: List[str] = []
    if curated:
        curated_missing_fs = sorted(curated - fs_slugs)
        curated_missing_or = sorted(curated - or_ids)

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project,
        "openrouter_count": len(or_ids),
        "firestore_unique_slug_count": len(fs_slugs),
        "firestore_meta": fs_meta,
        "missing_in_firestore": missing_in_firestore,
        "extra_in_firestore_not_on_openrouter": extra_in_firestore,
        "counts": {
            "openrouter_not_in_firestore": len(missing_in_firestore),
            "firestore_not_in_openrouter": len(extra_in_firestore),
        },
    }
    if curated:
        report["curated"] = {
            "picker_count": len(curated),
            "curated_missing_in_firestore": curated_missing_fs,
            "curated_missing_on_openrouter": curated_missing_or,
        }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out}", file=sys.stderr)

    # Human summary
    print("\n=== Audit: Firestore vs OpenRouter (read-only) ===\n")
    print(f"Project: {args.project}")
    print(f"OpenRouter live slugs: {len(or_ids)}")
    print(f"Firestore unique slugs: {len(fs_slugs)}")
    if fs_meta.get("newest_last_ingested_at"):
        print(f"Newest Firestore last_ingested_at (sampled max while streaming): {fs_meta['newest_last_ingested_at']}")
    print()
    print(f"On OpenRouter but NOT in Firestore: {len(missing_in_firestore)}")
    for s in missing_in_firestore[: args.max_list]:
        print(f"  - {s}")
    if len(missing_in_firestore) > args.max_list:
        print(f"  … and {len(missing_in_firestore) - args.max_list} more")
    print()
    print(f"In Firestore but NOT on OpenRouter catalog: {len(extra_in_firestore)} (often legacy / renamed)")
    for s in extra_in_firestore[: args.max_list]:
        print(f"  - {s}")
    if len(extra_in_firestore) > args.max_list:
        print(f"  … and {len(extra_in_firestore) - args.max_list} more")

    if curated:
        print("\n--- Curated chat picker (lib/models.ts) ---")
        print(f"Curated missing in Firestore: {len(curated_missing_fs)}")
        for s in curated_missing_fs[: args.max_list]:
            print(f"  - {s}")
        print(f"Curated missing on OpenRouter (bad slug / renamed): {len(curated_missing_or)}")
        for s in curated_missing_or[: args.max_list]:
            print(f"  - {s}")

    print(
        "\nRegression note: this script performs **zero writes**. "
        "To close gaps safely, review lists then use your gated sync (e.g. "
        "scripts/sync_missing_catalog_layers.py --dry-run first) or ModelDB refresh PRs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
