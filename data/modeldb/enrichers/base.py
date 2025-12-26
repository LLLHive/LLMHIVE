"""
Base classes for ModelDB enrichers.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class EnricherResult:
    """Result of running an enricher."""
    
    success: bool
    enricher_name: str
    columns_added: List[str] = field(default_factory=list)
    columns_updated: List[str] = field(default_factory=list)
    rows_enriched: int = 0
    rows_with_gaps: int = 0
    data_gaps: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "enricher_name": self.enricher_name,
            "columns_added": self.columns_added,
            "columns_updated": self.columns_updated,
            "rows_enriched": self.rows_enriched,
            "rows_with_gaps": self.rows_with_gaps,
            "data_gaps_count": len(self.data_gaps),
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": self.duration_seconds,
        }


class BaseEnricher(ABC):
    """
    Abstract base class for all enrichers.
    
    Enrichers add data from external sources to the model catalog.
    They must follow strict rules to prevent data loss.
    """
    
    name: str = "base"
    source_name: str = "Unknown"
    source_url: str = ""
    
    def __init__(self, dry_run: bool = False, cache_dir: Optional[str] = None):
        self.dry_run = dry_run
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(f"enricher.{self.name}")
        self._original_columns: Set[str] = set()
        self._original_row_count: int = 0
    
    def enrich(self, df: pd.DataFrame) -> tuple[pd.DataFrame, EnricherResult]:
        """
        Main entry point. Validates inputs/outputs and calls _do_enrich.
        
        Returns:
            (enriched_df, result)
        """
        import time
        
        start_time = time.time()
        
        # Store original state for validation
        self._original_columns = set(df.columns)
        self._original_row_count = len(df)
        
        result = EnricherResult(
            success=False,
            enricher_name=self.name,
        )
        
        try:
            # Run the enricher
            enriched_df = self._do_enrich(df.copy(), result)
            
            # Validate no data loss
            self._validate_no_data_loss(df, enriched_df, result)
            
            # Calculate stats
            result.columns_added = [
                c for c in enriched_df.columns if c not in self._original_columns
            ]
            result.success = len(result.errors) == 0
            
        except Exception as e:
            self.logger.error("Enricher %s failed: %s", self.name, e, exc_info=True)
            result.errors.append(str(e))
            enriched_df = df  # Return original on failure
        
        result.duration_seconds = time.time() - start_time
        
        self.logger.info(
            "Enricher %s completed: success=%s, added=%d columns, enriched=%d rows, gaps=%d",
            self.name, result.success, len(result.columns_added),
            result.rows_enriched, result.rows_with_gaps
        )
        
        return enriched_df, result
    
    @abstractmethod
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """
        Implement the actual enrichment logic.
        
        Args:
            df: Copy of the DataFrame to enrich (safe to modify)
            result: EnricherResult to update with stats
            
        Returns:
            Enriched DataFrame
        """
        raise NotImplementedError
    
    def _validate_no_data_loss(
        self, 
        original: pd.DataFrame, 
        enriched: pd.DataFrame,
        result: EnricherResult,
    ) -> None:
        """Validate that enrichment didn't lose data."""
        # Check row count
        if len(enriched) < self._original_row_count:
            result.errors.append(
                f"Row count decreased: {len(enriched)} < {self._original_row_count}"
            )
        
        # Check columns preserved
        missing_cols = self._original_columns - set(enriched.columns)
        if missing_cols:
            result.errors.append(
                f"Columns dropped: {sorted(missing_cols)}"
            )
    
    def _add_provenance(
        self,
        df: pd.DataFrame,
        field_prefix: str,
        source_name: Optional[str] = None,
        source_url: Optional[str] = None,
        confidence: str = "high",
    ) -> None:
        """Add provenance columns for a field or field group."""
        now_iso = datetime.now(timezone.utc).isoformat()
        
        df[f"{field_prefix}_source_name"] = source_name or self.source_name
        df[f"{field_prefix}_source_url"] = source_url or self.source_url
        df[f"{field_prefix}_retrieved_at"] = now_iso
        df[f"{field_prefix}_confidence"] = confidence
    
    def _safe_update(
        self,
        df: pd.DataFrame,
        index: Any,
        column: str,
        value: Any,
    ) -> bool:
        """
        Safely update a cell only if the existing value is null/empty.
        
        Returns True if update was made.
        """
        existing = df.loc[index, column] if column in df.columns else None
        
        if pd.isna(existing) or existing == "" or existing is None:
            df.loc[index, column] = value
            return True
        return False
    
    def _normalize_model_name(self, name: str) -> str:
        """Normalize a model name for matching."""
        if not name:
            return ""
        # Lowercase, remove common suffixes, normalize separators
        name = name.lower().strip()
        # Remove version suffixes like -v1, -v2, etc.
        import re
        name = re.sub(r"[-_]v?\d+(\.\d+)*$", "", name)
        # Normalize separators
        name = name.replace("_", "-").replace(" ", "-")
        return name

