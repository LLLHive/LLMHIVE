"""
HuggingFace Open LLM Leaderboard Enricher

Fetches benchmark results from the HuggingFace Open LLM Leaderboard.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)

# HuggingFace Open LLM Leaderboard data sources
HF_LEADERBOARD_DATASET = "open-llm-leaderboard/results"
HF_LEADERBOARD_URL = "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"


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
    """
    
    name = "hf_open_llm_leaderboard"
    source_name = "HuggingFace Open LLM Leaderboard"
    source_url = HF_LEADERBOARD_URL
    
    # Known benchmark columns in the leaderboard
    BENCHMARK_COLUMNS = [
        ("mmlu", "hf_ollb_mmlu"),
        ("arc_challenge", "hf_ollb_arc_challenge"),
        ("arc", "hf_ollb_arc_challenge"),  # alias
        ("hellaswag", "hf_ollb_hellaswag"),
        ("truthfulqa", "hf_ollb_truthfulqa"),
        ("winogrande", "hf_ollb_winogrande"),
        ("gsm8k", "hf_ollb_gsm8k"),
        ("average", "hf_ollb_avg"),
        ("avg", "hf_ollb_avg"),  # alias
    ]
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self._leaderboard_data: Optional[pd.DataFrame] = None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _fetch_leaderboard_data(self) -> pd.DataFrame:
        """
        Fetch Open LLM Leaderboard data.
        """
        try:
            from datasets import load_dataset
            
            self.logger.info("Loading HF Leaderboard data from datasets...")
            ds = load_dataset(HF_LEADERBOARD_DATASET, split="train")
            df = ds.to_pandas()
            self.logger.info("Loaded %d models from HF Leaderboard", len(df))
            return df
        except ImportError:
            self.logger.warning("datasets library not available")
            raise
        except Exception as e:
            self.logger.warning("HuggingFace datasets failed: %s", e)
            raise
    
    def _normalize_hf_name(self, name: str) -> str:
        """Normalize HuggingFace model name for matching."""
        if not name:
            return ""
        name = name.lower().strip()
        # Remove org prefix if present (e.g., "meta-llama/Llama-2-7b" -> "llama-2-7b")
        if "/" in name:
            name = name.split("/", 1)[1]
        # Normalize separators
        name = name.replace("_", "-").replace(" ", "-")
        # Remove common suffixes
        name = re.sub(r"[-_]?(chat|instruct|hf|gguf|gptq|awq|fp16|bf16)$", "", name)
        return name
    
    def _match_to_catalog(
        self,
        hf_name: str,
        catalog_slugs: List[str],
    ) -> Tuple[str, str, float]:
        """
        Match an HF model name to a catalog slug.
        
        Returns:
            (matched_slug, match_status, match_score)
        """
        if not hf_name:
            return "", "unmatched", 0.0
        
        hf_normalized = self._normalize_hf_name(hf_name)
        
        # Try exact match
        for slug in catalog_slugs:
            slug_normalized = self._normalize_hf_name(slug)
            if hf_normalized == slug_normalized:
                return slug, "exact", 1.0
        
        # Heuristic matching
        best_match = ""
        best_score = 0.0
        
        for slug in catalog_slugs:
            slug_normalized = self._normalize_hf_name(slug)
            
            # Check containment
            if hf_normalized in slug_normalized or slug_normalized in hf_normalized:
                score = len(set(hf_normalized) & set(slug_normalized)) / max(
                    len(hf_normalized), len(slug_normalized), 1
                )
                if score > best_score:
                    best_score = score
                    best_match = slug
        
        if best_score >= 0.6:
            return best_match, "heuristic", best_score
        
        return "", "unmatched", 0.0
    
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
        
        new_columns = [
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
            "hf_ollb_source_name",
            "hf_ollb_source_url",
            "hf_ollb_retrieved_at",
        ]
        
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        # Get catalog slugs for matching
        catalog_slugs = df["openrouter_slug"].dropna().tolist()
        
        # Identify HF columns
        hf_name_col = None
        for col in hf_df.columns:
            col_lower = col.lower()
            if "model" in col_lower or col_lower == "name":
                hf_name_col = col
                break
        
        if not hf_name_col:
            hf_name_col = hf_df.columns[0]
        
        self.logger.info("HF Leaderboard model name column: %s", hf_name_col)
        
        # Build HF lookup by normalized name
        hf_by_name: Dict[str, Dict[str, Any]] = {}
        for _, row in hf_df.iterrows():
            name = str(row.get(hf_name_col, ""))
            if name:
                normalized = self._normalize_hf_name(name)
                entry = {"original_name": name}
                
                # Map benchmark columns
                for hf_col, our_col in self.BENCHMARK_COLUMNS:
                    for df_col in hf_df.columns:
                        if hf_col in df_col.lower():
                            value = row.get(df_col)
                            if pd.notna(value):
                                entry[our_col] = value
                            break
                
                hf_by_name[normalized] = entry
        
        # Match and enrich
        enriched_count = 0
        gap_count = 0
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            slug_normalized = self._normalize_hf_name(slug)
            
            # Try direct match first
            hf_info = hf_by_name.get(slug_normalized)
            match_status = "exact" if hf_info else "unmatched"
            match_score = 1.0 if hf_info else 0.0
            
            if not hf_info:
                # Try heuristic match
                for hf_name, info in hf_by_name.items():
                    if slug_normalized in hf_name or hf_name in slug_normalized:
                        hf_info = info
                        match_status = "heuristic"
                        match_score = 0.7
                        break
            
            if hf_info:
                # Copy benchmark scores
                for _, our_col in self.BENCHMARK_COLUMNS:
                    if our_col in hf_info:
                        df.at[idx, our_col] = hf_info[our_col]
                
                df.at[idx, "hf_ollb_match_status"] = match_status
                df.at[idx, "hf_ollb_matched_name"] = hf_info.get("original_name")
                df.at[idx, "hf_ollb_source_name"] = self.source_name
                df.at[idx, "hf_ollb_source_url"] = self.source_url
                df.at[idx, "hf_ollb_retrieved_at"] = now_iso
                
                enriched_count += 1
            else:
                df.at[idx, "hf_ollb_match_status"] = "unmatched"
                gap_count += 1
                result.data_gaps.append({
                    "slug": slug,
                    "source": "hf_open_llm_leaderboard",
                    "reason": "No matching model found in HF Leaderboard",
                })
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = gap_count
        
        self.logger.info(
            "HF Leaderboard enrichment: matched %d models, %d unmatched",
            enriched_count, gap_count
        )
        
        return df

