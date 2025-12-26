"""
LMSYS Chatbot Arena Enricher

Fetches Elo ratings and rankings from the LMSYS Chatbot Arena leaderboard.
Uses HuggingFace datasets with local caching for reliability.
"""
from __future__ import annotations

import difflib
import hashlib
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
ARENA_HF_DATASET = "lmsys/chatbot_arena_leaderboard"
ARENA_LEADERBOARD_URL = "https://huggingface.co/datasets/lmsys/chatbot_arena_leaderboard"

# Fallback CSV endpoint (HuggingFace raw file URL)
ARENA_LEADERBOARD_CSV = "https://huggingface.co/datasets/lmsys/chatbot_arena_leaderboard/resolve/main/leaderboard_table.csv"

# Alternative: lmarena.ai API endpoint (if available)
ARENA_API_FALLBACK = "https://lmarena.ai/api/arena/leaderboard"

# Cache settings
DEFAULT_CACHE_DIR = Path(".cache/llmhive_modeldb/arena")
CACHE_TTL_HOURS = 24  # Cache validity period


class LMSYSArenaEnricher(BaseEnricher):
    """
    Enricher that fetches LMSYS Chatbot Arena Elo ratings.
    
    Adds columns:
    - arena_elo_overall
    - arena_rank_overall
    - arena_elo_<category> (for available splits like coding, long, etc.)
    - arena_match_status (exact/heuristic/unmatched)
    - arena_matched_name
    - arena_match_score
    - arena_asof_date
    - arena_retrieved_at
    - arena_source_url
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
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._arena_data: Optional[pd.DataFrame] = None
    
    def _get_cache_path(self) -> Path:
        """Get the path for cached arena data."""
        return self._cache_dir / "arena_leaderboard.parquet"
    
    def _get_cache_metadata_path(self) -> Path:
        """Get the path for cache metadata."""
        return self._cache_dir / "arena_cache_metadata.json"
    
    def _is_cache_valid(self) -> bool:
        """Check if cache exists and is still valid."""
        cache_path = self._get_cache_path()
        meta_path = self._get_cache_metadata_path()
        
        if not cache_path.exists() or not meta_path.exists():
            return False
        
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            cached_at = datetime.fromisoformat(meta.get("cached_at", ""))
            now = datetime.now(timezone.utc)
            age_hours = (now - cached_at).total_seconds() / 3600
            
            if age_hours > CACHE_TTL_HOURS:
                self.logger.info("Cache expired (%.1f hours old)", age_hours)
                return False
            
            self.logger.info("Using cached data (%.1f hours old)", age_hours)
            return True
            
        except Exception as e:
            self.logger.warning("Cache metadata invalid: %s", e)
            return False
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        """Load arena data from cache."""
        try:
            cache_path = self._get_cache_path()
            return pd.read_parquet(cache_path)
        except Exception as e:
            self.logger.warning("Failed to load cache: %s", e)
            return None
    
    def _save_to_cache(self, df: pd.DataFrame) -> None:
        """Save arena data to cache."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save data
            cache_path = self._get_cache_path()
            df.to_parquet(cache_path, index=False)
            
            # Save metadata
            meta_path = self._get_cache_metadata_path()
            meta = {
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "source": self.source_url,
                "row_count": len(df),
                "columns": list(df.columns),
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            
            self.logger.info("Cached arena data: %d rows", len(df))
            
        except Exception as e:
            self.logger.warning("Failed to cache arena data: %s", e)
    
    def _fetch_from_hf_datasets(self) -> Optional[pd.DataFrame]:
        """Try to fetch arena data using HuggingFace datasets library."""
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading Arena data from HuggingFace datasets...")
            ds = load_dataset(ARENA_HF_DATASET, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from Arena via HF datasets", len(df))
            return df
            
        except ImportError:
            self.logger.warning("datasets library not available")
            return None
        except Exception as e:
            self.logger.warning("HuggingFace datasets failed: %s", e)
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _fetch_from_csv(self) -> Optional[pd.DataFrame]:
        """Fallback: fetch arena data from CSV endpoint."""
        try:
            import io
            
            self.logger.info("Fetching Arena data from CSV endpoint...")
            response = requests.get(ARENA_LEADERBOARD_CSV, timeout=60)
            response.raise_for_status()
            
            df = pd.read_csv(io.StringIO(response.text))
            self.logger.info("Loaded %d models from Arena CSV", len(df))
            return df
            
        except Exception as e:
            self.logger.warning("CSV fetch failed: %s", e)
            return None
    
    def _fetch_arena_data(self) -> pd.DataFrame:
        """
        Fetch Arena leaderboard data with caching.
        
        Tries multiple sources in order of reliability.
        """
        # Check cache first
        if self._is_cache_valid():
            cached = self._load_from_cache()
            if cached is not None:
                return cached
        
        # Try HuggingFace datasets
        df = self._fetch_from_hf_datasets()
        
        # Fallback to CSV
        if df is None:
            df = self._fetch_from_csv()
        
        if df is None:
            raise RuntimeError("Failed to fetch Arena data from all sources")
        
        # Cache the result
        self._save_to_cache(df)
        
        return df
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize a model name for matching.
        
        Deterministic normalization:
        - Lowercase
        - Remove punctuation except hyphens
        - Normalize spaces/underscores to hyphens
        - Strip provider prefixes
        - Remove common suffixes
        """
        if not name:
            return ""
        
        name = str(name).lower().strip()
        
        # Remove org/provider prefix
        if "/" in name:
            name = name.split("/", 1)[1]
        
        # Normalize separators
        name = name.replace("_", "-").replace(" ", "-")
        
        # Remove punctuation except hyphens
        name = re.sub(r"[^\w\-]", "", name)
        
        # Remove common suffixes
        suffixes = [
            r"-?chat$",
            r"-?instruct$",
            r"-?turbo$",
            r"-?preview$",
            r"-?beta$",
            r"-?alpha$",
            r"-?exp$",
            r"-?hf$",
            r"-?online$",
            r"-?latest$",
            r"-?free$",
        ]
        for suffix in suffixes:
            name = re.sub(suffix, "", name, flags=re.IGNORECASE)
        
        # Normalize multiple hyphens
        name = re.sub(r"-+", "-", name).strip("-")
        
        return name
    
    def _fuzzy_score(self, s1: str, s2: str) -> float:
        """
        Compute fuzzy matching score between two strings.
        
        Uses difflib.SequenceMatcher for pure Python fuzzy matching.
        Returns score 0.0 to 1.0.
        """
        if not s1 or not s2:
            return 0.0
        
        # Use SequenceMatcher for similarity ratio
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    def _match_model(
        self,
        slug: str,
        arena_names: Dict[str, Dict[str, Any]],
    ) -> Tuple[str, str, float, Optional[str]]:
        """
        Match a catalog slug to Arena model names.
        
        Returns:
            (match_key, match_status, match_score, original_arena_name)
        """
        if not slug:
            return "", "unmatched", 0.0, None
        
        slug_normalized = self._normalize_name(slug)
        
        # Try exact match first
        if slug_normalized in arena_names:
            return slug_normalized, "exact", 1.0, arena_names[slug_normalized].get("original_name")
        
        # Try matching just the model part (after provider/)
        model_part = slug.split("/", 1)[1] if "/" in slug else slug
        model_normalized = self._normalize_name(model_part)
        
        if model_normalized in arena_names:
            return model_normalized, "exact", 1.0, arena_names[model_normalized].get("original_name")
        
        # Heuristic matching with fuzzy scoring
        best_match = ""
        best_score = 0.0
        best_arena_name = None
        
        for arena_key, arena_info in arena_names.items():
            # Try multiple matching strategies
            score = 0.0
            
            # Strategy 1: Direct fuzzy match
            score = max(score, self._fuzzy_score(slug_normalized, arena_key))
            score = max(score, self._fuzzy_score(model_normalized, arena_key))
            
            # Strategy 2: Check containment with scoring
            if len(model_normalized) >= 4 and len(arena_key) >= 4:
                if model_normalized in arena_key or arena_key in model_normalized:
                    containment_score = min(len(model_normalized), len(arena_key)) / max(len(model_normalized), len(arena_key))
                    score = max(score, containment_score * 0.9)  # Slightly penalize containment matches
            
            if score > best_score:
                best_score = score
                best_match = arena_key
                best_arena_name = arena_info.get("original_name")
        
        # Threshold for accepting heuristic match
        if best_score >= 0.7:
            return best_match, "heuristic", round(best_score, 3), best_arena_name
        
        return "", "unmatched", 0.0, None
    
    def _identify_columns(self, arena_df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Identify key columns in the Arena DataFrame."""
        columns = {
            "model_name": None,
            "elo": None,
            "rank": None,
            "categories": [],  # Additional category elo columns
        }
        
        for col in arena_df.columns:
            col_lower = col.lower()
            
            # Model name column
            if columns["model_name"] is None:
                if col_lower in ["model", "model_name", "name"]:
                    columns["model_name"] = col
                elif "model" in col_lower and "name" not in col_lower:
                    columns["model_name"] = col
            
            # Main elo column
            if columns["elo"] is None:
                if col_lower in ["elo", "rating", "elo_rating", "arena_score"]:
                    columns["elo"] = col
                elif col_lower == "overall" or "overall" in col_lower and "elo" in col_lower:
                    columns["elo"] = col
            
            # Rank column
            if columns["rank"] is None:
                if col_lower in ["rank", "ranking", "position"]:
                    columns["rank"] = col
            
            # Category elo columns
            if "elo" in col_lower or "rating" in col_lower:
                if col not in [columns["elo"]]:
                    columns["categories"].append(col)
        
        # Default to first column for model name
        if columns["model_name"] is None and len(arena_df.columns) > 0:
            columns["model_name"] = arena_df.columns[0]
        
        return columns
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fetch Arena data and enrich the catalog."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would fetch LMSYS Arena data")
            result.warnings.append("Dry run - no API calls made")
            return df
        
        try:
            arena_df = self._fetch_arena_data()
        except Exception as e:
            result.warnings.append(f"Failed to fetch Arena data: {e}")
            self.logger.warning("Arena fetch failed: %s", e)
            # Continue without Arena data - don't fail the enricher
            return df
        
        # Initialize new columns
        now_iso = datetime.now(timezone.utc).isoformat()
        
        new_columns = [
            "arena_elo_overall",
            "arena_rank_overall",
            "arena_match_status",
            "arena_matched_name",
            "arena_match_score",
            "arena_asof_date",
            "arena_source_name",
            "arena_source_url",
            "arena_retrieved_at",
        ]
        
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        # Identify Arena columns
        arena_cols = self._identify_columns(arena_df)
        name_col = arena_cols["model_name"]
        elo_col = arena_cols["elo"]
        rank_col = arena_cols["rank"]
        
        self.logger.info(
            "Arena columns identified: name=%s, elo=%s, rank=%s, categories=%d",
            name_col, elo_col, rank_col, len(arena_cols["categories"])
        )
        
        # Build Arena lookup by normalized name
        arena_by_name: Dict[str, Dict[str, Any]] = {}
        
        for idx, row in arena_df.iterrows():
            original_name = str(row.get(name_col, "")) if name_col else ""
            if not original_name or original_name == "nan":
                continue
            
            normalized = self._normalize_name(original_name)
            if not normalized:
                continue
            
            entry = {
                "original_name": original_name,
                "elo": row.get(elo_col) if elo_col else None,
                "rank": idx + 1 if rank_col is None else row.get(rank_col),  # Use index as rank if not available
            }
            
            # Add category scores
            for cat_col in arena_cols["categories"]:
                val = row.get(cat_col)
                if pd.notna(val):
                    entry[cat_col] = val
            
            arena_by_name[normalized] = entry
        
        self.logger.info("Built Arena lookup with %d unique models", len(arena_by_name))
        
        # Match and enrich
        enriched_count = 0
        gap_count = 0
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            
            # Match to Arena
            match_key, match_status, match_score, matched_name = self._match_model(
                slug, arena_by_name
            )
            
            # Update match status regardless
            df.at[idx, "arena_match_status"] = match_status
            df.at[idx, "arena_match_score"] = match_score if match_status != "unmatched" else None
            
            if match_status != "unmatched":
                arena_info = arena_by_name.get(match_key, {})
                
                # Set elo and rank
                elo_val = arena_info.get("elo")
                if pd.notna(elo_val):
                    df.at[idx, "arena_elo_overall"] = elo_val
                
                rank_val = arena_info.get("rank")
                if pd.notna(rank_val):
                    df.at[idx, "arena_rank_overall"] = rank_val
                
                df.at[idx, "arena_matched_name"] = matched_name
                df.at[idx, "arena_source_name"] = self.source_name
                df.at[idx, "arena_source_url"] = self.source_url
                df.at[idx, "arena_retrieved_at"] = now_iso
                df.at[idx, "arena_asof_date"] = now_iso[:10]  # Date portion
                
                # Add category elo columns if they exist
                for cat_col in arena_cols["categories"]:
                    cat_val = arena_info.get(cat_col)
                    if pd.notna(cat_val):
                        safe_col = f"arena_{cat_col.lower().replace(' ', '_')}"
                        if safe_col not in df.columns:
                            df[safe_col] = None
                        df.at[idx, safe_col] = cat_val
                
                enriched_count += 1
            else:
                gap_count += 1
                result.data_gaps.append({
                    "slug": slug,
                    "source": "lmsys_arena",
                    "field": "arena_elo_overall",
                    "reason": "unmatched",
                    "note": f"No matching model found in Arena leaderboard for '{slug}'",
                    "retrieved_at": now_iso,
                })
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = gap_count
        
        self.logger.info(
            "Arena enrichment complete: matched %d models (%.1f%%), %d unmatched",
            enriched_count,
            100.0 * enriched_count / len(df) if len(df) > 0 else 0,
            gap_count,
        )
        
        return df
