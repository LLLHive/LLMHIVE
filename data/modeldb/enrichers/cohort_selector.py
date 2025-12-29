"""
Cohort Selector for Incremental Enrichment

Provides deterministic, TTL-based cohort selection for evals and telemetry.
Ensures weekly runs naturally rotate through the model population.

Key Features:
- TTL-based refresh: only select models needing refresh
- Deterministic ordering: same seed = same cohort
- Top models bucket: always include high-priority models
- ISO week seed: automatic weekly rotation
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def get_iso_week_seed() -> str:
    """Get current ISO week as seed (YYYY-WW format)."""
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"


def stable_hash(seed_key: str, value: str) -> int:
    """
    Compute a stable hash for deterministic ordering.
    
    Uses SHA1 for consistency across Python versions.
    """
    combined = f"{seed_key}:{value}"
    h = hashlib.sha1(combined.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def parse_asof_date(asof_value: Any) -> Optional[datetime]:
    """
    Parse an asof_date value to datetime.
    
    Handles:
    - ISO8601 strings
    - datetime objects
    - pandas Timestamp
    - None/NaN
    """
    if pd.isna(asof_value) or asof_value is None:
        return None
    
    if isinstance(asof_value, datetime):
        if asof_value.tzinfo is None:
            return asof_value.replace(tzinfo=timezone.utc)
        return asof_value
    
    if isinstance(asof_value, pd.Timestamp):
        dt = asof_value.to_pydatetime()
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    if isinstance(asof_value, str):
        try:
            # Try ISO8601 format
            if "T" in asof_value:
                if asof_value.endswith("Z"):
                    return datetime.fromisoformat(asof_value.replace("Z", "+00:00"))
                return datetime.fromisoformat(asof_value)
            # Try date-only format
            return datetime.strptime(asof_value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    
    return None


def is_stale(
    asof_value: Any,
    ttl_days: int,
    now: Optional[datetime] = None,
) -> bool:
    """
    Check if a value is stale (older than TTL or missing).
    
    Returns True if refresh is needed.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    asof_dt = parse_asof_date(asof_value)
    
    if asof_dt is None:
        return True  # Missing = stale
    
    age = now - asof_dt
    return age > timedelta(days=ttl_days)


def select_cohort(
    df: pd.DataFrame,
    *,
    max_models: int,
    ttl_days: int,
    seed_key: Optional[str] = None,
    always_include_top: int = 10,
    slug_column: str = "openrouter_slug",
    asof_column: str = None,  # e.g., "eval_asof_date" or "telemetry_asof_date"
    metric_columns: Optional[List[str]] = None,  # Check if any metric is non-null
    rank_column: str = "derived_rank_overall",  # For top models
    eligibility_filter: Optional[str] = None,  # e.g., "in_openrouter"
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Select a deterministic cohort of models for enrichment.
    
    Selection priority:
    1. Top N models by rank (always included if budget allows)
    2. Models needing refresh (stale or missing)
    3. Deterministic hash order for remaining budget
    
    Args:
        df: DataFrame with models
        max_models: Maximum cohort size (0 = unlimited)
        ttl_days: Time-to-live for metrics
        seed_key: Seed for deterministic ordering (default: ISO week)
        always_include_top: Number of top-ranked models to always include
        slug_column: Column containing model slugs
        asof_column: Column with last refresh timestamp
        metric_columns: Columns to check for existing metrics
        rank_column: Column for ranking (lower = higher priority)
        eligibility_filter: Column that must be True for eligibility
    
    Returns:
        (list of selected slugs, selection metadata dict)
    """
    if seed_key is None:
        seed_key = get_iso_week_seed()
    
    now = datetime.now(timezone.utc)
    
    # Start with eligible models
    eligible_mask = df[slug_column].notna()
    
    if eligibility_filter and eligibility_filter in df.columns:
        eligible_mask = eligible_mask & (df[eligibility_filter] == True)
    
    eligible_df = df[eligible_mask].copy()
    
    if len(eligible_df) == 0:
        return [], {"seed_key": seed_key, "eligible_count": 0, "selected_count": 0}
    
    # Determine which models need refresh
    def needs_refresh(row: pd.Series) -> bool:
        # Check if asof is stale
        if asof_column and asof_column in row.index:
            if is_stale(row.get(asof_column), ttl_days, now):
                return True
        else:
            # No asof column = always needs refresh
            return True
        
        # Check if metrics are missing
        if metric_columns:
            has_any_metric = False
            for col in metric_columns:
                if col in row.index and pd.notna(row.get(col)):
                    has_any_metric = True
                    break
            if not has_any_metric:
                return True
        
        return False
    
    eligible_df["_needs_refresh"] = eligible_df.apply(needs_refresh, axis=1)
    
    # Compute stable hash for ordering
    eligible_df["_hash_order"] = eligible_df[slug_column].apply(
        lambda s: stable_hash(seed_key, str(s))
    )
    
    # Get top models bucket
    top_slugs: Set[str] = set()
    if always_include_top > 0 and rank_column in eligible_df.columns:
        # Filter to models with valid ranks
        ranked = eligible_df[eligible_df[rank_column].notna()].copy()
        ranked = ranked.sort_values(rank_column, ascending=True)
        top_slugs = set(ranked[slug_column].head(always_include_top).tolist())
    
    # Models needing refresh (prioritized)
    refresh_df = eligible_df[eligible_df["_needs_refresh"]]
    
    # Sort by hash for deterministic order
    refresh_df = refresh_df.sort_values("_hash_order")
    
    # Build cohort
    selected_slugs: List[str] = []
    
    # First, add top models that need refresh
    for slug in top_slugs:
        if slug in refresh_df[slug_column].values:
            selected_slugs.append(slug)
    
    # Then add other models needing refresh
    for slug in refresh_df[slug_column].tolist():
        if slug not in selected_slugs:
            selected_slugs.append(slug)
    
    # Apply max_models limit
    if max_models > 0 and len(selected_slugs) > max_models:
        selected_slugs = selected_slugs[:max_models]
    
    # Build metadata
    metadata = {
        "seed_key": seed_key,
        "ttl_days": ttl_days,
        "eligible_count": len(eligible_df),
        "needs_refresh_count": len(refresh_df),
        "top_models_in_cohort": len([s for s in selected_slugs if s in top_slugs]),
        "selected_count": len(selected_slugs),
        "max_models": max_models,
        "always_include_top": always_include_top,
    }
    
    logger.info(
        "Cohort selection: %d/%d eligible need refresh, selected %d (top=%d)",
        len(refresh_df), len(eligible_df), len(selected_slugs), 
        metadata["top_models_in_cohort"]
    )
    
    return selected_slugs, metadata


def generate_run_id() -> str:
    """Generate a run ID based on current timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
