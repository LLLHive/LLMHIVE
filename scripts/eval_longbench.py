#!/usr/bin/env python3
"""
LLMHive Long Context Evaluation — Needle in Haystack + LongBench
==================================================================
Self-contained eval script for the Long Context benchmark category.

Tests the model's ability to handle long-context inputs by finding specific
information ("needles") embedded in long passages ("haystacks").

Output: JSON with {score, attempted, correct, errors, avg_latency_ms, ...}

Usage:
    python scripts/eval_longbench.py --output /tmp/longbench_eval.json --seed 42
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_URL = os.getenv(
    "LLMHIVE_API_URL",
    os.getenv(
        "CATEGORY_BENCH_API_URL",
        "https://llmhive-orchestrator-792354158895.us-east1.run.app",
    ),
)
API_KEY = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))
TIER = os.getenv("CATEGORY_BENCH_TIER", "elite")
SAMPLE_SIZE = int(os.getenv("CATEGORY_BENCH_LONGBENCH_SAMPLES", "20"))
FIXED_SEED = int(os.getenv("CATEGORY_BENCH_SEED", "42"))

_INFRA_GARBAGE_MARKERS = (
    "<html>", "<!doctype", "service unavailable", "502 bad gateway",
    "503 service", "504 gateway", "internal server error",
)


def response_is_valid(text, min_length=10):
    if text is None:
        return False
    stripped = text.strip()
    if not stripped or stripped in ("None", "null", "error", ""):
        return False
    if len(stripped) < min_length:
        return False
    lower = stripped.lower()
    return not any(m in lower for m in _INFRA_GARBAGE_MARKERS)


# ---------------------------------------------------------------------------
# Needle-in-Haystack test cases
# ---------------------------------------------------------------------------

_FILLER_PARAGRAPH = (
    "The history of computing is rich with innovation. From the earliest "
    "mechanical calculators to modern quantum processors, each generation "
    "has pushed the boundaries of what is possible. Early pioneers like "
    "Ada Lovelace and Charles Babbage laid the groundwork for programmable "
    "machines. The invention of the transistor in 1947 revolutionized "
    "electronics, leading to the development of integrated circuits and "
    "eventually microprocessors. Today's computers can perform billions of "
    "operations per second, enabling everything from scientific simulations "
    "to artificial intelligence. The field continues to evolve rapidly, "
    "with new breakthroughs in areas like neuromorphic computing and "
    "photonic processors promising even greater capabilities. "
)

NEEDLES = [
    {
        "needle": "The secret passphrase for Project Aurora is 'crystalline horizon'.",
        "question": "What is the secret passphrase for Project Aurora?",
        "answer": "crystalline horizon",
    },
    {
        "needle": "The quarterly revenue target for Q3 was set at exactly $4.7 million.",
        "question": "What was the quarterly revenue target for Q3?",
        "answer": "$4.7 million",
    },
    {
        "needle": "Dr. Elara Chen discovered that compound XR-7 has a half-life of 3.2 hours.",
        "question": "What is the half-life of compound XR-7?",
        "answer": "3.2 hours",
    },
    {
        "needle": "The emergency evacuation code for Building 9 is 'red falcon alpha'.",
        "question": "What is the emergency evacuation code for Building 9?",
        "answer": "red falcon alpha",
    },
    {
        "needle": "Agent Morrison's meeting point is the third bench in Riverside Park at 14:30.",
        "question": "Where and when is Agent Morrison's meeting point?",
        "answer": "third bench in Riverside Park at 14:30",
    },
    {
        "needle": "The maximum safe operating temperature for the reactor is 847 degrees Kelvin.",
        "question": "What is the maximum safe operating temperature for the reactor?",
        "answer": "847 degrees Kelvin",
    },
    {
        "needle": "The winning lottery numbers from the 1987 drawing were 7, 14, 23, 35, 42.",
        "question": "What were the winning lottery numbers from the 1987 drawing?",
        "answer": "7, 14, 23, 35, 42",
    },
    {
        "needle": "Professor Yang's theorem states that the convergence rate is O(n^{-2/3}).",
        "question": "What does Professor Yang's theorem state about the convergence rate?",
        "answer": "O(n^{-2/3})",
    },
    {
        "needle": "The artifact was last seen in the west wing of the National Museum on March 15th.",
        "question": "Where and when was the artifact last seen?",
        "answer": "west wing of the National Museum on March 15th",
    },
    {
        "needle": "The access PIN for the satellite uplink terminal is 8-4-7-2-9-1.",
        "question": "What is the access PIN for the satellite uplink terminal?",
        "answer": "8-4-7-2-9-1",
    },
    {
        "needle": "The recommended dosage of medication Zephyrex is 25mg twice daily.",
        "question": "What is the recommended dosage of Zephyrex?",
        "answer": "25mg twice daily",
    },
    {
        "needle": "The ship's coordinates at the time of the incident were 34.052N, 118.243W.",
        "question": "What were the ship's coordinates at the time of the incident?",
        "answer": "34.052N, 118.243W",
    },
    {
        "needle": "The password to the encrypted archive is 'moonlight-sonata-1801'.",
        "question": "What is the password to the encrypted archive?",
        "answer": "moonlight-sonata-1801",
    },
    {
        "needle": "The total weight of the cargo shipment was exactly 12,847 kilograms.",
        "question": "What was the total weight of the cargo shipment?",
        "answer": "12,847 kilograms",
    },
    {
        "needle": "The next scheduled maintenance window is February 29th from 02:00 to 06:00 UTC.",
        "question": "When is the next scheduled maintenance window?",
        "answer": "February 29th from 02:00 to 06:00 UTC",
    },
    {
        "needle": "The chemical formula for the new superconductor is YBa2Cu3O7.",
        "question": "What is the chemical formula for the new superconductor?",
        "answer": "YBa2Cu3O7",
    },
    {
        "needle": "The hidden message in the painting reads 'truth lies beneath the surface'.",
        "question": "What is the hidden message in the painting?",
        "answer": "truth lies beneath the surface",
    },
    {
        "needle": "The prototype's fuel efficiency was measured at 127 miles per gallon.",
        "question": "What was the prototype's fuel efficiency?",
        "answer": "127 miles per gallon",
    },
    {
        "needle": "The treaty was signed by exactly 43 nations on December 10th, 2019.",
        "question": "How many nations signed the treaty and when?",
        "answer": "43 nations on December 10th, 2019",
    },
    {
        "needle": "The frequency of the distress signal was 121.5 megahertz.",
        "question": "What was the frequency of the distress signal?",
        "answer": "121.5 megahertz",
    },
]


def _build_haystack(needle_text: str, rng: random.Random, target_tokens: int = 4000) -> str:
    paragraphs = [_FILLER_PARAGRAPH] * (target_tokens // 60)
    insert_pos = rng.randint(len(paragraphs) // 4, 3 * len(paragraphs) // 4)
    paragraphs.insert(insert_pos, needle_text)
    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# API caller
# ---------------------------------------------------------------------------

_MAX_RETRIES = 5
_RETRYABLE = {429, 502, 503, 504}


async def call_api(prompt: str, timeout: int = 300) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(_MAX_RETRIES):
            try:
                start = time.time()
                payload = {
                    "prompt": prompt,
                    "reasoning_mode": "deep",
                    "tier": TIER,
                    "orchestration": {"accuracy_level": 5, "enable_verification": True},
                }
                if FIXED_SEED >= 0:
                    payload["seed"] = FIXED_SEED
                resp = await client.post(
                    f"{API_URL}/v1/chat",
                    json=payload,
                    headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
                )
                latency = int((time.time() - start) * 1000)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "response": data.get("message", ""),
                        "latency": latency,
                        "cost": data.get("extra", {}).get("cost_tracking", {}).get("total_cost", 0),
                    }
                if resp.status_code in _RETRYABLE:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"success": False, "error": f"HTTP {resp.status_code}", "latency": latency, "cost": 0}
            except Exception as exc:
                if attempt == _MAX_RETRIES - 1:
                    return {"success": False, "error": str(exc), "latency": 0, "cost": 0}
                await asyncio.sleep(2 ** attempt)
    return {"success": False, "error": "max retries", "latency": 0, "cost": 0}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

async def run_evaluation(seed: int = 42) -> dict:
    rng = random.Random(seed)
    cases = NEEDLES[:]
    rng.shuffle(cases)
    cases = cases[:SAMPLE_SIZE]

    correct = 0
    errors = 0
    infra_failures = 0
    total_latency = 0
    total_cost = 0.0

    print(f"-> Long Context (Needle-in-Haystack): {len(cases)} samples", flush=True)

    for i, case in enumerate(cases, 1):
        haystack = _build_haystack(case["needle"], rng)
        prompt = (
            f"Read the following long document carefully and answer the question at the end.\n\n"
            f"--- DOCUMENT START ---\n{haystack}\n--- DOCUMENT END ---\n\n"
            f"Question: {case['question']}\n\n"
            f"Answer concisely with the specific information requested."
        )
        result = await call_api(prompt)

        if not result.get("success"):
            infra_failures += 1
            print(f"  [{i}/{len(cases)}] LongBench: INFRA_FAILURE ({infra_failures} infra failures)", flush=True)
            continue

        resp_text = result.get("response", "")
        if not response_is_valid(resp_text):
            infra_failures += 1
            print(f"  [{i}/{len(cases)}] LongBench: INFRA_FAILURE (invalid response)", flush=True)
            continue

        total_latency += result.get("latency", 0)
        total_cost += result.get("cost", 0.0)

        answer_lower = case["answer"].lower()
        resp_lower = resp_text.lower()
        is_correct = answer_lower in resp_lower
        if not is_correct:
            key_tokens = [t for t in answer_lower.split() if len(t) > 2]
            if key_tokens:
                matched = sum(1 for t in key_tokens if t in resp_lower)
                is_correct = matched / len(key_tokens) >= 0.7

        if is_correct:
            correct += 1

        icon = "pass" if is_correct else "fail"
        print(f"  [{i}/{len(cases)}] LongBench: {icon} ({correct}/{i - infra_failures} correct)", flush=True)

    valid = len(cases) - infra_failures
    accuracy = (correct / valid * 100) if valid > 0 else 0.0

    return {
        "score": round(accuracy, 2),
        "accuracy": round(accuracy, 2),
        "attempted": len(cases),
        "correct": correct,
        "incorrect": valid - correct,
        "errors": errors,
        "infra_failures": infra_failures,
        "infra_failure_rate": round(infra_failures / len(cases) * 100, 2) if cases else 0.0,
        "avg_latency_ms": int(total_latency / valid) if valid > 0 else 0,
        "avg_cost": round(total_cost / valid, 6) if valid > 0 else 0.0,
        "total_cost": round(total_cost, 4),
    }


def main():
    parser = argparse.ArgumentParser(description="LLMHive Long Context Evaluation")
    parser.add_argument("--output", required=True, help="Path to write JSON results")
    parser.add_argument("--seed", type=int, default=FIXED_SEED)
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: API_KEY or LLMHIVE_API_KEY must be set", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(run_evaluation(seed=args.seed))

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResults written to {args.output}")
    print(f"Accuracy: {result['accuracy']}%  ({result['correct']}/{result['attempted']})")


if __name__ == "__main__":
    main()
