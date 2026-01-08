#!/usr/bin/env python3
"""
Weekly Optimization Script for LLMHive

This script runs the auto-improvement cycle to:
1. Gather user feedback and performance telemetry
2. Identify common failures and patterns
3. Plan and prioritize improvements
4. Apply safe configuration changes (if enabled)
5. Generate improvement reports

Can be run via:
- Vercel Cron: /api/cron/weekly-optimize
- Cloud Scheduler: python -m llmhive.scripts.weekly_optimize
- Manual: python weekly_optimize.py

Environment variables:
- AUTO_IMPROVE_APPLY: Set to "true" to automatically apply safe changes
- WEEKLY_LOOKBACK_DAYS: Number of days to look back (default: 7)
- SEND_REPORT_EMAIL: Set to "true" to email report (requires SMTP config)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("weekly_optimize")

# Add the app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from llmhive.app.auto_improve import (
        gather_improvement_data,
        plan_improvements,
        run_auto_improve_cycle,
        ImprovementItem,
        ImprovementData,
    )
    AUTO_IMPROVE_AVAILABLE = True
except ImportError as e:
    AUTO_IMPROVE_AVAILABLE = False
    logger.warning("Auto-improve module not available: %s", e)

try:
    from llmhive.app.performance_tracker import performance_tracker
    PERFORMANCE_TRACKER_AVAILABLE = True
except ImportError:
    PERFORMANCE_TRACKER_AVAILABLE = False
    performance_tracker = None

try:
    from llmhive.app.rlhf.pinecone_feedback import get_pinecone_feedback_store
    RLHF_AVAILABLE = True
except ImportError:
    RLHF_AVAILABLE = False
    get_pinecone_feedback_store = None


def format_report(
    data: "ImprovementData",
    plan: List["ImprovementItem"],
    stats: Dict[str, Any],
) -> str:
    """Format a human-readable improvement report."""
    lines = [
        "=" * 60,
        "🐝 LLMHive Weekly Optimization Report",
        f"📅 Generated: {datetime.now(timezone.utc).isoformat()}",
        "=" * 60,
        "",
        "## Summary",
        f"- Total feedback items analyzed: {stats.get('feedback_count', 0)}",
        f"- Performance metrics tracked: {data.metrics.get('models_tracked', 0)}",
        f"- Issues identified: {len(data.common_failures)}",
        f"- Improvement items planned: {len(plan)}",
        "",
    ]
    
    if stats.get("satisfaction_rate"):
        lines.append(f"- User satisfaction rate: {stats['satisfaction_rate']:.1%}")
    
    # Common failures
    if data.common_failures:
        lines.append("")
        lines.append("## Common Failures Identified")
        for i, failure in enumerate(data.common_failures[:10], 1):
            lines.append(f"  {i}. {failure}")
    
    # User requests
    if data.user_requests:
        lines.append("")
        lines.append("## User Feature Requests")
        for i, req in enumerate(data.user_requests[:5], 1):
            lines.append(f"  {i}. {req}")
    
    # Planned improvements
    if plan:
        lines.append("")
        lines.append("## Planned Improvements")
        by_priority = {"critical": [], "high": [], "medium": [], "low": []}
        for item in plan:
            by_priority.get(item.priority, by_priority["medium"]).append(item)
        
        for priority in ["critical", "high", "medium", "low"]:
            items = by_priority[priority]
            if items:
                lines.append(f"")
                lines.append(f"### {priority.upper()} Priority ({len(items)} items)")
                for item in items[:5]:
                    status_emoji = {
                        "planned": "📋",
                        "applied_pending_test": "🔄",
                        "done": "✅",
                        "failed": "❌",
                    }.get(item.status, "❓")
                    lines.append(f"  {status_emoji} [{item.id}] {item.description}")
    
    # Performance highlights
    if data.metrics.get("baseline"):
        lines.append("")
        lines.append("## Performance Baseline")
        baseline = data.metrics["baseline"]
        lines.append(f"  - Last updated: {baseline.get('timestamp', 'unknown')}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("End of Report")
    lines.append("=" * 60)
    
    return "\n".join(lines)


async def get_feedback_stats() -> Dict[str, Any]:
    """Get feedback statistics from RLHF store."""
    stats = {"feedback_count": 0, "satisfaction_rate": None}
    
    if RLHF_AVAILABLE and get_pinecone_feedback_store:
        try:
            store = get_pinecone_feedback_store()
            pinecone_stats = await store.get_stats()
            stats["feedback_count"] = pinecone_stats.get("total_feedback", 0)
        except Exception as e:
            logger.warning("Failed to get RLHF stats: %s", e)
    
    return stats


async def run_weekly_optimization():
    """Run the weekly optimization cycle."""
    logger.info("🚀 Starting weekly optimization cycle...")
    
    if not AUTO_IMPROVE_AVAILABLE:
        logger.error("Auto-improve module not available. Exiting.")
        return {"success": False, "error": "Auto-improve module not available"}
    
    # Configuration
    lookback_days = int(os.getenv("WEEKLY_LOOKBACK_DAYS", "7"))
    apply_changes = os.getenv("AUTO_IMPROVE_APPLY", "false").lower() in ("true", "1", "yes")
    
    logger.info(f"Configuration: lookback_days={lookback_days}, apply_changes={apply_changes}")
    
    # Step 1: Gather improvement data
    logger.info("📊 Step 1: Gathering improvement data...")
    data = gather_improvement_data(lookback_days=lookback_days)
    logger.info(f"  - Found {len(data.common_failures)} common failures")
    logger.info(f"  - Found {len(data.user_requests)} user requests")
    
    # Step 2: Get feedback stats
    logger.info("📈 Step 2: Getting feedback statistics...")
    stats = await get_feedback_stats()
    logger.info(f"  - Total feedback: {stats.get('feedback_count', 0)}")
    
    # Step 3: Plan improvements
    logger.info("📋 Step 3: Planning improvements...")
    plan = plan_improvements(data)
    
    planned_count = sum(1 for p in plan if p.status == "planned")
    done_count = sum(1 for p in plan if p.status == "done")
    logger.info(f"  - {planned_count} planned, {done_count} done")
    
    # Step 4: Apply safe changes if enabled
    if apply_changes:
        logger.info("⚙️ Step 4: Applying safe changes...")
        plan = await run_auto_improve_cycle(
            config={},
            apply_safe_changes=True,
            run_verifier=None,  # Skip verification in cron
        )
        applied_count = sum(1 for p in plan if p.status == "applied_pending_test")
        logger.info(f"  - Applied {applied_count} changes (pending verification)")
    else:
        logger.info("⏭️ Step 4: Skipping auto-apply (AUTO_IMPROVE_APPLY not set)")
    
    # Step 5: Generate report
    logger.info("📄 Step 5: Generating report...")
    report = format_report(data, plan, stats)
    
    # Save report
    report_dir = Path(__file__).parent.parent / "reports"
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"weekly_report_{timestamp}.txt"
    report_path.write_text(report)
    logger.info(f"  - Report saved to: {report_path}")
    
    # Print report to stdout
    print("\n" + report)
    
    # Return summary
    result = {
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lookback_days": lookback_days,
        "failures_found": len(data.common_failures),
        "user_requests": len(data.user_requests),
        "improvements_planned": len(plan),
        "changes_applied": sum(1 for p in plan if p.status == "applied_pending_test"),
        "report_path": str(report_path),
    }
    
    logger.info("✅ Weekly optimization cycle complete!")
    logger.info(f"   Summary: {json.dumps(result, indent=2)}")
    
    return result


def main():
    """Entry point for CLI execution."""
    asyncio.run(run_weekly_optimization())


if __name__ == "__main__":
    main()

