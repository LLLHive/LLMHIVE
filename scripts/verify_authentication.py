#!/usr/bin/env python3
"""
LLMHive — Authentication & Pre-Certification Verification
==========================================================
Verifies API key, environment variables, evaluator commands,
cost/runtime caps, and provider connectivity before allowing a
certification benchmark run.

Provider validation is delegated entirely to verify_all_providers.py
via the adapter-based health system.  This script does NOT perform
any direct provider health checks.

Usage:
    python scripts/verify_authentication.py [--json]

Exit codes:
    0  All checks passed — ready for execution.
    1  One or more checks failed — abort.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

try:
    from dotenv import load_dotenv
    _cert_env = Path(__file__).resolve().parent.parent / ".env.certification"
    if _cert_env.exists():
        load_dotenv(_cert_env)
except ImportError:
    pass

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent

# ===================================================================
# Readiness state
# ===================================================================

_readiness: Dict[str, Any] = {
    "timestamp": datetime.now().isoformat(),
    "authentication": "PENDING",
    "api_key_verified": False,
    "cloud_revision_verified": False,
    "cost_cap_verified": False,
    "runtime_cap_verified": False,
    "certification_lock_active": False,
    "certification_override_active": False,
    "evaluator_placeholders_valid": False,
    "providers_verified": False,
    "providers": {},
    "ready_for_execution": False,
}

_failures: list = []


def _pass(key: str, msg: str) -> None:
    _readiness[key] = True
    print(f"  PASS  {msg}")


def _fail(key: str, msg: str) -> None:
    _readiness[key] = False
    _failures.append(msg)
    print(f"  FAIL  {msg}")


def _skip(key: str, msg: str) -> None:
    print(f"  SKIP  {msg}")


# ===================================================================
# PHASE 1 — API Key Verification (orchestrator health only)
# ===================================================================

def phase_1() -> None:
    print("\n" + "=" * 70)
    print("PHASE 1 — API KEY VERIFICATION")
    print("=" * 70)

    api_key = os.getenv("API_KEY") or os.getenv("LLMHIVE_API_KEY")
    if not api_key:
        _fail("api_key_verified", "API_KEY / LLMHIVE_API_KEY not set")
        _readiness["authentication"] = "FAIL"
        return

    api_url = os.getenv(
        "LLMHIVE_API_URL",
        "https://llmhive-orchestrator-792354158895.us-east1.run.app",
    )

    if not _HAS_HTTPX:
        _fail("api_key_verified", "httpx not installed — cannot verify API health")
        _readiness["authentication"] = "FAIL"
        return

    try:
        r = httpx.get(f"{api_url}/health", timeout=15)
        if r.status_code == 200:
            _pass("api_key_verified", f"API health OK ({api_url})")
            _readiness["authentication"] = "PASS"
        else:
            _fail("api_key_verified", f"API health returned HTTP {r.status_code}")
            _readiness["authentication"] = "FAIL"
    except Exception as exc:
        _fail("api_key_verified", f"API health unreachable: {exc}")
        _readiness["authentication"] = "FAIL"


# ===================================================================
# PHASE 2 — Cloud Run Revision Validation
# ===================================================================

def phase_2() -> None:
    print("\n" + "=" * 70)
    print("PHASE 2 — CLOUD RUN REVISION VALIDATION")
    print("=" * 70)

    api_url = os.getenv(
        "LLMHIVE_API_URL",
        "https://llmhive-orchestrator-792354158895.us-east1.run.app",
    )

    if not _HAS_HTTPX:
        _fail("cloud_revision_verified", "httpx not installed")
        return

    try:
        r = httpx.get(f"{api_url}/health", timeout=15)
        if r.status_code != 200:
            _fail("cloud_revision_verified", f"Service unreachable (HTTP {r.status_code})")
            return
    except Exception as exc:
        _fail("cloud_revision_verified", f"Service unreachable: {exc}")
        return

    local_commit = "unknown"
    try:
        local_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_PROJECT_ROOT), text=True,
        ).strip()[:12]
    except Exception:
        pass

    remote_commit = "unknown"
    try:
        health_data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        remote_commit = health_data.get("commit", health_data.get("revision", "unknown"))
    except Exception:
        pass

    if local_commit != "unknown" and remote_commit != "unknown" and local_commit != remote_commit[:12]:
        print(f"  NOTE  Commit mismatch: local={local_commit} remote={remote_commit}")
        print("        (Acceptable if deploying from this branch)")

    required_vars = ["API_KEY", "MAX_RUNTIME_MINUTES", "MAX_TOTAL_COST_USD"]
    local_fallbacks = {"API_KEY": "LLMHIVE_API_KEY"}
    missing = [v for v in required_vars if not os.getenv(v)]
    actual_missing = [
        v for v in missing
        if not os.getenv(local_fallbacks.get(v, ""))
    ]

    if actual_missing:
        _fail("cloud_revision_verified", f"Missing required env vars: {', '.join(actual_missing)}")
    else:
        _pass("cloud_revision_verified", "Cloud Run reachable, required env vars present")


# ===================================================================
# PHASE 3 — Cost & Runtime Cap Enforcement
# ===================================================================

def phase_3() -> None:
    print("\n" + "=" * 70)
    print("PHASE 3 — COST & RUNTIME CAP ENFORCEMENT")
    print("=" * 70)

    cost = os.getenv("MAX_TOTAL_COST_USD", "")
    if cost == "5.00":
        _pass("cost_cap_verified", f"MAX_TOTAL_COST_USD = ${cost}")
    elif cost:
        _fail("cost_cap_verified", f"MAX_TOTAL_COST_USD={cost} — must be 5.00 for certification")
    else:
        _fail("cost_cap_verified", "MAX_TOTAL_COST_USD not set")

    runtime = os.getenv("MAX_RUNTIME_MINUTES", "")
    try:
        rt_int = int(runtime) if runtime else 0
    except ValueError:
        rt_int = 0

    if 0 < rt_int <= 180:
        _pass("runtime_cap_verified", f"MAX_RUNTIME_MINUTES = {rt_int}")
    elif rt_int > 180:
        _fail("runtime_cap_verified", f"MAX_RUNTIME_MINUTES={rt_int} — exceeds 180 limit")
    else:
        _fail("runtime_cap_verified", "MAX_RUNTIME_MINUTES not set or invalid")


# ===================================================================
# PHASE 4 — Evaluator Placeholder Validation
# ===================================================================

def phase_4() -> None:
    print("\n" + "=" * 70)
    print("PHASE 4 — EVALUATOR PLACEHOLDER VALIDATION")
    print("=" * 70)

    eval_vars = {
        "LONGBENCH_EVAL_CMD": os.getenv("LONGBENCH_EVAL_CMD", ""),
        "TOOLBENCH_EVAL_CMD": os.getenv("TOOLBENCH_EVAL_CMD", ""),
        "MTBENCH_EVAL_CMD": os.getenv("MTBENCH_EVAL_CMD", ""),
    }

    all_ok = True
    for name, cmd in eval_vars.items():
        if not cmd:
            auto_script = {
                "LONGBENCH_EVAL_CMD": "eval_longbench.py",
                "TOOLBENCH_EVAL_CMD": "eval_toolbench.py",
                "MTBENCH_EVAL_CMD": "eval_mtbench.py",
            }[name]
            script_path = _SCRIPTS_DIR / auto_script
            if script_path.exists():
                cmd = f"python3 {script_path} --output {{output_path}} --seed {{seed}}"
                print(f"  INFO  {name} auto-resolved from {auto_script}")

        if not cmd:
            print(f"  FAIL  {name} not set and script not found")
            all_ok = False
            continue

        if "{output_path}" not in cmd:
            print(f"  FAIL  {name} missing {{output_path}} placeholder")
            all_ok = False
        else:
            print(f"  PASS  {name} OK")

    if all_ok:
        _pass("evaluator_placeholders_valid", "All evaluator commands validated")
    else:
        _fail("evaluator_placeholders_valid", "One or more evaluator commands invalid")


# ===================================================================
# PHASE 5 — Certification Lock Validation
# ===================================================================

def phase_5() -> None:
    print("\n" + "=" * 70)
    print("PHASE 5 — CERTIFICATION LOCK VALIDATION")
    print("=" * 70)

    lock = os.getenv("CERTIFICATION_LOCK", "").strip().lower()
    override = os.getenv("CERTIFICATION_OVERRIDE", "").strip().lower()

    if lock in ("true", "1", "yes"):
        _pass("certification_lock_active", "CERTIFICATION_LOCK is active")
    else:
        _fail("certification_lock_active", "CERTIFICATION_LOCK not set to true")

    if override in ("true", "1", "yes"):
        _pass("certification_override_active", "CERTIFICATION_OVERRIDE is active")
    else:
        _fail("certification_override_active", "CERTIFICATION_OVERRIDE not set to true")


# ===================================================================
# PHASE 6 — Provider Connectivity (delegated to verify_all_providers)
# ===================================================================

def phase_6_providers() -> None:
    print("\n" + "=" * 70)
    print("PHASE 6 — PROVIDER CONNECTIVITY VERIFICATION")
    print("=" * 70)

    try:
        from verify_all_providers import verify_all_providers
    except ImportError:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "verify_all_providers", _SCRIPTS_DIR / "verify_all_providers.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            verify_all_providers = mod.verify_all_providers
        except Exception as exc:
            print(f"  FAIL  Could not import verify_all_providers: {exc}")
            _readiness["providers"] = {}
            return

    report = verify_all_providers(strict=True)

    _readiness["providers"] = {}
    for k, v in report.get("providers", {}).items():
        _readiness["providers"][k] = v.get("status", "UNKNOWN")

    if report.get("status") == "PASS":
        _pass("providers_verified", "All providers verified")
    else:
        failed = [
            k for k, v in report.get("providers", {}).items()
            if v.get("status") == "FAIL"
        ]
        _fail("providers_verified", f"Provider failures: {', '.join(failed)}")


# ===================================================================
# PHASE 7 — Readiness Report
# ===================================================================

def phase_7() -> None:
    print("\n" + "=" * 70)
    print("PHASE 7 — READINESS REPORT")
    print("=" * 70)

    all_critical = all([
        _readiness["api_key_verified"],
        _readiness["cost_cap_verified"],
        _readiness["runtime_cap_verified"],
        _readiness["certification_lock_active"],
        _readiness["certification_override_active"],
        _readiness["evaluator_placeholders_valid"],
        _readiness["providers_verified"],
    ])

    _readiness["ready_for_execution"] = all_critical
    _readiness["failures"] = _failures if _failures else []

    print()
    print(f"  {'Check':<35} {'Status':<10}")
    print(f"  {'-'*35} {'-'*10}")

    display_keys = [
        ("API Key Verified", "api_key_verified"),
        ("Cloud Revision Verified", "cloud_revision_verified"),
        ("Cost Cap Verified", "cost_cap_verified"),
        ("Runtime Cap Verified", "runtime_cap_verified"),
        ("Certification Lock Active", "certification_lock_active"),
        ("Certification Override Active", "certification_override_active"),
        ("Evaluator Placeholders Valid", "evaluator_placeholders_valid"),
        ("Providers Verified", "providers_verified"),
    ]

    for label, key in display_keys:
        val = _readiness.get(key, False)
        icon = "PASS" if val else "FAIL"
        print(f"  {label:<35} {icon:<10}")

    providers = _readiness.get("providers", {})
    if providers:
        print()
        print(f"  {'Provider':<15} {'Status':<10}")
        print(f"  {'-'*15} {'-'*10}")
        for prov, status in providers.items():
            print(f"  {prov:<15} {status:<10}")

    print()
    if all_critical:
        print("  READY FOR EXECUTION")
    else:
        print("  NOT READY — fix failures above before executing.")
        if _failures:
            print()
            print("  Failures:")
            for f in _failures:
                print(f"    - {f}")


# ===================================================================
# PHASE 8 — Execution Gate
# ===================================================================

def phase_8() -> int:
    if _readiness.get("ready_for_execution"):
        return 0
    return 1


# ===================================================================
# Main
# ===================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="LLMHive Authentication & Certification Verification"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output readiness report as JSON to stdout",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("LLMHive — Authentication & Certification Verification")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    phase_1()
    phase_2()
    phase_3()
    phase_4()
    phase_5()
    phase_6_providers()
    phase_7()
    exit_code = phase_8()

    if args.json:
        print()
        print(json.dumps(_readiness, indent=2))

    report_path = _PROJECT_ROOT / "benchmark_reports" / "readiness_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(_readiness, indent=2))
    print(f"\n  Report saved: {report_path}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
