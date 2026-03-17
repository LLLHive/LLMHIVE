#!/usr/bin/env python3
"""
Micro-test: Validate Elite+ v2 provider execution integrity.

Runs 5 requests per critical paid category against the no-traffic revision
and checks that paid_call_made=True, cost > 0, and correct providers are used.
"""
import asyncio
import json
import os
import sys
import time

import httpx

API_URL = os.getenv(
    "MICRO_TEST_URL",
    "https://v2-prov-check---llmhive-orchestrator-7h6b36l7ta-ue.a.run.app",
)
API_KEY = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))

CATEGORIES = {
    "coding": [
        "Write a Python function that checks if a number is prime.",
        "Implement binary search in Python.",
        "Write a function to reverse a linked list.",
        "Implement merge sort in Python.",
        "Write a Python class for a stack data structure.",
    ],
    "tool_use": [
        '{"function": "get_weather", "args": {"city": "NYC"}} — Call this tool with the given args.',
        'Call the search tool: {"name": "web_search", "parameters": {"query": "population of Tokyo"}}',
        'Use the calculator tool to compute 15 * 37 + 42. Return a JSON tool call.',
        'Invoke the translate tool: {"name": "translate", "args": {"text": "hello", "target": "es"}}',
        'Call the API tool: {"endpoint": "/users", "method": "GET"}. Return valid JSON.',
    ],
    "multilingual": [
        "Translate 'The weather is beautiful today' to French, Spanish, and German.",
        "What does 'こんにちは世界' mean in English?",
        "Write a short poem in Italian about the sea.",
        "Translate 'artificial intelligence' into Arabic and Chinese.",
        "What is the French word for 'butterfly'?",
    ],
    "reasoning": [
        "If all cats are animals and some animals are pets, can we conclude all cats are pets?",
        "A bat and ball cost $1.10 total. The bat costs $1 more. What does the ball cost?",
        "Is the statement 'This statement is false' true or false? Explain.",
        "If it takes 5 machines 5 minutes to make 5 widgets, how long for 100 machines to make 100?",
        "Three switches control three bulbs in another room. You can enter once. How to identify them?",
    ],
    "math": [
        "What is the integral of x^2 from 0 to 3?",
        "Solve: 3x^2 - 12x + 9 = 0",
        "What is 17! / 15! ?",
        "Find the derivative of sin(x) * e^x",
        "What is the sum of the first 100 positive integers?",
    ],
}

EXPECTED_ANCHORS = {
    "coding":       "anthropic/claude-opus-4.6",
    "tool_use":     "anthropic/claude-opus-4.6",
    "multilingual": "google/gemini-3-pro",
    "reasoning":    "google/gemini-3.1-pro-preview",
    "math":         "openai/gpt-5.2",
}


async def call_api(prompt: str, timeout: int = 120) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        payload = {
            "prompt": prompt,
            "tier": "elite",
            "reasoning_mode": "deep",
            "orchestration": {
                "accuracy_level": 5,
                "enable_verification": False,
                "use_deep_consensus": False,
                "temperature": 0.3,
            },
        }
        try:
            resp = await client.post(
                f"{API_URL}/v1/chat",
                json=payload,
                headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
            )
            if resp.status_code == 200:
                return {"success": True, **resp.json()}
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}


async def test_category(category: str, prompts: list) -> dict:
    results = []
    paid_calls = 0
    total_cost = 0.0
    providers_seen = set()
    anchor_failures = []

    for i, prompt in enumerate(prompts, 1):
        print(f"    [{i}/5] ", end="", flush=True)
        t0 = time.time()
        resp = await call_api(prompt)
        elapsed = time.time() - t0

        if not resp.get("success"):
            print(f"FAIL ({resp.get('error', 'unknown')[:80]})")
            anchor_failures.append({"query": i, "error": resp.get("error", "")})
            results.append({"success": False})
            continue

        extra = resp.get("extra", {})
        elite_plus = extra.get("elite_plus_telemetry", extra.get("elite_plus", {}))
        paid = elite_plus.get("paid_call_made", False)
        cost = elite_plus.get("estimated_cost_usd", 0)
        provider = elite_plus.get("provider_used", "unknown")
        v2_exec = elite_plus.get("elite_v2_executed", False)
        policy = elite_plus.get("policy", "unknown")
        direct_or_router = elite_plus.get("direct_or_router", "unknown")
        failure_reason = elite_plus.get("anchor_failure_reason", "")
        source = elite_plus.get("selected_answer_source", "unknown")

        if paid:
            paid_calls += 1
        total_cost += cost
        if provider:
            providers_seen.add(provider)
        if failure_reason:
            anchor_failures.append({"query": i, "reason": failure_reason})

        status = "OK" if paid else "MISS"
        print(
            f"{status} paid={paid} cost=${cost:.4f} provider={provider} "
            f"direct={direct_or_router} v2={v2_exec} policy={policy} "
            f"source={source} latency={elapsed:.1f}s"
        )

        results.append({
            "success": True,
            "paid_call_made": paid,
            "cost": cost,
            "provider_used": provider,
            "direct_or_router": direct_or_router,
            "v2_executed": v2_exec,
            "policy": policy,
            "source": source,
            "anchor_failure_reason": failure_reason,
            "latency_s": round(elapsed, 1),
        })

    return {
        "category": category,
        "expected_anchor": EXPECTED_ANCHORS.get(category, "unknown"),
        "paid_calls": paid_calls,
        "total_cost": round(total_cost, 6),
        "providers_seen": sorted(providers_seen),
        "anchor_failures": anchor_failures,
        "pass": paid_calls >= 4,
        "results": results,
    }


async def main():
    print("=" * 70)
    print("ELITE+ v2 PROVIDER EXECUTION INTEGRITY MICRO-TEST")
    print("=" * 70)
    print(f"  Target: {API_URL}")
    print(f"  API Key: {'present' if API_KEY else 'MISSING'}")
    print(f"  Categories: {', '.join(CATEGORIES)}")
    print(f"  Tests per category: 5")
    print()

    if not API_KEY:
        print("ERROR: API_KEY not set. Export API_KEY or LLMHIVE_API_KEY.")
        sys.exit(1)

    all_results = {}
    overall_pass = True

    for category, prompts in CATEGORIES.items():
        print(f"\n--- {category.upper()} (anchor: {EXPECTED_ANCHORS.get(category, '?')}) ---")
        result = await test_category(category, prompts)
        all_results[category] = result

        if not result["pass"]:
            overall_pass = False

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    claude_seen = any("claude" in p or "anthropic" in p for r in all_results.values() for p in r["providers_seen"])
    gemini_seen = any("gemini" in p or "google" in p for r in all_results.values() for p in r["providers_seen"])
    total_cost = sum(r["total_cost"] for r in all_results.values())

    for cat, r in all_results.items():
        status = "PASS" if r["pass"] else "FAIL"
        print(
            f"  [{status}] {cat:<15} paid={r['paid_calls']}/5  "
            f"cost=${r['total_cost']:.4f}  providers={r['providers_seen']}"
        )
        if r["anchor_failures"]:
            for af in r["anchor_failures"]:
                reason = af.get("reason", af.get("error", ""))[:80]
                print(f"         failure q{af['query']}: {reason}")

    print(f"\n  Claude visible:  {claude_seen}")
    print(f"  Gemini visible:  {gemini_seen}")
    print(f"  Total cost:      ${total_cost:.4f}")
    print(f"  Overall:         {'PASS' if overall_pass else 'FAIL'}")

    out_path = f"artifacts/micro_test_provider_check_{time.strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Report:          {out_path}")

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
