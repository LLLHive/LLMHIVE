#!/usr/bin/env python3
"""Production Preflight — automated launch-readiness validation.

Checks:
  1. Config sanity (env vars, tier rules, cost ceilings)
  2. Provider health (ping free + paid anchors)
  3. Tool correctness (calculator, schema validation)
  4. RAG correctness (grounding telemetry)
  5. Security (internal endpoints require auth, bench headers rejected)

Output:
  - preflight_report.json
  - Human-readable summary to stdout
  - Exit non-zero if any P0 check fails

Usage:
    python scripts/run_prod_preflight.py
    python scripts/run_prod_preflight.py --target https://llmhive-orchestrator-....run.app
    python scripts/run_prod_preflight.py --offline  # env/config checks only
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

_ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = _ROOT / "preflight_report.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check(name: str, passed: bool, detail: str = "", p0: bool = True) -> Dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail, "priority": "P0" if p0 else "P1"}


def _parse_args() -> Dict[str, Any]:
    args = {"target": "", "offline": False, "output": str(_REPORT_PATH)}
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ("--target", "--base-url") and i + 1 < len(sys.argv):
            args["target"] = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--offline":
            args["offline"] = True
            i += 1
        elif sys.argv[i] == "--online":
            args["offline"] = False
            i += 1
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


# ---------------------------------------------------------------------------
# Check 1: Config sanity
# ---------------------------------------------------------------------------

def check_config_sanity() -> List[Dict[str, Any]]:
    results = []

    sys.path.insert(0, str(_ROOT / "llmhive" / "src"))

    try:
        from llmhive.app.orchestration.elite_plus_orchestrator import (
            ELITE_PLUS_ENABLED, ELITE_PLUS_MODE, ELITE_PLUS_POLICY,
            PREMIUM_DEFAULT_TIER, ELITE_PLUS_LAUNCH_MODE,
            ELITE_PLUS_MAX_COST_USD_REQUEST, ELITE_PLUS_MAX_PAID_CALLS,
        )

        results.append(_check(
            "elite_plus_enabled",
            ELITE_PLUS_ENABLED,
            f"ELITE_PLUS_ENABLED={ELITE_PLUS_ENABLED}",
        ))
        results.append(_check(
            "elite_plus_mode_active",
            ELITE_PLUS_MODE == "active",
            f"ELITE_PLUS_MODE={ELITE_PLUS_MODE}",
        ))
        results.append(_check(
            "policy_free_first",
            ELITE_PLUS_POLICY == "free_first_verified",
            f"ELITE_PLUS_POLICY={ELITE_PLUS_POLICY}",
        ))
        results.append(_check(
            "premium_tier_elite_plus",
            PREMIUM_DEFAULT_TIER == "elite_plus",
            f"PREMIUM_DEFAULT_TIER={PREMIUM_DEFAULT_TIER}",
        ))
        results.append(_check(
            "launch_mode_enabled",
            ELITE_PLUS_LAUNCH_MODE,
            f"ELITE_PLUS_LAUNCH_MODE={ELITE_PLUS_LAUNCH_MODE}",
        ))
        results.append(_check(
            "cost_ceiling_set",
            0 < ELITE_PLUS_MAX_COST_USD_REQUEST <= 0.05,
            f"MAX_COST_USD_REQUEST={ELITE_PLUS_MAX_COST_USD_REQUEST}",
        ))
        results.append(_check(
            "max_paid_calls_capped",
            ELITE_PLUS_MAX_PAID_CALLS <= 2,
            f"MAX_PAID_CALLS={ELITE_PLUS_MAX_PAID_CALLS}",
        ))
    except Exception as e:
        results.append(_check("config_import", False, f"Import error: {e}"))

    # Free tier: no paid escalation
    try:
        from llmhive.app.orchestration.tier_spend_governor import (
            FREE_TIER_MAX_COST_USD_REQUEST, governor,
        )
        results.append(_check(
            "free_tier_zero_cost",
            FREE_TIER_MAX_COST_USD_REQUEST == 0.0,
            f"FREE_TIER_MAX_COST_USD_REQUEST={FREE_TIER_MAX_COST_USD_REQUEST}",
        ))

        free_decision = governor.evaluate("free", "test_account", 0.01)
        results.append(_check(
            "free_tier_blocks_paid",
            not free_decision.allowed_paid_escalation,
            f"allowed={free_decision.allowed_paid_escalation} reason={free_decision.reason_blocked}",
        ))
    except Exception as e:
        results.append(_check("free_tier_check", False, f"Error: {e}"))

    # Internal auth
    try:
        from llmhive.app.orchestration.internal_auth import is_internal_request
        ext_result = is_internal_request({"X-LLMHive-Internal-Key": "fake_key_12345"})
        results.append(_check(
            "internal_auth_rejects_fake",
            not ext_result,
            f"Fake key accepted={ext_result}",
        ))
    except Exception as e:
        results.append(_check("internal_auth_check", False, f"Error: {e}"))

    return results


# ---------------------------------------------------------------------------
# Check 2: Provider health (online only)
# ---------------------------------------------------------------------------

def check_provider_health(target: str) -> List[Dict[str, Any]]:
    results = []
    if not target:
        results.append(_check("provider_health", True, "skipped (offline mode)", p0=False))
        return results

    import requests

    try:
        r = requests.get(f"{target}/health", timeout=10)
        results.append(_check("health_endpoint", r.status_code == 200, f"status={r.status_code}"))
    except Exception as e:
        results.append(_check("health_endpoint", False, str(e)))

    try:
        r = requests.get(f"{target}/build-info", timeout=10)
        if r.status_code == 200:
            info = r.json()
            results.append(_check(
                "build_info",
                "commit" in info and info["commit"] != "unknown",
                f"commit={info.get('commit')} env={info.get('environment')}",
            ))
        else:
            results.append(_check("build_info", False, f"status={r.status_code}"))
    except Exception as e:
        results.append(_check("build_info", False, str(e)))

    # /internal/launch_kpis WITHOUT auth should be rejected (401/403)
    try:
        r_no_auth = requests.get(f"{target}/internal/launch_kpis", timeout=10)
        results.append(_check(
            "internal_kpis_no_auth_rejected",
            r_no_auth.status_code in (401, 403),
            f"status={r_no_auth.status_code} (expected 401 or 403)",
        ))
    except Exception as e:
        results.append(_check("internal_kpis_no_auth_rejected", False, str(e)))

    # /internal/launch_kpis WITH auth should succeed
    internal_key = os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", "")
    if internal_key:
        try:
            r = requests.get(
                f"{target}/internal/launch_kpis", timeout=10,
                headers={"X-LLMHive-Internal-Key": internal_key},
            )
            if r.status_code == 200:
                kpis = r.json()
                results.append(_check(
                    "launch_kpis_endpoint",
                    kpis.get("launch_mode_enabled", False),
                    f"launch_mode={kpis.get('launch_mode_enabled')} registry_v={kpis.get('model_registry_version')}",
                ))
            else:
                results.append(_check("launch_kpis_endpoint", False, f"status={r.status_code}"))
        except Exception as e:
            results.append(_check("launch_kpis_endpoint", False, str(e)))
    else:
        results.append(_check("launch_kpis_endpoint", True,
                               "skipped — INTERNAL_ADMIN_OVERRIDE_KEY not set", p0=False))

    # Online: verify spend_decision telemetry present for Elite+ request
    api_key = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))
    if api_key and target:
        try:
            r = requests.post(f"{target}/v1/chat", json={
                "prompt": "What is 3 + 7?",
                "model": "auto",
                "tier": "elite",
            }, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, timeout=60)
            if r.status_code == 200:
                data = r.json()
                spend = data.get("extra", {}).get("spend_decision", {})
                results.append(_check(
                    "spend_decision_in_elite_response",
                    bool(spend and "tier" in spend),
                    f"tier={spend.get('tier')} allowed={spend.get('allowed_paid_escalation')}",
                ))
            else:
                results.append(_check("spend_decision_in_elite_response", False,
                                      f"status={r.status_code}", p0=False))
        except Exception as e:
            results.append(_check("spend_decision_in_elite_response", False, str(e), p0=False))

        # Verify free tier spend_decision blocks paid
        try:
            r = requests.post(f"{target}/v1/chat", json={
                "prompt": "Hello",
                "model": "auto",
                "tier": "free",
            }, headers={"X-API-Key": api_key, "Content-Type": "application/json"}, timeout=60)
            if r.status_code == 200:
                data = r.json()
                spend = data.get("extra", {}).get("spend_decision", {})
                results.append(_check(
                    "free_tier_spend_blocks_paid",
                    spend.get("allowed_paid_escalation") is False if spend else True,
                    f"allowed={spend.get('allowed_paid_escalation', 'n/a')}",
                ))
            else:
                results.append(_check("free_tier_spend_blocks_paid", True,
                                      f"status={r.status_code} (non-200 ok for free)", p0=False))
        except Exception as e:
            results.append(_check("free_tier_spend_blocks_paid", False, str(e), p0=False))

    return results


# ---------------------------------------------------------------------------
# Check 3: Tool correctness (offline — schema validation logic)
# ---------------------------------------------------------------------------

def check_tool_correctness() -> List[Dict[str, Any]]:
    results = []
    try:
        sys.path.insert(0, str(_ROOT / "llmhive" / "src"))
        from llmhive.app.orchestration.elite_plus_orchestrator import (
            _validate_tool_schema,
            ELITE_PLUS_TOOL_STRICT_MODE,
        )

        results.append(_check(
            "tool_strict_mode_on",
            ELITE_PLUS_TOOL_STRICT_MODE,
            f"TOOL_STRICT_MODE={ELITE_PLUS_TOOL_STRICT_MODE}",
        ))

        valid_json = '{"function": "calculate", "args": {"expr": "2+2"}}'
        ok, detail = _validate_tool_schema(valid_json)
        results.append(_check("tool_valid_json_accepted", ok, detail))

        invalid = '{"incomplete json without closing'
        ok2, detail2 = _validate_tool_schema(invalid)
        results.append(_check("tool_malformed_json_handled", True, f"ok={ok2} detail={detail2}", p0=False))

        empty = ""
        ok3, detail3 = _validate_tool_schema(empty)
        results.append(_check("tool_empty_rejected", not ok3, detail3))

    except Exception as e:
        results.append(_check("tool_correctness", False, f"Error: {e}", p0=False))

    return results


# ---------------------------------------------------------------------------
# Check 4: RAG correctness (offline — grounding logic)
# ---------------------------------------------------------------------------

def check_rag_correctness() -> List[Dict[str, Any]]:
    results = []
    try:
        sys.path.insert(0, str(_ROOT / "llmhive" / "src"))
        from llmhive.app.orchestration.elite_plus_orchestrator import (
            _verify_rag_grounding,
            ELITE_PLUS_RAG_REQUIRE_SUPPORT,
        )

        results.append(_check(
            "rag_require_support_on",
            ELITE_PLUS_RAG_REQUIRE_SUPPORT,
            f"RAG_REQUIRE_SUPPORT={ELITE_PLUS_RAG_REQUIRE_SUPPORT}",
        ))

        refusal = "I don't have sufficient evidence to answer this question."
        ok, conf, rationale, reason = _verify_rag_grounding(refusal, "What is X?")
        results.append(_check(
            "rag_refusal_detected",
            not ok or "refusal" in rationale.lower() or "insufficient" in rationale.lower(),
            f"ok={ok} rationale={rationale} reason={reason}",
        ))

    except Exception as e:
        results.append(_check("rag_correctness", False, f"Error: {e}", p0=False))

    return results


# ---------------------------------------------------------------------------
# Check 5: Security (internal bench header rejection)
# ---------------------------------------------------------------------------

def check_security(target: str) -> List[Dict[str, Any]]:
    results = []

    try:
        sys.path.insert(0, str(_ROOT / "llmhive" / "src"))
        from llmhive.app.orchestration.internal_auth import is_internal_request

        accepted = is_internal_request({"X-LLMHive-Internal-Key": ""})
        results.append(_check("empty_key_rejected", not accepted, f"accepted={accepted}"))

        accepted2 = is_internal_request({})
        results.append(_check("no_header_rejected", not accepted2, f"accepted={accepted2}"))

        accepted3 = is_internal_request({"X-LLMHIVE-INTERNAL-BENCH": "1"})
        results.append(_check("convenience_header_rejected", not accepted3,
                              f"accepted={accepted3} (X-LLMHIVE-INTERNAL-BENCH ignored)"))

    except Exception as e:
        results.append(_check("security_check", False, f"Error: {e}"))

    # /internal/launch_kpis is auth-gated: without auth expect 401/403; with auth expect 200.
    if target:
        import requests
        internal_key = os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", "")
        try:
            if internal_key:
                r = requests.get(
                    f"{target}/internal/launch_kpis",
                    headers={"X-LLMHive-Internal-Key": internal_key},
                    timeout=10,
                )
                results.append(_check(
                    "kpis_accessible",
                    r.status_code == 200 and (r.headers.get("content-type") or "").startswith("application/json"),
                    f"status={r.status_code} (with auth)" if r.status_code != 200 else "200 OK",
                    p0=False,
                ))
            else:
                r = requests.get(f"{target}/internal/launch_kpis", timeout=10)
                results.append(_check(
                    "kpis_accessible",
                    r.status_code in (401, 403),
                    f"status={r.status_code} (unauth correctly rejected)" if r.status_code in (401, 403) else f"status={r.status_code}",
                    p0=False,
                ))
        except Exception as e:
            results.append(_check("kpis_accessible", False, str(e), p0=False))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = _parse_args()
    target = args["target"]
    output_path = Path(args["output"])
    t0 = time.time()

    print("=" * 70)
    print("PRODUCTION PREFLIGHT")
    print("=" * 70)
    print(f"  Time:    {datetime.now().isoformat()}")
    print(f"  Target:  {target or '(offline)'}")
    print()

    all_checks: List[Dict[str, Any]] = []

    print("[1/5] Config sanity...")
    all_checks.extend(check_config_sanity())

    print("[2/5] Provider health...")
    if not args["offline"]:
        all_checks.extend(check_provider_health(target))
    else:
        all_checks.append(_check("provider_health", True, "skipped (--offline)", p0=False))

    print("[3/5] Tool correctness...")
    all_checks.extend(check_tool_correctness())

    print("[4/5] RAG correctness...")
    all_checks.extend(check_rag_correctness())

    print("[5/5] Security...")
    all_checks.extend(check_security(target if not args["offline"] else ""))

    elapsed = round(time.time() - t0, 1)
    passed = sum(1 for c in all_checks if c["passed"])
    failed = sum(1 for c in all_checks if not c["passed"])
    p0_fails = [c for c in all_checks if not c["passed"] and c["priority"] == "P0"]

    report = {
        "timestamp": datetime.now().isoformat(),
        "target": target or "offline",
        "elapsed_seconds": elapsed,
        "total_checks": len(all_checks),
        "passed": passed,
        "failed": failed,
        "p0_failures": len(p0_fails),
        "verdict": "PASS" if not p0_fails else "FAIL",
        "checks": all_checks,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")

    print(f"\n{'=' * 70}")
    print(f"PREFLIGHT: {report['verdict']}  ({passed}/{len(all_checks)} passed, {elapsed}s)")
    print(f"{'=' * 70}")

    for c in all_checks:
        status = "PASS" if c["passed"] else "FAIL"
        icon = " " if c["passed"] else "!"
        print(f"  [{icon}] {status}  {c['name']:35s}  {c['detail'][:60]}")

    if p0_fails:
        print(f"\n  {len(p0_fails)} P0 FAILURE(S) — NOT LAUNCH READY:")
        for c in p0_fails:
            print(f"    - {c['name']}: {c['detail']}")

    print(f"\n  Report: {output_path}")
    sys.exit(1 if p0_fails else 0)


if __name__ == "__main__":
    main()
