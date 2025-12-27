"""
Telemetry Probe Enricher

Measures real latency, throughput, and error rates by calling models.

Key Features:
- Incremental probing with TTL-based cohort selection
- Sticky metrics: previous values preserved for non-selected models
- Deterministic cohort: same seed = same selection
- Per-row provenance: attempted, asof_date, run_id, outcome, error
"""
from __future__ import annotations

import logging
import os
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult
from .cohort_selector import select_cohort, generate_run_id, get_iso_week_seed

logger = logging.getLogger(__name__)

# OpenRouter API
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Standard test prompt for telemetry
TELEMETRY_PROMPT = "Say 'Hello World' and nothing else."
TELEMETRY_MAX_TOKENS = 16

# Telemetry outcome values
OUTCOME_SUCCESS = "success"
OUTCOME_ERROR = "error"
OUTCOME_SKIPPED_TTL = "skipped_ttl"
OUTCOME_SKIPPED_BUDGET = "skipped_budget"
OUTCOME_DISABLED = "disabled"


class TelemetryProbeEnricher(BaseEnricher):
    """
    Enricher that measures model performance via live probes.
    
    Measures:
    - latency_p50_ms, latency_p95_ms
    - tokens_per_sec_estimated
    - error_rate (over N trials)
    
    Provenance Columns:
    - telemetry_attempted (boolean): True if probe was attempted
    - telemetry_asof_date (string): ISO8601 timestamp of last probe
    - telemetry_run_id (string): Batch run identifier
    - telemetry_outcome (string): success/error/skipped_ttl/skipped_budget/disabled
    - telemetry_error (string): Last error message if any
    
    Metric Columns:
    - telemetry_latency_p50_ms
    - telemetry_latency_p95_ms
    - telemetry_tps_p50
    - telemetry_error_rate
    - telemetry_trials
    """
    
    name = "telemetry_probe"
    source_name = "LLMHive Telemetry Probe"
    source_url = ""
    
    # Provenance columns
    PROVENANCE_COLUMNS = [
        "telemetry_attempted",
        "telemetry_asof_date",
        "telemetry_run_id",
        "telemetry_outcome",
        "telemetry_error",
        "telemetry_source_name",
    ]
    
    # Metric columns
    METRIC_COLUMNS = [
        "telemetry_trials",
        "telemetry_latency_p50_ms",
        "telemetry_latency_p95_ms",
        "telemetry_tps_p50",
        "telemetry_error_rate",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
        trials: int = 3,
        max_models: int = 0,  # 0 = no limit
        timeout_seconds: int = 30,
        ttl_days: int = 14,
        seed_key: Optional[str] = None,
        always_include_top: int = 10,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.trials = max(1, trials)
        self.max_models = max_models
        self.timeout_seconds = timeout_seconds
        self.ttl_days = ttl_days
        self.seed_key = seed_key
        self.always_include_top = always_include_top
    
    def _probe_model(
        self,
        model_id: str,
    ) -> Tuple[Optional[float], Optional[int], Optional[str]]:
        """
        Run a single probe against a model.
        
        Returns:
            (latency_ms, tokens_generated, error_message)
        """
        if not self.api_key:
            return None, None, "No API key"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": TELEMETRY_PROMPT}],
            "max_tokens": TELEMETRY_MAX_TOKENS,
            "temperature": 0,
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                OPENROUTER_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return latency_ms, None, f"HTTP {response.status_code}"
            
            data = response.json()
            
            # Extract token usage
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            
            return latency_ms, completion_tokens, None
            
        except requests.Timeout:
            return self.timeout_seconds * 1000, None, "Timeout"
        except Exception as e:
            return None, None, str(e)
    
    def _run_trials(
        self,
        model_id: str,
    ) -> Dict[str, Any]:
        """
        Run multiple trials and compute statistics.
        
        Returns:
            Dict with telemetry measurements
        """
        latencies = []
        tokens_list = []
        errors = []
        
        for i in range(self.trials):
            try:
                latency, tokens, error = self._probe_model(model_id)
                
                if error:
                    errors.append(error)
                else:
                    if latency is not None:
                        latencies.append(latency)
                    if tokens is not None and tokens > 0:
                        tokens_list.append(tokens)
                
                # Small delay between trials
                time.sleep(0.3)
            except Exception as e:
                errors.append(str(e)[:100])
        
        result = {
            "trials": self.trials,
            "successful_trials": len(latencies),
            "error_rate": len(errors) / self.trials if self.trials > 0 else 1.0,
            "errors": errors,
        }
        
        if latencies:
            result["latency_p50_ms"] = round(statistics.median(latencies), 1)
            if len(latencies) >= 2:
                # Compute p95 (use max for small samples)
                sorted_latencies = sorted(latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                result["latency_p95_ms"] = round(sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)], 1)
            else:
                result["latency_p95_ms"] = result["latency_p50_ms"]
            
            # Compute tokens per second
            if tokens_list and latencies:
                avg_tokens = statistics.mean(tokens_list)
                avg_latency_s = statistics.mean(latencies) / 1000
                if avg_latency_s > 0:
                    result["tps_p50"] = round(avg_tokens / avg_latency_s, 1)
        
        return result
    
    def _initialize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Initialize provenance and metric columns if not present."""
        for col in self.PROVENANCE_COLUMNS + self.METRIC_COLUMNS:
            if col not in df.columns:
                df[col] = None
        return df
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Run telemetry probes with incremental/sticky behavior."""
        
        # Always initialize columns (but don't wipe existing values)
        df = self._initialize_columns(df)
        
        if self.dry_run:
            # Log what would happen
            seed = self.seed_key or get_iso_week_seed()
            cohort, metadata = select_cohort(
                df,
                max_models=self.max_models,
                ttl_days=self.ttl_days,
                seed_key=seed,
                always_include_top=self.always_include_top,
                slug_column="openrouter_slug",
                asof_column="telemetry_asof_date",
                metric_columns=self.METRIC_COLUMNS,
                rank_column="derived_rank_overall",
                eligibility_filter="in_openrouter",
            )
            
            self.logger.info("[DRY RUN] Would probe %d models with %d trials each", 
                           len(cohort), self.trials)
            self.logger.info("[DRY RUN] Cohort metadata: %s", metadata)
            self.logger.info("[DRY RUN] Sample cohort (first 10): %s", cohort[:10])
            result.warnings.append(f"Dry run - would probe {len(cohort)} models")
            return df
        
        if not self.api_key:
            result.warnings.append("No OPENROUTER_API_KEY - skipping telemetry")
            return df
        
        now_iso = datetime.now(timezone.utc).isoformat()
        run_id = generate_run_id()
        
        # Select cohort using TTL-based selection
        cohort, metadata = select_cohort(
            df,
            max_models=self.max_models,
            ttl_days=self.ttl_days,
            seed_key=self.seed_key,
            always_include_top=self.always_include_top,
            slug_column="openrouter_slug",
            asof_column="telemetry_asof_date",
            metric_columns=self.METRIC_COLUMNS,
            rank_column="derived_rank_overall",
            eligibility_filter="in_openrouter",
        )
        
        self.logger.info("Telemetry cohort selected: %d models (seed=%s, ttl=%d days, trials=%d)",
                        len(cohort), metadata.get("seed_key"), self.ttl_days, self.trials)
        
        # Mark non-cohort eligible models with skipped_budget outcome (only if no prior outcome)
        eligible_mask = df["in_openrouter"] == True
        for idx, row in df[eligible_mask].iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or slug in cohort:
                continue
            
            # Only set skipped outcome if not already set
            current_outcome = row.get("telemetry_outcome")
            if pd.isna(current_outcome) or current_outcome == "":
                df.at[idx, "telemetry_outcome"] = OUTCOME_SKIPPED_BUDGET
        
        if len(cohort) == 0:
            self.logger.info("No models need telemetry probing (all within TTL)")
            return df
        
        enriched_count = 0
        error_count = 0
        
        for slug in cohort:
            matches = df[df["openrouter_slug"] == slug]
            if len(matches) == 0:
                continue
            
            idx = matches.index[0]
            
            self.logger.debug("Probing %s...", slug)
            
            try:
                telemetry = self._run_trials(slug)
                
                # Record metrics
                df.at[idx, "telemetry_trials"] = telemetry.get("trials")
                df.at[idx, "telemetry_error_rate"] = round(telemetry.get("error_rate", 1.0), 3)
                
                if "latency_p50_ms" in telemetry:
                    df.at[idx, "telemetry_latency_p50_ms"] = telemetry["latency_p50_ms"]
                    df.at[idx, "telemetry_latency_p95_ms"] = telemetry.get("latency_p95_ms")
                    df.at[idx, "telemetry_tps_p50"] = telemetry.get("tps_p50")
                    enriched_count += 1
                    df.at[idx, "telemetry_outcome"] = OUTCOME_SUCCESS
                    df.at[idx, "telemetry_error"] = None
                else:
                    error_count += 1
                    error_msg = telemetry.get("errors", ["Unknown"])[0] if telemetry.get("errors") else "No latency data"
                    df.at[idx, "telemetry_error"] = error_msg[:200]
                    df.at[idx, "telemetry_outcome"] = OUTCOME_ERROR
                    result.data_gaps.append({
                        "slug": slug,
                        "source": "telemetry_probe",
                        "reason": f"Probe failed: {error_msg}",
                    })
                
            except Exception as e:
                error_count += 1
                df.at[idx, "telemetry_error"] = str(e)[:200]
                df.at[idx, "telemetry_outcome"] = OUTCOME_ERROR
            
            # Record provenance (always, even on error)
            df.at[idx, "telemetry_attempted"] = True
            df.at[idx, "telemetry_asof_date"] = now_iso
            df.at[idx, "telemetry_run_id"] = run_id
            df.at[idx, "telemetry_source_name"] = self.source_name
            
            # Rate limiting between models
            time.sleep(0.5)
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = error_count
        
        self.logger.info(
            "Telemetry probes completed: %d/%d successful, %d failed",
            enriched_count, len(cohort), error_count
        )
        
        return df
