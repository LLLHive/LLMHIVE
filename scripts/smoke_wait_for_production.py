#!/usr/bin/env python3
"""Block until production orchestrator passes health checks (post-deploy warm-up)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.smoke.conftest import warm_up_production  # noqa: E402


def main() -> int:
    url = os.environ.get("PRODUCTION_URL", "").strip().rstrip("/")
    if not url:
        print("PRODUCTION_URL is required", file=sys.stderr)
        return 1

    session = requests.Session()
    try:
        path, latency_ms = warm_up_production(session, url)
    except RuntimeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    print(f"Production ready via {path} (last warm-up latency: {latency_ms:.0f}ms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
