#!/usr/bin/env python3
"""
LLMHive ModelDB Coverage Report Generator

Generates comprehensive coverage reports analyzing data population across
different sources (OpenRouter, LMSYS Arena, HF Leaderboard, Evals, Telemetry).

Outputs:
- JSON report: Machine-readable coverage statistics
- Markdown report: Human-readable summary with unmatched lists

Usage:
    python modeldb_coverage_report.py --excel path/to/modeldb.xlsx
    python modeldb_coverage_report.py --excel path/to/modeldb.xlsx --output-dir custom/dir
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

# =============================================================================
# Constants
# =============================================================================

SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_EXCEL = SCRIPT_DIR / "LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "archives"

# Source group definitions - column prefix patterns
SOURCE_GROUPS = {
    "openrouter_rankings": {
        "description": "OpenRouter API rankings and scores",
        "prefixes": ["openrouter_rank_", "openrouter_score_", "openrouter_rankings_"],
        "key_columns": ["openrouter_rank_context_length", "openrouter_rank_price_input"],
    },
    "lmsys_arena": {
        "description": "LMSYS Chatbot Arena Elo ratings and rankings",
        "prefixes": ["arena_"],
        "key_columns": ["arena_elo_overall", "arena_rank_overall", "arena_match_status"],
    },
    "hf_leaderboard": {
        "description": "HuggingFace Open LLM Leaderboard benchmarks",
        "prefixes": ["hf_ollb_", "hf_match_"],
        "key_columns": ["hf_ollb_mmlu", "hf_ollb_avg", "hf_ollb_match_status"],
    },
    "eval_harness": {
        "description": "Eval harness scores from prompt-based testing",
        "prefixes": ["eval_"],
        "key_columns": ["eval_programming_languages_score", "eval_languages_score", "eval_tool_use_score"],
    },
    "telemetry": {
        "description": "Live telemetry measurements (latency, TPS, errors)",
        "prefixes": ["telemetry_"],
        "key_columns": ["telemetry_latency_p50_ms", "telemetry_tps_p50", "telemetry_error_rate"],
    },
    "provider_docs": {
        "description": "Data enriched from provider documentation",
        "prefixes": ["provider_docs_"],
        "key_columns": ["modalities", "supports_function_calling", "supports_vision"],
    },
    "derived_rankings": {
        "description": "Rankings computed from existing data",
        "prefixes": ["rank_", "derived_rank_"],
        "key_columns": ["rank_context_length_desc", "rank_cost_input_asc"],
    },
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("coverage_report")


# =============================================================================
# Coverage Analysis
# =============================================================================


def find_columns_for_group(
    all_columns: List[str],
    prefixes: List[str],
) -> List[str]:
    """Find all columns matching any of the given prefixes."""
    matches = []
    for col in all_columns:
        col_lower = col.lower()
        for prefix in prefixes:
            if col_lower.startswith(prefix.lower()):
                matches.append(col)
                break
    return sorted(matches)


def compute_group_coverage(
    df: pd.DataFrame,
    group_columns: List[str],
) -> Dict[str, Any]:
    """Compute coverage statistics for a column group."""
    if not group_columns:
        return {
            "total_models": len(df),
            "models_with_any_data": 0,
            "coverage_percent": 0.0,
            "columns_found": 0,
            "columns_with_data": 0,
            "column_coverage": {},
        }
    
    total_models = len(df)
    
    # Check which models have at least one non-null value in the group
    group_data = df[group_columns]
    models_with_any = (group_data.notna().any(axis=1)).sum()
    
    # Compute per-column coverage
    column_coverage = {}
    for col in group_columns:
        non_null_count = df[col].notna().sum()
        column_coverage[col] = {
            "non_null_count": int(non_null_count),
            "coverage_percent": round(100.0 * non_null_count / total_models, 1) if total_models > 0 else 0.0,
        }
    
    # Count columns with any data
    columns_with_data = sum(1 for c in column_coverage.values() if c["non_null_count"] > 0)
    
    return {
        "total_models": total_models,
        "models_with_any_data": int(models_with_any),
        "coverage_percent": round(100.0 * models_with_any / total_models, 1) if total_models > 0 else 0.0,
        "columns_found": len(group_columns),
        "columns_with_data": columns_with_data,
        "column_coverage": column_coverage,
    }


def find_unmatched_models(
    df: pd.DataFrame,
    group_name: str,
    source_config: Dict[str, Any],
    top_n: int = 20,
) -> List[Dict[str, Any]]:
    """
    Find top N models that are unmatched for a given source.
    
    Returns list of dicts with slug and reason.
    """
    if "openrouter_slug" not in df.columns:
        return []
    
    prefixes = source_config.get("prefixes", [])
    group_columns = find_columns_for_group(list(df.columns), prefixes)
    
    if not group_columns:
        # No columns exist for this group at all
        return []
    
    unmatched = []
    
    # Check for match_status column
    match_status_col = None
    for col in group_columns:
        if "match_status" in col.lower():
            match_status_col = col
            break
    
    for idx, row in df.iterrows():
        slug = row.get("openrouter_slug")
        if pd.isna(slug) or not slug:
            continue
        
        slug = str(slug).strip()
        is_unmatched = False
        reason = ""
        
        if match_status_col and match_status_col in df.columns:
            status = row.get(match_status_col)
            if status == "unmatched" or pd.isna(status):
                is_unmatched = True
                reason = f"{match_status_col}=unmatched" if status == "unmatched" else "match_status is null"
        else:
            # Check if all group columns are null
            all_null = True
            for col in group_columns:
                if pd.notna(row.get(col)):
                    all_null = False
                    break
            if all_null:
                is_unmatched = True
                reason = "all columns null"
        
        if is_unmatched:
            unmatched.append({
                "slug": slug,
                "reason": reason,
            })
    
    # Sort by slug and return top N
    unmatched.sort(key=lambda x: x["slug"])
    return unmatched[:top_n]


def generate_coverage_report(
    df: pd.DataFrame,
    excel_path: str,
) -> Dict[str, Any]:
    """Generate complete coverage report."""
    now = datetime.now(timezone.utc)
    all_columns = list(df.columns)
    
    report = {
        "generated_at": now.isoformat(),
        "excel_path": excel_path,
        "total_models": len(df),
        "total_columns": len(all_columns),
        "source_groups": {},
        "unmatched_lists": {},
        "summary": {},
    }
    
    # Analyze each source group
    for group_name, config in SOURCE_GROUPS.items():
        group_columns = find_columns_for_group(all_columns, config["prefixes"])
        coverage = compute_group_coverage(df, group_columns)
        
        # Add representative columns (top 10 by coverage)
        sorted_cols = sorted(
            coverage["column_coverage"].items(),
            key=lambda x: x[1]["coverage_percent"],
            reverse=True,
        )
        coverage["representative_columns"] = [c[0] for c in sorted_cols[:10]]
        
        report["source_groups"][group_name] = {
            "description": config["description"],
            "key_columns": config["key_columns"],
            **coverage,
        }
        
        # Find unmatched models
        unmatched = find_unmatched_models(df, group_name, config, top_n=20)
        report["unmatched_lists"][group_name] = unmatched
    
    # Generate summary
    total_groups = len(SOURCE_GROUPS)
    groups_with_data = sum(
        1 for g in report["source_groups"].values()
        if g["coverage_percent"] > 0
    )
    
    report["summary"] = {
        "total_source_groups": total_groups,
        "groups_with_any_data": groups_with_data,
        "groups_fully_empty": total_groups - groups_with_data,
        "best_coverage_group": max(
            report["source_groups"].items(),
            key=lambda x: x[1]["coverage_percent"],
        )[0] if report["source_groups"] else None,
        "worst_coverage_group": min(
            report["source_groups"].items(),
            key=lambda x: x[1]["coverage_percent"],
        )[0] if report["source_groups"] else None,
    }
    
    return report


def format_report_markdown(report: Dict[str, Any]) -> str:
    """Format coverage report as Markdown."""
    lines = []
    
    lines.append("# ModelDB Coverage Report")
    lines.append("")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append(f"**Excel Path:** `{report['excel_path']}`")
    lines.append(f"**Total Models:** {report['total_models']}")
    lines.append(f"**Total Columns:** {report['total_columns']}")
    lines.append("")
    
    # Summary
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- **Source Groups Analyzed:** {summary['total_source_groups']}")
    lines.append(f"- **Groups with Data:** {summary['groups_with_any_data']}")
    lines.append(f"- **Groups Fully Empty:** {summary['groups_fully_empty']}")
    if summary.get("best_coverage_group"):
        best = summary["best_coverage_group"]
        best_pct = report["source_groups"][best]["coverage_percent"]
        lines.append(f"- **Best Coverage:** {best} ({best_pct}%)")
    if summary.get("worst_coverage_group"):
        worst = summary["worst_coverage_group"]
        worst_pct = report["source_groups"][worst]["coverage_percent"]
        lines.append(f"- **Worst Coverage:** {worst} ({worst_pct}%)")
    lines.append("")
    
    # Coverage by Source Group
    lines.append("## Coverage by Source Group")
    lines.append("")
    
    # Table header
    lines.append("| Source Group | Description | Models with Data | Coverage % | Columns |")
    lines.append("|--------------|-------------|------------------|------------|---------|")
    
    for group_name, data in sorted(report["source_groups"].items(), key=lambda x: -x[1]["coverage_percent"]):
        desc = data["description"][:40] + "..." if len(data["description"]) > 40 else data["description"]
        lines.append(
            f"| {group_name} | {desc} | {data['models_with_any_data']} | "
            f"{data['coverage_percent']}% | {data['columns_found']} |"
        )
    lines.append("")
    
    # Detailed breakdown per group
    lines.append("## Detailed Coverage")
    lines.append("")
    
    for group_name, data in report["source_groups"].items():
        lines.append(f"### {group_name}")
        lines.append("")
        lines.append(f"_{data['description']}_")
        lines.append("")
        lines.append(f"- **Coverage:** {data['coverage_percent']}% ({data['models_with_any_data']}/{data['total_models']} models)")
        lines.append(f"- **Columns Found:** {data['columns_found']} ({data['columns_with_data']} with data)")
        lines.append("")
        
        if data.get("representative_columns"):
            lines.append("**Top Columns by Coverage:**")
            lines.append("")
            for col in data["representative_columns"][:5]:
                col_data = data["column_coverage"].get(col, {})
                pct = col_data.get("coverage_percent", 0)
                cnt = col_data.get("non_null_count", 0)
                lines.append(f"- `{col}`: {pct}% ({cnt} values)")
            lines.append("")
    
    # Unmatched Lists
    lines.append("## Unmatched Models (Top 20 per Source)")
    lines.append("")
    lines.append("These models could not be matched to external data sources.")
    lines.append("")
    
    for group_name, unmatched in report["unmatched_lists"].items():
        lines.append(f"### {group_name}")
        lines.append("")
        
        if not unmatched:
            lines.append("_No unmatched models detected (or no match_status column)._")
        else:
            lines.append(f"**{len(unmatched)} models unmatched:**")
            lines.append("")
            for item in unmatched[:20]:
                lines.append(f"- `{item['slug']}`: {item['reason']}")
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# Helper Functions
# =============================================================================


def find_latest_runlog(archives_dir: Path) -> Optional[Path]:
    """Find the most recent refresh_runlog_*.json file."""
    pattern = "refresh_runlog_*.json"
    logs = sorted(archives_dir.glob(pattern), reverse=True)
    return logs[0] if logs else None


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate ModelDB coverage report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--excel",
        type=str,
        default=str(DEFAULT_EXCEL),
        help=f"Path to Excel file (default: {DEFAULT_EXCEL.name})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory for reports (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate report but don't write files",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print coverage summary to stdout",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    excel_path = Path(args.excel)
    output_dir = Path(args.output_dir)
    
    # Validate input
    if not excel_path.exists():
        logger.error("Excel file not found: %s", excel_path)
        sys.exit(1)
    
    # Load Excel
    logger.info("Loading Excel: %s", excel_path)
    try:
        df = pd.read_excel(excel_path)
        logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
    except Exception as e:
        logger.error("Failed to read Excel: %s", e)
        sys.exit(1)
    
    # Generate report
    logger.info("Generating coverage report...")
    report = generate_coverage_report(df, str(excel_path))
    
    # Generate markdown
    markdown = format_report_markdown(report)
    
    # Print summary if requested
    if args.print_summary or args.dry_run:
        print("\n" + "=" * 70)
        print("COVERAGE REPORT SUMMARY")
        print("=" * 70)
        print(f"Total Models: {report['total_models']}")
        print(f"Total Columns: {report['total_columns']}")
        print("")
        print("Source Group Coverage:")
        for group_name, data in sorted(
            report["source_groups"].items(),
            key=lambda x: -x[1]["coverage_percent"],
        ):
            status = "✅" if data["coverage_percent"] > 0 else "❌"
            print(f"  {status} {group_name}: {data['coverage_percent']}% ({data['models_with_any_data']}/{data['total_models']})")
        print("")
        
        # Show groups needing attention
        empty_groups = [
            g for g, d in report["source_groups"].items()
            if d["coverage_percent"] == 0
        ]
        if empty_groups:
            print("⚠️  Groups with 0% coverage:")
            for g in empty_groups:
                print(f"   - {g}")
        print("=" * 70)
    
    # Write output files
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        
        # JSON report
        json_path = output_dir / f"coverage_report_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("Wrote JSON report: %s", json_path)
        
        # Markdown report
        md_path = output_dir / f"coverage_report_{timestamp}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        logger.info("Wrote Markdown report: %s", md_path)
        
        print(f"\n✅ Coverage reports written to:")
        print(f"   - {json_path}")
        print(f"   - {md_path}")
    else:
        print("\n[DRY RUN] Would write reports to:")
        print(f"   - {output_dir}/coverage_report_<timestamp>.json")
        print(f"   - {output_dir}/coverage_report_<timestamp>.md")
    
    # Return report for programmatic use
    return report


if __name__ == "__main__":
    main()

