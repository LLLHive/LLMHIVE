#!/usr/bin/env python3
"""
LLMHive — Weekly Model Upgrade Workflow
========================================
Discovers the latest models across all providers, compares them against
the current production lineup, and generates an upgrade proposal if a
higher-tier candidate is found.

Never auto-activates — requires ``MODEL_UPGRADE_APPROVED=true`` to apply.

Usage:
    python scripts/weekly_model_upgrade.py [--apply]

Environment:
    MODEL_UPGRADE_APPROVED=true   Required to actually apply an upgrade.
    OPENAI_API_KEY                Optional — enables OpenAI discovery.
    ANTHROPIC_API_KEY             Optional — enables Anthropic discovery.
    GOOGLE_AI_API_KEY             Optional — enables Google discovery.
    XAI_API_KEY                   Optional — enables Grok discovery.
    DEEPSEEK_API_KEY              Optional — enables DeepSeek discovery.
    GROQ_API_KEY                  Optional — enables Groq discovery.
    TOGETHER_API_KEY              Optional — enables Together discovery.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llmhive" / "src"))

from llmhive.app.providers.provider_policy import (
    ALL_POLICIES,
    discover_all_providers,
    select_best_model,
    shadow_validate_candidate,
    DiscoveredModel,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REPORTS_DIR = _PROJECT_ROOT / "benchmark_reports"


def _load_current_models() -> dict:
    """Load the current production model selection (if recorded)."""
    path = _REPORTS_DIR / "current_models.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save_current_models(models: dict) -> None:
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (_REPORTS_DIR / "current_models.json").write_text(json.dumps(models, indent=2))


async def run_discovery():
    print("=" * 70)
    print("LLMHive — Weekly Model Upgrade Discovery")
    print("=" * 70)
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print()

    discovered = await discover_all_providers()

    current = _load_current_models()
    proposals: list = []

    print(f"{'Provider':<15} {'Discovered':<8} {'Stable':<8} {'Best Candidate':<40}")
    print(f"{'-'*15} {'-'*8} {'-'*8} {'-'*40}")

    for provider_name, models in discovered.items():
        best = select_best_model(discovered, provider_name, workload="reasoning")
        best_id = best.model_id if best else "(none)"
        print(f"  {provider_name:<15} {len(models):<8} {len(models):<8} {best_id:<40}")

        if best:
            current_model = current.get(provider_name, {}).get("model_id", "")
            if current_model and current_model != best.model_id:
                proposals.append({
                    "provider": provider_name,
                    "current": current_model,
                    "candidate": best.model_id,
                    "priority_delta": best.priority - current.get(provider_name, {}).get("priority", 0),
                })
            elif not current_model:
                proposals.append({
                    "provider": provider_name,
                    "current": "(none)",
                    "candidate": best.model_id,
                    "priority_delta": best.priority,
                })

    print()

    if not proposals:
        print("  No upgrades available — all providers at latest stable.")
        return discovered, proposals

    print("UPGRADE PROPOSALS")
    print("-" * 70)
    for p in proposals:
        print(f"  {p['provider']}: {p['current']} -> {p['candidate']} (priority +{p['priority_delta']})")

    # Shadow validation
    print()
    print("SHADOW VALIDATION")
    print("-" * 70)
    for p in proposals:
        candidate_model = select_best_model(discovered, p["provider"], "reasoning")
        if candidate_model:
            report = await shadow_validate_candidate(candidate_model)
            p["shadow_result"] = report
            icon = "PASS" if report.get("status") == "pass" else "FAIL"
            print(f"  {p['provider']}: {icon} — {report.get('note', '')}")

    # Generate proposal document
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    proposal_path = _REPORTS_DIR / f"MODEL_UPGRADE_PROPOSAL_{ts}.md"
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Model Upgrade Proposal",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Proposed Changes",
        "",
        "| Provider | Current | Candidate | Shadow |",
        "|---|---|---|---|",
    ]
    for p in proposals:
        shadow = p.get("shadow_result", {}).get("status", "N/A")
        lines.append(f"| {p['provider']} | {p['current']} | {p['candidate']} | {shadow} |")

    lines += [
        "",
        "## Approval",
        "",
        "To apply these upgrades, run:",
        "",
        "```bash",
        "MODEL_UPGRADE_APPROVED=true python scripts/weekly_model_upgrade.py --apply",
        "```",
        "",
        "This will update `benchmark_reports/current_models.json` with the new selections.",
        "It will **not** deploy or restart any services automatically.",
    ]
    proposal_path.write_text("\n".join(lines))
    print(f"\n  Proposal saved: {proposal_path}")

    return discovered, proposals


async def apply_upgrades(discovered: dict, proposals: list):
    approved = os.getenv("MODEL_UPGRADE_APPROVED", "").strip().lower() in ("true", "1", "yes")
    if not approved:
        print("\n  MODEL_UPGRADE_APPROVED not set — upgrades NOT applied.")
        print("  Set MODEL_UPGRADE_APPROVED=true to activate.")
        return

    current = _load_current_models()
    for p in proposals:
        shadow = p.get("shadow_result", {})
        if shadow.get("status") != "pass":
            print(f"  SKIP {p['provider']}: shadow validation did not pass")
            continue

        best = select_best_model(discovered, p["provider"], "reasoning")
        if best:
            current[p["provider"]] = {
                "model_id": best.model_id,
                "display_name": best.display_name,
                "priority": best.priority,
                "activated_at": datetime.now().isoformat(),
                "previous": p["current"],
            }
            print(f"  ACTIVATED {p['provider']}: {p['current']} -> {best.model_id}")

    _save_current_models(current)
    print(f"\n  Updated: benchmark_reports/current_models.json")


async def main():
    parser = argparse.ArgumentParser(description="Weekly Model Upgrade Workflow")
    parser.add_argument("--apply", action="store_true", help="Apply approved upgrades")
    args = parser.parse_args()

    discovered, proposals = await run_discovery()

    if args.apply and proposals:
        await apply_upgrades(discovered, proposals)

    print("\n" + "=" * 70)
    print("DONE — review proposals before approving.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
