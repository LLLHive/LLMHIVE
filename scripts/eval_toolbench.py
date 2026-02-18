#!/usr/bin/env python3
"""
LLMHive Tool Use Evaluation
============================
Self-contained eval script for the Tool Use benchmark category.

Tests the model's ability to select appropriate tools and provide correct
arguments given user queries and available function schemas.

Output: JSON with {accuracy, attempted, correct, errors, avg_latency_ms, ...}

Usage:
    python scripts/eval_toolbench.py --output /tmp/toolbench_eval.json --seed 42
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
SAMPLE_SIZE = int(os.getenv("CATEGORY_BENCH_TOOLBENCH_SAMPLES", "10"))
FIXED_SEED = int(os.getenv("CATEGORY_BENCH_SEED", "42"))

# ---------------------------------------------------------------------------
# Tool-use scenarios
# ---------------------------------------------------------------------------

TOOLS = {
    "get_weather": {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or coordinates"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature unit"},
            },
            "required": ["location"],
        },
    },
    "search_web": {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "description": "Number of results to return"},
            },
            "required": ["query"],
        },
    },
    "send_email": {
        "name": "send_email",
        "description": "Send an email to a recipient",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    "calculate": {
        "name": "calculate",
        "description": "Perform a mathematical calculation",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate"},
            },
            "required": ["expression"],
        },
    },
    "create_calendar_event": {
        "name": "create_calendar_event",
        "description": "Create a calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "date": {"type": "string", "description": "Event date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Event time in HH:MM format"},
                "duration_minutes": {"type": "integer", "description": "Duration in minutes"},
            },
            "required": ["title", "date", "time"],
        },
    },
    "translate_text": {
        "name": "translate_text",
        "description": "Translate text from one language to another",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to translate"},
                "source_language": {"type": "string", "description": "Source language code (e.g., en, fr, es)"},
                "target_language": {"type": "string", "description": "Target language code"},
            },
            "required": ["text", "target_language"],
        },
    },
    "get_stock_price": {
        "name": "get_stock_price",
        "description": "Get the current stock price for a ticker symbol",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock ticker symbol (e.g., AAPL, GOOGL)"},
                "include_history": {"type": "boolean", "description": "Include 30-day price history"},
            },
            "required": ["ticker"],
        },
    },
    "set_reminder": {
        "name": "set_reminder",
        "description": "Set a reminder for a specific time",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Reminder message"},
                "datetime": {"type": "string", "description": "When to remind in ISO format"},
            },
            "required": ["message", "datetime"],
        },
    },
    "convert_currency": {
        "name": "convert_currency",
        "description": "Convert an amount from one currency to another",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Amount to convert"},
                "from_currency": {"type": "string", "description": "Source currency code (e.g., USD)"},
                "to_currency": {"type": "string", "description": "Target currency code (e.g., EUR)"},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
    "get_directions": {
        "name": "get_directions",
        "description": "Get driving/walking directions between two locations",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Starting location"},
                "destination": {"type": "string", "description": "Destination location"},
                "mode": {"type": "string", "enum": ["driving", "walking", "transit"], "description": "Travel mode"},
            },
            "required": ["origin", "destination"],
        },
    },
}

SCENARIOS = [
    {
        "query": "What's the weather like in Tokyo right now? Give me the temperature in Celsius.",
        "available_tools": ["get_weather", "search_web", "calculate"],
        "expected_tool": "get_weather",
        "expected_args": {"location": "Tokyo", "unit": "celsius"},
        "required_args": ["location"],
    },
    {
        "query": "Send an email to john@example.com with subject 'Meeting Tomorrow' and tell him the meeting is at 3pm in conference room B.",
        "available_tools": ["send_email", "set_reminder", "create_calendar_event"],
        "expected_tool": "send_email",
        "expected_args": {"to": "john@example.com", "subject": "Meeting Tomorrow"},
        "required_args": ["to", "subject", "body"],
    },
    {
        "query": "What is 2847 multiplied by 39?",
        "available_tools": ["calculate", "search_web", "translate_text"],
        "expected_tool": "calculate",
        "expected_args": {"expression": "2847 * 39"},
        "required_args": ["expression"],
    },
    {
        "query": "Schedule a team standup meeting for January 15, 2026 at 9:30 AM, lasting 30 minutes.",
        "available_tools": ["create_calendar_event", "set_reminder", "send_email"],
        "expected_tool": "create_calendar_event",
        "expected_args": {"title": "team standup", "date": "2026-01-15", "time": "09:30"},
        "required_args": ["title", "date", "time"],
    },
    {
        "query": "Translate 'Good morning, how are you?' into Spanish.",
        "available_tools": ["translate_text", "search_web", "send_email"],
        "expected_tool": "translate_text",
        "expected_args": {"target_language": "es"},
        "required_args": ["text", "target_language"],
    },
    {
        "query": "What's Apple's current stock price?",
        "available_tools": ["get_stock_price", "search_web", "calculate"],
        "expected_tool": "get_stock_price",
        "expected_args": {"ticker": "AAPL"},
        "required_args": ["ticker"],
    },
    {
        "query": "Remind me to call the dentist tomorrow at 2pm.",
        "available_tools": ["set_reminder", "create_calendar_event", "send_email"],
        "expected_tool": "set_reminder",
        "expected_args": {},
        "required_args": ["message"],
    },
    {
        "query": "Convert 500 US dollars to Euros.",
        "available_tools": ["convert_currency", "calculate", "search_web"],
        "expected_tool": "convert_currency",
        "expected_args": {"amount": 500, "from_currency": "USD", "to_currency": "EUR"},
        "required_args": ["amount", "from_currency", "to_currency"],
    },
    {
        "query": "How do I get from Times Square to JFK Airport by transit?",
        "available_tools": ["get_directions", "search_web", "get_weather"],
        "expected_tool": "get_directions",
        "expected_args": {"origin": "Times Square", "destination": "JFK Airport", "mode": "transit"},
        "required_args": ["origin", "destination"],
    },
    {
        "query": "Search for the latest news about artificial intelligence breakthroughs.",
        "available_tools": ["search_web", "get_stock_price", "translate_text"],
        "expected_tool": "search_web",
        "expected_args": {"query": "artificial intelligence breakthroughs"},
        "required_args": ["query"],
    },
    {
        "query": "What's the current temperature in Berlin in Fahrenheit?",
        "available_tools": ["get_weather", "convert_currency", "search_web"],
        "expected_tool": "get_weather",
        "expected_args": {"location": "Berlin", "unit": "fahrenheit"},
        "required_args": ["location"],
    },
    {
        "query": "Send a meeting invitation email to alice@company.com about the Q4 budget review.",
        "available_tools": ["send_email", "create_calendar_event", "search_web"],
        "expected_tool": "send_email",
        "expected_args": {"to": "alice@company.com"},
        "required_args": ["to", "subject", "body"],
    },
    {
        "query": "Calculate the compound interest on $10,000 at 5% annual rate for 3 years.",
        "available_tools": ["calculate", "convert_currency", "get_stock_price"],
        "expected_tool": "calculate",
        "expected_args": {},
        "required_args": ["expression"],
    },
    {
        "query": "Translate 'Thank you very much' into Japanese.",
        "available_tools": ["translate_text", "search_web", "get_directions"],
        "expected_tool": "translate_text",
        "expected_args": {"target_language": "ja"},
        "required_args": ["text", "target_language"],
    },
    {
        "query": "Get me directions from LAX to Hollywood Walk of Fame, driving.",
        "available_tools": ["get_directions", "search_web", "get_weather"],
        "expected_tool": "get_directions",
        "expected_args": {"mode": "driving"},
        "required_args": ["origin", "destination"],
    },
    {
        "query": "How much is 1000 British Pounds in Japanese Yen?",
        "available_tools": ["convert_currency", "calculate", "search_web"],
        "expected_tool": "convert_currency",
        "expected_args": {"amount": 1000, "from_currency": "GBP", "to_currency": "JPY"},
        "required_args": ["amount", "from_currency", "to_currency"],
    },
    {
        "query": "Set up a dentist appointment on my calendar for March 5, 2026 at 2:00 PM for 1 hour.",
        "available_tools": ["create_calendar_event", "set_reminder", "send_email"],
        "expected_tool": "create_calendar_event",
        "expected_args": {"date": "2026-03-05", "time": "14:00", "duration_minutes": 60},
        "required_args": ["title", "date", "time"],
    },
    {
        "query": "Look up what Tesla's stock is trading at today and include the recent history.",
        "available_tools": ["get_stock_price", "search_web", "calculate"],
        "expected_tool": "get_stock_price",
        "expected_args": {"ticker": "TSLA", "include_history": True},
        "required_args": ["ticker"],
    },
    {
        "query": "Remind me to submit the report at 5pm on Friday.",
        "available_tools": ["set_reminder", "create_calendar_event", "send_email"],
        "expected_tool": "set_reminder",
        "expected_args": {},
        "required_args": ["message"],
    },
    {
        "query": "Find information about the latest Mars rover discoveries.",
        "available_tools": ["search_web", "translate_text", "get_weather"],
        "expected_tool": "search_web",
        "expected_args": {},
        "required_args": ["query"],
    },
]


def build_prompt(scenario: dict) -> str:
    """Build a tool-calling prompt for the model."""
    tools_json = json.dumps(
        [TOOLS[t] for t in scenario["available_tools"]],
        indent=2,
    )
    return (
        "You are a tool-calling AI assistant. You MUST respond with a single JSON object and NOTHING else.\n"
        "Do NOT include any explanation, markdown formatting, or commentary — ONLY raw JSON.\n\n"
        "Available tools:\n"
        f"{tools_json}\n\n"
        f"User request: {scenario['query']}\n\n"
        "RESPOND with exactly ONE JSON object in this EXACT format (no extra text):\n"
        '{"tool": "<tool_name>", "arguments": {"<arg_name>": <arg_value>}}\n\n'
        "Output ONLY the JSON object:"
    )


def parse_tool_call(response_text: str) -> dict:
    """Extract tool call JSON from model response."""
    if not response_text:
        return {}

    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            if "name" in obj and "tool" not in obj:
                obj["tool"] = obj.pop("name")
            if "function" in obj and "tool" not in obj:
                obj["tool"] = obj.pop("function")
            if "parameters" in obj and "arguments" not in obj:
                obj["arguments"] = obj.pop("parameters")
            return obj
    except json.JSONDecodeError:
        pass

    # Regex fallback
    patterns = [
        r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}[^}]*\}',
        r'\{[^{}]*"name"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}[^}]*\}',
        r'\{[^{}]*"function"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]*\}[^}]*\}',
    ]
    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group())
                return obj
            except json.JSONDecodeError:
                continue

    # Brute-force: find any JSON object
    try:
        start = response_text.index("{")
        depth = 0
        for i in range(start, len(response_text)):
            if response_text[i] == "{":
                depth += 1
            elif response_text[i] == "}":
                depth -= 1
            if depth == 0:
                obj = json.loads(response_text[start : i + 1])
                if "name" in obj and "tool" not in obj:
                    obj["tool"] = obj.pop("name")
                if "function" in obj and "tool" not in obj:
                    obj["tool"] = obj.pop("function")
                if "parameters" in obj and "arguments" not in obj:
                    obj["arguments"] = obj.pop("parameters")
                return obj
    except (ValueError, json.JSONDecodeError):
        pass
    return {}


def score_tool_call(parsed: dict, scenario: dict) -> tuple:
    """Score a parsed tool call. Returns (tool_correct, args_correct, total_points, max_points)."""
    tool_name = parsed.get("tool") or parsed.get("name") or parsed.get("function") or ""
    args = parsed.get("arguments") or parsed.get("parameters") or {}

    tool_correct = tool_name.lower().strip() == scenario["expected_tool"].lower().strip()

    # Check required arguments are present
    required = scenario["required_args"]
    args_present = sum(1 for a in required if a in args) if args else 0
    args_total = len(required)

    # Tool name is worth 1 point, each required arg is worth 1 point
    max_points = 1 + args_total
    points = (1 if tool_correct else 0) + args_present

    return tool_correct, args_present == args_total, points, max_points


_INFRA_GARBAGE_MARKERS = (
    "<html>", "<!doctype", "service unavailable", "502 bad gateway",
    "503 service", "504 gateway", "internal server error",
)
_MAX_RETRIES = 5
_RETRYABLE_STATUS = {429, 502, 503, 504}


def response_is_valid(text: str) -> bool:
    """Return True if text looks like a genuine model response."""
    if not text or not text.strip():
        return False
    lower = text.strip().lower()
    if lower in ("none", "null", "error", ""):
        return False
    return not any(m in lower for m in _INFRA_GARBAGE_MARKERS)


async def call_api(prompt: str, timeout: int = 120) -> dict:
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
                            "max_tokens": 500,
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


async def run_evaluation(seed: int, output_path: str):
    """Run the full tool-use evaluation."""
    rng = random.Random(seed)
    sample_size = min(SAMPLE_SIZE, len(SCENARIOS))
    selected = rng.sample(range(len(SCENARIOS)), sample_size)

    correct = 0
    errors = 0
    infra_failures = 0
    parsing_failures = 0
    total_points = 0
    max_points = 0
    total_latency = 0

    print(f"\n{'='*70}", flush=True)
    print(f"Tool Use Evaluation", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"  Samples: {sample_size}, Seed: {seed}, API: {API_URL}", flush=True)
    print(flush=True)

    for idx, scenario_idx in enumerate(selected):
        scenario = SCENARIOS[scenario_idx]
        prompt = build_prompt(scenario)
        result = await call_api(prompt)

        if result.get("success"):
            resp_text = result.get("response", "")

            # INFRA HARDENING: check response validity
            if not response_is_valid(resp_text):
                infra_failures += 1
                max_points += 1 + len(scenario["required_args"])
                print(
                    f"  [{idx+1}/{sample_size}] ToolUse: ⚠️ INFRA_FAILURE (invalid response)",
                    flush=True,
                )
                continue

            total_latency += result.get("latency", 0)
            parsed = parse_tool_call(resp_text)

            # INFRA HARDENING: if JSON parse produced nothing, retry with strict instruction
            if not parsed or not (parsed.get("tool") or parsed.get("name") or parsed.get("function")):
                strict_prompt = prompt + "\n\nCRITICAL: Return ONLY valid JSON. No markdown, no explanation."
                retry_result = await call_api(strict_prompt)
                if retry_result.get("success"):
                    parsed = parse_tool_call(retry_result.get("response", ""))

            # Classify: still no valid parse after retry?
            if not parsed or not (parsed.get("tool") or parsed.get("name") or parsed.get("function")):
                parsing_failures += 1
                max_points += 1 + len(scenario["required_args"])
                print(
                    f"  [{idx+1}/{sample_size}] ToolUse: ⚠️ PARSING_FAILURE (no valid JSON after retry)",
                    flush=True,
                )
                continue

            tool_ok, args_ok, pts, max_pts = score_tool_call(parsed, scenario)
            total_points += pts
            max_points += max_pts

            if tool_ok and args_ok:
                correct += 1
                status = "✅"
            elif tool_ok:
                status = "⚠️ tool ok, args incomplete"
            else:
                status = "❌"

            called = parsed.get("tool") or parsed.get("name") or parsed.get("function") or "none"
            print(
                f"  [{idx+1}/{sample_size}] ToolUse: {status} "
                f"expected={scenario['expected_tool']} got={called} "
                f"({correct}/{idx+1} fully correct)",
                flush=True,
            )
        else:
            err_msg = result.get("error", "")
            if any(tok in err_msg for tok in ("502", "503", "504", "timeout", "Timeout", "Max retries")):
                infra_failures += 1
            else:
                errors += 1
            max_points += 1 + len(scenario["required_args"])
            print(
                f"  [{idx+1}/{sample_size}] ToolUse: ⚠️ error: {err_msg[:80]}",
                flush=True,
            )

    attempted = sample_size
    valid = attempted - errors - infra_failures
    accuracy = round((correct / valid) * 100, 2) if valid > 0 else 0.0
    weighted_accuracy = round((total_points / max_points) * 100, 2) if max_points > 0 else 0.0
    avg_latency = int(total_latency / max(valid, 1))

    output = {
        "accuracy": accuracy,
        "success_rate": accuracy,
        "weighted_accuracy": weighted_accuracy,
        "attempted": attempted,
        "correct": correct,
        "errors": errors,
        "infra_failures": infra_failures,
        "parsing_failures": parsing_failures,
        "infra_failure_rate": round(infra_failures / max(attempted, 1) * 100, 1),
        "total_points": total_points,
        "max_points": max_points,
        "avg_latency_ms": avg_latency,
        "avg_cost": 0.0,
        "total_cost": 0.0,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Result: {correct}/{valid} = {accuracy}% (weighted: {weighted_accuracy}%, errors: {errors}, infra: {infra_failures}, parse: {parsing_failures})", flush=True)
    print(f"  Output written to: {output_path}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="LLMHive Tool Use Eval")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--data-dir", default="", help="Data directory (unused, for compatibility)")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: API_KEY or LLMHIVE_API_KEY environment variable required", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run_evaluation(args.seed, args.output))


if __name__ == "__main__":
    main()
