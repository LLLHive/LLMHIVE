#!/usr/bin/env python3
"""Promote a passing release candidate — generate release_manifest.json.

Reads rc_summary.json, verifies gate passed, and writes
public/release_manifest.json with deployment metadata.

Usage:
    python scripts/promote_release_candidate.py
    python scripts/promote_release_candidate.py --force  # skip gate check
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_RC_SUMMARY = _ROOT / "benchmark_reports" / "rc_summary.json"
_MANIFEST = _ROOT / "public" / "release_manifest.json"


def main():
    force = "--force" in sys.argv

    if not _RC_SUMMARY.exists():
        print(f"ERROR: {_RC_SUMMARY} not found. Run run_release_candidate.py first.")
        sys.exit(2)

    summary = json.loads(_RC_SUMMARY.read_text())

    if summary.get("gate_status") != "pass" and not force:
        print(f"ERROR: RC gate status is '{summary.get('gate_status')}'. Cannot promote.")
        print("  Use --force to override (not recommended).")
        for f in summary.get("p0_failures", []):
            print(f"  P0: {f}")
        sys.exit(1)

    # Require evidence bundle artifacts
    required_artifacts = ["gate_result.json", "preflight_report.json", "synthetic_suite_results.json"]
    latest_dir = _ROOT / "benchmark_reports" / "latest"
    missing = [a for a in required_artifacts if not (latest_dir / a).exists()]
    if missing and not force:
        print(f"ERROR: Missing required artifacts in benchmark_reports/latest/:")
        for m in missing:
            print(f"  - {m}")
        print("  Run: python scripts/run_release_candidate.py")
        sys.exit(1)

    # Get model registry version and integrity hash
    sys.path.insert(0, str(_ROOT / "llmhive" / "src"))
    try:
        from llmhive.app.orchestration.model_registry import (
            MODEL_REGISTRY_VERSION,
            REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE,
            compute_registry_integrity_hash,
            check_champion_challenger_gate,
        )
        registry_hash = compute_registry_integrity_hash()
    except ImportError:
        MODEL_REGISTRY_VERSION = "unknown"
        REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE = False
        registry_hash = "unknown"
        check_champion_challenger_gate = None

    # Champion/challenger gate: block promotion if registry version bumped
    # without a passing RC gate
    if check_champion_challenger_gate and not force:
        existing_manifest = {}
        if _MANIFEST.exists():
            existing_manifest = json.loads(_MANIFEST.read_text())
        prev_ver = existing_manifest.get("model_registry_version", MODEL_REGISTRY_VERSION)
        if str(prev_ver) != str(MODEL_REGISTRY_VERSION):
            if not check_champion_challenger_gate(MODEL_REGISTRY_VERSION, str(_RC_SUMMARY)):
                print(
                    f"ERROR: Registry version changed ({prev_ver} → {MODEL_REGISTRY_VERSION}) "
                    f"but RC gate has not passed for the new version."
                )
                print("  Set REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE=0 or use --force to override.")
                sys.exit(1)

    git_sha = summary.get("git_sha", "unknown")
    if git_sha == "unknown":
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(_ROOT))
            if r.returncode == 0:
                git_sha = r.stdout.strip()[:12]
        except Exception:
            pass

    # Read launch mode config snapshot (redact secrets)
    config_snapshot = {}
    for key in [
        "ELITE_PLUS_ENABLED", "ELITE_PLUS_MODE", "ELITE_PLUS_POLICY",
        "PREMIUM_DEFAULT_TIER", "ELITE_PUBLIC_ENABLED", "ELITE_FALLBACK_ENABLED",
        "ELITE_PLUS_MAX_PAID_CALLS", "ELITE_PLUS_BUDGET_USD_P50",
        "ELITE_PLUS_BUDGET_USD_P95", "ELITE_PLUS_LAUNCH_MODE",
        "ELITE_PLUS_MAX_COST_USD_REQUEST",
    ]:
        val = os.getenv(key)
        if val is not None:
            config_snapshot[key] = val

    manifest = {
        "version": "1",
        "model_registry_version": MODEL_REGISTRY_VERSION,
        "registry_integrity_hash": registry_hash,
        "gate_timestamp": summary.get("timestamp"),
        "promote_timestamp": datetime.now().isoformat(),
        "git_sha": git_sha,
        "gate_status": summary.get("gate_status"),
        "launch_mode_enabled": os.getenv("ELITE_PLUS_LAUNCH_MODE", "0") == "1",
        "config_snapshot": config_snapshot,
        "total_samples_evaluated": summary.get("total_samples", 0),
        "p0_failures": summary.get("p0_failures", []),
        "forced": force,
        "champion_challenger_enforced": REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE
            if isinstance(REQUIRE_RC_GATE_PASS_FOR_REGISTRY_UPDATE, bool)
            else False,
    }

    # Evidence bundle listing
    latest_artifacts = []
    if latest_dir.exists():
        latest_artifacts = sorted(f.name for f in latest_dir.iterdir() if f.is_file())
    manifest["evidence_bundle"] = latest_artifacts

    _MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Release manifest written: {_MANIFEST}")
    print(f"  Registry version: {MODEL_REGISTRY_VERSION}")
    print(f"  Git SHA: {git_sha}")
    print(f"  Gate: {summary.get('gate_status')}")
    print(f"  Evidence artifacts: {len(latest_artifacts)}")

    # Copy marketing benchmark if present
    mkt_md = latest_dir / "marketing_benchmark.md"
    if mkt_md.exists():
        dest = _MANIFEST.parent / "marketing_benchmark.md"
        import shutil
        shutil.copy2(mkt_md, dest)
        print(f"  Marketing benchmark copied to {dest}")

    if force:
        print("  WARNING: Promoted with --force (gate may not have passed)")


if __name__ == "__main__":
    main()
