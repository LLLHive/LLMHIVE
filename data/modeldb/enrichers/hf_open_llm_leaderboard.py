"""
HuggingFace Open LLM Leaderboard Enricher

Fetches benchmark results from the HuggingFace Open LLM Leaderboard.
Uses HuggingFace datasets with local caching for reliability.
"""
from __future__ import annotations

import difflib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)

# HuggingFace Open LLM Leaderboard data sources
# Note: The leaderboard has migrated to v2 with new evaluation framework
HF_LEADERBOARD_DATASET = "open-llm-leaderboard/contents"  # New v2 leaderboard
HF_LEADERBOARD_DATASET_V1 = "open-llm-leaderboard/results"  # Legacy v1
HF_LEADERBOARD_URL = "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"

# Fallback: Direct API endpoint
HF_LEADERBOARD_API = "https://huggingface.co/api/spaces/open-llm-leaderboard/open_llm_leaderboard"

# Cache settings
DEFAULT_CACHE_DIR = Path(".cache/llmhive_modeldb/hf_ollb")
CACHE_TTL_HOURS = 24  # Cache validity period


class HFLeaderboardEnricher(BaseEnricher):
    """
    Enricher that fetches HuggingFace Open LLM Leaderboard metrics.
    
    Adds columns for standard benchmarks:
    - hf_ollb_mmlu
    - hf_ollb_arc_challenge
    - hf_ollb_hellaswag
    - hf_ollb_truthfulqa
    - hf_ollb_winogrande
    - hf_ollb_gsm8k
    - hf_ollb_avg
    - hf_ollb_rank_overall
    - hf_ollb_match_status
    - hf_ollb_matched_name
    - hf_ollb_match_score
    - hf_ollb_retrieved_at
    - hf_ollb_source_url
    """
    
    name = "hf_open_llm_leaderboard"
    source_name = "HuggingFace Open LLM Leaderboard"
    source_url = HF_LEADERBOARD_URL
    
    # Known benchmark columns and their mappings
    BENCHMARK_MAPPINGS = {
        # V2 leaderboard column names
        "mmlu": "hf_ollb_mmlu",
        "mmlu_pro": "hf_ollb_mmlu_pro",
        "arc_challenge": "hf_ollb_arc_challenge",
        "arc": "hf_ollb_arc_challenge",
        "hellaswag": "hf_ollb_hellaswag",
        "truthfulqa": "hf_ollb_truthfulqa",
        "truthfulqa_mc2": "hf_ollb_truthfulqa",
        "winogrande": "hf_ollb_winogrande",
        "gsm8k": "hf_ollb_gsm8k",
        "math": "hf_ollb_math",
        "gpqa": "hf_ollb_gpqa",
        "musr": "hf_ollb_musr",
        "bbh": "hf_ollb_bbh",
        "ifeval": "hf_ollb_ifeval",
        "average": "hf_ollb_avg",
        "avg": "hf_ollb_avg",
        "mean": "hf_ollb_avg",
    }
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self._leaderboard_data: Optional[pd.DataFrame] = None
    
    def _get_cache_path(self) -> Path:
        """Get the path for cached leaderboard data."""
        return self._cache_dir / "hf_leaderboard.parquet"
    
    def _get_cache_metadata_path(self) -> Path:
        """Get the path for cache metadata."""
        return self._cache_dir / "hf_cache_metadata.json"
    
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
            
            self.logger.info("Using cached HF leaderboard data (%.1f hours old)", age_hours)
            return True
            
        except Exception as e:
            self.logger.warning("Cache metadata invalid: %s", e)
            return False
    
    def _load_from_cache(self) -> Optional[pd.DataFrame]:
        """Load leaderboard data from cache."""
        try:
            cache_path = self._get_cache_path()
            return pd.read_parquet(cache_path)
        except Exception as e:
            self.logger.warning("Failed to load cache: %s", e)
            return None
    
    def _save_to_cache(self, df: pd.DataFrame) -> None:
        """Save leaderboard data to cache."""
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
            
            self.logger.info("Cached HF leaderboard data: %d rows", len(df))
            
        except Exception as e:
            self.logger.warning("Failed to cache HF leaderboard data: %s", e)
    
    def _fetch_from_hf_datasets_v2(self) -> Optional[pd.DataFrame]:
        """Try to fetch leaderboard data from v2 dataset."""
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading HF Leaderboard (v2) from datasets...")
            ds = load_dataset(HF_LEADERBOARD_DATASET, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from HF Leaderboard v2", len(df))
            return df
            
        except Exception as e:
            self.logger.debug("HF datasets v2 fetch failed: %s", e)
            return None
    
    def _fetch_from_hf_datasets_v1(self) -> Optional[pd.DataFrame]:
        """Fallback to v1 dataset."""
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading HF Leaderboard (v1) from datasets...")
            ds = load_dataset(HF_LEADERBOARD_DATASET_V1, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from HF Leaderboard v1", len(df))
            return df
            
        except Exception as e:
            self.logger.debug("HF datasets v1 fetch failed: %s", e)
            return None
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _fetch_from_api(self) -> Optional[pd.DataFrame]:
        """Try to fetch from HuggingFace Spaces API."""
        try:
            # This is a fallback - HF Spaces API structure may vary
            self.logger.info("Trying HF Leaderboard API fallback...")
            
            # Note: This may need adjustment based on actual API structure
            response = requests.get(
                HF_LEADERBOARD_API,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    self.logger.info("Loaded %d models from HF API", len(df))
                    return df
            
            return None
            
        except Exception as e:
            self.logger.debug("HF API fallback failed: %s", e)
            return None
    
    def _fetch_leaderboard_data(self) -> pd.DataFrame:
        """
        Fetch leaderboard data with caching.
        
        Tries multiple sources in order of preference.
        """
        # Check cache first
        if self._is_cache_valid():
            cached = self._load_from_cache()
            if cached is not None:
                return cached
        
        # Check if datasets library is available
        datasets_available = True
        try:
            import datasets
        except ImportError:
            datasets_available = False
            self.logger.warning("datasets library not installed - HF leaderboard enrichment limited")
        
        df = None
        
        if datasets_available:
            # Try v2 dataset first
            df = self._fetch_from_hf_datasets_v2()
            
            # Fallback to v1
            if df is None:
                df = self._fetch_from_hf_datasets_v1()
        
        # Final fallback: API
        if df is None:
            df = self._fetch_from_api()
        
        if df is None or len(df) == 0:
            raise RuntimeError("Failed to fetch HF Leaderboard data from all sources")
        
        # Cache the result
        self._save_to_cache(df)
        
        return df
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize a model name for matching.
        
        Deterministic normalization for fuzzy matching.
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
            r"-?hf$",
            r"-?gguf$",
            r"-?gptq$",
            r"-?awq$",
            r"-?fp16$",
            r"-?bf16$",
            r"-?base$",
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
        """
        if not s1 or not s2:
            return 0.0
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    def _match_model(
        self,
        slug: str,
        hf_lookup: Dict[str, Dict[str, Any]],
    ) -> Tuple[str, str, float, Optional[str]]:
        """
        Match a catalog slug to HF leaderboard models.
        
        Returns:
            (match_key, match_status, match_score, original_hf_name)
        """
        if not slug:
            return "", "unmatched", 0.0, None
        
        slug_normalized = self._normalize_name(slug)
        
        # Try exact match
        if slug_normalized in hf_lookup:
            return slug_normalized, "exact", 1.0, hf_lookup[slug_normalized].get("original_name")
        
        # Try with full slug (including provider)
        if "/" in slug:
            full_normalized = self._normalize_name(slug.replace("/", "-"))
            if full_normalized in hf_lookup:
                return full_normalized, "exact", 1.0, hf_lookup[full_normalized].get("original_name")
        
        # Heuristic matching
        best_match = ""
        best_score = 0.0
        best_name = None
        
        for hf_key, hf_info in hf_lookup.items():
            # Calculate fuzzy score
            score = self._fuzzy_score(slug_normalized, hf_key)
            
            # Boost score for containment
            if len(slug_normalized) >= 4 and len(hf_key) >= 4:
                if slug_normalized in hf_key or hf_key in slug_normalized:
                    containment_score = min(len(slug_normalized), len(hf_key)) / max(len(slug_normalized), len(hf_key))
                    score = max(score, containment_score * 0.9)
            
            if score > best_score:
                best_score = score
                best_match = hf_key
                best_name = hf_info.get("original_name")
        
        if best_score >= 0.7:
            return best_match, "heuristic", round(best_score, 3), best_name
        
        return "", "unmatched", 0.0, None
    
    def _identify_columns(self, hf_df: pd.DataFrame) -> Dict[str, Any]:
        """Identify key columns in the HF leaderboard DataFrame."""
        columns = {
            "model_name": None,
            "benchmarks": {},
            "rank": None,
        }
        
        for col in hf_df.columns:
            col_lower = col.lower()
            
            # Model name column
            if columns["model_name"] is None:
                if col_lower in ["model", "model_name", "name", "fullname"]:
                    columns["model_name"] = col
                elif "model" in col_lower:
                    columns["model_name"] = col
            
            # Rank column
            if columns["rank"] is None:
                if col_lower in ["rank", "ranking", "position", "#"]:
                    columns["rank"] = col
            
            # Map benchmark columns
            for benchmark_key, our_col in self.BENCHMARK_MAPPINGS.items():
                if benchmark_key in col_lower.replace(" ", "_").replace("-", "_"):
                    if our_col not in columns["benchmarks"]:
                        columns["benchmarks"][col] = our_col
        
        # Default to first column for model name
        if columns["model_name"] is None and len(hf_df.columns) > 0:
            columns["model_name"] = hf_df.columns[0]
        
        return columns
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fetch HF Leaderboard data and enrich the catalog."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would fetch HF Leaderboard data")
            result.warnings.append("Dry run - no API calls made")
            return df
        
        try:
            hf_df = self._fetch_leaderboard_data()
        except Exception as e:
            result.warnings.append(f"Failed to fetch HF Leaderboard data: {e}")
            self.logger.warning("HF Leaderboard fetch failed: %s", e)
            # Continue without HF data - don't fail the enricher
            return df
        
        # Initialize new columns
        now_iso = datetime.now(timezone.utc).isoformat()
        
        base_columns = [
            "hf_ollb_mmlu",
            "hf_ollb_arc_challenge",
            "hf_ollb_hellaswag",
            "hf_ollb_truthfulqa",
            "hf_ollb_winogrande",
            "hf_ollb_gsm8k",
            "hf_ollb_avg",
            "hf_ollb_rank_overall",
            "hf_ollb_match_status",
            "hf_ollb_matched_name",
            "hf_ollb_match_score",
            "hf_ollb_asof_date",
            "hf_ollb_source_name",
            "hf_ollb_source_url",
            "hf_ollb_retrieved_at",
        ]
        
        for col in base_columns:
            if col not in df.columns:
                df[col] = None
        
        # Identify HF columns
        hf_cols = self._identify_columns(hf_df)
        name_col = hf_cols["model_name"]
        rank_col = hf_cols["rank"]
        benchmark_cols = hf_cols["benchmarks"]
        
        self.logger.info(
            "HF Leaderboard columns: name=%s, rank=%s, benchmarks=%d",
            name_col, rank_col, len(benchmark_cols)
        )
        
        # Build HF lookup by normalized name
        hf_lookup: Dict[str, Dict[str, Any]] = {}
        
        for idx, row in hf_df.iterrows():
            original_name = str(row.get(name_col, "")) if name_col else ""
            if not original_name or original_name == "nan":
                continue
            
            normalized = self._normalize_name(original_name)
            if not normalized:
                continue
            
            entry = {
                "original_name": original_name,
                "rank": idx + 1 if rank_col is None else row.get(rank_col),
            }
            
            # Map benchmark values
            for hf_col, our_col in benchmark_cols.items():
                val = row.get(hf_col)
                if pd.notna(val):
                    entry[our_col] = val
            
            # Calculate average if not present
            if "hf_ollb_avg" not in entry:
                benchmark_values = [
                    v for k, v in entry.items()
                    if k.startswith("hf_ollb_") and k != "hf_ollb_avg" and isinstance(v, (int, float))
                ]
                if benchmark_values:
                    entry["hf_ollb_avg"] = sum(benchmark_values) / len(benchmark_values)
            
            hf_lookup[normalized] = entry
        
        self.logger.info("Built HF lookup with %d unique models", len(hf_lookup))
        
        # Match and enrich
        enriched_count = 0
        gap_count = 0
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            
            # Match to HF leaderboard
            match_key, match_status, match_score, matched_name = self._match_model(
                slug, hf_lookup
            )
            
            # Update match status regardless
            df.at[idx, "hf_ollb_match_status"] = match_status
            df.at[idx, "hf_ollb_match_score"] = match_score if match_status != "unmatched" else None
            
            if match_status != "unmatched":
                hf_info = hf_lookup.get(match_key, {})
                
                # Copy benchmark scores
                for our_col in set(self.BENCHMARK_MAPPINGS.values()):
                    if our_col in hf_info:
                        if our_col not in df.columns:
                            df[our_col] = None
                        df.at[idx, our_col] = hf_info[our_col]
                
                # Set rank
                rank_val = hf_info.get("rank")
                if pd.notna(rank_val):
                    df.at[idx, "hf_ollb_rank_overall"] = rank_val
                
                df.at[idx, "hf_ollb_matched_name"] = matched_name
                df.at[idx, "hf_ollb_source_name"] = self.source_name
                df.at[idx, "hf_ollb_source_url"] = self.source_url
                df.at[idx, "hf_ollb_retrieved_at"] = now_iso
                df.at[idx, "hf_ollb_asof_date"] = now_iso[:10]
                
                enriched_count += 1
            else:
                gap_count += 1
                result.data_gaps.append({
                    "slug": slug,
                    "source": "hf_open_llm_leaderboard",
                    "field": "hf_ollb_mmlu",
                    "reason": "unmatched",
                    "note": f"No matching model found in HF Leaderboard for '{slug}'",
                    "retrieved_at": now_iso,
                })
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = gap_count
        
        self.logger.info(
            "HF Leaderboard enrichment complete: matched %d models (%.1f%%), %d unmatched",
            enriched_count,
            100.0 * enriched_count / len(df) if len(df) > 0 else 0,
            gap_count,
        )
        
        return df
