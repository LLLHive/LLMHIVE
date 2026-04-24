from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_market_release_isolation import (
    BENCHMARK_CRITICAL,
    MINIMAL_RUNTIME_RELEASE,
)


def test_minimal_market_release_surface_does_not_overlap_benchmark_files():
    assert MINIMAL_RUNTIME_RELEASE.isdisjoint(BENCHMARK_CRITICAL)


def test_runtime_release_surface_stays_minimal():
    assert MINIMAL_RUNTIME_RELEASE == {"proxy.ts", "cloudbuild.yaml"}
