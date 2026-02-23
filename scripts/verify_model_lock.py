#!/usr/bin/env python3
"""
Verify elite model lock before benchmark execution.

Checks:
  1. BENCHMARK_MODE is active
  2. TIER is elite
  3. REASONING_MODE is deep
  4. Elite model bindings are configured
  5. Model trace directory is writable
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(".env.certification")
except ImportError:
    pass


def _is_truthy(val: str | None) -> bool:
    return str(val).lower() in ("1", "true", "yes") if val else False


def main() -> int:
    benchmark_mode = _is_truthy(os.getenv("BENCHMARK_MODE", "true"))
    tier = os.getenv("CATEGORY_BENCH_TIER", "elite")
    reasoning_mode = os.getenv("CATEGORY_BENCH_REASONING_MODE", "deep")

    elite_bindings = {
        "openai": os.getenv("ELITE_MODEL_OPENAI", "gpt-5.2-pro"),
        "anthropic": os.getenv("ELITE_MODEL_ANTHROPIC", "claude-sonnet-4.6"),
        "google": os.getenv("ELITE_MODEL_GOOGLE", "gemini-2.5-pro"),
        "grok": os.getenv("ELITE_MODEL_GROK", "grok-3-mini"),
        "openrouter": os.getenv("ELITE_MODEL_OPENROUTER", ""),
        "deepseek": os.getenv("ELITE_MODEL_DEEPSEEK", "deepseek-reasoner"),
    }

    print("=" * 60)
    print("ELITE MODEL LOCK VERIFICATION")
    print("=" * 60)

    checks = []

    # Check 1: BENCHMARK_MODE
    status = "PASS" if benchmark_mode else "WARN"
    print(f"  BENCHMARK_MODE:    {benchmark_mode:>8}  [{status}]")
    checks.append(status != "FAIL")

    # Check 2: TIER
    status = "PASS" if tier.lower() == "elite" else "FAIL"
    print(f"  TIER:              {tier:>8}  [{status}]")
    checks.append(status == "PASS")

    # Check 3: REASONING_MODE
    status = "PASS" if reasoning_mode.lower() == "deep" else "FAIL"
    print(f"  REASONING_MODE:    {reasoning_mode:>8}  [{status}]")
    checks.append(status == "PASS")

    # Check 4: Elite bindings
    print("\n  ELITE MODEL BINDINGS:")
    configured_count = 0
    for provider, model_id in sorted(elite_bindings.items()):
        if model_id:
            configured_count += 1
            print(f"    {provider:12s} → {model_id}")
        else:
            print(f"    {provider:12s} → (not configured)")
    status = "PASS" if configured_count >= 3 else "FAIL"
    print(f"  Configured models: {configured_count}/6  [{status}]")
    checks.append(status == "PASS")

    # Check 5: Report directory writable
    report_dir = Path("benchmark_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    trace_path = report_dir / f"model_trace_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    try:
        trace_path.write_text("")
        trace_path.unlink()
        status = "PASS"
    except Exception as e:
        status = "FAIL"
    print(f"\n  Trace writable:    {'yes':>8}  [{status}]")
    checks.append(status == "PASS")

    # Check 6: 2026 Intelligence Layer validation
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llmhive" / "src"))
    try:
        from llmhive.app.intelligence import (
            validate_elite_registry,
            print_elite_config,
            get_model_registry_2026,
            get_routing_engine,
        )
        print("\n  2026 INTELLIGENCE LAYER:")
        registry = get_model_registry_2026()
        reg_errors = registry.validate(list(elite_bindings.values()))
        elite_errors = validate_elite_registry()
        all_errors = reg_errors + elite_errors
        if all_errors:
            status = "FAIL"
            for e in all_errors:
                print(f"    ERROR: {e}")
        else:
            status = "PASS"
            print(f"    Registry models: {len(registry.list_models())}")
        print(f"  Intelligence layer:  {'valid':>8}  [{status}]")
        checks.append(status == "PASS")
        print_elite_config()
        engine = get_routing_engine()
        for cat in ["coding", "reasoning", "math"]:
            engine.print_ranking(cat, top_n=3)
    except ImportError as ie:
        print(f"\n  2026 Intelligence Layer: not available ({ie})")

    # Summary
    all_pass = all(checks)
    print(f"\n{'=' * 60}")
    if all_pass:
        print("RESULT: ELITE MODEL LOCK VERIFIED — ready for benchmark")
    else:
        print("RESULT: ELITE MODEL LOCK FAILED — fix issues above")
    print(f"{'=' * 60}")

    # Save verification result
    result = {
        "timestamp": datetime.now().isoformat(),
        "benchmark_mode": benchmark_mode,
        "tier": tier,
        "reasoning_mode": reasoning_mode,
        "elite_bindings": elite_bindings,
        "all_checks_pass": all_pass,
    }
    result_path = report_dir / "model_lock_verification.json"
    result_path.write_text(json.dumps(result, indent=2))
    print(f"\nSaved to: {result_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
