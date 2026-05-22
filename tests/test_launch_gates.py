from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_launch_gates import run_checks


def test_launch_gates_script_runs():
    """Gate script returns structured result (may skip chat without secrets)."""
    result = run_checks()
    assert "checks" in result
    assert isinstance(result["checks"], list)
