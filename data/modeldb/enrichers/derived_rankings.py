"""
Derived Rankings Enricher

Computes rankings from existing ModelDB fields (no external data needed).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)


class DerivedRankingsEnricher(BaseEnricher):
    """
    Enricher that computes derived rankings from existing fields.
    
    Adds columns:
    - rank_context_length_desc (1 = largest context)
    - rank_cost_input_asc (1 = cheapest input)
    - rank_cost_output_asc (1 = cheapest output)
    - rank_tool_support (based on function calling / tools)
    - rank_multimodal_support (text-only < vision < vision+audio)
    - derived_rank_formula_notes (explains all derivations)
    """
    
    name = "derived_rankings"
    source_name = "Derived from ModelDB fields"
    source_url = ""
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
    
    def _compute_multimodal_score(self, row: pd.Series) -> int:
        """
        Compute a multimodal support score.
        
        Returns:
            0 = text-only
            1 = vision support
            2 = vision + audio or more
        """
        modalities = str(row.get("modalities", "") or "").lower()
        architecture = str(row.get("architecture", "") or "").lower()
        supports_vision = row.get("supports_vision", False)
        
        score = 0
        
        # Check for vision
        if supports_vision or "vision" in modalities or "image" in modalities:
            score = 1
        
        # Check for audio
        if "audio" in modalities or "speech" in modalities:
            score = 2
        
        return score
    
    def _compute_tool_score(self, row: pd.Series) -> int:
        """
        Compute a tool support score.
        
        Returns:
            0 = no tool support
            1 = function calling
            2 = structured output + function calling
        """
        supports_fc = row.get("supports_function_calling", False)
        structured_output = row.get("structured_output_support", False)
        
        if supports_fc is True or supports_fc == "True" or supports_fc == 1:
            if structured_output is True or structured_output == "True" or structured_output == 1:
                return 2
            return 1
        return 0
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Compute derived rankings from existing fields."""
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Initialize columns
        new_columns = [
            "rank_context_length_desc",
            "rank_cost_input_asc",
            "rank_cost_output_asc",
            "rank_tool_support",
            "rank_multimodal_support",
            "multimodal_score",
            "tool_score",
            "derived_rank_source_name",
            "derived_rank_retrieved_at",
            "derived_rank_formula_notes",
        ]
        
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        # Compute scores first
        df["_context_tokens"] = pd.to_numeric(
            df.get("max_context_tokens", 0), errors="coerce"
        ).fillna(0)
        
        df["_price_input"] = pd.to_numeric(
            df.get("price_input_usd_per_1m", 999999), errors="coerce"
        ).fillna(999999)
        
        df["_price_output"] = pd.to_numeric(
            df.get("price_output_usd_per_1m", 999999), errors="coerce"
        ).fillna(999999)
        
        # Compute multimodal and tool scores
        df["multimodal_score"] = df.apply(self._compute_multimodal_score, axis=1)
        df["tool_score"] = df.apply(self._compute_tool_score, axis=1)
        
        # Rank by context length (descending - higher is better)
        df["rank_context_length_desc"] = df["_context_tokens"].rank(
            ascending=False, method="min"
        ).astype(int)
        
        # Rank by input cost (ascending - lower is better)
        df["rank_cost_input_asc"] = df["_price_input"].rank(
            ascending=True, method="min"
        ).astype(int)
        
        # Rank by output cost (ascending - lower is better)
        df["rank_cost_output_asc"] = df["_price_output"].rank(
            ascending=True, method="min"
        ).astype(int)
        
        # Rank by tool support (descending - higher is better)
        df["rank_tool_support"] = df["tool_score"].rank(
            ascending=False, method="min"
        ).astype(int)
        
        # Rank by multimodal support (descending - higher is better)
        df["rank_multimodal_support"] = df["multimodal_score"].rank(
            ascending=False, method="min"
        ).astype(int)
        
        # Clean up temp columns
        df.drop(columns=["_context_tokens", "_price_input", "_price_output"], inplace=True)
        
        # Add provenance and formula notes
        formula_notes = """
Derived Rankings (computed from ModelDB fields):
- rank_context_length_desc: Ranked by max_context_tokens DESC (1 = largest)
- rank_cost_input_asc: Ranked by price_input_usd_per_1m ASC (1 = cheapest)
- rank_cost_output_asc: Ranked by price_output_usd_per_1m ASC (1 = cheapest)
- rank_tool_support: Ranked by tool_score DESC (2=structured+fc, 1=fc, 0=none)
- rank_multimodal_support: Ranked by multimodal_score DESC (2=vision+audio, 1=vision, 0=text)
- multimodal_score: 0=text-only, 1=vision, 2=vision+audio
- tool_score: 0=none, 1=function_calling, 2=structured_output+fc
""".strip()
        
        df["derived_rank_source_name"] = self.source_name
        df["derived_rank_retrieved_at"] = now_iso
        df["derived_rank_formula_notes"] = formula_notes
        
        result.rows_enriched = len(df)
        
        self.logger.info(
            "Derived rankings computed for %d models",
            len(df)
        )
        
        return df

