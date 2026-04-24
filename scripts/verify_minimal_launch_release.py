#!/usr/bin/env python3
"""Verify the minimal launch release after deployment.

Checks only the release-surface risks identified during market-readiness work:
1. `llmhive.vercel.app` redirects to the canonical domain
2. Canonical sign-in page renders expected Clerk UI markers
3. Canonical root redirects into sign-in flow
4. Backend health endpoint responds
5. Backend build-info exposes a non-unknown commit
6. Internal launch KPI endpoint works when an internal key is provided

This script is read-only and does not mutate production state.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any

import requests


DEFAULT_VERCEL_BASE = "https://llmhive.vercel.app"
DEFAULT_CANONICAL_BASE = "https://www.llmhive.ai"
DEFAULT_BACKEND_BASE = "https://llmhive-orchestrator-7h6b36l7ta-ue.a.run.app"
REDIRECT_CODES = {301, 302, 307, 308}


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str = "P0"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify minimal launch release state.")
    parser.add_argument("--vercel-base", default=DEFAULT_VERCEL_BASE)
    parser.add_argument("--canonical-base", default=DEFAULT_CANONICAL_BASE)
    parser.add_argument("--backend-base", default=DEFAULT_BACKEND_BASE)
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-backend", action="store_true")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def _get(url: str, *, timeout: int, allow_redirects: bool = True, headers: dict[str, str] | None = None):
    return requests.get(url, timeout=timeout, allow_redirects=allow_redirects, headers=headers or {})


def _probe_redirect(url: str, *, timeout: int) -> requests.Response:
    """Prefer HEAD for redirect probes to avoid slow full-body reads."""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=False)
        if response.status_code in REDIRECT_CODES:
            return response
        if response.status_code == 405:
            return _get(url, timeout=timeout, allow_redirects=False)
        return response
    except requests.RequestException:
        return _get(url, timeout=timeout, allow_redirects=False)


def _check_vercel_redirect(vercel_base: str, canonical_base: str, timeout: int) -> CheckResult:
    url = f"{vercel_base.rstrip('/')}/sign-in"
    try:
        response = _probe_redirect(url, timeout=timeout)
        location = response.headers.get("Location", "")
        expected_host = canonical_base.rstrip("/").replace("https://", "").replace("http://", "")
        passed = response.status_code in REDIRECT_CODES and expected_host in location
        return CheckResult(
            name="vercel_redirect",
            passed=passed,
            detail=f"status={response.status_code} location={location or '<none>'}",
        )
    except requests.RequestException as exc:
        return CheckResult("vercel_redirect", False, f"request_error={exc}")


def _check_sign_in_page(canonical_base: str, timeout: int) -> CheckResult:
    url = f"{canonical_base.rstrip('/')}/sign-in"
    try:
        response = _get(url, timeout=timeout)
        body = response.text
        shell_markers = ["Next-Generation AI Orchestration", "Protected by enterprise-grade security"]
        clerk_markers = ["https://clerk.llmhive.ai/npm/@clerk/clerk-js", "data-clerk-publishable-key="]
        passed = (
            response.status_code == 200
            and all(marker in body for marker in shell_markers)
            and all(marker in body for marker in clerk_markers)
        )
        return CheckResult(
            name="canonical_sign_in",
            passed=passed,
            detail=f"status={response.status_code} shell_and_clerk_markers_present={passed}",
        )
    except requests.RequestException as exc:
        return CheckResult("canonical_sign_in", False, f"request_error={exc}")


def _check_root_redirect(canonical_base: str, timeout: int) -> CheckResult:
    url = f"{canonical_base.rstrip('/')}/"
    try:
        response = _probe_redirect(url, timeout=timeout)
        location = response.headers.get("Location", "")
        passed = response.status_code in REDIRECT_CODES and "/sign-in" in location
        return CheckResult(
            name="canonical_root_redirect",
            passed=passed,
            detail=f"status={response.status_code} location={location or '<none>'}",
            severity="P1",
        )
    except requests.RequestException as exc:
        return CheckResult("canonical_root_redirect", False, f"request_error={exc}", severity="P1")


def _check_backend_health(backend_base: str, timeout: int) -> CheckResult:
    url = f"{backend_base.rstrip('/')}/health"
    try:
        response = _get(url, timeout=timeout)
        passed = response.status_code == 200
        return CheckResult(
            name="backend_health",
            passed=passed,
            detail=f"status={response.status_code}",
        )
    except requests.RequestException as exc:
        return CheckResult("backend_health", False, f"request_error={exc}")


def _check_build_info(backend_base: str, timeout: int) -> CheckResult:
    url = f"{backend_base.rstrip('/')}/build-info"
    try:
        response = _get(url, timeout=timeout)
        payload: dict[str, Any] = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        commit = payload.get("commit", "unknown")
        passed = response.status_code == 200 and commit != "unknown"
        return CheckResult(
            name="build_info",
            passed=passed,
            detail=f"status={response.status_code} commit={commit}",
        )
    except requests.RequestException as exc:
        return CheckResult("build_info", False, f"request_error={exc}")


def _check_launch_kpis(backend_base: str, timeout: int) -> CheckResult:
    internal_key = os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", "")
    if not internal_key:
        return CheckResult(
            name="launch_kpis",
            passed=True,
            detail="skipped (INTERNAL_ADMIN_OVERRIDE_KEY not set)",
            severity="P1",
        )

    url = f"{backend_base.rstrip('/')}/internal/launch_kpis"
    try:
        response = _get(url, timeout=timeout, headers={"X-LLMHive-Internal-Key": internal_key})
        passed = response.status_code == 200
        return CheckResult(
            name="launch_kpis",
            passed=passed,
            detail=f"status={response.status_code}",
            severity="P1",
        )
    except requests.RequestException as exc:
        return CheckResult("launch_kpis", False, f"request_error={exc}", severity="P1")


def main() -> int:
    args = _parse_args()
    checks: list[CheckResult] = []

    if not args.skip_frontend:
        checks.extend(
            [
                _check_vercel_redirect(args.vercel_base, args.canonical_base, args.timeout),
                _check_sign_in_page(args.canonical_base, args.timeout),
                _check_root_redirect(args.canonical_base, args.timeout),
            ]
        )

    if not args.skip_backend:
        checks.extend(
            [
                _check_backend_health(args.backend_base, args.timeout),
                _check_build_info(args.backend_base, args.timeout),
                _check_launch_kpis(args.backend_base, args.timeout),
            ]
        )

    if args.as_json:
        print(json.dumps([asdict(c) for c in checks], indent=2))
    else:
        print("=" * 70)
        print("MINIMAL LAUNCH RELEASE VERIFICATION")
        print("=" * 70)
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"[{status}] {check.name:<24} {check.detail}")

    hard_failures = [c for c in checks if not c.passed and c.severity == "P0"]
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
