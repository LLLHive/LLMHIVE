#!/usr/bin/env python3
"""Record production launch freeze snapshot.

Creates artifacts/launch_freeze/ with:
  - prod_identity.json (from /build-info, /health)
  - prod_env_snapshot.txt (non-secret env from build-info; gcloud for full snapshot)
  - prod_memory_cpu_snapshot.txt (from gcloud run services describe if available)
  - marketing_pack_pointer.txt (ref, release URL, checksums when publish/ exists)

Usage:
    export PROD_URL="https://llmhive-orchestrator-....run.app"
    python scripts/record_launch_freeze.py
    python scripts/record_launch_freeze.py --target "$PROD_URL"
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_OUTDIR = _ROOT / "artifacts" / "launch_freeze"


def _parse_args() -> dict:
    args = {"target": os.getenv("PROD_URL", "")}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("--target", "--base-url") and i + 1 < len(sys.argv):
            args["target"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def _fetch(url: str, timeout: int = 10) -> dict | None:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "LLMHive-LaunchFreeze/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def main() -> int:
    args = _parse_args()
    target = (args["target"] or "").rstrip("/")
    if not target:
        print("ERROR: Set PROD_URL or pass --target <url>")
        return 1

    _OUTDIR.mkdir(parents=True, exist_ok=True)

    # 1. prod_identity.json
    identity = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "prod_url": target,
        "build_info": None,
        "health": None,
    }
    if build := _fetch(f"{target}/build-info"):
        identity["build_info"] = build
    if health := _fetch(f"{target}/health"):
        identity["health"] = health
    (_OUTDIR / "prod_identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(f"  prod_identity.json: commit={identity.get('build_info', {}).get('commit', '?')}")

    # 2. prod_env_snapshot.txt (non-secret keys from build-info)
    lines = [
        f"# Production env snapshot (non-secret) — {datetime.now(timezone.utc).isoformat()}",
        f"# Source: {target}/build-info",
        "",
    ]
    if build := identity.get("build_info"):
        for k, v in build.items():
            lines.append(f"{k}={v}")
    lines.append("")
    lines.append("# Full env requires: gcloud run services describe llmhive-orchestrator --region us-east1 --format='yaml(spec.template.spec.containers[0].env)'")
    (_OUTDIR / "prod_env_snapshot.txt").write_text("\n".join(lines) + "\n")
    print("  prod_env_snapshot.txt: written")

    # 3. prod_memory_cpu_snapshot.txt (gcloud if available)
    try:
        r = subprocess.run(
            [
                "gcloud", "run", "services", "describe", "llmhive-orchestrator",
                "--region", "us-east1",
                "--format", "yaml(spec.template.spec.containers[0].resources)",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        content = f"# Cloud Run resources — {datetime.now(timezone.utc).isoformat()}\n\n{r.stdout}" if r.returncode == 0 else "# gcloud not available or failed\n"
    except Exception:
        content = "# gcloud not available\n"
    (_OUTDIR / "prod_memory_cpu_snapshot.txt").write_text(content)
    print("  prod_memory_cpu_snapshot.txt: written")

    # 4. marketing_pack_pointer.txt (when publish/ exists)
    publish = _ROOT / "artifacts" / "marketing_certified" / "publish"
    if publish.exists():
        prov_path = publish / "provenance.json"
        checksum_path = publish / "checksums.txt"
        ref = "unknown"
        if prov_path.exists():
            prov = json.loads(prov_path.read_text())
            ref = prov.get("ref", "unknown")
        checksums = checksum_path.read_text() if checksum_path.exists() else "(no checksums)"
        pointer = f"""# Marketing pack pointer — {datetime.now(timezone.utc).isoformat()}
ref={ref}
release_url=https://github.com/LLLHive/LLMHIVE/releases/tag/{ref}
publish_dir=artifacts/marketing_certified/publish/

## Checksums
{checksums}
"""
        (_OUTDIR / "marketing_pack_pointer.txt").write_text(pointer)
        print(f"  marketing_pack_pointer.txt: ref={ref}")
    else:
        (_OUTDIR / "marketing_pack_pointer.txt").write_text(
            f"# Marketing pack not yet generated — {datetime.now(timezone.utc).isoformat()}\n"
            "Run: python scripts/run_marketing_certified_release.py --ref certified-eliteplus-firestore-2026-03-07 --outdir artifacts/marketing_certified\n"
        )
        print("  marketing_pack_pointer.txt: (placeholder, run marketing pipeline first)")

    print()
    print(f"Launch freeze snapshot: {_OUTDIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
