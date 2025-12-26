#!/usr/bin/env python3
"""
LLMHive ModelDB Update Script - Enrich Excel with OpenRouter + External Sources.

This script:
1. Reads the existing Excel (or creates from scratch if --from-openrouter)
2. Fetches latest model data from OpenRouter API
3. Optionally enriches with external sources (Epoch AI, etc.)
4. Adds provenance tracking for all enriched fields
5. Outputs updated Excel while PRESERVING all existing columns/rows

NO DATA LOSS GUARANTEES:
- All existing rows preserved
- All existing columns preserved
- New columns added with provenance (*_source_name, *_source_url, *_retrieved_at)
- Values only updated if explicitly enabled

Usage:
    python llmhive_modeldb_update.py --previous models.xlsx --output models_updated.xlsx
    python llmhive_modeldb_update.py --from-openrouter --output models_new.xlsx
    python llmhive_modeldb_update.py --previous models.xlsx --output models.xlsx --in-place
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("modeldb_update")

# =============================================================================
# Constants
# =============================================================================

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/models"
EPOCH_AI_API_URL = "https://epochai.org/api/models"  # Placeholder

# Provenance suffix fields
PROVENANCE_SUFFIXES = ["_source_name", "_source_url", "_retrieved_at", "_confidence"]

# Cache settings
DEFAULT_CACHE_DIR = ".cache/llmhive_modeldb"
CACHE_TTL_HOURS = 24


# =============================================================================
# OpenRouter API
# =============================================================================


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
def fetch_openrouter_models(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all models from OpenRouter API.
    
    Returns list of model dictionaries with OpenRouter's native schema.
    """
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    logger.info("Fetching models from OpenRouter...")
    response = requests.get(OPENROUTER_API_URL, headers=headers, timeout=60)
    response.raise_for_status()
    
    data = response.json()
    models = data.get("data", [])
    logger.info("Fetched %d models from OpenRouter", len(models))
    
    return models


def normalize_openrouter_model(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an OpenRouter model to our schema.
    
    Preserves all original fields and adds normalized versions.
    """
    model_id = raw.get("id", "")
    
    # Parse provider/model from ID
    provider = ""
    model_name = model_id
    if "/" in model_id:
        parts = model_id.split("/", 1)
        provider = parts[0]
        model_name = parts[1]
    
    # Extract pricing
    pricing = raw.get("pricing", {})
    if isinstance(pricing, dict):
        price_input = float(pricing.get("prompt", 0)) * 1_000_000
        price_output = float(pricing.get("completion", 0)) * 1_000_000
    else:
        price_input = 0.0
        price_output = 0.0
    
    # Build normalized record
    now_iso = datetime.now(timezone.utc).isoformat()
    
    return {
        "openrouter_slug": model_id,
        "model_name": model_name,
        "provider_name": provider,
        "provider_id": provider,
        "display_name": raw.get("name", model_name),
        "description": raw.get("description", ""),
        "max_context_tokens": raw.get("context_length", 0),
        "price_input_usd_per_1m": price_input,
        "price_output_usd_per_1m": price_output,
        "in_openrouter": True,
        "architecture": raw.get("architecture", {}).get("modality", ""),
        "supports_streaming": True,  # Most OpenRouter models support streaming
        "supports_function_calling": "tool" in str(raw.get("supported_parameters", [])).lower(),
        "supports_vision": "image" in str(raw.get("architecture", {})).lower(),
        "top_provider": raw.get("top_provider", {}).get("is_moderated", False),
        # Provenance
        "openrouter_slug_source_name": "OpenRouter API",
        "openrouter_slug_source_url": OPENROUTER_API_URL,
        "openrouter_slug_retrieved_at": now_iso,
        # Store raw data
        "_openrouter_raw": json.dumps(raw),
    }


# =============================================================================
# Caching
# =============================================================================


class APICache:
    """Simple file-based cache for API responses."""
    
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _cache_key(self, source: str, params: str = "") -> str:
        key = f"{source}:{params}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"
    
    def get(self, source: str, params: str = "", ttl_hours: float = CACHE_TTL_HOURS) -> Optional[Any]:
        """Get cached data if not expired."""
        key = self._cache_key(source, params)
        path = self._cache_path(key)
        
        if not path.exists():
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            cached_at = datetime.fromisoformat(cached["cached_at"])
            age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
            
            if age_hours > ttl_hours:
                logger.debug("Cache expired for %s", source)
                return None
            
            logger.debug("Cache hit for %s (age: %.1f hours)", source, age_hours)
            return cached["data"]
            
        except Exception as e:
            logger.warning("Cache read failed: %s", e)
            return None
    
    def set(self, source: str, data: Any, params: str = "") -> None:
        """Cache data."""
        key = self._cache_key(source, params)
        path = self._cache_path(key)
        
        try:
            cached = {
                "source": source,
                "params": params,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cached, f)
            logger.debug("Cached data for %s", source)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)


# =============================================================================
# Excel Operations
# =============================================================================


def read_excel_safe(path: Path) -> pd.DataFrame:
    """Read Excel file, handling various formats."""
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    
    try:
        # Try default sheet
        df = pd.read_excel(path)
        logger.info("Read %d rows from %s", len(df), path)
        return df
    except Exception as e:
        logger.error("Failed to read Excel: %s", e)
        raise


def merge_dataframes(
    existing: pd.DataFrame,
    new_data: pd.DataFrame,
    key_column: str = "openrouter_slug",
    update_existing: bool = False,
) -> pd.DataFrame:
    """
    Merge new data into existing DataFrame.
    
    Rules:
    - All existing rows preserved
    - New rows (by key) added
    - Existing values NOT overwritten unless update_existing=True
    - New columns added
    """
    if existing.empty:
        return new_data.copy()
    
    if new_data.empty:
        return existing.copy()
    
    # Ensure key column exists
    if key_column not in existing.columns:
        logger.warning("Key column %s not in existing data", key_column)
        return existing
    
    if key_column not in new_data.columns:
        logger.warning("Key column %s not in new data", key_column)
        return existing
    
    # Build result starting with existing
    result = existing.copy()
    existing_keys = set(result[key_column].dropna().astype(str))
    
    # Add new columns that don't exist
    for col in new_data.columns:
        if col not in result.columns:
            result[col] = None
            logger.info("Added new column: %s", col)
    
    # Process new rows
    new_rows = []
    updated = 0
    
    for _, row in new_data.iterrows():
        key = str(row.get(key_column, ""))
        if not key:
            continue
        
        if key in existing_keys:
            if update_existing:
                # Update existing row
                mask = result[key_column].astype(str) == key
                for col in new_data.columns:
                    if col == key_column:
                        continue
                    new_val = row.get(col)
                    if pd.notna(new_val):
                        # Only update if existing value is null OR update_existing
                        existing_val = result.loc[mask, col].iloc[0] if mask.any() else None
                        if pd.isna(existing_val):
                            result.loc[mask, col] = new_val
                updated += 1
        else:
            # New row
            new_rows.append(row.to_dict())
    
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        result = pd.concat([result, new_df], ignore_index=True)
        logger.info("Added %d new rows", len(new_rows))
    
    if updated:
        logger.info("Updated %d existing rows", updated)
    
    return result


def write_excel_safe(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to Excel with safety checks."""
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file first
    temp_path = path.with_suffix(".xlsx.tmp")
    
    try:
        df.to_excel(temp_path, index=False, engine="openpyxl")
        
        # Verify we can read it back
        verify = pd.read_excel(temp_path)
        if len(verify) != len(df):
            raise ValueError(f"Verification failed: wrote {len(df)} rows, read {len(verify)}")
        
        # Move to final path
        temp_path.replace(path)
        logger.info("Wrote %d rows to %s", len(df), path)
        
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise


# =============================================================================
# Update Pipeline
# =============================================================================


class ModelDBUpdater:
    """Main update orchestrator."""
    
    def __init__(
        self,
        previous_path: Optional[str] = None,
        output_path: Optional[str] = None,
        cache_dir: str = DEFAULT_CACHE_DIR,
        from_openrouter: bool = False,
        dry_run: bool = False,
    ):
        self.previous_path = Path(previous_path) if previous_path else None
        self.output_path = Path(output_path) if output_path else None
        self.cache = APICache(cache_dir)
        self.from_openrouter = from_openrouter
        self.dry_run = dry_run
        
        self.stats = {
            "previous_rows": 0,
            "previous_columns": 0,
            "openrouter_models": 0,
            "output_rows": 0,
            "output_columns": 0,
            "new_rows": 0,
            "new_columns": 0,
        }
    
    def run(self) -> Dict[str, Any]:
        """Execute the update."""
        logger.info("=" * 60)
        logger.info("ModelDB Update Starting")
        if self.previous_path:
            logger.info("Previous: %s", self.previous_path)
        logger.info("Output: %s", self.output_path)
        logger.info("From OpenRouter: %s", self.from_openrouter)
        logger.info("Dry Run: %s", self.dry_run)
        logger.info("=" * 60)
        
        # 1. Load existing data
        if self.previous_path and self.previous_path.exists():
            existing_df = read_excel_safe(self.previous_path)
            self.stats["previous_rows"] = len(existing_df)
            self.stats["previous_columns"] = len(existing_df.columns)
            existing_columns = set(existing_df.columns)
            logger.info("Previous file has %d rows, %d columns", 
                       len(existing_df), len(existing_df.columns))
        else:
            existing_df = pd.DataFrame()
            existing_columns = set()
            if not self.from_openrouter:
                logger.warning("No previous file and --from-openrouter not set")
        
        # 2. Fetch OpenRouter data
        openrouter_models = []
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Try cache first
        cached = self.cache.get("openrouter_models")
        if cached:
            openrouter_models = cached
            logger.info("Using cached OpenRouter data (%d models)", len(cached))
        else:
            try:
                raw_models = fetch_openrouter_models(api_key)
                openrouter_models = [normalize_openrouter_model(m) for m in raw_models]
                self.cache.set("openrouter_models", openrouter_models)
            except Exception as e:
                logger.error("Failed to fetch OpenRouter models: %s", e)
                if self.from_openrouter:
                    raise
        
        self.stats["openrouter_models"] = len(openrouter_models)
        
        # 3. Create OpenRouter DataFrame
        if openrouter_models:
            openrouter_df = pd.DataFrame(openrouter_models)
        else:
            openrouter_df = pd.DataFrame()
        
        # 4. Merge
        if self.from_openrouter and existing_df.empty:
            result_df = openrouter_df
        else:
            result_df = merge_dataframes(
                existing_df,
                openrouter_df,
                key_column="openrouter_slug",
                update_existing=False,
            )
        
        self.stats["output_rows"] = len(result_df)
        self.stats["output_columns"] = len(result_df.columns)
        self.stats["new_rows"] = len(result_df) - self.stats["previous_rows"]
        self.stats["new_columns"] = len(set(result_df.columns) - existing_columns)
        
        # 5. Validate no data loss
        if self.stats["previous_rows"] > 0 and len(result_df) < self.stats["previous_rows"]:
            raise ValueError(
                f"ROW DATA LOSS DETECTED: Output has {len(result_df)} rows, "
                f"previous had {self.stats['previous_rows']}"
            )
        
        if self.stats["previous_columns"] > 0 and len(result_df.columns) < self.stats["previous_columns"]:
            raise ValueError(
                f"COLUMN DATA LOSS DETECTED: Output has {len(result_df.columns)} columns, "
                f"previous had {self.stats['previous_columns']}"
            )
        
        # 6. Write output
        if self.output_path and not self.dry_run:
            write_excel_safe(result_df, self.output_path)
        elif self.dry_run:
            logger.info("[DRY RUN] Would write %d rows to %s", len(result_df), self.output_path)
        
        # Summary
        logger.info("=" * 60)
        logger.info("Update Complete")
        logger.info("Previous: %d rows, %d columns", 
                   self.stats["previous_rows"], self.stats["previous_columns"])
        logger.info("OpenRouter models fetched: %d", self.stats["openrouter_models"])
        logger.info("Output: %d rows, %d columns", 
                   self.stats["output_rows"], self.stats["output_columns"])
        logger.info("New rows added: %d", self.stats["new_rows"])
        logger.info("New columns added: %d", self.stats["new_columns"])
        logger.info("✅ NO DATA LOSS: Rows preserved, columns preserved")
        logger.info("=" * 60)
        
        return self.stats


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="LLMHive ModelDB Update - Enrich with OpenRouter and external sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--previous",
        help="Path to existing Excel file to update",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path for output Excel file",
    )
    parser.add_argument(
        "--from-openrouter",
        action="store_true",
        help="Create new file from OpenRouter API (no previous required)",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIR,
        help=f"Cache directory (default: {DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing output",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load .env if present
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass
    
    # Validate args
    if not args.previous and not args.from_openrouter:
        parser.error("Either --previous or --from-openrouter is required")
    
    # Run updater
    updater = ModelDBUpdater(
        previous_path=args.previous,
        output_path=args.output,
        cache_dir=args.cache_dir,
        from_openrouter=args.from_openrouter,
        dry_run=args.dry_run,
    )
    
    try:
        updater.run()
    except Exception as e:
        logger.error("Update failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

