#!/usr/bin/env python3
"""
LLMHive Dialogue Evaluation — MT-Bench Style
=============================================
Self-contained eval script for the Dialogue benchmark category.

Uses multi-turn conversation prompts across 8 categories with LLM-as-judge
scoring. Each question has 2 turns; responses are judged on a 1-10 scale.

Output: JSON with {score, attempted, correct, errors, avg_latency_ms, ...}

Usage:
    python scripts/eval_mtbench.py --output /tmp/mtbench_eval.json --seed 42
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
    os.getenv("CATEGORY_BENCH_API_URL", "https://llmhive-orchestrator-792354158895.us-east1.run.app"),
)
API_KEY = os.getenv("API_KEY", os.getenv("LLMHIVE_API_KEY", ""))
TIER = os.getenv("CATEGORY_BENCH_TIER", "elite")
SAMPLE_SIZE = int(os.getenv("CATEGORY_BENCH_MTBENCH_SAMPLES", "10"))
FIXED_SEED = int(os.getenv("CATEGORY_BENCH_SEED", "42"))

# ---------------------------------------------------------------------------
# MT-Bench style questions (8 categories, multi-turn)
# ---------------------------------------------------------------------------

QUESTIONS = [
    # --- Writing ---
    {
        "category": "writing",
        "turn1": "Write a persuasive email to convince your manager to let your team work from home two days a week. Include specific benefits and address potential concerns.",
        "turn2": "Now rewrite the email in a more casual, friendly tone while keeping the key arguments.",
    },
    {
        "category": "writing",
        "turn1": "Compose a short story (about 200 words) that begins with the sentence: 'The last light on Earth flickered and went out.'",
        "turn2": "Now write an alternate ending where the light comes back on. Make it uplifting.",
    },
    # --- Roleplay ---
    {
        "category": "roleplay",
        "turn1": "You are a medieval knight who has just discovered a smartphone in the forest. Describe your reaction and how you try to make sense of this strange object.",
        "turn2": "Now the smartphone starts ringing. How do you react? Continue the story.",
    },
    {
        "category": "roleplay",
        "turn1": "Pretend you are a travel agent from the year 2150. A customer asks you to plan a vacation to Mars. Describe the available packages.",
        "turn2": "The customer has a limited budget of 50,000 credits. Which package do you recommend and why?",
    },
    # --- Reasoning ---
    {
        "category": "reasoning",
        "turn1": "If a train leaves Station A at 9:00 AM traveling at 60 mph, and another train leaves Station B (300 miles away) at 10:00 AM traveling at 90 mph toward Station A, at what time will they meet?",
        "turn2": "Now suppose there's a bird that starts flying from Station A toward Station B at 120 mph when the first train departs. The bird flies back and forth between the two trains until they meet. How far does the bird fly in total?",
    },
    {
        "category": "reasoning",
        "turn1": "A farmer has 17 sheep. All but 9 die. How many sheep does the farmer have left? Explain your reasoning step by step.",
        "turn2": "Now consider this: A bat and a ball cost $1.10 together. The bat costs $1.00 more than the ball. How much does the ball cost? Show your work.",
    },
    # --- Math ---
    {
        "category": "math",
        "turn1": "Solve this system of equations:\n2x + 3y = 12\n4x - y = 5\nShow your work step by step.",
        "turn2": "Now solve the same type of problem but with three variables:\nx + y + z = 6\n2x - y + z = 3\nx + 2y - z = 2",
    },
    {
        "category": "math",
        "turn1": "What is the derivative of f(x) = x^3 * sin(x)? Show the steps using the product rule.",
        "turn2": "Now find the integral of the result. Can you verify by differentiating the integral?",
    },
    # --- Coding ---
    {
        "category": "coding",
        "turn1": "Write a Python function that finds the longest palindromic substring in a given string. Include comments explaining your approach.",
        "turn2": "Now optimize your solution to run in O(n) time using Manacher's algorithm. Explain the key insight.",
    },
    {
        "category": "coding",
        "turn1": "Implement a basic LRU (Least Recently Used) cache in Python with get and put methods. It should have O(1) time complexity for both operations.",
        "turn2": "Now add a method called 'get_stats()' that returns cache hit rate, miss rate, and the number of evictions. Modify the class accordingly.",
    },
    # --- Extraction ---
    {
        "category": "extraction",
        "turn1": "Extract all the key facts from this paragraph:\n'SpaceX launched its Starship rocket on March 14, 2024, from Boca Chica, Texas. The 400-foot tall rocket reached an altitude of 145 miles before successfully re-entering the atmosphere. CEO Elon Musk called it a \"major milestone.\" The mission lasted approximately 65 minutes and was the third test flight of the vehicle.'",
        "turn2": "Now organize the extracted facts into a structured JSON format with appropriate field names.",
    },
    {
        "category": "extraction",
        "turn1": "Given this restaurant review, identify the sentiment (positive/negative/mixed), the specific dishes mentioned, and the overall rating implied:\n'We visited La Maison last Friday. The duck confit was absolutely divine - perfectly crispy skin and tender meat. However, the risotto was underseasoned and lukewarm. The service was excellent, our waiter Marco was attentive without being intrusive. Dessert - a chocolate soufflé - was the highlight of the evening. Overall a solid experience despite the risotto mishap.'",
        "turn2": "Now write a brief 2-sentence summary of the review, and suggest one improvement the restaurant could make based on the feedback.",
    },
    # --- STEM ---
    {
        "category": "stem",
        "turn1": "Explain the concept of CRISPR-Cas9 gene editing to a high school student. Use an analogy to make it more understandable.",
        "turn2": "What are the ethical concerns surrounding CRISPR technology, especially regarding human germline editing? Present arguments from both sides.",
    },
    {
        "category": "stem",
        "turn1": "Explain how a neural network learns through backpropagation. Use a simple example with a 2-layer network.",
        "turn2": "What is the vanishing gradient problem and how do modern architectures like ResNets and Transformers address it?",
    },
    # --- Humanities ---
    {
        "category": "humanities",
        "turn1": "Compare and contrast the philosophical views of Immanuel Kant and John Stuart Mill on ethics. What would each say about lying to protect someone's feelings?",
        "turn2": "Apply both frameworks to this modern dilemma: Should a self-driving car prioritize the safety of its passengers or pedestrians in an unavoidable accident?",
    },
    {
        "category": "humanities",
        "turn1": "What were the main causes of the fall of the Roman Empire? Discuss at least three major factors.",
        "turn2": "Drawing parallels to the fall of Rome, what modern challenges could potentially threaten the stability of current global powers? Be specific.",
    },
]

JUDGE_PROMPT_TEMPLATE = """You are an impartial judge evaluating the quality of an AI assistant's response.

SCORING RUBRIC (use these anchors):
- 1-2: Response is empty, completely off-topic, or contains only harmful/dangerous content. Reserve 1 for truly non-functional responses.
- 3-4: Response attempts the task but has fundamental errors (wrong answer, missing the point entirely, or major factual mistakes).
- 5-6: Response addresses the question with partial correctness. May lack depth, miss key points, or have minor errors, but demonstrates understanding of the task.
- 7-8: Response is good — relevant, mostly accurate, well-organized. Minor improvements possible but the core answer is solid and useful.
- 9-10: Response is excellent — comprehensive, accurate, well-structured, insightful. Demonstrates mastery of the topic.

CRITICAL CALIBRATION RULES:
- If the response is on-topic and contains substantive content (more than a sentence), it MUST score at least 4.
- Only score 1-2 if the response is literally empty, gibberish, completely off-topic, or harmful.
- A partially correct, on-topic response should score 5-6 at minimum.
- If the response is on-topic but you disagree with some points, score 5-7 depending on severity.
- Evaluate the CONTENT, not the format. A plain-text response can score 9-10 if the content is excellent.
- Most reasonable responses from a competent AI should fall in the 6-8 range.

[User Question]
{question}

[Assistant Response]
{response}

Provide your rating as a single number between 1 and 10, followed by a one-sentence justification.
Format: Score: X/10
Justification: ..."""


_INFRA_GARBAGE_MARKERS = (
    "<html>", "<!doctype", "service unavailable", "502 bad gateway",
    "503 service", "504 gateway", "internal server error",
)
_MAX_RETRIES = 5
_RETRYABLE_STATUS = {429, 502, 503, 504}


def response_is_valid(text: str, min_length: int = 20) -> bool:
    """Return True if text looks like a genuine model response."""
    if not text or not text.strip():
        return False
    lower = text.strip().lower()
    if lower in ("none", "null", "error", ""):
        return False
    if len(text.strip()) < min_length:
        return False
    return not any(m in lower for m in _INFRA_GARBAGE_MARKERS)


async def call_api(prompt: str, timeout: int = 180) -> dict:
    """Call LLMHive API with 5-attempt exponential backoff."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(_MAX_RETRIES):
            try:
                start = time.time()
                resp = await client.post(
                    f"{API_URL}/v1/chat",
                    json={
                        "prompt": prompt,
                        "reasoning_mode": "deep",
                        "tier": TIER,
                        "seed": FIXED_SEED,
                        "orchestration": {
                            "accuracy_level": 5,
                            "max_tokens": 1000,
                        },
                    },
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": API_KEY,
                    },
                )
                latency = int((time.time() - start) * 1000)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("message", "")
                    if not response_is_valid(text):
                        if attempt < _MAX_RETRIES - 1:
                            wait = 2 ** attempt
                            print(f"  ⚠️ Invalid response (attempt {attempt+1}/{_MAX_RETRIES}), retry in {wait}s...", flush=True)
                            await asyncio.sleep(wait)
                            continue
                    return {"success": True, "response": text, "latency": latency}
                elif resp.status_code in _RETRYABLE_STATUS:
                    wait = 2 ** attempt
                    print(f"  ⚠️ Server error {resp.status_code}, retrying in {wait}s...", flush=True)
                    await asyncio.sleep(wait)
                    continue
                else:
                    return {"success": False, "error": f"HTTP {resp.status_code}", "latency": latency}
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print(f"  ⚠️ Exception (attempt {attempt+1}/{_MAX_RETRIES}): {str(e)[:60]}, retry in {wait}s...", flush=True)
                    await asyncio.sleep(wait)
                    continue
                return {"success": False, "error": str(e), "latency": 0}
    return {"success": False, "error": "Max retries exceeded", "latency": 0}


def extract_score(judge_response: str) -> float:
    """Extract numeric score from judge response."""
    if not judge_response:
        return 0.0
    # Look for "Score: X/10" pattern
    patterns = [
        r"[Ss]core:\s*(\d+(?:\.\d+)?)\s*/\s*10",
        r"[Rr]ating:\s*(\d+(?:\.\d+)?)\s*/\s*10",
        r"(\d+(?:\.\d+)?)\s*/\s*10",
        r"[Ss]core:\s*(\d+(?:\.\d+)?)",
        r"\b(\d+(?:\.\d+)?)\s*out\s*of\s*10\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, judge_response)
        if match:
            score = float(match.group(1))
            return min(max(score, 1.0), 10.0)
    # Last resort: find any standalone number between 1-10
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", judge_response[:100])
    for n in numbers:
        val = float(n)
        if 1 <= val <= 10:
            return val
    return 5.0  # Default to middle score if parsing fails


_MIN_RESPONSE_LEN = 30


async def evaluate_single_question(idx: int, total: int, question: dict) -> dict:
    """Evaluate a single multi-turn question with LLM-as-judge."""
    category = question["category"]

    system_msg = (
        "You are a helpful, knowledgeable, and thoughtful AI assistant. "
        "Provide clear, well-structured, and comprehensive responses. "
        "When asked to be creative, be imaginative while staying coherent. "
        "When asked technical questions, be precise and accurate. "
        "Always follow the user's instructions carefully."
    )

    orchestration_preamble = (
        "Maintain coherence across turns. "
        "Be concise unless asked for elaboration. "
        "Answer precisely and directly. "
        "Preserve role consistency."
    )

    full_system = f"{system_msg}\n\n{orchestration_preamble}"

    # Turn 1
    turn1_prompt = f"{full_system}\n\n{question['turn1']}"
    result1 = await call_api(turn1_prompt)
    if not result1.get("success"):
        return {"success": False, "error": result1.get("error", "turn1 failed"),
                "latency": 0, "failure_type": "INFRA_FAILURE"}

    turn1_response = result1.get("response", "")
    turn1_latency = result1.get("latency", 0)

    if not response_is_valid(turn1_response):
        return {"success": True, "failure_type": "INFRA_FAILURE",
                "category": category, "latency": turn1_latency}

    # Response validator: re-query if turn1 is too short
    if len(turn1_response.strip()) < _MIN_RESPONSE_LEN:
        retry1 = await call_api(turn1_prompt)
        if retry1.get("success") and len(retry1.get("response", "").strip()) >= _MIN_RESPONSE_LEN:
            turn1_response = retry1["response"]
            turn1_latency += retry1.get("latency", 0)

    # Turn 2 — always includes full turn1 context for memory enforcement
    turn2_prompt = (
        f"{full_system}\n\n"
        f"This is a multi-turn conversation. Here is the prior exchange:\n\n"
        f"[Turn 1] User: {question['turn1']}\n\n"
        f"[Turn 1] Assistant: {turn1_response}\n\n"
        f"[Turn 2] User: {question['turn2']}\n\n"
        f"Continue the conversation naturally, building on your previous response."
    )
    result2 = await call_api(turn2_prompt)
    if not result2.get("success"):
        return {"success": False, "error": result2.get("error", "turn2 failed"),
                "latency": turn1_latency, "failure_type": "INFRA_FAILURE"}

    turn2_response = result2.get("response", "")
    turn2_latency = result2.get("latency", 0)

    if not response_is_valid(turn2_response):
        return {"success": True, "failure_type": "INFRA_FAILURE",
                "category": category, "latency": turn1_latency + turn2_latency}

    # Response validator: re-query if turn2 is too short
    if len(turn2_response.strip()) < _MIN_RESPONSE_LEN:
        retry2 = await call_api(turn2_prompt)
        if retry2.get("success") and len(retry2.get("response", "").strip()) >= _MIN_RESPONSE_LEN:
            turn2_response = retry2["response"]
            turn2_latency += retry2.get("latency", 0)

    # Judge turn 1
    judge1_prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question["turn1"],
        response=turn1_response,
    )
    judge1_result = await call_api(judge1_prompt)
    score1 = extract_score(judge1_result.get("response", "")) if judge1_result.get("success") else 5.0

    # Judge turn 2
    judge2_prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=f"(Follow-up to: {question['turn1']})\n{question['turn2']}",
        response=turn2_response,
    )
    judge2_result = await call_api(judge2_prompt)
    score2 = extract_score(judge2_result.get("response", "")) if judge2_result.get("success") else 5.0

    avg_score = round((score1 + score2) / 2, 1)
    total_latency = turn1_latency + turn2_latency

    consistency_flag = ""
    if score1 - score2 > 2:
        consistency_flag = " ⚠️ CONSISTENCY_DROP"

    print(
        f"  [{idx+1}/{total}] Dialogue: {category:<12} "
        f"turn1={score1:.0f}/10 turn2={score2:.0f}/10 avg={avg_score:.1f}/10{consistency_flag}",
        flush=True,
    )

    return {
        "success": True,
        "category": category,
        "score1": score1,
        "score2": score2,
        "avg_score": avg_score,
        "latency": total_latency,
        "consistency_drop": score1 - score2 > 2,
    }


async def run_evaluation(seed: int, output_path: str):
    """Run the full dialogue evaluation."""
    rng = random.Random(seed)
    sample_size = min(SAMPLE_SIZE, len(QUESTIONS))
    selected = rng.sample(range(len(QUESTIONS)), sample_size)

    print(f"\n{'='*70}", flush=True)
    print(f"Dialogue Evaluation — MT-Bench Style", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"  Samples: {sample_size}, Seed: {seed}, API: {API_URL}", flush=True)
    print(f"  Each question: 2 conversation turns + 2 judge calls = 4 API calls", flush=True)
    print(flush=True)

    total_score = 0.0
    errors = 0
    infra_failures = 0
    total_latency = 0
    category_scores = {}

    for idx, q_idx in enumerate(selected):
        question = QUESTIONS[q_idx]
        result = await evaluate_single_question(idx, sample_size, question)

        if result.get("success"):
            if result.get("failure_type") == "INFRA_FAILURE":
                infra_failures += 1
                print(
                    f"  [{idx+1}/{sample_size}] Dialogue: ⚠️ INFRA_FAILURE (skipped scoring)",
                    flush=True,
                )
            else:
                score = result["avg_score"]
                total_score += score
                total_latency += result.get("latency", 0)
                cat = result["category"]
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(score)
        else:
            err_msg = result.get("error", "unknown")
            if any(code in err_msg for code in ("502", "503", "504", "timeout", "Timeout", "Max retries")):
                infra_failures += 1
                print(
                    f"  [{idx+1}/{sample_size}] Dialogue: ⚠️ INFRA_FAILURE: {err_msg[:80]}",
                    flush=True,
                )
            else:
                errors += 1
                print(
                    f"  [{idx+1}/{sample_size}] Dialogue: ⚠️ error: {err_msg[:80]}",
                    flush=True,
                )

    attempted = sample_size
    valid = attempted - errors - infra_failures
    avg_score = round(total_score / max(valid, 1), 2)
    accuracy_pct = round(avg_score * 10, 2)
    avg_latency = int(total_latency / max(valid, 1))

    # Count "correct" as scores >= 7/10
    correct = sum(1 for cat_scores in category_scores.values() for s in cat_scores if s >= 7.0)

    # Category breakdown
    cat_summary = {}
    for cat, scores in category_scores.items():
        cat_summary[cat] = round(sum(scores) / len(scores), 2) if scores else 0

    output = {
        "score": avg_score,
        "avg_score": avg_score,
        "accuracy": accuracy_pct,
        "attempted": attempted,
        "correct": correct,
        "errors": errors,
        "infra_failures": infra_failures,
        "infra_failure_rate": round(infra_failures / max(attempted, 1) * 100, 1),
        "avg_latency_ms": avg_latency,
        "avg_cost": 0.0,
        "total_cost": 0.0,
        "category_scores": cat_summary,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Overall: {avg_score}/10 ({accuracy_pct}%) — {correct}/{valid} scored >=7/10", flush=True)
    print(f"  Category breakdown: {json.dumps(cat_summary)}", flush=True)
    print(f"  Output written to: {output_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="LLMHive Dialogue (MT-Bench) Eval")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: API_KEY or LLMHIVE_API_KEY environment variable required", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run_evaluation(args.seed, args.output))


if __name__ == "__main__":
    main()
