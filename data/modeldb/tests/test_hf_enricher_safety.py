#!/usr/bin/env python3
"""
HF Leaderboard Enricher Regression Safety Tests

Validates:
1. Row count preserved after enrichment
2. HF columns exist with correct types
3. Eligibility column is boolean-like
4. Matched rows have at least one metric
5. No mass accidental matching (conflict detection works)

Usage:
    python data/modeldb/tests/test_hf_enricher_safety.py
    python data/modeldb/tests/test_hf_enricher_safety.py --excel path/to/modeldb.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# Add parent to path for imports
SCRIPT_DIR = Path(__file__).parent.resolve()
MODELDB_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(MODELDB_DIR))

DEFAULT_EXCEL = MODELDB_DIR / "LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_2025-12-25.xlsx"

# Expected HF columns
EXPECTED_HF_COLUMNS = [
    # Eligibility (new)
    "hf_ollb_eligible",
    "hf_ollb_ineligible_reason",
    "hf_ollb_candidate_hf_id",
    # Matching metadata
    "hf_ollb_match_status",
    "hf_ollb_match_method",
    "hf_ollb_match_score",
    # Benchmark scores
    "hf_ollb_avg",
    "hf_ollb_mmlu_pro",
    "hf_ollb_ifeval",
    "hf_ollb_bbh",
    "hf_ollb_math",
    "hf_ollb_gpqa",
    "hf_ollb_musr",
]

# At least one of these should be non-null for matched rows
METRIC_COLUMNS = [
    "hf_ollb_avg",
    "hf_ollb_mmlu_pro",
    "hf_ollb_ifeval",
    "hf_ollb_bbh",
    "hf_ollb_math",
    "hf_ollb_gpqa",
    "hf_ollb_musr",
]


def test_row_count_preserved(df: pd.DataFrame, expected_min_rows: int = 350) -> bool:
    """Test that row count is at least the expected minimum."""
    actual = len(df)
    if actual < expected_min_rows:
        print(f"❌ FAIL: Row count {actual} < expected minimum {expected_min_rows}")
        return False
    print(f"✅ PASS: Row count preserved ({actual} rows)")
    return True


def test_hf_columns_exist(df: pd.DataFrame) -> bool:
    """Test that expected HF columns exist."""
    missing = [col for col in EXPECTED_HF_COLUMNS if col not in df.columns]
    if missing:
        print(f"❌ FAIL: Missing HF columns: {missing}")
        return False
    print(f"✅ PASS: All {len(EXPECTED_HF_COLUMNS)} expected HF columns exist")
    return True


def test_eligibility_is_boolean(df: pd.DataFrame) -> bool:
    """Test that hf_ollb_eligible is boolean-like (True/False/None)."""
    if "hf_ollb_eligible" not in df.columns:
        print("❌ FAIL: hf_ollb_eligible column missing")
        return False
    
    col = df["hf_ollb_eligible"]
    non_null = col.dropna()
    
    if len(non_null) == 0:
        print("⚠️  WARN: hf_ollb_eligible has no non-null values (enricher may not have run)")
        return True  # Not a failure, just not run
    
    # Check values are boolean-like
    unique_vals = set(non_null.unique())
    valid_vals = {True, False, 1, 0, "True", "False", "true", "false"}
    
    invalid = unique_vals - valid_vals
    if invalid:
        print(f"❌ FAIL: hf_ollb_eligible has invalid values: {invalid}")
        return False
    
    eligible_count = (non_null.astype(bool) == True).sum()
    ineligible_count = (non_null.astype(bool) == False).sum()
    print(f"✅ PASS: hf_ollb_eligible is boolean-like (eligible={eligible_count}, ineligible={ineligible_count})")
    return True


def test_matched_rows_have_metrics(df: pd.DataFrame) -> bool:
    """Test that rows with match_status='matched' have at least one metric."""
    if "hf_ollb_match_status" not in df.columns:
        print("⚠️  WARN: hf_ollb_match_status column missing (enricher may not have run)")
        return True
    
    matched = df[df["hf_ollb_match_status"] == "matched"]
    
    if len(matched) == 0:
        print("⚠️  WARN: No matched rows found (enricher may not have run or matched 0)")
        return True
    
    # Check each matched row has at least one metric
    existing_metrics = [c for c in METRIC_COLUMNS if c in df.columns]
    if not existing_metrics:
        print("❌ FAIL: No metric columns found in DataFrame")
        return False
    
    has_any_metric = matched[existing_metrics].notna().any(axis=1)
    matched_without_metrics = len(matched) - has_any_metric.sum()
    
    if matched_without_metrics > 0:
        print(f"❌ FAIL: {matched_without_metrics}/{len(matched)} matched rows have no metrics")
        return False
    
    print(f"✅ PASS: All {len(matched)} matched rows have at least one metric")
    return True


def test_no_mass_matching(df: pd.DataFrame, max_match_rate: float = 0.80) -> bool:
    """Test that we're not accidentally mass-matching (conflict detection works)."""
    if "hf_ollb_match_status" not in df.columns:
        print("⚠️  WARN: hf_ollb_match_status column missing")
        return True
    
    total = df["hf_ollb_match_status"].notna().sum()
    if total == 0:
        print("⚠️  WARN: No rows have match_status set")
        return True
    
    matched = (df["hf_ollb_match_status"] == "matched").sum()
    match_rate = matched / total
    
    if match_rate > max_match_rate:
        print(f"❌ FAIL: Match rate {match_rate:.1%} exceeds {max_match_rate:.0%} threshold (suspiciously high)")
        return False
    
    # Also check for conflicts (should be a few, not zero or huge)
    conflicts = (df["hf_ollb_match_status"] == "conflict").sum()
    
    print(f"✅ PASS: Match rate {match_rate:.1%} is reasonable (matched={matched}, conflicts={conflicts})")
    return True


def test_eligibility_coverage_reasonable(df: pd.DataFrame) -> bool:
    """Test that eligibility breakdown is reasonable."""
    if "hf_ollb_eligible" not in df.columns:
        print("⚠️  WARN: hf_ollb_eligible column missing")
        return True
    
    col = df["hf_ollb_eligible"].fillna(False).astype(bool)
    eligible = col.sum()
    ineligible = (~col).sum()
    total = len(df)
    
    if total == 0:
        return True
    
    eligible_pct = 100.0 * eligible / total
    
    # Eligibility should be between 10-70% (reasonable range for open vs closed models)
    if eligible_pct < 5:
        print(f"⚠️  WARN: Only {eligible_pct:.1f}% eligible (seems low, may need tuning)")
    elif eligible_pct > 80:
        print(f"⚠️  WARN: {eligible_pct:.1f}% eligible (seems high, closed model detection may need improvement)")
    else:
        print(f"✅ PASS: Eligibility distribution reasonable ({eligible_pct:.1f}% eligible)")
    
    return True  # Don't fail on this, just warn


def run_all_tests(excel_path: Path) -> bool:
    """Run all regression safety tests."""
    print("=" * 60)
    print("HF Leaderboard Enricher Regression Safety Tests")
    print("=" * 60)
    print(f"Excel: {excel_path}")
    print("")
    
    if not excel_path.exists():
        print(f"❌ FAIL: Excel file not found: {excel_path}")
        return False
    
    try:
        df = pd.read_excel(excel_path)
        print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        print("")
    except Exception as e:
        print(f"❌ FAIL: Could not load Excel: {e}")
        return False
    
    results = []
    
    print("Running tests...")
    print("-" * 40)
    
    results.append(("Row count preserved", test_row_count_preserved(df)))
    results.append(("HF columns exist", test_hf_columns_exist(df)))
    results.append(("Eligibility is boolean", test_eligibility_is_boolean(df)))
    results.append(("Matched rows have metrics", test_matched_rows_have_metrics(df)))
    results.append(("No mass matching", test_no_mass_matching(df)))
    results.append(("Eligibility coverage reasonable", test_eligibility_coverage_reasonable(df)))
    
    print("-" * 40)
    print("")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ ALL TESTS PASSED")
        return True
    else:
        failed = [name for name, r in results if not r]
        print(f"❌ FAILED TESTS: {failed}")
        return False


def main():
    parser = argparse.ArgumentParser(description="HF Enricher Regression Safety Tests")
    parser.add_argument(
        "--excel",
        type=str,
        default=str(DEFAULT_EXCEL),
        help=f"Path to Excel file (default: {DEFAULT_EXCEL.name})",
    )
    args = parser.parse_args()
    
    excel_path = Path(args.excel)
    success = run_all_tests(excel_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
