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
    assert "anthropic/claude-opus-5" in ui_ids
    assert "anthropic/claude-opus-4.8" in ui_ids
    paid_ids = [m["model_id"] for m in payload.get("paid_catalog") or []]
    assert paid_ids[0] == "anthropic/claude-opus-5"


def test_generated_surfaces_are_current():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_frontier_surfaces.py"), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_models_generated_includes_opus_5():
    text = (ROOT / "lib" / "models.generated.ts").read_text(encoding="utf-8")
    assert "anthropic/claude-opus-5" in text
    assert "anthropic/claude-opus-4.8" in text


def test_paid_catalog_generated_loads_in_python():
    from llmhive.app.data.frontier_roster_loader import load_paid_model_catalog

    catalog = load_paid_model_catalog()
    assert catalog
    assert catalog[0]["model_id"] == "anthropic/claude-opus-5"


def test_category_rankings_include_opus_5():
    payload = json.loads(
        (ROOT / "lib" / "marketing" / "usecase-category-rankings.generated.json").read_text(
            encoding="utf-8"
        )
    )
    programming = [
        row["model_id"] for row in (payload.get("categories") or {}).get("programming") or []
    ]
    assert "anthropic/claude-opus-5" in programming
    assert programming.index("anthropic/claude-opus-5") < programming.index(
        "anthropic/claude-opus-4.8"
    )


def _load_drift_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_frontier_surface_drift",
        ROOT / "scripts" / "check_frontier_surface_drift.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_latest_family_slug_skips_batch_and_snapshots():
    drift = _load_drift_module()
    or_ids = {
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-luna:batch",
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-pro-0813",
        "google/gemini-3.6-flash",
        "google/gemini-3.6-flash:batch",
        "z-ai/glm-5.1",
        "z-ai/glm-5.2:batch",
    }
    assert drift._latest_family_slug(or_ids, "openai/gpt-5.6-") == "openai/gpt-5.6-luna"
    assert drift._latest_family_slug(or_ids, "deepseek/deepseek-v4-") == "deepseek/deepseek-v4-pro"
    assert (
        drift._latest_family_slug(or_ids, "google/gemini-3.6-") == "google/gemini-3.6-flash"
    )
    assert drift._latest_family_slug(or_ids, "z-ai/glm-5.") == "z-ai/glm-5.1"
