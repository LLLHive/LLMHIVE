#!/usr/bin/env python3
"""Run the minimal market-release no-regression gate.

Default behavior is intentionally safe:
- run only focused local tests
- run only static benchmark-isolation verification
- do not hit live production unless explicitly requested

This gate is designed to protect the minimal launch release surface without
touching benchmark execution or runtime orchestration behavior.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

FOCUSED_TESTS = [
    "tests/test_market_release_isolation.py",
    "tests/test_verify_minimal_launch_release.py",
    "tests/test_launch_verification_tooling.py",
]


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the minimal market-release gate.")
    parser.add_argument(
        "--include-live",
        action="store_true",
        help="Also run the live read-only minimal release verifier.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    checks: list[dict[str, object]] = []

    rc, output = _run(["pytest", *FOCUSED_TESTS, "-q"])
    checks.append(
        {
            "name": "focused_release_tests",
            "passed": rc == 0,
            "detail": output.splitlines()[-1] if output else "no output",
        }
    )

    rc, output = _run(["python", "scripts/verify_market_release_isolation.py"])
    checks.append(
        {
            "name": "benchmark_isolation",
            "passed": rc == 0,
            "detail": output,
        }
    )

    if args.include_live:
        rc, output = _run(["python", "scripts/verify_minimal_launch_release.py", "--json"])
        checks.append(
            {
                "name": "live_minimal_release_verifier",
                "passed": rc == 0,
                "detail": output,
            }
        )

    overall_pass = all(bool(check["passed"]) for check in checks)

    if args.as_json:
        print(json.dumps({"passed": overall_pass, "checks": checks}, indent=2))
    else:
        print("=" * 70)
        print("MARKET RELEASE GATE")
        print("=" * 70)
        for check in checks:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"[{status}] {check['name']}")
            print(f"  {check['detail']}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
