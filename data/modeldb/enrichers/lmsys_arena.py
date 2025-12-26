"""
LMSYS Chatbot Arena Enricher

Fetches Elo ratings and rankings from the LMSYS Chatbot Arena leaderboard.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)

# LMSYS Arena data sources
# The official leaderboard data is available via HuggingFace datasets
ARENA_HF_DATASET = "lmsys/chatbot_arena_leaderboard"
ARENA_LEADERBOARD_URL = "https://huggingface.co/datasets/lmsys/chatbot_arena_leaderboard"

# Direct CSV/JSON endpoints (if available)
ARENA_LEADERBOARD_CSV = "https://huggingface.co/datasets/lmsys/chatbot_arena_leaderboard/resolve/main/leaderboard_table.csv"


class LMSYSArenaEnricher(BaseEnricher):
    """
    Enricher that fetches LMSYS Chatbot Arena Elo ratings.
    
    Adds columns:
    - arena_elo_overall
    - arena_rank_overall
    - arena_elo_<category> (for available splits like coding, long, etc.)
    - arena_match_status (exact/heuristic/unmatched)
    - arena_matched_name
    """
    
    name = "lmsys_arena"
    source_name = "LMSYS Chatbot Arena"
    source_url = ARENA_LEADERBOARD_URL
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self._arena_data: Optional[pd.DataFrame] = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _fetch_arena_data(self) -> pd.DataFrame:
        """
        Fetch Arena leaderboard data.
        
        Tries multiple sources in order of reliability.
        """
        # Try HuggingFace datasets API first
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading Arena data from HuggingFace datasets...")
            ds = load_dataset(ARENA_HF_DATASET, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from Arena leaderboard", len(df))
            return df
        except ImportError:
            self.logger.warning("datasets library not available, trying CSV fallback")
        except Exception as e:
            self.logger.warning("HuggingFace datasets failed: %s", e)
        
        # Fallback to CSV
        try:
            self.logger.info("Fetching Arena data from CSV...")
            response = requests.get(ARENA_LEADERBOARD_CSV, timeout=30)
            response.raise_for_status()
            
            import io
            df = pd.read_csv(io.StringIO(response.text))
            self.logger.info("Loaded %d models from Arena CSV", len(df))
            return df
        except Exception as e:
            self.logger.error("CSV fallback failed: %s", e)
            raise
    
    def _normalize_arena_name(self, name: str) -> str:
        """Normalize Arena model name for matching."""
        if not name:
            return ""
        name = name.lower().strip()
        # Remove common suffixes
        name = re.sub(r"[-_]?(chat|instruct|turbo|preview|beta|alpha|exp)$", "", name)
        # Normalize separators
        name = name.replace("_", "-").replace(" ", "-")
        return name
    
    def _match_to_catalog(
        self,
        arena_name: str,
        catalog_slugs: List[str],
    ) -> Tuple[str, str, float]:
        """
        Match an Arena model name to a catalog slug.
        
        Returns:
            (matched_slug, match_status, match_score)
        """
        if not arena_name:
            return "", "unmatched", 0.0
        
        arena_normalized = self._normalize_arena_name(arena_name)
        
        # Try exact slug match first
        for slug in catalog_slugs:
            if arena_normalized == slug.lower():
                return slug, "exact", 1.0
            # Try matching just the model part (after /)
            if "/" in slug:
                model_part = slug.split("/", 1)[1].lower()
                if arena_normalized == model_part:
                    return slug, "exact", 1.0
        
        # Heuristic matching
        best_match = ""
        best_score = 0.0
        
        for slug in catalog_slugs:
            slug_normalized = self._normalize_model_name(slug)
            model_part = slug.split("/", 1)[1] if "/" in slug else slug
            model_normalized = self._normalize_model_name(model_part)
            
            # Check if arena name is contained in slug or vice versa
            if arena_normalized in model_normalized or model_normalized in arena_normalized:
                # Calculate similarity score
                score = len(set(arena_normalized) & set(model_normalized)) / max(
                    len(arena_normalized), len(model_normalized), 1
                )
                if score > best_score:
                    best_score = score
                    best_match = slug
        
        if best_score >= 0.6:
            return best_match, "heuristic", best_score
        
        return "", "unmatched", 0.0
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fetch Arena data and enrich the catalog."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would fetch LMSYS Arena data")
            result.warnings.append("Dry run - no API calls made")
            return df
        
        try:
            arena_df = self._fetch_arena_data()
        except Exception as e:
            result.errors.append(f"Failed to fetch Arena data: {e}")
            # Continue without Arena data
            return df
        
        # Initialize new columns
        now_iso = datetime.now(timezone.utc).isoformat()
        
        new_columns = [
            "arena_elo_overall",
            "arena_rank_overall",
            "arena_match_status",
            "arena_matched_name",
            "arena_match_score",
            "arena_source_name",
            "arena_source_url",
            "arena_retrieved_at",
        ]
        
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        # Get catalog slugs for matching
        catalog_slugs = df["openrouter_slug"].dropna().tolist()
        
        # Identify Arena columns
        # Common column names: 'Model', 'Elo', 'Rank', or variations
        arena_name_col = None
        arena_elo_col = None
        arena_rank_col = None
        
        for col in arena_df.columns:
            col_lower = col.lower()
            if "model" in col_lower and "name" in col_lower or col_lower == "model":
                arena_name_col = col
            elif col_lower == "elo" or "elo_rating" in col_lower or "rating" in col_lower:
                arena_elo_col = col
            elif col_lower == "rank":
                arena_rank_col = col
        
        if not arena_name_col:
            # Try first column as model name
            arena_name_col = arena_df.columns[0]
        
        self.logger.info(
            "Arena columns: name=%s, elo=%s, rank=%s",
            arena_name_col, arena_elo_col, arena_rank_col
        )
        
        # Build Arena lookup
        arena_by_name: Dict[str, Dict[str, Any]] = {}
        for _, row in arena_df.iterrows():
            name = str(row.get(arena_name_col, ""))
            if name:
                arena_by_name[self._normalize_arena_name(name)] = {
                    "original_name": name,
                    "elo": row.get(arena_elo_col) if arena_elo_col else None,
                    "rank": row.get(arena_rank_col) if arena_rank_col else None,
                }
        
        # Match and enrich
        enriched_count = 0
        gap_count = 0
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            
            # Try to match
            matched_slug, match_status, match_score = self._match_to_catalog(
                slug.split("/", 1)[1] if "/" in slug else slug,
                list(arena_by_name.keys())
            )
            
            if match_status != "unmatched":
                arena_info = arena_by_name.get(matched_slug, {})
                
                df.at[idx, "arena_elo_overall"] = arena_info.get("elo")
                df.at[idx, "arena_rank_overall"] = arena_info.get("rank")
                df.at[idx, "arena_match_status"] = match_status
                df.at[idx, "arena_matched_name"] = arena_info.get("original_name")
                df.at[idx, "arena_match_score"] = match_score
                df.at[idx, "arena_source_name"] = self.source_name
                df.at[idx, "arena_source_url"] = self.source_url
                df.at[idx, "arena_retrieved_at"] = now_iso
                
                enriched_count += 1
            else:
                df.at[idx, "arena_match_status"] = "unmatched"
                gap_count += 1
                result.data_gaps.append({
                    "slug": slug,
                    "source": "lmsys_arena",
                    "reason": "No matching model found in Arena leaderboard",
                })
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = gap_count
        
        self.logger.info(
            "Arena enrichment: matched %d models, %d unmatched",
            enriched_count, gap_count
        )
        
        return df

