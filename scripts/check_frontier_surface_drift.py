#!/usr/bin/env python3
"""Detect drift between frontier roster source, generated surfaces, and OpenRouter.

Exit codes:
  0 — no drift (or warn-only mode with only warnings)
  1 — drift detected in --strict mode

Usage:
  python scripts/check_frontier_surface_drift.py
  python scripts/check_frontier_surface_drift.py --strict
  python scripts/check_frontier_surface_drift.py --strict --verify-openrouter
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = ROOT / "data" / "generated" / "frontier_roster.json"
SYNC_SCRIPT = ROOT / "scripts" / "sync_frontier_surfaces.py"
CATEGORY_RANKINGS_PATH = ROOT / "lib" / "marketing" / "usecase-category-rankings.generated.json"

# UI categories that must surface the top paid roster model when benchmarks include it.
_CATEGORY_RANKINGS_REQUIRED_SLUGS: Dict[str, List[str]] = {
    "programming": ["anthropic/claude-opus-4.8"],
    "science": ["anthropic/claude-opus-4.8"],
    "reasoning": ["anthropic/claude-opus-4.8"],
    "technology": ["anthropic/claude-opus-4.8"],
}


def _fetch_openrouter_ids() -> Set[str]:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return {
        str(row.get("id")).strip().lower()
        for row in (payload.get("data") or [])
        if isinstance(row.get("id"), str) and row.get("id").strip()
    }


def _latest_family_slug(or_ids: Set[str], prefix: str) -> str | None:
    """Return highest-version non-fast slug for a family prefix."""
    skip_tokens = ("-fast", "-multi-agent", ":free", "customtools")
    candidates = [
        mid
        for mid in or_ids
        if mid.startswith(prefix.lower()) and not any(tok in mid for tok in skip_tokens)
    ]
    if not candidates:
        return None

    def sort_key(slug: str) -> tuple:
        tail = slug.split("/")[-1]
        nums = [int(n) for n in re.findall(r"\d+", tail)]
        return tuple(nums or [0])

    return sorted(candidates, key=sort_key)[-1]


def _category_rankings_model_ids(payload: Dict[str, Any], category: str) -> List[str]:
    rows = (payload.get("categories") or {}).get(category) or []
    return [
        str(row.get("model_id", "")).lower()
        for row in rows
        if isinstance(row, dict) and row.get("model_id")
    ]


def _check_category_rankings(roster: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not CATEGORY_RANKINGS_PATH.is_file():
        return ["Missing category rankings JSON — run scripts/sync_frontier_surfaces.py"]

    try:
        payload = json.loads(CATEGORY_RANKINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid category rankings JSON: {exc}"]

    top_paid = (roster.get("paid_catalog") or [{}])[0]
    flagship_slug = str(top_paid.get("model_id") or "").lower()
    if flagship_slug:
        all_ranked: Set[str] = set()
        for cat_rows in (payload.get("categories") or {}).values():
            if isinstance(cat_rows, list):
                for row in cat_rows:
                    if isinstance(row, dict) and row.get("model_id"):
                        all_ranked.add(str(row["model_id"]).lower())
        if flagship_slug not in all_ranked:
            errors.append(
                f"Category rankings missing top paid roster model {flagship_slug!r}"
            )

    for category, required_slugs in _CATEGORY_RANKINGS_REQUIRED_SLUGS.items():
        ranked = _category_rankings_model_ids(payload, category)
        if len(ranked) < 10:
            errors.append(f"Category {category!r} has fewer than 10 ranked models")
            continue
        for slug in required_slugs:
            if slug.lower() not in ranked:
                errors.append(
                    f"Category {category!r} rankings missing required model {slug!r}"
                )

    return errors


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any drift")
    parser.add_argument("--verify-openrouter", action="store_true")
    args = parser.parse_args()

    errors: List[str] = []
    warnings: List[str] = []

    if not ROSTER_PATH.is_file():
        errors.append(f"Missing roster source: {ROSTER_PATH}")
    else:
        roster = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
        ui_slugs = {
            str(m.get("model_id", "")).lower()
            for m in (roster.get("ui_models") or [])
            if m.get("model_id")
        }
        paid_slugs = {
            str(m.get("model_id", "")).lower()
            for m in (roster.get("paid_catalog") or [])
            if m.get("model_id")
        }

        marketing = roster.get("marketing") or {}
        featured_line = str(marketing.get("featured_line") or "")
        if "Claude Opus 4.8" not in featured_line and "claude-opus-4.8" not in featured_line.lower():
            top_paid = (roster.get("paid_catalog") or [{}])[0]
            expected_name = str(top_paid.get("display") or "")
            if expected_name and expected_name not in featured_line:
                errors.append(
                    f"Marketing featured_line missing top paid model {expected_name!r}"
                )

        if args.verify_openrouter:
            try:
                or_ids = _fetch_openrouter_ids()
            except Exception as exc:
                warnings.append(f"OpenRouter fetch failed: {exc}")
                or_ids = set()
            else:
                for slug in sorted(ui_slugs | paid_slugs):
                    if slug not in or_ids:
                        errors.append(f"Roster slug not on OpenRouter: {slug}")

                for prefix in roster.get("frontier_watch_families") or []:
                    latest = _latest_family_slug(or_ids, str(prefix))
                    if not latest:
                        continue
                    if latest not in ui_slugs:
                        errors.append(
                            f"Newest frontier slug {latest} missing from ui_models roster"
                        )
                    if latest not in paid_slugs and "opus" in latest:
                        warnings.append(
                            f"Newest Opus slug {latest} not in paid_catalog top tier (ui only)"
                        )

        errors.extend(_check_category_rankings(roster))

    proc = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        errors.append("Generated surfaces are stale — run scripts/sync_frontier_surfaces.py")
        if proc.stderr.strip():
            errors.append(proc.stderr.strip())

    marketing_gen = _read_text(ROOT / "lib" / "marketing" / "featured-models.generated.ts")
    marketing_src = _read_text(ROOT / "lib" / "marketing" / "featured-models.ts")
    if "featured-models.generated" not in marketing_src:
        errors.append("lib/marketing/featured-models.ts must re-export from generated file")

    models_src = _read_text(ROOT / "lib" / "models.ts")
    if "models.generated" not in models_src:
        errors.append("lib/models.ts must import from models.generated.ts")

    for msg in warnings:
        print(f"WARNING: {msg}", file=sys.stderr)
    for msg in errors:
        print(f"ERROR: {msg}", file=sys.stderr)

    if errors:
        if args.strict:
            return 1
        print("Drift detected (non-strict mode — exit 0).", file=sys.stderr)
        return 0

    print("Frontier surface drift check passed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
