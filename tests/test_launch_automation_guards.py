from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.verify_launch_automation_guards import run_checks


def _by_name(checks, name: str):
    return next(c for c in checks if c["name"] == name)


def test_launch_automation_guards_pass():
    result = run_checks()
    assert result["passed"] is True


def test_recurring_automation_is_pr_routed():
    checks = run_checks()["checks"]
    assert _by_name(checks, "modeldb_refresh_routes_to_pr_branch")["passed"] is True
    assert _by_name(checks, "weekly_improvement_routes_to_pr_branch")["passed"] is True
    assert _by_name(checks, "auto_restore_routes_to_pr_branch")["passed"] is True
    assert _by_name(checks, "automation_workflows_avoid_direct_main_push")["passed"] is True


def test_post_incident_workflow_safety_hooks_remain_present():
    checks = run_checks()["checks"]
    assert _by_name(checks, "secure_history_manual_only")["passed"] is True
    assert _by_name(checks, "scheduled_benchmarks_exports_api_key_aliases")["passed"] is True
    assert _by_name(checks, "smoke_tests_capture_latency_diagnostics")["passed"] is True
