#!/usr/bin/env python3
"""
LLMHive — Google Model Access Verification
============================================
Verifies GOOGLE_AI_API_KEY, discovers production models, selects the
best stable candidate, and performs a lightweight inference test.

Usage:
    python scripts/verify_google_models.py [--json]

Exit codes:
    0  Google model verified and healthy.
    1  Verification failed — abort certification.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ===================================================================
# Model ranking helpers
# ===================================================================

_REJECT_PATTERN = re.compile(
    r"(preview|exp(erimental)?|deprecated|canary|internal|dev|vision)",
    re.IGNORECASE,
)


def _parse_version(model_name: str) -> tuple:
    """Extract (major, minor) version from model name for ranking."""
    m = re.search(r"gemini-(\d+)\.(\d+)", model_name)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = re.search(r"gemini-(\d+)", model_name)
    if m:
        return (int(m.group(1)), 0)
    return (0, 0)


def _variant_score(model_name: str) -> int:
    lower = model_name.lower()
    if "pro" in lower:
        return 100
    if "ultra" in lower:
        return 90
    if "flash" in lower:
        return 50
    if "nano" in lower:
        return 10
    return 30


def _rank_model(model: dict) -> tuple:
    name = model.get("name", "").replace("models/", "")
    ver = _parse_version(name)
    variant = _variant_score(name)
    ctx = model.get("inputTokenLimit", 0)
    return (ver[0], ver[1], variant, ctx)


# ===================================================================
# Discovery + selection
# ===================================================================

def discover_google_models(api_key: str) -> List[dict]:
    """Fetch all models from Google AI API and filter to production."""
    if not _HAS_HTTPX:
        print("  httpx not installed — cannot query Google AI")
        return []

    try:
        r = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
            timeout=15,
        )
    except Exception as exc:
        print(f"  Google AI API unreachable: {exc}")
        return []

    if r.status_code == 401:
        print("  GOOGLE_AI_API_KEY rejected (401 Unauthorized)")
        return []
    if r.status_code == 404:
        print("  Google AI models endpoint returned 404")
        return []
    if r.status_code != 200:
        print(f"  Google AI models endpoint returned HTTP {r.status_code}")
        return []

    raw_models = r.json().get("models", [])
    production: List[dict] = []

    for m in raw_models:
        name = m.get("name", "")
        methods = m.get("supportedGenerationMethods", [])

        if "generateContent" not in methods:
            continue

        short_name = name.replace("models/", "")
        if _REJECT_PATTERN.search(short_name):
            continue

        if not any(short_name.startswith(f"gemini-{v}") for v in ("1.5", "2.0", "2.5", "3")):
            continue

        production.append(m)

    return production


def select_best_model(models: List[dict]) -> Optional[dict]:
    """Select the highest-ranked stable production model (Pro preferred)."""
    if not models:
        return None
    ranked = sorted(models, key=_rank_model, reverse=True)
    return ranked[0]


def validate_model(api_key: str, model_name: str) -> Dict[str, Any]:
    """Perform a lightweight test call: ask the model to return '4'."""
    short = model_name.replace("models/", "")
    result: Dict[str, Any] = {
        "model": short,
        "status": "FAIL",
        "latency_ms": 0,
        "error": None,
    }

    if not _HAS_HTTPX:
        result["error"] = "httpx not installed"
        return result

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"{model_name}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": "Return the number 4."}]}],
        "generationConfig": {"maxOutputTokens": 10},
    }

    t0 = time.time()
    try:
        r = httpx.post(url, json=payload, timeout=15)
        latency = int((time.time() - t0) * 1000)
        result["latency_ms"] = latency

        if r.status_code == 404:
            result["error"] = "404 — model not found"
            return result
        if r.status_code == 401:
            result["error"] = "401 — unauthorized"
            return result
        if r.status_code != 200:
            result["error"] = f"HTTP {r.status_code}"
            return result

        data = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            result["error"] = "Empty response — no candidates"
            return result

        text = ""
        parts = candidates[0].get("content", {}).get("parts", [])
        for p in parts:
            text += p.get("text", "")

        if "4" in text:
            result["status"] = "PASS"
        else:
            result["error"] = f"Unexpected response: {text[:80]}"

    except httpx.TimeoutException:
        result["latency_ms"] = int((time.time() - t0) * 1000)
        result["error"] = "Timeout"
    except Exception as exc:
        result["latency_ms"] = int((time.time() - t0) * 1000)
        result["error"] = str(exc)

    return result


# ===================================================================
# Main
# ===================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="LLMHive — Google Model Access Verification"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    print("=" * 70)
    print("LLMHive — Google Model Access Verification")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    report: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "status": "FAIL",
        "selected_model": None,
        "total_production_models": 0,
        "test_result": None,
    }

    # 1. Check API key
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("\n  ABORT: GOOGLE_AI_API_KEY is not set.")
        report["error"] = "GOOGLE_AI_API_KEY not set"
        if args.json:
            print(json.dumps(report, indent=2))
        return 1

    print(f"\n  GOOGLE_AI_API_KEY present ({len(api_key)} chars)")

    # 2. Discover models
    print("\n  Discovering production models...")
    models = discover_google_models(api_key)
    report["total_production_models"] = len(models)

    if not models:
        print("  ABORT: No production models found.")
        report["error"] = "No production models found"
        if args.json:
            print(json.dumps(report, indent=2))
        return 1

    print(f"  Found {len(models)} production models:")
    for m in sorted(models, key=_rank_model, reverse=True)[:8]:
        name = m.get("name", "").replace("models/", "")
        ctx = m.get("inputTokenLimit", 0)
        print(f"    {name:<35} ctx={ctx}")

    # 3. Select best
    best = select_best_model(models)
    if not best:
        print("  ABORT: Could not select a model.")
        report["error"] = "Selection failed"
        if args.json:
            print(json.dumps(report, indent=2))
        return 1

    best_name = best.get("name", "")
    short_name = best_name.replace("models/", "")
    report["selected_model"] = short_name
    print(f"\n  Selected Google Model: {short_name}")

    # 4. Validate
    print("  Running lightweight test call...")
    result = validate_model(api_key, best_name)
    report["test_result"] = result

    if result["status"] == "PASS":
        print(f"  Status: PASS (latency: {result['latency_ms']}ms)")
        report["status"] = "PASS"
    else:
        print(f"  Status: FAIL — {result.get('error', 'unknown')}")
        report["error"] = result.get("error")

    # Latency guard
    if result["latency_ms"] > 10000:
        print(f"  ABORT: Latency {result['latency_ms']}ms exceeds 10s limit")
        report["status"] = "FAIL"
        report["error"] = f"Latency {result['latency_ms']}ms > 10s"

    print()

    # Save report
    report_path = _PROJECT_ROOT / "benchmark_reports" / "google_model_verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: {report_path}")

    if args.json:
        print()
        print(json.dumps(report, indent=2))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
