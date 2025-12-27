#!/usr/bin/env python3
"""
LLMHive ModelDB Coverage Report Generator

Generates comprehensive coverage reports analyzing data population across
different sources (OpenRouter, LMSYS Arena, HF Leaderboard, Evals, Telemetry).

Key distinction:
- ATTEMPT COVERAGE: % of rows where match was attempted (metadata columns populated)
- METRIC COVERAGE: % of rows where actual benchmark/metric data was retrieved

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

# Source group definitions with separate metadata vs metric columns
SOURCE_GROUPS = {
    "openrouter_rankings": {
        "description": "OpenRouter API rankings and scores",
        "prefixes": ["openrouter_rank_", "openrouter_score_", "openrouter_rankings_"],
        # Metadata columns (indicate attempt was made)
        "metadata_columns": [
            "openrouter_rankings_source_name",
            "openrouter_rankings_retrieved_at",
        ],
        # Metric columns (actual benchmark data)
        "metric_columns": [
            "openrouter_rank_context_length",
            "openrouter_rank_price_input",
            "openrouter_rank_price_output",
        ],
    },
    "lmsys_arena": {
        "description": "LMSYS Chatbot Arena Elo ratings and rankings",
        "prefixes": ["arena_"],
        # Metadata columns (match status, provenance)
        "metadata_columns": [
            "arena_match_status",
            "arena_match_score",
            "arena_asof_date",
            "arena_source_name",
            "arena_retrieved_at",
        ],
        # Metric columns (actual Arena data)
        "metric_columns": [
            "arena_rank",
            "arena_score",
            "arena_votes",
            "arena_95ci",
            "arena_organization",
            "arena_license",
        ],
    },
    "hf_leaderboard": {
        "description": "HuggingFace Open LLM Leaderboard benchmarks",
        "prefixes": ["hf_ollb_", "hf_match_"],
        # Metadata columns
        "metadata_columns": [
            "hf_ollb_match_status",
            "hf_ollb_match_method",
            "hf_ollb_match_score",
            "hf_ollb_source_name",
            "hf_ollb_source_dataset",
            "hf_ollb_retrieved_at",
            "hf_ollb_repo_id",
            # Eligibility columns
            "hf_ollb_eligible",
            "hf_ollb_ineligible_reason",
            "hf_ollb_candidate_hf_id",
            # HF ID inference columns
            "hf_ollb_inferred_hf_id",
            "hf_ollb_inferred_hf_id_source",
            "hf_ollb_base_model_hf_id",
            "hf_ollb_candidate_set",
            # Listed/Not-listed columns
            "hf_ollb_listed_in_dataset",
            "hf_ollb_listed_but_missing_metrics",
            "hf_ollb_not_listed_on_leaderboard",
            "hf_ollb_not_listed_reason",
            # Debug/audit columns
            "hf_ollb_attempted_methods",
            "hf_ollb_match_outcome",
            "hf_ollb_conflict_candidates",
        ],
        # Metric columns (v2 leaderboard benchmarks ONLY - hf_ollb_mmlu is legacy/deprecated)
        "metric_columns": [
            # V2 benchmarks (current)
            "hf_ollb_mmlu_pro",
            "hf_ollb_ifeval",
            "hf_ollb_bbh",
            "hf_ollb_math",
            "hf_ollb_gpqa",
            "hf_ollb_musr",
            "hf_ollb_avg",
            # Note: hf_ollb_mmlu is legacy v1 and NOT included in v2 metric coverage
        ],
        # Eligibility column for computing eligible coverage
        "eligibility_column": "hf_ollb_eligible",
        # Not-listed column for additional breakdown
        "not_listed_column": "hf_ollb_not_listed_on_leaderboard",
    },
    "eval_harness": {
        "description": "Eval harness scores from prompt-based testing",
        "prefixes": ["eval_"],
        # Metadata columns
        "metadata_columns": [
            "eval_source_name",
            "eval_retrieved_at",
        ],
        # Metric columns
        "metric_columns": [
            "eval_programming_languages_score",
            "eval_languages_score",
            "eval_tool_use_score",
        ],
    },
    "telemetry": {
        "description": "Live telemetry measurements (latency, TPS, errors)",
        "prefixes": ["telemetry_"],
        # Metadata columns
        "metadata_columns": [
            "telemetry_source_name",
            "telemetry_retrieved_at",
        ],
        # Metric columns
        "metric_columns": [
            "telemetry_latency_p50_ms",
            "telemetry_latency_p95_ms",
            "telemetry_tps_p50",
            "telemetry_error_rate",
        ],
    },
    "provider_docs": {
        "description": "Data enriched from provider documentation",
        "prefixes": ["provider_docs_"],
        # Metadata columns
        "metadata_columns": [
            "provider_docs_source_url",
            "provider_docs_verified_at",
        ],
        # Metric columns (actual capability data)
        "metric_columns": [
            "modalities",
            "supports_function_calling",
            "supports_vision",
        ],
    },
    "derived_rankings": {
        "description": "Rankings computed from existing data",
        "prefixes": ["rank_", "derived_rank_"],
        # Metadata columns
        "metadata_columns": [
            "derived_rank_source_name",
            "derived_rank_retrieved_at",
        ],
        # Metric columns
        "metric_columns": [
            "rank_context_length_desc",
            "rank_cost_input_asc",
            "rank_cost_output_asc",
        ],
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


def compute_dual_coverage(
    df: pd.DataFrame,
    all_group_columns: List[str],
    metadata_columns: List[str],
    metric_columns: List[str],
    eligibility_column: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute attempt, metric, and (optionally) eligible coverage for a column group.
    
    - attempt_coverage: % of rows where ANY metadata column is non-null
    - metric_coverage: % of rows where ANY metric column is non-null
    - eligible_count: number of rows where eligibility_column is True (if provided)
    - eligible_metric_coverage: % of eligible rows with metric data (the key KPI)
    """
    total_models = len(df)
    
    if not all_group_columns:
        return {
            "total_models": total_models,
            "attempt_coverage_percent": 0.0,
            "attempt_models": 0,
            "metric_coverage_percent": 0.0,
            "metric_models": 0,
            "eligible_count": 0,
            "eligible_metric_models": 0,
            "eligible_metric_coverage_percent": 0.0,
            "ineligible_count": 0,
            "columns_found": 0,
            "metadata_columns_found": 0,
            "metric_columns_found": 0,
            "column_coverage": {},
        }
    
    # Filter to columns that actually exist in the DataFrame
    existing_metadata = [c for c in metadata_columns if c in df.columns]
    existing_metrics = [c for c in metric_columns if c in df.columns]
    
    # Also include any prefix-matched columns as metrics if not in metadata
    for col in all_group_columns:
        if col not in existing_metadata and col not in existing_metrics:
            existing_metrics.append(col)
    
    # Compute attempt coverage (any metadata populated)
    if existing_metadata:
        metadata_data = df[existing_metadata]
        models_with_attempt = (metadata_data.notna().any(axis=1)).sum()
    else:
        # If no specific metadata columns, use all columns for attempt
        all_data = df[[c for c in all_group_columns if c in df.columns]]
        models_with_attempt = (all_data.notna().any(axis=1)).sum() if len(all_data.columns) > 0 else 0
    
    # Compute metric coverage (any metric populated)
    has_metrics_mask = pd.Series([False] * len(df), index=df.index)
    if existing_metrics:
        metric_data = df[existing_metrics]
        has_metrics_mask = metric_data.notna().any(axis=1)
    models_with_metrics = has_metrics_mask.sum()
    
    # Compute eligibility-based coverage if column provided
    eligible_count = 0
    eligible_metric_models = 0
    eligible_metric_coverage_percent = 0.0
    ineligible_count = 0
    
    if eligibility_column and eligibility_column in df.columns:
        # Eligibility column should be boolean-like (True/False or 1/0)
        eligible_mask = df[eligibility_column].fillna(False).astype(bool)
        eligible_count = eligible_mask.sum()
        ineligible_count = (~eligible_mask).sum()
        
        # Compute metric coverage among eligible models only
        if eligible_count > 0:
            eligible_with_metrics = (eligible_mask & has_metrics_mask).sum()
            eligible_metric_models = int(eligible_with_metrics)
            eligible_metric_coverage_percent = round(100.0 * eligible_with_metrics / eligible_count, 1)
    
    # Per-column coverage
    column_coverage = {}
    for col in all_group_columns:
        if col in df.columns:
            non_null_count = df[col].notna().sum()
            is_metadata = col in existing_metadata
            column_coverage[col] = {
                "non_null_count": int(non_null_count),
                "coverage_percent": round(100.0 * non_null_count / total_models, 1) if total_models > 0 else 0.0,
                "column_type": "metadata" if is_metadata else "metric",
            }
    
    return {
        "total_models": total_models,
        "attempt_coverage_percent": round(100.0 * models_with_attempt / total_models, 1) if total_models > 0 else 0.0,
        "attempt_models": int(models_with_attempt),
        "metric_coverage_percent": round(100.0 * models_with_metrics / total_models, 1) if total_models > 0 else 0.0,
        "metric_models": int(models_with_metrics),
        # Eligibility stats (new)
        "eligible_count": int(eligible_count),
        "eligible_metric_models": int(eligible_metric_models),
        "eligible_metric_coverage_percent": eligible_metric_coverage_percent,
        "ineligible_count": int(ineligible_count),
        "columns_found": len(all_group_columns),
        "metadata_columns_found": len(existing_metadata),
        "metric_columns_found": len(existing_metrics),
        "column_coverage": column_coverage,
    }


def find_unmatched_models(
    df: pd.DataFrame,
    group_name: str,
    source_config: Dict[str, Any],
    top_n: int = 20,
    eligible_only: bool = False,
) -> List[Dict[str, Any]]:
    """
    Find top N models that have no METRIC data for a given source.
    
    Uses metric coverage (not attempt coverage) to determine unmatched status.
    
    If eligible_only=True and an eligibility_column is configured, only returns
    unmatched models that are marked as eligible (the ones that matter).
    """
    if "openrouter_slug" not in df.columns:
        return []
    
    prefixes = source_config.get("prefixes", [])
    all_group_columns = find_columns_for_group(list(df.columns), prefixes)
    metric_columns = source_config.get("metric_columns", [])
    eligibility_column = source_config.get("eligibility_column")
    
    # Filter to existing metric columns
    existing_metrics = [c for c in metric_columns if c in df.columns]
    
    # If no specified metric columns, use all non-metadata columns
    if not existing_metrics:
        metadata_columns = source_config.get("metadata_columns", [])
        existing_metrics = [c for c in all_group_columns if c not in metadata_columns]
    
    if not existing_metrics:
        return []
    
    unmatched = []
    
    for idx, row in df.iterrows():
        slug = row.get("openrouter_slug")
        if pd.isna(slug) or not slug:
            continue
        
        slug = str(slug).strip()
        
        # Filter by eligibility if requested
        if eligible_only and eligibility_column and eligibility_column in df.columns:
            is_eligible = row.get(eligibility_column)
            if pd.isna(is_eligible) or not is_eligible:
                continue
        
        # Check if all metric columns are null
        all_metrics_null = True
        for col in existing_metrics:
            if col in df.columns and pd.notna(row.get(col)):
                all_metrics_null = False
                break
        
        if all_metrics_null:
            # Determine reason
            match_status_col = None
            for col in source_config.get("metadata_columns", []):
                if "match_status" in col.lower() and col in df.columns:
                    match_status_col = col
                    break
            
            reason = "no metric data"
            if match_status_col:
                status = row.get(match_status_col)
                if status == "unmatched":
                    reason = "match_status=unmatched"
                elif status == "conflict":
                    reason = "match_status=conflict"
                elif status == "low_confidence":
                    reason = "match_status=low_confidence"
                elif pd.isna(status):
                    reason = "match not attempted"
            
            # Add candidate HF ID if available (for debugging)
            candidate_col = "hf_ollb_candidate_hf_id"
            candidate_id = ""
            if candidate_col in df.columns:
                cand = row.get(candidate_col)
                if pd.notna(cand):
                    candidate_id = str(cand)
            
            unmatched.append({
                "slug": slug,
                "reason": reason,
                "candidate_hf_id": candidate_id,
            })
    
    # Sort by slug and return top N
    unmatched.sort(key=lambda x: x["slug"])
    return unmatched[:top_n]


def compute_hf_extended_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute HF-specific extended statistics:
    - Conflict count (all and eligible)
    - Not-listed count (eligible)
    - True gaps count (eligible - matched - conflict - not_listed)
    - Match method breakdown (matched rows only)
    - Match outcome breakdown (non-matched)
    - Unmatched split by has_hf_id and not_listed status
    """
    stats = {
        "conflict_count_all": 0,
        "conflict_count_eligible": 0,
        "not_listed_count_eligible": 0,
        "true_gaps_count": 0,
        "inferred_hf_id_count": 0,
        "match_method_breakdown": {},
        "match_outcome_breakdown": {},
        # Split unmatched lists:
        # 1. WITH hf_id AND not_listed=False (likely matching bug - highest priority)
        # 2. WITH hf_id AND not_listed=True (informational - not on leaderboard)
        # 3. WITHOUT hf_id (needs ID discovery)
        "unmatched_with_hf_id_not_listed_false": [],
        "unmatched_with_hf_id_not_listed_true": [],
        "unmatched_without_hf_id": [],
    }
    
    if "hf_ollb_match_status" not in df.columns:
        return stats
    
    # Count conflicts
    conflict_mask = df["hf_ollb_match_status"] == "conflict"
    stats["conflict_count_all"] = int(conflict_mask.sum())
    
    eligible_mask = None
    if "hf_ollb_eligible" in df.columns:
        eligible_mask = df["hf_ollb_eligible"].fillna(False).astype(bool)
        stats["conflict_count_eligible"] = int((conflict_mask & eligible_mask).sum())
    
    # Count not-listed (eligible only)
    not_listed_mask = None
    if "hf_ollb_not_listed_on_leaderboard" in df.columns and eligible_mask is not None:
        not_listed_mask = df["hf_ollb_not_listed_on_leaderboard"].fillna(False).astype(bool)
        stats["not_listed_count_eligible"] = int((not_listed_mask & eligible_mask).sum())
    
    # Count inferred HF IDs
    if "hf_ollb_inferred_hf_id" in df.columns:
        inferred_mask = df["hf_ollb_inferred_hf_id"].notna() & (df["hf_ollb_inferred_hf_id"] != "")
        stats["inferred_hf_id_count"] = int(inferred_mask.sum())
    
    # Match method breakdown (matched rows only)
    if "hf_ollb_match_method" in df.columns:
        matched_mask = df["hf_ollb_match_status"] == "matched"
        matched_methods = df.loc[matched_mask, "hf_ollb_match_method"].dropna()
        stats["match_method_breakdown"] = matched_methods.value_counts().to_dict()
    
    # Match outcome breakdown (non-matched rows)
    if "hf_ollb_match_outcome" in df.columns:
        non_matched_mask = df["hf_ollb_match_status"] != "matched"
        outcomes = df.loc[non_matched_mask, "hf_ollb_match_outcome"].dropna()
        stats["match_outcome_breakdown"] = outcomes.value_counts().to_dict()
    
    # Compute true gaps (eligible - matched - conflict - not_listed)
    if eligible_mask is not None:
        eligible_count = int(eligible_mask.sum())
        matched_mask = df["hf_ollb_match_status"] == "matched"
        eligible_matched = int((matched_mask & eligible_mask).sum())
        eligible_conflict = stats["conflict_count_eligible"]
        eligible_not_listed = stats["not_listed_count_eligible"]
        stats["true_gaps_count"] = eligible_count - eligible_matched - eligible_conflict - eligible_not_listed
    
    # Split unmatched eligible by has_hf_id and not_listed
    if eligible_mask is not None and "openrouter_slug" in df.columns:
        matched_mask = df["hf_ollb_match_status"] == "matched"
        unmatched_eligible_mask = eligible_mask & ~matched_mask
        
        has_hf_id_col = "hugging_face_id" in df.columns
        has_not_listed_col = "hf_ollb_not_listed_on_leaderboard" in df.columns
        
        for idx, row in df[unmatched_eligible_mask].iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            entry = {
                "slug": str(slug).strip(),
                "match_status": row.get("hf_ollb_match_status"),
                "match_outcome": row.get("hf_ollb_match_outcome") if "hf_ollb_match_outcome" in df.columns else None,
                "candidate_hf_id": str(row.get("hf_ollb_candidate_hf_id", "")) if pd.notna(row.get("hf_ollb_candidate_hf_id")) else "",
                "candidate_set": str(row.get("hf_ollb_candidate_set", "")) if pd.notna(row.get("hf_ollb_candidate_set")) else "",
                "conflict_candidates": str(row.get("hf_ollb_conflict_candidates", "")) if pd.notna(row.get("hf_ollb_conflict_candidates")) else "",
                "inferred_hf_id": str(row.get("hf_ollb_inferred_hf_id", "")) if pd.notna(row.get("hf_ollb_inferred_hf_id")) else "",
                "not_listed": bool(row.get("hf_ollb_not_listed_on_leaderboard")) if has_not_listed_col and pd.notna(row.get("hf_ollb_not_listed_on_leaderboard")) else False,
            }
            
            has_hf_id = False
            if has_hf_id_col:
                hf_id = row.get("hugging_face_id")
                if pd.notna(hf_id) and hf_id:
                    has_hf_id = True
                    entry["hugging_face_id"] = str(hf_id).strip()
            
            is_not_listed = entry["not_listed"]
            
            if has_hf_id:
                if is_not_listed:
                    stats["unmatched_with_hf_id_not_listed_true"].append(entry)
                else:
                    stats["unmatched_with_hf_id_not_listed_false"].append(entry)
            else:
                stats["unmatched_without_hf_id"].append(entry)
        
        # Sort by slug
        stats["unmatched_with_hf_id_not_listed_false"].sort(key=lambda x: x["slug"])
        stats["unmatched_with_hf_id_not_listed_true"].sort(key=lambda x: x["slug"])
        stats["unmatched_without_hf_id"].sort(key=lambda x: x["slug"])
    
    return stats


def generate_coverage_report(
    df: pd.DataFrame,
    excel_path: str,
) -> Dict[str, Any]:
    """Generate complete coverage report with dual coverage semantics."""
    now = datetime.now(timezone.utc)
    all_columns = list(df.columns)
    
    report = {
        "generated_at": now.isoformat(),
        "excel_path": excel_path,
        "total_models": len(df),
        "total_columns": len(all_columns),
        "source_groups": {},
        "unmatched_lists": {},
        "hf_extended_stats": {},
        "summary": {},
    }
    
    # Analyze each source group
    for group_name, config in SOURCE_GROUPS.items():
        group_columns = find_columns_for_group(all_columns, config["prefixes"])
        
        coverage = compute_dual_coverage(
            df,
            group_columns,
            config.get("metadata_columns", []),
            config.get("metric_columns", []),
            eligibility_column=config.get("eligibility_column"),
        )
        
        # Add representative columns (top 10 by coverage)
        sorted_cols = sorted(
            coverage["column_coverage"].items(),
            key=lambda x: x[1]["coverage_percent"],
            reverse=True,
        )
        coverage["representative_columns"] = [c[0] for c in sorted_cols[:10]]
        
        report["source_groups"][group_name] = {
            "description": config["description"],
            "configured_metadata_columns": config.get("metadata_columns", []),
            "configured_metric_columns": config.get("metric_columns", []),
            **coverage,
        }
        
        # Find unmatched models (based on metric coverage)
        # For groups with eligibility tracking, only show eligible unmatched (the ones that matter)
        has_eligibility = config.get("eligibility_column") is not None
        unmatched = find_unmatched_models(
            df, group_name, config, top_n=20, 
            eligible_only=has_eligibility
        )
        report["unmatched_lists"][group_name] = unmatched
    
    # Compute HF-specific extended stats
    report["hf_extended_stats"] = compute_hf_extended_stats(df)
    
    # Generate summary
    total_groups = len(SOURCE_GROUPS)
    groups_with_metrics = sum(
        1 for g in report["source_groups"].values()
        if g["metric_coverage_percent"] > 0
    )
    groups_with_attempts = sum(
        1 for g in report["source_groups"].values()
        if g["attempt_coverage_percent"] > 0
    )
    
    report["summary"] = {
        "total_source_groups": total_groups,
        "groups_with_metric_data": groups_with_metrics,
        "groups_with_attempt_data": groups_with_attempts,
        "groups_fully_empty": total_groups - max(groups_with_metrics, groups_with_attempts),
        "best_metric_coverage_group": max(
            report["source_groups"].items(),
            key=lambda x: x[1]["metric_coverage_percent"],
        )[0] if report["source_groups"] else None,
        "worst_metric_coverage_group": min(
            report["source_groups"].items(),
            key=lambda x: x[1]["metric_coverage_percent"],
        )[0] if report["source_groups"] else None,
    }
    
    return report


def format_report_markdown(report: Dict[str, Any]) -> str:
    """Format coverage report as Markdown with dual coverage."""
    lines = []
    
    lines.append("# ModelDB Coverage Report")
    lines.append("")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append(f"**Excel Path:** `{report['excel_path']}`")
    lines.append(f"**Total Models:** {report['total_models']}")
    lines.append(f"**Total Columns:** {report['total_columns']}")
    lines.append("")
    
    # Coverage semantics explanation
    lines.append("## Coverage Semantics")
    lines.append("")
    lines.append("- **Attempt Coverage**: % of models where enrichment was attempted (metadata populated)")
    lines.append("- **Metric Coverage**: % of models where actual benchmark/rating data was retrieved")
    lines.append("- **Eligible Coverage** (HF only): % of open-weight models expected to be on the leaderboard")
    lines.append("- **Metric(Eligible)** (HF only): % of eligible models with benchmark data — the key KPI")
    lines.append("")
    
    # Summary
    lines.append("## Summary")
    lines.append("")
    summary = report["summary"]
    lines.append(f"- **Source Groups Analyzed:** {summary['total_source_groups']}")
    lines.append(f"- **Groups with Metric Data:** {summary['groups_with_metric_data']}")
    lines.append(f"- **Groups with Attempt Data:** {summary['groups_with_attempt_data']}")
    lines.append(f"- **Groups Fully Empty:** {summary['groups_fully_empty']}")
    if summary.get("best_metric_coverage_group"):
        best = summary["best_metric_coverage_group"]
        best_pct = report["source_groups"][best]["metric_coverage_percent"]
        lines.append(f"- **Best Metric Coverage:** {best} ({best_pct}%)")
    if summary.get("worst_metric_coverage_group"):
        worst = summary["worst_metric_coverage_group"]
        worst_pct = report["source_groups"][worst]["metric_coverage_percent"]
        lines.append(f"- **Worst Metric Coverage:** {worst} ({worst_pct}%)")
    lines.append("")
    
    # Coverage by Source Group
    lines.append("## Coverage by Source Group")
    lines.append("")
    
    # Table header with both coverages + eligibility
    lines.append("| Source Group | Metric % | Attempt % | Eligible | Metric(Eligible) |")
    lines.append("|--------------|----------|-----------|----------|------------------|")
    
    for group_name, data in sorted(report["source_groups"].items(), key=lambda x: -x[1]["metric_coverage_percent"]):
        eligible_str = str(data.get("eligible_count", "-")) if data.get("eligible_count", 0) > 0 else "-"
        eligible_metric_str = f"{data['eligible_metric_coverage_percent']}%" if data.get("eligible_count", 0) > 0 else "-"
        
        lines.append(
            f"| {group_name} | {data['metric_coverage_percent']}% | "
            f"{data['attempt_coverage_percent']}% | {eligible_str} | {eligible_metric_str} |"
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
        lines.append(f"- **Metric Coverage:** {data['metric_coverage_percent']}% ({data['metric_models']}/{data['total_models']} models)")
        lines.append(f"- **Attempt Coverage:** {data['attempt_coverage_percent']}% ({data['attempt_models']}/{data['total_models']} models)")
        
        # Add eligibility info if available
        if data.get("eligible_count", 0) > 0:
            lines.append(f"- **Eligible Models:** {data['eligible_count']} ({100.0 * data['eligible_count'] / data['total_models']:.1f}% of total)")
            lines.append(f"- **Ineligible Models:** {data['ineligible_count']} (closed/proprietary)")
            lines.append(f"- **Metric Coverage (Eligible):** {data['eligible_metric_coverage_percent']}% ({data['eligible_metric_models']}/{data['eligible_count']} eligible models)")
            
            # Add HF extended stats if this is HF leaderboard
            if group_name == "hf_leaderboard":
                hf_ext = report.get("hf_extended_stats", {})
                if hf_ext.get("conflict_count_eligible", 0) > 0:
                    lines.append(f"- **Conflicts (Eligible):** {hf_ext['conflict_count_eligible']}")
                if hf_ext.get("not_listed_count_eligible", 0) > 0:
                    lines.append(f"- **Not-Listed (Eligible):** {hf_ext['not_listed_count_eligible']} (candidates absent from leaderboard)")
                if hf_ext.get("true_gaps_count", 0) > 0:
                    lines.append(f"- **True Gaps:** {hf_ext['true_gaps_count']} (need investigation)")
                if hf_ext.get("inferred_hf_id_count", 0) > 0:
                    lines.append(f"- **Inferred HF IDs:** {hf_ext['inferred_hf_id_count']}")
                
                method_breakdown = hf_ext.get("match_method_breakdown", {})
                if method_breakdown:
                    lines.append("")
                    lines.append("**Match Method Breakdown (matched rows):**")
                    lines.append("")
                    for method, count in sorted(method_breakdown.items(), key=lambda x: -x[1]):
                        lines.append(f"- `{method}`: {count}")
                
                outcome_breakdown = hf_ext.get("match_outcome_breakdown", {})
                if outcome_breakdown:
                    lines.append("")
                    lines.append("**Match Outcome Breakdown (non-matched):**")
                    lines.append("")
                    for outcome, count in sorted(outcome_breakdown.items(), key=lambda x: -x[1]):
                        lines.append(f"- `{outcome}`: {count}")
        
        lines.append(f"- **Columns Found:** {data['columns_found']} (metadata: {data['metadata_columns_found']}, metrics: {data['metric_columns_found']})")
        lines.append("")
        
        if data.get("representative_columns"):
            lines.append("**Top Columns by Coverage:**")
            lines.append("")
            for col in data["representative_columns"][:5]:
                col_data = data["column_coverage"].get(col, {})
                pct = col_data.get("coverage_percent", 0)
                cnt = col_data.get("non_null_count", 0)
                col_type = col_data.get("column_type", "metric")
                lines.append(f"- `{col}` [{col_type}]: {pct}% ({cnt} values)")
            lines.append("")
    
    # Unmatched Lists
    lines.append("## Unmatched Models (Top 20 per Source)")
    lines.append("")
    lines.append("Models without metric data from each source.")
    lines.append("For sources with eligibility tracking (e.g., HF Leaderboard), only eligible models are shown.")
    lines.append("")
    
    for group_name, unmatched in report["unmatched_lists"].items():
        # Check if this group has eligibility
        group_data = report["source_groups"].get(group_name, {})
        has_eligibility = group_data.get("eligible_count", 0) > 0
        
        lines.append(f"### {group_name}")
        if has_eligibility:
            lines.append("_(Showing eligible models only)_")
        lines.append("")
        
        if not unmatched:
            if has_eligibility:
                lines.append("_All eligible models have metric data, or no unmatched eligible models._")
            else:
                lines.append("_No unmatched models (or all models have metric data)._")
        else:
            lines.append(f"**{len(unmatched)} models without metric data:**")
            lines.append("")
            for item in unmatched[:20]:
                candidate_info = f" (tried: `{item['candidate_hf_id']}`)" if item.get("candidate_hf_id") else ""
                lines.append(f"- `{item['slug']}`: {item['reason']}{candidate_info}")
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
        print("\n" + "=" * 80)
        print("COVERAGE REPORT SUMMARY")
        print("=" * 80)
        print(f"Total Models: {report['total_models']}")
        print(f"Total Columns: {report['total_columns']}")
        print("")
        print("Source Group Coverage:")
        print("")
        for group_name, data in sorted(
            report["source_groups"].items(),
            key=lambda x: -x[1]["metric_coverage_percent"],
        ):
            metric_status = "✅" if data["metric_coverage_percent"] > 0 else "❌"
            
            # Check if this group has eligibility tracking
            has_eligibility = data.get("eligible_count", 0) > 0
            
            if has_eligibility:
                # Show eligibility-aware format for HF leaderboard
                print(
                    f"  {metric_status} {group_name:25} Metric: {data['metric_coverage_percent']:5.1f}% "
                    f"| Attempt: {data['attempt_coverage_percent']:5.1f}% "
                    f"| Eligible: {data['eligible_count']} "
                    f"| Metric(Eligible): {data['eligible_metric_coverage_percent']:.1f}%"
                )
            else:
                # Standard format for other groups
                print(
                    f"  {metric_status} {group_name:25} Metric: {data['metric_coverage_percent']:5.1f}% "
                    f"| Attempt: {data['attempt_coverage_percent']:5.1f}% "
                    f"| Models: {data['metric_models']}/{data['total_models']}"
                )
        print("")
        
        # Show HF-specific summary if eligibility is present
        hf_data = report["source_groups"].get("hf_leaderboard", {})
        hf_ext = report.get("hf_extended_stats", {})
        if hf_data.get("eligible_count", 0) > 0:
            print("📊 HF Leaderboard Eligibility Breakdown:")
            print(f"   Eligible models: {hf_data['eligible_count']} ({100.0 * hf_data['eligible_count'] / hf_data['total_models']:.1f}%)")
            print(f"   Ineligible models: {hf_data['ineligible_count']} (closed/proprietary)")
            print(f"   Eligible with metrics: {hf_data['eligible_metric_models']}/{hf_data['eligible_count']} ({hf_data['eligible_metric_coverage_percent']:.1f}%)")
            if hf_ext.get("conflict_count_eligible", 0) > 0:
                print(f"   Conflicts (eligible): {hf_ext['conflict_count_eligible']}")
            if hf_ext.get("not_listed_count_eligible", 0) > 0:
                print(f"   Not-listed (eligible): {hf_ext['not_listed_count_eligible']} (candidates absent from leaderboard)")
            if hf_ext.get("true_gaps_count", 0) > 0:
                print(f"   True gaps (eligible): {hf_ext['true_gaps_count']} (need investigation)")
            if hf_ext.get("inferred_hf_id_count", 0) > 0:
                print(f"   Inferred HF IDs: {hf_ext['inferred_hf_id_count']}")
            print("")
            
            # Show match method breakdown if available
            method_breakdown = hf_ext.get("match_method_breakdown", {})
            if method_breakdown:
                print("   Match method breakdown (matched rows):")
                for method, count in sorted(method_breakdown.items(), key=lambda x: -x[1]):
                    print(f"     {method}: {count}")
                print("")
            
            # Show match outcome breakdown if available
            outcome_breakdown = hf_ext.get("match_outcome_breakdown", {})
            if outcome_breakdown:
                print("   Match outcome breakdown (non-matched):")
                for outcome, count in sorted(outcome_breakdown.items(), key=lambda x: -x[1]):
                    print(f"     {outcome}: {count}")
                print("")
            
            # Show unmatched split (3 categories now)
            unmatched_with_hf_not_listed_false = hf_ext.get("unmatched_with_hf_id_not_listed_false", [])
            unmatched_with_hf_not_listed_true = hf_ext.get("unmatched_with_hf_id_not_listed_true", [])
            unmatched_without_hf = hf_ext.get("unmatched_without_hf_id", [])
            
            if unmatched_with_hf_not_listed_false:
                print(f"   🔴 Unmatched WITH hf_id (not_listed=False) ({len(unmatched_with_hf_not_listed_false)} - likely matching bug):")
                for item in unmatched_with_hf_not_listed_false[:5]:
                    outcome = item.get("match_outcome") or item.get("match_status", "?")
                    print(f"     - {item['slug']}: {outcome}")
                if len(unmatched_with_hf_not_listed_false) > 5:
                    print(f"     ... and {len(unmatched_with_hf_not_listed_false) - 5} more")
                print("")
            
            if unmatched_with_hf_not_listed_true:
                print(f"   🟡 Unmatched WITH hf_id (not_listed=True) ({len(unmatched_with_hf_not_listed_true)} - not on leaderboard):")
                for item in unmatched_with_hf_not_listed_true[:3]:
                    print(f"     - {item['slug']} -> {item.get('candidate_hf_id', '?')}")
                if len(unmatched_with_hf_not_listed_true) > 3:
                    print(f"     ... and {len(unmatched_with_hf_not_listed_true) - 3} more")
                print("")
            
            if unmatched_without_hf:
                print(f"   ⚪ Unmatched WITHOUT hf_id ({len(unmatched_without_hf)} - need ID discovery):")
                for item in unmatched_without_hf[:3]:
                    inferred = item.get("inferred_hf_id", "")
                    if inferred:
                        print(f"     - {item['slug']} (inferred: {inferred})")
                    else:
                        print(f"     - {item['slug']}")
                if len(unmatched_without_hf) > 3:
                    print(f"     ... and {len(unmatched_without_hf) - 3} more")
                print("")
        
        # Show groups needing attention
        low_metric_groups = [
            g for g, d in report["source_groups"].items()
            if d["metric_coverage_percent"] == 0 and d["attempt_coverage_percent"] > 0
            and d.get("eligible_count", 0) == 0  # Exclude if eligibility tracking present
        ]
        if low_metric_groups:
            print("⚠️  Groups with attempts but no metrics (enricher may need fixing):")
            for g in low_metric_groups:
                print(f"   - {g}")
        
        empty_groups = [
            g for g, d in report["source_groups"].items()
            if d["attempt_coverage_percent"] == 0
        ]
        if empty_groups:
            print("ℹ️  Groups not yet run:")
            for g in empty_groups:
                print(f"   - {g}")
        print("=" * 80)
    
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
