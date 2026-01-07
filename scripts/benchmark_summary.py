#!/usr/bin/env python3
"""Benchmark summary and alerting script.

This script:
1. Parses the latest benchmark results
2. Identifies regressions and new failures
3. Generates a summary report
4. Optionally sends alerts (Slack, email, etc.)

Usage:
    python scripts/benchmark_summary.py [--compare-to PREVIOUS_REPORT] [--alert]
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def find_latest_report(artifacts_dir: str = "artifacts/benchmarks") -> Optional[Path]:
    """Find the most recent benchmark report."""
    artifacts_path = Path(artifacts_dir)
    if not artifacts_path.exists():
        return None
    
    # Find all report.json files
    reports = list(artifacts_path.glob("*/report.json"))
    if not reports:
        return None
    
    # Sort by modification time (most recent first)
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0]


def load_report(report_path: Path) -> Dict[str, Any]:
    """Load a benchmark report from JSON."""
    with open(report_path, 'r') as f:
        return json.load(f)


def compare_reports(
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare current and previous reports to identify changes."""
    comparison = {
        "new_failures": [],
        "fixed": [],
        "regressions": [],
        "improvements": [],
        "unchanged": [],
    }
    
    if not previous:
        return comparison
    
    # Build lookup of previous scores by prompt_id + system
    prev_scores = {}
    for score in previous.get("scores", []):
        key = f"{score['prompt_id']}_{score['system_name']}"
        prev_scores[key] = score
    
    # Compare each current score
    for score in current.get("scores", []):
        key = f"{score['prompt_id']}_{score['system_name']}"
        curr_passed = score.get("objective_score", {}).get("passed", False) if score.get("objective_score") else False
        curr_composite = score.get("composite_score", 0)
        
        if key not in prev_scores:
            continue  # New prompt, skip comparison
        
        prev = prev_scores[key]
        prev_passed = prev.get("objective_score", {}).get("passed", False) if prev.get("objective_score") else False
        prev_composite = prev.get("composite_score", 0)
        
        if not prev_passed and curr_passed:
            comparison["fixed"].append({
                "prompt_id": score["prompt_id"],
                "system": score["system_name"],
                "prev_score": prev_composite,
                "curr_score": curr_composite,
            })
        elif prev_passed and not curr_passed:
            comparison["new_failures"].append({
                "prompt_id": score["prompt_id"],
                "system": score["system_name"],
                "prev_score": prev_composite,
                "curr_score": curr_composite,
                "is_critical": score.get("is_critical", False),
            })
        elif curr_composite < prev_composite - 0.1:  # >10% regression
            comparison["regressions"].append({
                "prompt_id": score["prompt_id"],
                "system": score["system_name"],
                "prev_score": prev_composite,
                "curr_score": curr_composite,
                "delta": curr_composite - prev_composite,
            })
        elif curr_composite > prev_composite + 0.1:  # >10% improvement
            comparison["improvements"].append({
                "prompt_id": score["prompt_id"],
                "system": score["system_name"],
                "prev_score": prev_composite,
                "curr_score": curr_composite,
                "delta": curr_composite - prev_composite,
            })
    
    return comparison


def generate_summary(report: Dict[str, Any], comparison: Optional[Dict[str, Any]] = None) -> str:
    """Generate a human-readable summary."""
    lines = [
        "=" * 60,
        "BENCHMARK SUMMARY",
        "=" * 60,
        "",
        f"Suite: {report.get('suite_name', 'Unknown')} v{report.get('suite_version', '?')}",
        f"Run: {report.get('timestamp', 'Unknown')}",
        f"Git: {report.get('git_commit', 'N/A')}",
        f"Status: {'✅ PASSED' if report.get('passed', False) else '❌ FAILED'}",
        "",
    ]
    
    # System scores
    lines.append("SYSTEM SCORES:")
    lines.append("-" * 40)
    for system, stats in report.get("aggregate", {}).get("systems", {}).items():
        mean = stats.get("composite_mean", 0)
        passed = stats.get("passed_count", 0)
        failed = stats.get("failed_count", 0)
        critical = stats.get("critical_failures", 0)
        
        status = "🔴" if critical > 0 else "🟡" if failed > 0 else "🟢"
        lines.append(f"  {status} {system}: {mean:.3f} ({passed}✓ {failed}✗ {critical}⚠)")
    lines.append("")
    
    # Critical failures
    critical_failures = report.get("critical_failures", [])
    if critical_failures:
        lines.append("⚠️  CRITICAL FAILURES:")
        lines.append("-" * 40)
        for fail_id in critical_failures:
            lines.append(f"  • {fail_id}")
        lines.append("")
    
    # Comparison with previous run
    if comparison:
        if comparison["new_failures"]:
            lines.append("🆕 NEW FAILURES (regression!):")
            lines.append("-" * 40)
            for item in comparison["new_failures"]:
                crit = " [CRITICAL]" if item.get("is_critical") else ""
                lines.append(f"  • {item['prompt_id']} ({item['system']}): {item['prev_score']:.3f} → {item['curr_score']:.3f}{crit}")
            lines.append("")
        
        if comparison["fixed"]:
            lines.append("🎉 FIXED (improvements!):")
            lines.append("-" * 40)
            for item in comparison["fixed"]:
                lines.append(f"  • {item['prompt_id']} ({item['system']}): {item['prev_score']:.3f} → {item['curr_score']:.3f}")
            lines.append("")
        
        if comparison["regressions"]:
            lines.append("📉 SCORE REGRESSIONS (>10% drop):")
            lines.append("-" * 40)
            for item in comparison["regressions"][:5]:  # Top 5
                lines.append(f"  • {item['prompt_id']} ({item['system']}): {item['delta']:+.3f}")
            lines.append("")
        
        if comparison["improvements"]:
            lines.append("📈 SCORE IMPROVEMENTS (>10% gain):")
            lines.append("-" * 40)
            for item in comparison["improvements"][:5]:  # Top 5
                lines.append(f"  • {item['prompt_id']} ({item['system']}): {item['delta']:+.3f}")
            lines.append("")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def send_slack_alert(summary: str, webhook_url: str) -> bool:
    """Send summary to Slack via webhook."""
    try:
        import httpx
        response = httpx.post(
            webhook_url,
            json={"text": f"```\n{summary}\n```"},
            timeout=10,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Slack alert: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Analyze and summarize benchmark results")
    parser.add_argument("--report", help="Path to specific report.json (default: latest)")
    parser.add_argument("--compare-to", help="Path to previous report.json for comparison")
    parser.add_argument("--alert", action="store_true", help="Send alerts if critical failures found")
    parser.add_argument("--slack-webhook", help="Slack webhook URL for alerts")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of text")
    args = parser.parse_args()
    
    # Find report
    if args.report:
        report_path = Path(args.report)
    else:
        report_path = find_latest_report()
    
    if not report_path or not report_path.exists():
        print("❌ No benchmark report found. Run a benchmark first:")
        print("   python scripts/run_benchmarks.py --systems llmhive --mode local")
        sys.exit(1)
    
    print(f"Loading report: {report_path}")
    report = load_report(report_path)
    
    # Load comparison report if provided
    comparison = None
    if args.compare_to:
        prev_path = Path(args.compare_to)
        if prev_path.exists():
            previous = load_report(prev_path)
            comparison = compare_reports(report, previous)
    
    # Generate output
    if args.json:
        output = {
            "report": report,
            "comparison": comparison,
        }
        print(json.dumps(output, indent=2))
    else:
        summary = generate_summary(report, comparison)
        print(summary)
    
    # Send alerts if requested
    if args.alert:
        critical_failures = report.get("critical_failures", [])
        new_failures = comparison.get("new_failures", []) if comparison else []
        
        should_alert = len(critical_failures) > 0 or len(new_failures) > 0
        
        if should_alert:
            print("\n⚠️  ALERT: Critical issues detected!")
            
            if args.slack_webhook:
                summary = generate_summary(report, comparison)
                if send_slack_alert(summary, args.slack_webhook):
                    print("✓ Slack alert sent")
                else:
                    print("✗ Failed to send Slack alert")
            
            # Exit with error code for CI
            sys.exit(1)
    
    # Exit with appropriate code
    if not report.get("passed", False):
        sys.exit(1)


if __name__ == "__main__":
    main()

