#!/usr/bin/env python3
"""
LLMHive — Authentication & Pre-Certification Verification
==========================================================
Verifies all API keys, environment variables, evaluator commands,
cost/runtime caps, and Cloud Run configuration before allowing a
certification benchmark run.

Usage:
    python scripts/verify_authentication.py [--json]

Exit codes:
    0  All checks passed — ready for execution.
    1  One or more checks failed — abort.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent

# ===================================================================
# Readiness state — accumulates results across all phases
# ===================================================================

_readiness: Dict[str, Any] = {
    "timestamp": datetime.now().isoformat(),
    "authentication": "PENDING",
    "api_key_verified": False,
    "hf_authenticated": False,
    "google_models_available": False,
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
    print(f"  ✅  {msg}")


def _fail(key: str, msg: str) -> None:
    _readiness[key] = False
    _failures.append(msg)
    print(f"  ❌  {msg}")


def _skip(key: str, msg: str) -> None:
    print(f"  ⏭   {msg}")


# ===================================================================
# PHASE 1 — Local Authentication Verification
# ===================================================================

def verify_api_key() -> None:
    """Check API_KEY / LLMHIVE_API_KEY and hit the orchestrator health endpoint."""
    api_key = os.getenv("API_KEY") or os.getenv("LLMHIVE_API_KEY")
    if not api_key:
        _fail("api_key_verified", "API_KEY / LLMHIVE_API_KEY not set")
        return

    api_url = os.getenv(
        "LLMHIVE_API_URL",
        "https://llmhive-orchestrator-792354158895.us-east1.run.app",
    )

    if not _HAS_HTTPX:
        _fail("api_key_verified", "httpx not installed — cannot verify API health")
        return

    try:
        r = httpx.get(f"{api_url}/health", timeout=15)
        if r.status_code == 200:
            _pass("api_key_verified", f"API health OK ({api_url})")
        else:
            _fail("api_key_verified", f"API health returned HTTP {r.status_code}")
    except Exception as exc:
        _fail("api_key_verified", f"API health unreachable: {exc}")


def verify_hf_token() -> None:
    """Check HF_TOKEN exists, run whoami, and verify authenticated access."""
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        _fail("hf_authenticated", "HF_TOKEN not set")
        return

    if not _HAS_HTTPX:
        _fail("hf_authenticated", "httpx not installed — cannot verify HF auth")
        return

    try:
        r = httpx.get(
            "https://huggingface.co/api/whoami",
            headers={"Authorization": f"Bearer {hf_token}"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            username = data.get("name", data.get("fullname", "unknown"))
            _pass("hf_authenticated", f"HF authenticated as: {username}")
        elif r.status_code == 401:
            _fail("hf_authenticated", "HF_TOKEN invalid or expired")
            print("       ─────────────────────────────────────────────")
            print("       HF_TOKEN invalid or expired.")
            print("       Run:  huggingface-cli login")
            print("       Then: export HF_TOKEN=$(cat ~/.cache/huggingface/token)")
            print("       ─────────────────────────────────────────────")
        else:
            _fail("hf_authenticated", f"HF whoami returned HTTP {r.status_code}")
    except Exception as exc:
        _fail("hf_authenticated", f"HF whoami failed: {exc}")

    try:
        r = httpx.head(
            "https://huggingface.co/api/datasets/openai/gsm8k",
            headers={"Authorization": f"Bearer {hf_token}"},
            timeout=15,
        )
        if r.status_code in (200, 302):
            print("       Dataset metadata download OK")
        else:
            print(f"       ⚠ Dataset metadata returned HTTP {r.status_code}")
    except Exception:
        pass


def verify_google_ai() -> None:
    """If GOOGLE_AI_API_KEY set, query models endpoint and confirm availability."""
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        _skip("google_models_available", "GOOGLE_AI_API_KEY not set — skipping Google verification")
        return

    if not _HAS_HTTPX:
        _fail("google_models_available", "httpx not installed — cannot verify Google AI")
        return

    try:
        r = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=15,
        )
        if r.status_code == 200:
            models = r.json().get("models", [])
            prod = [
                m for m in models
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "exp" not in m.get("name", "").lower()
            ]
            if prod:
                _pass("google_models_available", f"Google AI: {len(prod)} production models available")
            else:
                _fail("google_models_available", "Google AI: no production models found")
        elif r.status_code == 404:
            _fail("google_models_available", "Google AI: models endpoint returned 404")
        else:
            _fail("google_models_available", f"Google AI: models endpoint returned HTTP {r.status_code}")
    except Exception as exc:
        _fail("google_models_available", f"Google AI verification failed: {exc}")


def phase_1() -> None:
    print("\n" + "=" * 70)
    print("PHASE 1 — LOCAL AUTHENTICATION VERIFICATION")
    print("=" * 70)
    verify_api_key()
    verify_hf_token()
    verify_google_ai()

    if _readiness["api_key_verified"] and _readiness["hf_authenticated"]:
        _readiness["authentication"] = "PASS"
    else:
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
        print(f"  ⚠  Commit mismatch: local={local_commit} remote={remote_commit}")
        print("       (Acceptable if deploying from this branch)")

    required_vars = [
        "HF_TOKEN", "API_KEY", "MAX_RUNTIME_MINUTES", "MAX_TOTAL_COST_USD",
    ]
    optional_provider_vars = [
        "GOOGLE_AI_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY",
    ]
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

    missing_optional = [v for v in optional_provider_vars if not os.getenv(v)]
    if missing_optional:
        print(f"       Note: optional provider keys not set: {', '.join(missing_optional)}")
        print("       (These providers will be skipped during benchmark)")


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
                print(f"  ℹ   {name} auto-resolved from {auto_script}")

        if not cmd:
            print(f"  ❌  {name} not set and script not found")
            all_ok = False
            continue

        if "{output_path}" not in cmd:
            print(f"  ❌  {name} missing {{output_path}} placeholder")
            all_ok = False
        else:
            print(f"  ✅  {name} OK")

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
# PHASE 6 — Provider Connectivity Verification
# ===================================================================

def phase_6_providers() -> None:
    print("\n" + "=" * 70)
    print("PHASE 6 — PROVIDER CONNECTIVITY VERIFICATION")
    print("=" * 70)

    try:
        from verify_all_providers import verify_all_providers
        report = verify_all_providers()
    except ImportError:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "verify_all_providers", _SCRIPTS_DIR / "verify_all_providers.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            report = mod.verify_all_providers()
        except Exception as exc:
            print(f"  Could not run provider verification: {exc}")
            _readiness["providers"] = {}
            return

    provider_results = report.get("providers", {})
    _readiness["providers"] = {
        k: v.get("status", "UNKNOWN") for k, v in provider_results.items()
    }

    passed = [k for k, v in provider_results.items() if v.get("status") == "PASS"]
    failed = [k for k, v in provider_results.items() if v.get("status") == "FAIL"]

    if failed:
        _fail("providers_verified", f"Provider failures: {', '.join(failed)}")
    elif passed:
        _pass("providers_verified", f"{len(passed)} providers verified")
    else:
        print("  ℹ   No provider keys configured — skipping")


# ===================================================================
# PHASE 7 — Readiness Report
# ===================================================================

def phase_7() -> None:
    print("\n" + "=" * 70)
    print("PHASE 7 — READINESS REPORT")
    print("=" * 70)

    all_critical = all([
        _readiness["api_key_verified"],
        _readiness["hf_authenticated"],
        _readiness["cost_cap_verified"],
        _readiness["runtime_cap_verified"],
        _readiness["certification_lock_active"],
        _readiness["certification_override_active"],
        _readiness["evaluator_placeholders_valid"],
    ])

    # Provider failures block certification only if a provider was
    # configured (key set) but its test call failed.
    provider_hard_fail = any(
        v == "FAIL" for v in _readiness.get("providers", {}).values()
    )
    if provider_hard_fail:
        all_critical = False

    _readiness["ready_for_execution"] = all_critical
    _readiness["authentication"] = "PASS" if _readiness["api_key_verified"] and _readiness["hf_authenticated"] else "FAIL"
    _readiness["failures"] = _failures if _failures else []

    print()
    print(f"  {'Check':<35} {'Status':<10}")
    print(f"  {'-'*35} {'-'*10}")

    display_keys = [
        ("API Key Verified", "api_key_verified"),
        ("HF Authenticated", "hf_authenticated"),
        ("Google Models Available", "google_models_available"),
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
        icon = "PASS" if val else ("FAIL" if val is False else "SKIP")
        print(f"  {label:<35} {icon:<10}")

    # Provider detail table
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
    """Return 0 if ready, 1 if not."""
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
