"""
OpenRouter Rankings Enricher

Fetches ranking data from OpenRouter for all available categories.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)

# OpenRouter API endpoints
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


class OpenRouterRankingsEnricher(BaseEnricher):
    """
    Enricher that fetches OpenRouter ranking data.
    
    OpenRouter provides model rankings across various categories.
    This enricher discovers categories dynamically and populates:
    - openrouter_rank_<category>
    - openrouter_rankings_json_full (compact JSON of all rankings)
    """
    
    name = "openrouter_rankings"
    source_name = "OpenRouter API"
    source_url = "https://openrouter.ai/api/v1/models"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _fetch_models(self) -> List[Dict[str, Any]]:
        """Fetch all models from OpenRouter API."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.logger.info("Fetching models from OpenRouter...")
        response = requests.get(OPENROUTER_MODELS_URL, headers=headers, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        models = data.get("data", [])
        self.logger.info("Fetched %d models from OpenRouter", len(models))
        
        return models
    
    def _extract_rankings(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ranking information from a model object.
        
        OpenRouter model objects may contain:
        - top_provider info
        - per_request_limits
        - pricing tier info
        
        We'll track position in various orderings.
        """
        rankings = {}
        
        # Extract top_provider info
        top_provider = model.get("top_provider", {})
        if isinstance(top_provider, dict):
            rankings["is_moderated"] = top_provider.get("is_moderated", False)
        
        # Extract context length for ranking
        rankings["context_length"] = model.get("context_length", 0)
        
        # Extract pricing
        pricing = model.get("pricing", {})
        if isinstance(pricing, dict):
            try:
                rankings["price_prompt"] = float(pricing.get("prompt", 0))
                rankings["price_completion"] = float(pricing.get("completion", 0))
            except (ValueError, TypeError):
                pass
        
        return rankings
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fetch OpenRouter data and add ranking columns."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would fetch OpenRouter rankings")
            result.warnings.append("Dry run - no API calls made")
            return df
        
        try:
            models = self._fetch_models()
        except Exception as e:
            result.errors.append(f"Failed to fetch OpenRouter models: {e}")
            return df
        
        # Build lookup by slug
        or_models_by_slug: Dict[str, Dict[str, Any]] = {}
        for m in models:
            slug = m.get("id", "")
            if slug:
                or_models_by_slug[slug] = m
        
        # Compute rankings
        # Sort models by various criteria to compute ranks
        sorted_by_context = sorted(models, key=lambda x: x.get("context_length", 0), reverse=True)
        sorted_by_price_input = sorted(
            models, 
            key=lambda x: float(x.get("pricing", {}).get("prompt", 999999) or 999999)
        )
        sorted_by_price_output = sorted(
            models,
            key=lambda x: float(x.get("pricing", {}).get("completion", 999999) or 999999)
        )
        
        # Create rank lookups
        context_rank = {m.get("id"): i + 1 for i, m in enumerate(sorted_by_context)}
        price_input_rank = {m.get("id"): i + 1 for i, m in enumerate(sorted_by_price_input)}
        price_output_rank = {m.get("id"): i + 1 for i, m in enumerate(sorted_by_price_output)}
        
        # Initialize new columns
        now_iso = datetime.now(timezone.utc).isoformat()
        
        new_columns = [
            "openrouter_rank_context_length",
            "openrouter_rank_price_input",
            "openrouter_rank_price_output",
            "openrouter_total_models",
            "openrouter_rankings_json_full",
            "openrouter_rankings_source_name",
            "openrouter_rankings_source_url",
            "openrouter_rankings_retrieved_at",
        ]
        
        for col in new_columns:
            if col not in df.columns:
                df[col] = None
        
        # Enrich each model
        enriched_count = 0
        gap_count = 0
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            
            if slug in or_models_by_slug:
                # Found in OpenRouter
                or_model = or_models_by_slug[slug]
                
                # Set ranks
                df.at[idx, "openrouter_rank_context_length"] = context_rank.get(slug)
                df.at[idx, "openrouter_rank_price_input"] = price_input_rank.get(slug)
                df.at[idx, "openrouter_rank_price_output"] = price_output_rank.get(slug)
                df.at[idx, "openrouter_total_models"] = len(models)
                
                # Store full rankings as JSON
                rankings_data = self._extract_rankings(or_model)
                rankings_data["rank_context"] = context_rank.get(slug)
                rankings_data["rank_price_input"] = price_input_rank.get(slug)
                rankings_data["rank_price_output"] = price_output_rank.get(slug)
                df.at[idx, "openrouter_rankings_json_full"] = json.dumps(rankings_data)
                
                # Provenance
                df.at[idx, "openrouter_rankings_source_name"] = self.source_name
                df.at[idx, "openrouter_rankings_source_url"] = self.source_url
                df.at[idx, "openrouter_rankings_retrieved_at"] = now_iso
                
                enriched_count += 1
            else:
                # Not found - log gap
                gap_count += 1
                result.data_gaps.append({
                    "slug": slug,
                    "source": "openrouter_rankings",
                    "reason": "Model not found in current OpenRouter catalog",
                })
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = gap_count
        
        self.logger.info(
            "OpenRouter rankings: enriched %d models, %d gaps",
            enriched_count, gap_count
        )
        
        return df

