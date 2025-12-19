#!/usr/bin/env python3
"""Weekly Improvement CLI Script.

Run the full weekly improvement cycle from the command line.

Usage:
    # Full weekly run
    python scripts/weekly_improve.py
    
    # Dry run (no changes applied)
    python scripts/weekly_improve.py --dry-run
    
    # Skip benchmarks for faster execution
    python scripts/weekly_improve.py --no-benchmarks
    
    # Generate report only from existing data
    python scripts/weekly_improve.py --report-only
    
    # Verbose output
    python scripts/weekly_improve.py -v
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add the llmhive package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "llmhive" / "src"))


def main():
    parser = argparse.ArgumentParser(
        description="LLMHive Weekly Improvement System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                    # Run full weekly cycle
    %(prog)s --dry-run          # Simulate without changes
    %(prog)s --no-benchmarks    # Skip benchmark runs (faster)
    %(prog)s -v                 # Verbose output
        """,
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - no changes applied to database or code",
    )
    
    parser.add_argument(
        "--no-benchmarks",
        action="store_true",
        help="Skip benchmark runs for faster execution",
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from existing data only",
    )
    
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Run OpenRouter sync only (no research/benchmarks)",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG level) logging",
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for reports",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    
    async def run():
        try:
            from llmhive.app.weekly_improvement import WeeklyImprovementOrchestrator
            
            logger.info("=" * 60)
            logger.info("LLMHIVE WEEKLY IMPROVEMENT SYSTEM")
            logger.info("=" * 60)
            
            if args.dry_run:
                logger.info("Mode: DRY RUN (no changes will be applied)")
            else:
                logger.info("Mode: LIVE (changes will be applied)")
            
            if args.sync_only:
                # Just run OpenRouter sync
                logger.info("Running OpenRouter sync only...")
                from llmhive.app.openrouter.scheduler import cli_sync
                cli_sync(dry_run=args.dry_run)
                return
            
            # Create orchestrator
            orchestrator = WeeklyImprovementOrchestrator(
                dry_run=args.dry_run,
                apply_safe_changes=not args.dry_run,
                run_benchmarks=not args.no_benchmarks,
            )
            
            # Run the full cycle
            report = await orchestrator.run_full_cycle()
            
            # Print summary
            print("\n" + "=" * 60)
            print("WEEKLY IMPROVEMENT COMPLETE")
            print("=" * 60)
            print(f"Safe to deploy: {'✅ YES' if report.safe_to_deploy else '❌ NO'}")
            print(f"Models added: {len(report.models_added)}")
            print(f"Models removed: {len(report.models_removed)}")
            print(f"Category changes: {len(report.category_changes)}")
            print(f"Research findings: {len(report.research_findings)}")
            print(f"Upgrades applied: {len(report.upgrades_applied)}")
            print(f"Upgrades gated: {len(report.upgrades_gated)}")
            print(f"Duration: {report.total_duration_seconds:.1f}s")
            
            if report.safety_notes:
                print("\nSafety Notes:")
                for note in report.safety_notes:
                    print(f"  ⚠️ {note}")
            
            if report.regression_alerts:
                print("\nRegression Alerts:")
                for alert in report.regression_alerts:
                    print(f"  📉 {alert.get('category', 'unknown')}: {alert.get('delta', 0):+.3f}")
            
            # Return exit code based on safety status
            if not report.safe_to_deploy:
                logger.warning("Cycle completed with SAFE=false")
                return 1
            
            logger.info("Cycle completed successfully with SAFE=true")
            return 0
            
        except ImportError as e:
            logger.error(f"Failed to import weekly improvement module: {e}")
            logger.error("Make sure llmhive package is installed: pip install -e llmhive/")
            return 1
        except Exception as e:
            logger.error(f"Weekly improvement cycle failed: {e}", exc_info=True)
            return 1
    
    # Run async main
    exit_code = asyncio.run(run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

