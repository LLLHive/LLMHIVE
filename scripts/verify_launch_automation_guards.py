#!/usr/bin/env python3
"""Static safety checks for launch automation guardrails.

This verifier intentionally checks only repository configuration and workflow
content. It does not contact production systems, mutate remote state, or run
benchmarks.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

WORKFLOWS = {
    "modeldb_refresh": ".github/workflows/modeldb_refresh.yml",
    "weekly_improvement": ".github/workflows/weekly-improvement.yml",
    "auto_restore": ".github/workflows/auto-restore-critical-files.yaml",
    "secure_history": ".github/workflows/secure-history.yml",
    "scheduled_benchmarks": ".github/workflows/scheduled-benchmarks.yml",
    "smoke_tests": ".github/workflows/smoke-tests.yml",
}


def _workflow_text(name: str) -> str:
    return (ROOT / WORKFLOWS[name]).read_text()


def _check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"name": name, "passed": passed, "details": details}


def run_checks() -> dict[str, object]:
    checks: list[dict[str, object]] = []

    modeldb = _workflow_text("modeldb_refresh")
    weekly = _workflow_text("weekly_improvement")
    auto_restore = _workflow_text("auto_restore")
    secure_history = _workflow_text("secure_history")
    scheduled = _workflow_text("scheduled_benchmarks")
    smoke = _workflow_text("smoke_tests")

    checks.append(
        _check(
            "modeldb_refresh_routes_to_pr_branch",
            'BRANCH="automation/modeldb-refresh"' in modeldb
            and "gh pr create --base main --head" in modeldb,
            "ModelDB refresh must push to an automation branch and open/update a PR.",
        )
    )
    checks.append(
        _check(
            "weekly_improvement_routes_to_pr_branch",
            "automation/improvement-reports" in weekly
            and "gh pr create --base main --head" in weekly,
            "Improvement reports workflow must push to an automation branch and open/update a PR.",
        )
    )
    checks.append(
        _check(
            "weekly_improvement_no_force_push",
            "force-with-lease" not in weekly.lower(),
            "Improvement reports workflow must not force-push (report history must accumulate).",
        )
    )
    checks.append(
        _check(
            "auto_restore_routes_to_pr_branch",
            'BRANCH="automation/restore-critical-files"' in auto_restore
            and "gh pr create --base main --head" in auto_restore,
            "Auto-restore must push to an automation branch and open/update a PR.",
        )
    )
    checks.append(
        _check(
            "automation_workflows_avoid_direct_main_push",
            all(token not in (modeldb + weekly + auto_restore) for token in ('git push origin main', 'git push origin "$DEFAULT_BRANCH"')),
            "Recurring automation workflows must not push directly to main/default branch.",
        )
    )
    checks.append(
        _check(
            "secure_history_manual_only",
            "workflow_dispatch" in secure_history and "\npush:" not in secure_history,
            "Secure history rewrite must remain manual-only.",
        )
    )
    checks.append(
        _check(
            "scheduled_benchmarks_exports_api_key_aliases",
            'echo "API_KEY=$API_KEY" >> $GITHUB_ENV' in scheduled
            and 'echo "LLMHIVE_API_KEY=$API_KEY" >> $GITHUB_ENV' in scheduled,
            "Scheduled benchmarks must export both API_KEY and LLMHIVE_API_KEY.",
        )
    )
    checks.append(
        _check(
            "smoke_tests_capture_latency_diagnostics",
            "Capture Cloud Run latency diagnostics on failure" in smoke
            and '"/v1/chat"' in smoke,
            "Smoke tests must capture Cloud Run /v1/chat diagnostics on failure.",
        )
    )

    passed = all(bool(check["passed"]) for check in checks)
    return {
        "passed": passed,
        "checks": checks,
        "workflows": WORKFLOWS,
    }


def main() -> int:
    result = run_checks()
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
