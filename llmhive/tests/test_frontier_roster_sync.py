"""Tests for frontier roster sync and drift checks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_frontier_roster_source_exists():
    roster = ROOT / "data" / "generated" / "frontier_roster.json"
    assert roster.is_file()
    payload = json.loads(roster.read_text(encoding="utf-8"))
    ui_ids = [m["model_id"] for m in payload.get("ui_models") or []]
    assert "anthropic/claude-opus-4.8" in ui_ids
    paid_ids = [m["model_id"] for m in payload.get("paid_catalog") or []]
    assert paid_ids[0] == "anthropic/claude-opus-4.8"


def test_generated_surfaces_are_current():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_frontier_surfaces.py"), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_models_generated_includes_opus_48():
    text = (ROOT / "lib" / "models.generated.ts").read_text(encoding="utf-8")
    assert "anthropic/claude-opus-4.8" in text


def test_paid_catalog_generated_loads_in_python():
    from llmhive.app.data.frontier_roster_loader import load_paid_model_catalog

    catalog = load_paid_model_catalog()
    assert catalog
    assert catalog[0]["model_id"] == "anthropic/claude-opus-4.8"


def test_category_rankings_include_opus_48():
    payload = json.loads(
        (ROOT / "lib" / "marketing" / "usecase-category-rankings.generated.json").read_text(
            encoding="utf-8"
        )
    )
    programming = [
        row["model_id"] for row in (payload.get("categories") or {}).get("programming") or []
    ]
    assert "anthropic/claude-opus-4.8" in programming
    assert programming.index("anthropic/claude-opus-4.8") < programming.index(
        "anthropic/claude-opus-4.7"
    )
