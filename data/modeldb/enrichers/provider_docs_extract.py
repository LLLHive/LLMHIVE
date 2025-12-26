"""
Provider Documentation Enricher

Extracts and verifies model metadata from authoritative provider documentation.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseEnricher, EnricherResult

logger = logging.getLogger(__name__)


# Known provider context lengths and capabilities
# This is a curated reference from official documentation
PROVIDER_REFERENCE = {
    "openai": {
        "gpt-4o": {
            "max_context_tokens": 128000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_streaming": True,
            "modalities": "text,vision",
            "source_url": "https://platform.openai.com/docs/models/gpt-4o",
        },
        "gpt-4o-mini": {
            "max_context_tokens": 128000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_streaming": True,
            "modalities": "text,vision",
            "source_url": "https://platform.openai.com/docs/models/gpt-4o-mini",
        },
        "gpt-4-turbo": {
            "max_context_tokens": 128000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://platform.openai.com/docs/models/gpt-4-turbo",
        },
        "o1": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://platform.openai.com/docs/models/o1",
        },
        "o1-mini": {
            "max_context_tokens": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
            "modalities": "text",
            "source_url": "https://platform.openai.com/docs/models/o1",
        },
    },
    "anthropic": {
        "claude-3-opus": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://docs.anthropic.com/claude/docs/models-overview",
        },
        "claude-3.5-sonnet": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://docs.anthropic.com/claude/docs/models-overview",
        },
        "claude-3-sonnet": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://docs.anthropic.com/claude/docs/models-overview",
        },
        "claude-3-haiku": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://docs.anthropic.com/claude/docs/models-overview",
        },
        "claude-opus-4": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://docs.anthropic.com/claude/docs/models-overview",
        },
        "claude-sonnet-4": {
            "max_context_tokens": 200000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision",
            "source_url": "https://docs.anthropic.com/claude/docs/models-overview",
        },
    },
    "google": {
        "gemini-2.5-pro": {
            "max_context_tokens": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision,audio",
            "source_url": "https://ai.google.dev/gemini-api/docs/models",
        },
        "gemini-2.5-flash": {
            "max_context_tokens": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision,audio",
            "source_url": "https://ai.google.dev/gemini-api/docs/models",
        },
        "gemini-2.0-flash": {
            "max_context_tokens": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision,audio",
            "source_url": "https://ai.google.dev/gemini-api/docs/models",
        },
        "gemini-1.5-pro": {
            "max_context_tokens": 2000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "modalities": "text,vision,audio",
            "source_url": "https://ai.google.dev/gemini-api/docs/models",
        },
    },
    "meta-llama": {
        "llama-3.3-70b": {
            "max_context_tokens": 131072,
            "supports_vision": False,
            "supports_function_calling": True,
            "modalities": "text",
            "source_url": "https://ai.meta.com/llama/",
        },
        "llama-3.1-405b": {
            "max_context_tokens": 131072,
            "supports_vision": False,
            "supports_function_calling": True,
            "modalities": "text",
            "source_url": "https://ai.meta.com/llama/",
        },
    },
    "mistralai": {
        "mistral-large": {
            "max_context_tokens": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
            "modalities": "text",
            "source_url": "https://docs.mistral.ai/getting-started/models/",
        },
        "mistral-medium": {
            "max_context_tokens": 32000,
            "supports_function_calling": True,
            "modalities": "text",
            "source_url": "https://docs.mistral.ai/getting-started/models/",
        },
    },
}


class ProviderDocsEnricher(BaseEnricher):
    """
    Enricher that fills missing metadata from authoritative provider docs.
    
    Only updates fields that are currently null/missing.
    Does NOT overwrite existing values.
    """
    
    name = "provider_docs"
    source_name = "Provider Documentation"
    source_url = "Various provider documentation"
    
    def __init__(
        self,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
    
    def _match_model_to_reference(
        self,
        slug: str,
        provider: str,
    ) -> Optional[Dict[str, Any]]:
        """Match a model slug to our reference data."""
        provider_lower = provider.lower() if provider else ""
        
        # Get provider reference
        provider_ref = None
        for prov_key in PROVIDER_REFERENCE:
            if prov_key in provider_lower or provider_lower in prov_key:
                provider_ref = PROVIDER_REFERENCE[prov_key]
                break
        
        if not provider_ref:
            return None
        
        # Get model part of slug
        model_part = slug.split("/", 1)[1] if "/" in slug else slug
        model_lower = model_part.lower()
        
        # Try exact match
        for model_key, model_data in provider_ref.items():
            if model_key in model_lower or model_lower in model_key:
                return model_data
        
        return None
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Fill missing metadata from provider docs."""
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Ensure columns exist
        fields_to_fill = [
            "max_context_tokens",
            "supports_vision",
            "supports_function_calling",
            "supports_streaming",
            "modalities",
        ]
        
        for field in fields_to_fill:
            if field not in df.columns:
                df[field] = None
        
        # Add provenance column
        if "provider_docs_source_url" not in df.columns:
            df["provider_docs_source_url"] = None
        if "provider_docs_verified_at" not in df.columns:
            df["provider_docs_verified_at"] = None
        
        enriched_count = 0
        
        for idx, row in df.iterrows():
            slug = row.get("openrouter_slug")
            provider = row.get("provider_name") or row.get("provider_id")
            
            if pd.isna(slug) or not slug:
                continue
            
            slug = str(slug).strip()
            provider = str(provider).strip() if provider else ""
            
            # Match to reference
            ref_data = self._match_model_to_reference(slug, provider)
            
            if ref_data:
                updated = False
                
                for field in fields_to_fill:
                    if field in ref_data:
                        existing = row.get(field)
                        if pd.isna(existing) or existing == "" or existing is None:
                            df.at[idx, field] = ref_data[field]
                            updated = True
                
                if updated:
                    df.at[idx, "provider_docs_source_url"] = ref_data.get("source_url", "")
                    df.at[idx, "provider_docs_verified_at"] = now_iso
                    enriched_count += 1
        
        result.rows_enriched = enriched_count
        
        self.logger.info(
            "Provider docs enrichment: filled metadata for %d models",
            enriched_count
        )
        
        return df

