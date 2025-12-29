#!/usr/bin/env python3
"""
HF OLLB True Gaps Triage Script

Identifies "true gaps" in HF OLLB coverage:
- Eligible models that are not matched, not conflict, and not marked as not-listed
- These represent potential matching bugs or data quality issues

True gaps = eligible AND match_status != matched AND match_status != conflict AND not_listed != True

Exit codes:
- 0: No true gaps (success)
- 2: True gaps exist (need investigation)

Usage:
    python scripts/triage_hf_ollb_true_gaps.py
    python scripts/triage_hf_ollb_true_gaps.py --excel path/to/modeldb.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Default paths
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
MODELDB_DIR = REPO_ROOT / "data" / "modeldb"
DEFAULT_EXCEL = MODELDB_DIR / "LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx"

# Columns to display for debugging
DISPLAY_COLUMNS = [
    "openrouter_slug",
    "model_name",
    "hugging_face_id",
    "hf_ollb_inferred_hf_id",
    "hf_ollb_base_model_hf_id",
    "hf_ollb_candidate_set",
    "hf_ollb_attempted_methods",
    "hf_ollb_match_outcome",
    "hf_ollb_conflict_candidates",
    "hf_ollb_match_status",
    "hf_ollb_not_listed_on_leaderboard",
]


def load_excel(excel_path: Path) -> pd.DataFrame:
    """Load the ModelDB Excel file."""
    if not excel_path.exists():
        print(f"ERROR: Excel file not found: {excel_path}")
        sys.exit(1)
    
    return pd.read_excel(excel_path)


def get_true_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get true gaps: eligible rows that are not matched, not conflict, and not not-listed.
    
    True gaps = eligible AND match_status != matched AND match_status != conflict AND not_listed != True
    """
    # Check required columns
    required = ["hf_ollb_eligible", "hf_ollb_match_status", "hf_ollb_not_listed_on_leaderboard"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        sys.exit(1)
    
    # Build masks
    eligible_mask = df["hf_ollb_eligible"].fillna(False).astype(bool)
    not_matched_mask = df["hf_ollb_match_status"] != "matched"
    not_conflict_mask = df["hf_ollb_match_status"] != "conflict"
    not_listed_mask = df["hf_ollb_not_listed_on_leaderboard"].fillna(False).astype(bool)
    
    # True gaps: eligible AND not matched AND not conflict AND not not-listed
    true_gaps_mask = eligible_mask & not_matched_mask & not_conflict_mask & ~not_listed_mask
    
    return df[true_gaps_mask]


def get_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """Get conflict rows for inspection."""
    if "hf_ollb_match_status" not in df.columns:
        return pd.DataFrame()
    
    conflict_mask = df["hf_ollb_match_status"] == "conflict"
    eligible_mask = df["hf_ollb_eligible"].fillna(False).astype(bool) if "hf_ollb_eligible" in df.columns else True
    
    return df[conflict_mask & eligible_mask]


def print_rows(df: pd.DataFrame, title: str, columns: list) -> None:
    """Print rows with selected columns."""
    print(f"\n{'='*80}")
    print(f"{title} ({len(df)} rows)")
    print("="*80)
    
    if len(df) == 0:
        print("  (none)")
        return
    
    # Filter to available columns
    available = [c for c in columns if c in df.columns]
    
    for idx, row in df.iterrows():
        print(f"\n--- Row {idx} ---")
        for col in available:
            val = row.get(col)
            if pd.notna(val) and val != "":
                # Truncate long values
                val_str = str(val)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                print(f"  {col}: {val_str}")


def main():
    parser = argparse.ArgumentParser(description="HF OLLB True Gaps Triage")
    parser.add_argument(
        "--excel",
        type=str,
        default=str(DEFAULT_EXCEL),
        help=f"Path to Excel file (default: {DEFAULT_EXCEL.name})",
    )
    args = parser.parse_args()
    
    excel_path = Path(args.excel)
    
    print("="*80)
    print("HF OLLB TRUE GAPS TRIAGE")
    print("="*80)
    print(f"Excel: {excel_path}")
    
    # Load data
    df = load_excel(excel_path)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Get true gaps
    true_gaps = get_true_gaps(df)
    
    # Get conflicts for reference
    conflicts = get_conflicts(df)
    
    # Print summary
    print(f"\nSummary:")
    
    if "hf_ollb_eligible" in df.columns:
        eligible_count = df["hf_ollb_eligible"].fillna(False).astype(bool).sum()
        print(f"  Eligible models: {eligible_count}")
    
    if "hf_ollb_match_status" in df.columns:
        matched_count = (df["hf_ollb_match_status"] == "matched").sum()
        conflict_count = (df["hf_ollb_match_status"] == "conflict").sum()
        print(f"  Matched: {matched_count}")
        print(f"  Conflicts: {conflict_count}")
    
    if "hf_ollb_not_listed_on_leaderboard" in df.columns:
        not_listed_count = df["hf_ollb_not_listed_on_leaderboard"].fillna(False).astype(bool).sum()
        print(f"  Not-listed: {not_listed_count}")
    
    print(f"  TRUE GAPS: {len(true_gaps)}")
    
    # Print details
    print_rows(true_gaps, "TRUE GAPS (need investigation)", DISPLAY_COLUMNS)
    print_rows(conflicts, "CONFLICTS (for reference)", DISPLAY_COLUMNS)
    
    # Match outcome breakdown for true gaps
    if len(true_gaps) > 0 and "hf_ollb_match_outcome" in df.columns:
        print(f"\nTrue gaps by match_outcome:")
        outcomes = true_gaps["hf_ollb_match_outcome"].value_counts()
        for outcome, count in outcomes.items():
            print(f"  {outcome}: {count}")
    
    # Exit code
    if len(true_gaps) == 0:
        print(f"\n✅ SUCCESS: No true gaps!")
        sys.exit(0)
    else:
        print(f"\n❌ FAIL: {len(true_gaps)} true gaps remain")
        sys.exit(2)


if __name__ == "__main__":
    main()

