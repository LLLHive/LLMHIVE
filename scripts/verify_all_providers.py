#!/usr/bin/env python3
"""
LLMHive — Multi-Provider Access Verification
==============================================
Validates provider health through connectivity, authentication, and
model listing — no inference calls.

Usage:
    python scripts/verify_all_providers.py [--json] [--strict]
    python scripts/verify_all_providers.py --required google openrouter deepseek huggingface
    python scripts/verify_all_providers.py --strict --required openai,google,anthropic

Exit codes:
    0  All required providers passed.
    1  One or more required providers failed — abort certification.
"""

import argparse
import json
import os
import sys
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

from provider_health_adapters import check_all, ALL_ADAPTERS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def verify_all_providers(
    required: Optional[List[str]] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Run adapter-based health checks and print results."""
    report = check_all(required=required, strict=strict)
    providers = report["providers"]

    print()
    print(f"  {'Provider':<15} {'Status':<8} {'Latency':<10} {'Models':<8} {'Selected Model'}")
    print(f"  {'-'*15} {'-'*8} {'-'*10} {'-'*8} {'-'*30}")

    for name, info in providers.items():
        status = info.get("status", "?")
        latency = info.get("latency_ms", 0)
        lat_str = f"{latency}ms" if latency > 0 else "-"
        models = info.get("models_found", 0)
        mod_str = str(models) if models > 0 else "-"
        selected = info.get("selected_model", "")
        err = info.get("error", "")

        note = selected if status == "PASS" else err
        print(f"  {name:<15} {status:<8} {lat_str:<10} {mod_str:<8} {note}")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LLMHive — Multi-Provider Access Verification"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--required", nargs="+", default=[],
        help="Required provider names (e.g., --required google openrouter deepseek)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat SKIP as FAIL (all providers must have keys and pass)",
    )
    args = parser.parse_args()

    # Normalize: support both "google,openrouter" and "google openrouter"
    required_raw: list = []
    for token in args.required:
        required_raw.extend(t.strip() for t in token.split(",") if t.strip())
    required = required_raw if required_raw else None

    print("=" * 70)
    print("LLMHive — Multi-Provider Access Verification")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print(f"  Method:    Adapter-based (connectivity + auth + model listing)")
    if required:
        print(f"  Required:  {', '.join(required)}")
    if args.strict:
        print(f"  Mode:      STRICT (SKIP = FAIL)")
    print("=" * 70)

    report = verify_all_providers(required=required, strict=args.strict)

    print()
    if report["status"] == "PASS":
        print("  PROVIDER VERIFICATION: PASS")
    else:
        print("  PROVIDER VERIFICATION: FAIL")
        failed = [
            k for k, v in report["providers"].items()
            if v.get("status") == "FAIL"
        ]
        if failed:
            print(f"  Failed: {', '.join(failed)}")
        if required:
            missing = [
                r for r in required
                if report["providers"].get(r, {}).get("status") != "PASS"
            ]
            if missing:
                print(f"  Required but not passing: {', '.join(missing)}")

    report["timestamp"] = datetime.now().isoformat()
    report_path = _PROJECT_ROOT / "benchmark_reports" / "provider_verification.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n  Report saved: {report_path}")

    if args.json:
        print()
        print(json.dumps(report, indent=2, default=str))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
