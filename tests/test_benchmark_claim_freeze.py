from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_benchmark_claim_freeze import run_checks


def test_benchmark_claim_freeze_passes():
    result = run_checks()
    assert result["passed"] is True, result.get("issues", [])
