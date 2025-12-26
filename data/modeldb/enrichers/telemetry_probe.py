"""
Telemetry Probe Enricher

Measures real latency, throughput, and error rates by calling models.
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

logger = logging.getLogger(__name__)

# OpenRouter API
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Standard test prompt for telemetry
TELEMETRY_PROMPT = "Say 'Hello World' and nothing else."
TELEMETRY_MAX_TOKENS = 16


class TelemetryProbeEnricher(BaseEnricher):
    """
    Enricher that measures model performance via live probes.
    
    Measures:
    - latency_p50_ms, latency_p95_ms
    - tokens_per_sec_estimated
    - error_rate (over N trials)
    """
    
    name = "telemetry_probe"
    source_name = "LLMHive Telemetry Probe"
    source_url = ""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
        trials: int = 3,
        max_models: int = 0,  # 0 = no limit
        timeout_seconds: int = 30,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.trials = max(1, trials)
        self.max_models = max_models
        self.timeout_seconds = timeout_seconds
    
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
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Run telemetry probes on models."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would run telemetry probes")
            result.warnings.append("Dry run - no probes run")
            return df
        
        if not self.api_key:
            result.warnings.append("No OPENROUTER_API_KEY - skipping telemetry")
            return df
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Initialize columns
        telemetry_columns = [
            "telemetry_trials",
            "telemetry_latency_p50_ms",
            "telemetry_latency_p95_ms",
            "telemetry_tps_p50",
            "telemetry_error_rate",
            "telemetry_retrieved_at",
            "telemetry_source_name",
        ]
        
        for col in telemetry_columns:
            if col not in df.columns:
                df[col] = None
        
        # Filter models to probe
        models_to_probe = df[df["in_openrouter"] == True]["openrouter_slug"].dropna().tolist()
        
        if self.max_models > 0:
            models_to_probe = models_to_probe[:self.max_models]
        
        self.logger.info("Probing %d models with %d trials each", len(models_to_probe), self.trials)
        
        enriched_count = 0
        error_count = 0
        
        for slug in models_to_probe:
            idx = df[df["openrouter_slug"] == slug].index[0]
            
            self.logger.debug("Probing %s...", slug)
            telemetry = self._run_trials(slug)
            
            df.at[idx, "telemetry_trials"] = telemetry.get("trials")
            df.at[idx, "telemetry_error_rate"] = round(telemetry.get("error_rate", 1.0), 3)
            
            if "latency_p50_ms" in telemetry:
                df.at[idx, "telemetry_latency_p50_ms"] = telemetry["latency_p50_ms"]
                df.at[idx, "telemetry_latency_p95_ms"] = telemetry.get("latency_p95_ms")
                df.at[idx, "telemetry_tps_p50"] = telemetry.get("tps_p50")
                enriched_count += 1
            else:
                error_count += 1
                result.data_gaps.append({
                    "slug": slug,
                    "source": "telemetry_probe",
                    "reason": f"Probe failed: {telemetry.get('errors', ['Unknown'])[0]}",
                })
            
            df.at[idx, "telemetry_retrieved_at"] = now_iso
            df.at[idx, "telemetry_source_name"] = self.source_name
            
            # Rate limiting between models
            time.sleep(0.5)
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = error_count
        
        self.logger.info(
            "Telemetry probes completed: %d successful, %d failed",
            enriched_count, error_count
        )
        
        return df

