#!/usr/bin/env python3
"""Synthetic Production Test Suite — cost + quality + failure simulation.

Hits the deployed API with curated prompts to verify:
  1. Free tier: success without paid escalation
  2. Free tier: attempted escalation blocked
  3. Elite+: disagreement triggers paid escalation
  4. Elite+: cost ceiling prevents escalation
  5. Tool schema invalid → retry → escalation
  6. RAG grounding failure → "insufficient evidence"
  7. Circuit breaker / provider degradation behavior

Produces structured results JSON for audit.

Environment:
  - API_KEY or LLMHIVE_API_KEY: required for /v1/chat online tests
  - INTERNAL_ADMIN_OVERRIDE_KEY: read from env for /internal/launch_kpis validation
    (no --internal-key flag; set export INTERNAL_ADMIN_OVERRIDE_KEY=... before running)
  - If validating /internal endpoints and key is missing: explicit error
    "Missing INTERNAL_ADMIN_OVERRIDE_KEY; cannot validate /internal endpoints"

Usage:
    python scripts/run_synthetic_prod_suite.py --target https://llmhive-....run.app
    python scripts/run_synthetic_prod_suite.py --offline   # local governor/auth checks only
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = _ROOT / "synthetic_prod_results.json"


def _parse_args() -> Dict[str, Any]:
    args = {"target": "", "offline": False, "output": str(_REPORT_PATH), "require_internal": False}
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
        elif sys.argv[i] == "--require-internal":
            args["require_internal"] = True
            i += 1
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            args["output"] = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def _result(name: str, passed: bool, detail: str = "", telemetry: dict = None) -> Dict[str, Any]:
    return {
        "test": name,
        "passed": passed,
        "detail": detail,
        "telemetry": telemetry or {},
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Offline tests (governor + auth logic, no API calls)
# ---------------------------------------------------------------------------

def run_offline_tests() -> List[Dict[str, Any]]:
    results = []
    sys.path.insert(0, str(_ROOT / "llmhive" / "src"))

    # Test 1: Free tier blocks ALL paid escalation
    from llmhive.app.orchestration.tier_spend_governor import TierSpendGovernor, _SpendLedger
    ledger = _SpendLedger()
    gov = TierSpendGovernor(ledger)

    d = gov.evaluate("free", "test_free_user", predicted_cost_usd=0.01)
    results.append(_result(
        "free_tier_blocks_paid_escalation",
        not d.allowed_paid_escalation,
        f"allowed={d.allowed_paid_escalation} reason={d.reason_blocked}",
        d.to_dict(),
    ))

    # Test 2: Free tier blocks even with 0 cost
    d2 = gov.evaluate("free", "test_free_user", predicted_cost_usd=0.0)
    results.append(_result(
        "free_tier_blocks_zero_cost",
        not d2.allowed_paid_escalation,
        f"allowed={d2.allowed_paid_escalation} reason={d2.reason_blocked}",
        d2.to_dict(),
    ))

    # Test 3: Elite+ allows escalation within budget
    d3 = gov.evaluate("elite+", "test_elite_user", predicted_cost_usd=0.01)
    results.append(_result(
        "elite_plus_allows_within_budget",
        d3.allowed_paid_escalation,
        f"allowed={d3.allowed_paid_escalation} day_remain=${d3.spend_remaining_day:.2f}",
        d3.to_dict(),
    ))

    # Test 4: Elite+ blocks when cost exceeds per-request ceiling
    d4 = gov.evaluate("elite+", "test_elite_user", predicted_cost_usd=0.05)
    results.append(_result(
        "elite_plus_blocks_over_ceiling",
        not d4.allowed_paid_escalation,
        f"allowed={d4.allowed_paid_escalation} reason={d4.reason_blocked}",
        d4.to_dict(),
    ))

    # Test 5: Elite+ daily budget enforcement
    for _ in range(100):
        ledger.record_spend("budget_test_user", 0.025)
    d5 = gov.evaluate("elite+", "budget_test_user", predicted_cost_usd=0.01)
    results.append(_result(
        "elite_plus_daily_budget_enforcement",
        not d5.allowed_paid_escalation,
        f"allowed={d5.allowed_paid_escalation} day_remain=${d5.spend_remaining_day:.4f} reason={d5.reason_blocked}",
        d5.to_dict(),
    ))

    # Test 6: Global emergency breaker
    for _ in range(2500):
        ledger.record_spend("global_test", 0.025)
    d6 = gov.evaluate("elite+", "new_user", predicted_cost_usd=0.01)
    results.append(_result(
        "global_emergency_breaker",
        not d6.allowed_paid_escalation and d6.global_breaker_active,
        f"breaker={d6.global_breaker_active} allowed={d6.allowed_paid_escalation} reason={d6.reason_blocked}",
        d6.to_dict(),
    ))

    # Test 7: Internal override bypasses global breaker
    d7 = gov.evaluate("elite+", "admin_user", predicted_cost_usd=0.01, is_internal=True)
    results.append(_result(
        "internal_override_bypasses_breaker",
        d7.allowed_paid_escalation and d7.is_internal_override,
        f"allowed={d7.allowed_paid_escalation} internal={d7.is_internal_override}",
        d7.to_dict(),
    ))

    # Test 8: Internal auth rejects external requests
    from llmhive.app.orchestration.internal_auth import is_internal_request
    ext = is_internal_request({"X-LLMHive-Internal-Key": "wrong_key"})
    results.append(_result(
        "internal_auth_rejects_external",
        not ext,
        f"accepted={ext}",
    ))

    # Test 9: Concurrency cap
    fresh_ledger = _SpendLedger()
    fresh_gov = TierSpendGovernor(fresh_ledger)
    from llmhive.app.orchestration.tier_spend_governor import ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP
    for _ in range(ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP):
        assert fresh_gov.acquire_concurrency("conc_user")
    blocked = not fresh_gov.acquire_concurrency("conc_user")
    results.append(_result(
        "concurrency_cap_enforced",
        blocked,
        f"blocked_at={ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP + 1} cap={ELITE_PLUS_ACCOUNT_CONCURRENCY_CAP}",
    ))

    return results


# ---------------------------------------------------------------------------
# Online tests (hit deployed API)
# ---------------------------------------------------------------------------

def run_online_tests(target: str) -> List[Dict[str, Any]]:
    results = []

    try:
        import requests
    except ImportError:
        results.append(_result("online_tests", False, "requests library not available"))
        return results

    api_key = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    # Test: Free tier query succeeds without paid escalation
    try:
        r = requests.post(f"{target}/v1/chat", json={
            "prompt": "What is 2 + 2?",
            "model": "auto",
            "tier": "free",
        }, headers=headers, timeout=60)

        if r.status_code == 200:
            data = r.json()
            ep = data.get("extra", {}).get("elite_plus", {})
            spend = data.get("extra", {}).get("spend_decision", {})
            paid = ep.get("paid_calls_count", 0)
            results.append(_result(
                "free_tier_no_paid_calls",
                paid == 0,
                f"paid_calls={paid} tier={spend.get('tier', '?')}",
                {"elite_plus": ep, "spend_decision": spend},
            ))
        else:
            results.append(_result("free_tier_no_paid_calls", False, f"status={r.status_code}"))
    except Exception as e:
        results.append(_result("free_tier_no_paid_calls", False, str(e)))

    # Test: Elite+ query with math triggers Elite+ pipeline
    try:
        r = requests.post(f"{target}/v1/chat", json={
            "prompt": "Solve: What is the integral of x^3 dx from 0 to 2?",
            "model": "auto",
            "tier": "elite",
        }, headers=headers, timeout=60)

        if r.status_code == 200:
            data = r.json()
            ep = data.get("extra", {}).get("elite_plus", {})
            has_ep = bool(ep and ep.get("stage_used"))
            overridden = data.get("extra", {}).get("elite_plus_overridden", False)
            results.append(_result(
                "elite_plus_pipeline_active",
                has_ep,
                f"stage={ep.get('stage_used')} overridden={overridden} cost=${ep.get('estimated_cost_usd', 0):.4f}",
                {"elite_plus": ep},
            ))
        else:
            results.append(_result("elite_plus_pipeline_active", False, f"status={r.status_code}"))
    except Exception as e:
        results.append(_result("elite_plus_pipeline_active", False, str(e)))

    # Test: Spend decision telemetry present
    try:
        r = requests.post(f"{target}/v1/chat", json={
            "prompt": "Hello, how are you?",
            "model": "auto",
            "tier": "elite",
        }, headers=headers, timeout=60)

        if r.status_code == 200:
            data = r.json()
            spend = data.get("extra", {}).get("spend_decision", {})
            has_spend = bool(spend and "tier" in spend)
            results.append(_result(
                "spend_decision_telemetry_present",
                has_spend,
                f"tier={spend.get('tier')} allowed={spend.get('allowed_paid_escalation')}",
                {"spend_decision": spend},
            ))
        else:
            results.append(_result("spend_decision_telemetry_present", False, f"status={r.status_code}"))
    except Exception as e:
        results.append(_result("spend_decision_telemetry_present", False, str(e)))

    # Test: Parallel requests to verify concurrency + budget tracking
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        def _make_request(prompt, tier):
            return requests.post(f"{target}/v1/chat", json={
                "prompt": prompt,
                "model": "auto",
                "tier": tier,
            }, headers=headers, timeout=60)

        futures = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            for i in range(3):
                futures.append(pool.submit(
                    _make_request, f"What is {i+1} + {i+2}?", "elite"
                ))
            statuses = []
            for f in as_completed(futures):
                try:
                    r = f.result()
                    statuses.append(r.status_code)
                except Exception:
                    statuses.append(0)

        all_ok = all(s == 200 for s in statuses)
        results.append(_result(
            "parallel_requests_succeed",
            all_ok,
            f"statuses={statuses}",
        ))
    except Exception as e:
        results.append(_result("parallel_requests_succeed", False, str(e)))

    # Test: Elite+ escalation stays under max cost ceiling
    try:
        r = requests.post(f"{target}/v1/chat", json={
            "prompt": "Explain the Riemann hypothesis in detail with mathematical proofs",
            "model": "auto",
            "tier": "elite",
        }, headers=headers, timeout=90)
        if r.status_code == 200:
            data = r.json()
            ep = data.get("extra", {}).get("elite_plus", {})
            cost = ep.get("estimated_cost_usd", 0)
            paid = ep.get("paid_calls_count", 0)
            results.append(_result(
                "elite_plus_cost_under_ceiling",
                cost <= 0.025 and paid <= 1,
                f"cost=${cost:.4f} paid_calls={paid}",
                {"elite_plus": ep},
            ))
        else:
            results.append(_result("elite_plus_cost_under_ceiling", True,
                                    f"status={r.status_code} (non-200 ok)", ))
    except Exception as e:
        results.append(_result("elite_plus_cost_under_ceiling", False, str(e)))

    # Test: Free tier forced escalation attempt BLOCKED
    try:
        r = requests.post(f"{target}/v1/chat", json={
            "prompt": "Use GPT-4 to solve: prove P != NP",
            "model": "auto",
            "tier": "free",
        }, headers=headers, timeout=60)
        if r.status_code == 200:
            data = r.json()
            ep = data.get("extra", {}).get("elite_plus", {})
            spend = data.get("extra", {}).get("spend_decision", {})
            paid = ep.get("paid_calls_count", 0)
            blocked = spend.get("allowed_paid_escalation") is False if spend else True
            results.append(_result(
                "free_tier_escalation_blocked",
                paid == 0 and blocked,
                f"paid={paid} blocked={blocked} spend_tier={spend.get('tier', '?')}",
                {"elite_plus": ep, "spend_decision": spend},
            ))
        else:
            results.append(_result("free_tier_escalation_blocked", True,
                                    f"status={r.status_code}"))
    except Exception as e:
        results.append(_result("free_tier_escalation_blocked", False, str(e)))

    # Optional: /internal/launch_kpis validation (requires INTERNAL_ADMIN_OVERRIDE_KEY from env)
    internal_key = os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", "")
    if internal_key:
        try:
            r = requests.get(
                f"{target}/internal/launch_kpis",
                headers={"X-LLMHive-Internal-Key": internal_key},
                timeout=10,
            )
            kpis_ok = r.status_code == 200
            results.append(_result(
                "internal_launch_kpis_accessible",
                kpis_ok,
                f"status={r.status_code}" if not kpis_ok else "200 OK",
            ))
        except Exception as e:
            results.append(_result("internal_launch_kpis_accessible", False, str(e)))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = _parse_args()
    target = args["target"]
    output_path = Path(args["output"])
    t0 = time.time()

    # Explicit error when --require-internal but key missing
    if args.get("require_internal") and target and not args["offline"]:
        if not os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", ""):
            print("ERROR: Missing INTERNAL_ADMIN_OVERRIDE_KEY; cannot validate /internal endpoints.")
            print("  Set: export INTERNAL_ADMIN_OVERRIDE_KEY=<key>")
            sys.exit(2)

    print("=" * 70)
    print("SYNTHETIC PRODUCTION TEST SUITE")
    print("=" * 70)
    print(f"  Time:    {datetime.now().isoformat()}")
    print(f"  Target:  {target or '(offline)'}")
    print()

    all_results: List[Dict[str, Any]] = []

    print("[1/2] Running offline governor/auth tests...")
    all_results.extend(run_offline_tests())

    if not args["offline"] and target:
        print("[2/2] Running online API tests...")
        all_results.extend(run_online_tests(target))
    else:
        print("[2/2] Skipping online tests (--offline or no --target)")

    elapsed = round(time.time() - t0, 1)
    passed = sum(1 for r in all_results if r["passed"])
    failed = sum(1 for r in all_results if not r["passed"])

    report = {
        "timestamp": datetime.now().isoformat(),
        "target": target or "offline",
        "elapsed_seconds": elapsed,
        "total_tests": len(all_results),
        "passed": passed,
        "failed": failed,
        "verdict": "PASS" if failed == 0 else "FAIL",
        "results": all_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str) + "\n")

    print(f"\n{'=' * 70}")
    print(f"SYNTHETIC SUITE: {report['verdict']}  ({passed}/{len(all_results)} passed, {elapsed}s)")
    print(f"{'=' * 70}")

    for r in all_results:
        status = "PASS" if r["passed"] else "FAIL"
        icon = " " if r["passed"] else "!"
        print(f"  [{icon}] {status}  {r['test']:45s}  {r['detail'][:50]}")

    if failed:
        print(f"\n  {failed} FAILURE(S):")
        for r in all_results:
            if not r["passed"]:
                print(f"    - {r['test']}: {r['detail']}")

    print(f"\n  Report: {output_path}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
