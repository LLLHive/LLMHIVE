#!/usr/bin/env python3
"""
LLMHive — Google Model Access Verification
============================================
Verifies GOOGLE_AI_API_KEY, discovers production models, and confirms
the selected model exists.

No inference calls.  Health = connectivity + auth + model listing +
model existence.

Usage:
    python scripts/verify_google_models.py [--json]

Exit codes:
    0  Google models verified and accessible.
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

# ===================================================================
# Model ranking helpers
# ===================================================================

_REJECT_PATTERN = re.compile(
    r"(preview|exp(erimental)?|deprecated|canary|internal|dev|vision)",
    re.IGNORECASE,
)


def _parse_version(model_name: str) -> tuple:
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
# Discovery + selection (no inference)
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
    if r.status_code == 400:
        print("  400 Bad Request — API key format may be incorrect")
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
    if not models:
        return None
    ranked = sorted(models, key=_rank_model, reverse=True)
    return ranked[0]


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
    print(f"  Timestamp:  {datetime.now().isoformat()}")
    print(f"  Method:     Model listing only (no inference)")
    print("=" * 70)

    report: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "status": "FAIL",
        "connectivity": False,
        "auth": False,
        "models_listed": False,
        "target_model_exists": False,
        "selected_model": None,
        "total_production_models": 0,
        "latency_ms": 0,
        "error": None,
    }

    # 1. Check API key
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("\n  ABORT: GOOGLE_AI_API_KEY is not set.")
        report["error"] = "GOOGLE_AI_API_KEY not set"
        _save_and_print(report, args.json)
        return 1

    print(f"\n  GOOGLE_AI_API_KEY present ({len(api_key)} chars)")

    # 2. Discover models (connectivity + auth + listing in one call)
    print("\n  Discovering production models...")
    t0 = time.time()
    models = discover_google_models(api_key)
    report["latency_ms"] = int((time.time() - t0) * 1000)
    report["connectivity"] = True
    report["total_production_models"] = len(models)

    if not models:
        print("  ABORT: No production models found.")
        report["error"] = "No production models found"
        _save_and_print(report, args.json)
        return 1

    report["auth"] = True
    report["models_listed"] = True

    print(f"  Found {len(models)} production models (latency: {report['latency_ms']}ms):")
    for m in sorted(models, key=_rank_model, reverse=True)[:8]:
        name = m.get("name", "").replace("models/", "")
        ctx = m.get("inputTokenLimit", 0)
        print(f"    {name:<35} ctx={ctx}")

    # 3. Select best
    best = select_best_model(models)
    if not best:
        print("  ABORT: Could not select a model.")
        report["error"] = "Selection failed"
        _save_and_print(report, args.json)
        return 1

    short_name = best.get("name", "").replace("models/", "")
    report["selected_model"] = short_name
    report["target_model_exists"] = True
    report["status"] = "PASS"

    print(f"\n  Selected Google Model: {short_name}")

    # Latency guard
    if report["latency_ms"] > 10_000:
        print(f"  WARN: Latency {report['latency_ms']}ms exceeds 10s")
        report["status"] = "FAIL"
        report["error"] = f"Latency {report['latency_ms']}ms > 10s"

    # Summary
    print()
    print(f"  {'Check':<25} {'Result'}")
    print(f"  {'-'*25} {'-'*10}")
    print(f"  {'Connectivity':<25} {'PASS' if report['connectivity'] else 'FAIL'}")
    print(f"  {'Authentication':<25} {'PASS' if report['auth'] else 'FAIL'}")
    print(f"  {'Models Listed':<25} {'PASS' if report['models_listed'] else 'FAIL'}")
    print(f"  {'Target Model Exists':<25} {'PASS' if report['target_model_exists'] else 'FAIL'}")
    print(f"  {'Overall':<25} {report['status']}")
    print()

    _save_and_print(report, args.json)
    return 0 if report["status"] == "PASS" else 1


def _save_and_print(report: Dict[str, Any], as_json: bool) -> None:
    report_path = _PROJECT_ROOT / "benchmark_reports" / "google_model_verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: {report_path}")
    if as_json:
        print()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    sys.exit(main())
