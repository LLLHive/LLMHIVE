#!/usr/bin/env python3
"""
Quick test for PhD-Level Physics benchmark only.
Tests both ELITE and FREE tiers for the gr_001 test case.
"""

import asyncio
import os
import httpx
from typing import Dict, List
from scripts.run_elite_free_benchmarks import evaluate_response

# Production API endpoint
LLMHIVE_API_URL = os.getenv("LLMHIVE_API_URL", "https://llmhive-orchestrator-792354158895.us-east1.run.app")
API_KEY = os.getenv("API_KEY") or os.getenv("LLMHIVE_API_KEY", "")

# PhD-Level Physics test case
PHYSICS_TEST = {
    "id": "gr_001",
    "prompt": "A researcher observes that a newly discovered exoplanet has a surface gravity of 15 m/s². If Earth's surface gravity is approximately 9.8 m/s², and this planet has the same density as Earth, what is the approximate ratio of this planet's radius to Earth's radius?",
    "expected_contains": ["gravity", "radius", "density"],
    "category": "PhD-Level Physics"
}


def check_keywords(response: str, expected: List[str]) -> Dict:
    """Check keywords using shared benchmark evaluation logic."""
    eval_result = evaluate_response(response, PHYSICS_TEST)
    return {
        "score": eval_result["score"],
        "found": [k for k in expected if k not in eval_result.get("missing", [])],
        "missing": eval_result.get("missing", []),
        "passed": eval_result["passed"],
    }


async def run_physics_test(tier: str) -> Dict:
    """Run the physics test for a specific tier."""
    print(f"\n{'='*60}")
    print(f"Testing {tier.upper()} tier - PhD-Level Physics")
    print(f"{'='*60}")
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }
    
    payload = {
        "prompt": PHYSICS_TEST["prompt"],
        "reasoning_mode": "deep",
        "tier": tier,
    }
    
    print(f"Sending request to {LLMHIVE_API_URL}/v1/chat...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{LLMHIVE_API_URL}/v1/chat",
                json=payload,
                headers=headers,
            )
            
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return {"tier": tier, "error": f"HTTP {response.status_code}"}
            
            data = response.json()
            print(f"Full API response keys: {data.keys()}")
            print(f"Full API response: {str(data)[:500]}")
            answer = data.get("response", "") or data.get("content", "") or data.get("message", "")
            cost = data.get("cost", 0) or data.get("total_cost", 0)
            
            print(f"\nResponse received ({len(answer)} chars, cost=${cost:.4f})")
            print(f"\n--- Response ---")
            print(answer[:1000])
            if len(answer) > 1000:
                print("... [truncated]")
            print(f"--- End Response ---")
            
            # Check keywords
            result = check_keywords(answer, PHYSICS_TEST["expected_contains"])
            
            print(f"\n--- Keyword Analysis ---")
            print(f"Expected: {PHYSICS_TEST['expected_contains']}")
            print(f"Found: {result['found']}")
            print(f"Missing: {result['missing']}")
            print(f"Score: {result['score']*100:.0f}%")
            print(f"Passed: {'✅ YES' if result['passed'] else '❌ NO'}")
            
            return {
                "tier": tier,
                "score": result["score"],
                "passed": result["passed"],
                "found": result["found"],
                "missing": result["missing"],
                "cost": cost,
                "response_length": len(answer),
            }
            
        except Exception as e:
            print(f"Error: {e}")
            return {"tier": tier, "error": str(e)}


async def main():
    print(f"\n🔬 LLMHive PhD-Level Physics Benchmark Test")
    print(f"API URL: {LLMHIVE_API_URL}")
    print(f"API Key: {'***' + API_KEY[-4:] if API_KEY else 'NOT SET'}")
    
    if not API_KEY:
        print("\n⚠️ WARNING: API_KEY not set. Tests will likely fail.")
        return
    
    # Run ELITE test
    elite_result = await run_physics_test("elite")
    
    # Run FREE test
    free_result = await run_physics_test("free")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"\n| Tier  | Score | Passed | Missing Keywords | Cost |")
    print(f"|-------|-------|--------|------------------|------|")
    
    for result in [elite_result, free_result]:
        if "error" in result:
            print(f"| {result['tier'].upper():5} | ERROR | ❌     | {result['error'][:20]} | - |")
        else:
            missing = ", ".join(result.get("missing", [])) or "None"
            print(f"| {result['tier'].upper():5} | {result['score']*100:4.0f}% | {'✅' if result['passed'] else '⚠️':6} | {missing:16} | ${result.get('cost', 0):.4f} |")


if __name__ == "__main__":
    asyncio.run(main())
