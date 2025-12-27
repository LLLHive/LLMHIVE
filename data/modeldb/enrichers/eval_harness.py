"""
Eval Harness Enricher

Runs deterministic evaluations on models via OpenRouter API.
Measures language and programming language capabilities.

Key Features:
- Incremental evaluation with TTL-based cohort selection
- Sticky metrics: previous values preserved for non-selected models
- Deterministic cohort: same seed = same selection
- Per-row provenance: attempted, asof_date, run_id, outcome, error
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseEnricher, EnricherResult
from .cohort_selector import select_cohort, generate_run_id, get_iso_week_seed

logger = logging.getLogger(__name__)

# Eval prompt storage
EVALS_DIR = Path(__file__).parent.parent / "evals"

# OpenRouter API
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Eval outcome values
OUTCOME_SUCCESS = "success"
OUTCOME_ERROR = "error"
OUTCOME_SKIPPED_TTL = "skipped_ttl"
OUTCOME_SKIPPED_BUDGET = "skipped_budget"
OUTCOME_DISABLED = "disabled"


class EvalHarnessEnricher(BaseEnricher):
    """
    Enricher that runs deterministic evaluations on models.
    
    Evaluates:
    - Natural language understanding (multiple languages)
    - Programming language capabilities
    - Tool use / structured output
    
    All evaluations use fixed prompts with verifiable answers.
    
    Provenance Columns:
    - eval_attempted (boolean): True if evaluation was attempted
    - eval_asof_date (string): ISO8601 timestamp of last evaluation
    - eval_run_id (string): Batch run identifier
    - eval_outcome (string): success/error/skipped_ttl/skipped_budget/disabled
    - eval_error (string): Last error message if any
    
    Metric Columns:
    - eval_{category}_score: Score 0-1 for each category
    - eval_{category}_trials: Number of prompts evaluated
    """
    
    name = "eval_harness"
    source_name = "LLMHive Eval Harness"
    source_url = ""
    
    # Provenance columns (always initialized)
    PROVENANCE_COLUMNS = [
        "eval_attempted",
        "eval_asof_date",
        "eval_run_id",
        "eval_outcome",
        "eval_error",
        "eval_source_name",
    ]
    
    # Metric columns (depend on categories loaded)
    METRIC_COLUMN_SUFFIXES = ["_score", "_trials"]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
        max_models: int = 0,  # 0 = no limit
        skip_expensive: bool = False,
        timeout_seconds: int = 30,
        max_cost_usd: float = 0.0,  # 0 = no limit
        ttl_days: int = 30,
        seed_key: Optional[str] = None,
        always_include_top: int = 10,
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.max_models = max_models
        self.skip_expensive = skip_expensive
        self.timeout_seconds = timeout_seconds
        self.max_cost_usd = max_cost_usd
        self.ttl_days = ttl_days
        self.seed_key = seed_key
        self.always_include_top = always_include_top
        self._eval_prompts: Dict[str, List[Dict[str, Any]]] = {}
        self._load_eval_prompts()
    
    def _get_metric_columns(self) -> List[str]:
        """Get list of metric columns based on loaded categories."""
        columns = []
        for category in self._eval_prompts:
            columns.append(f"eval_{category}_score")
            columns.append(f"eval_{category}_trials")
        return columns
    
    def _load_eval_prompts(self) -> None:
        """Load evaluation prompts from files."""
        # Create default prompts if directory is empty
        self._ensure_eval_prompts_exist()
        
        # Load prompts by category
        for category_dir in EVALS_DIR.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                prompts = []
                
                for prompt_file in category_dir.glob("*.jsonl"):
                    try:
                        with open(prompt_file, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    prompts.append(json.loads(line))
                    except Exception as e:
                        self.logger.warning("Failed to load %s: %s", prompt_file, e)
                
                if prompts:
                    self._eval_prompts[category] = prompts
                    self.logger.info("Loaded %d prompts for category: %s", len(prompts), category)
    
    def _ensure_eval_prompts_exist(self) -> None:
        """Create default eval prompts if they don't exist."""
        # Programming languages
        pl_dir = EVALS_DIR / "programming_languages"
        pl_dir.mkdir(parents=True, exist_ok=True)
        
        pl_prompts = pl_dir / "basic.jsonl"
        if not pl_prompts.exists():
            prompts = [
                {
                    "id": "python_hello",
                    "lang": "python",
                    "prompt": "Write a Python function that takes a name and returns 'Hello, {name}!'. Only output the function, no explanation.",
                    "expected_contains": ["def ", "return", "Hello"],
                    "difficulty": "easy",
                },
                {
                    "id": "python_factorial",
                    "lang": "python",
                    "prompt": "Write a Python function `factorial(n)` that computes n! recursively. Only output the function.",
                    "expected_contains": ["def factorial", "return", "factorial(n"],
                    "difficulty": "easy",
                },
                {
                    "id": "javascript_map",
                    "lang": "javascript",
                    "prompt": "Write a JavaScript function that doubles each number in an array using map. Only output the function.",
                    "expected_contains": ["function", "map", "return"],
                    "difficulty": "easy",
                },
                {
                    "id": "sql_select",
                    "lang": "sql",
                    "prompt": "Write a SQL query to select all users older than 30 from a 'users' table. Only output the query.",
                    "expected_contains": ["SELECT", "FROM", "users", "WHERE", "30"],
                    "difficulty": "easy",
                },
            ]
            with open(pl_prompts, "w", encoding="utf-8") as f:
                for p in prompts:
                    f.write(json.dumps(p) + "\n")
        
        # Natural languages
        lang_dir = EVALS_DIR / "languages"
        lang_dir.mkdir(parents=True, exist_ok=True)
        
        lang_prompts = lang_dir / "basic.jsonl"
        if not lang_prompts.exists():
            prompts = [
                {
                    "id": "en_capital",
                    "lang": "en",
                    "prompt": "What is the capital of France? Answer with just the city name.",
                    "expected_exact": "Paris",
                    "difficulty": "easy",
                },
                {
                    "id": "es_capital",
                    "lang": "es",
                    "prompt": "¿Cuál es la capital de España? Responde solo con el nombre de la ciudad.",
                    "expected_exact": "Madrid",
                    "difficulty": "easy",
                },
                {
                    "id": "zh_capital",
                    "lang": "zh",
                    "prompt": "中国的首都是哪个城市？只回答城市名。",
                    "expected_contains": ["北京", "Beijing"],
                    "difficulty": "easy",
                },
            ]
            with open(lang_prompts, "w", encoding="utf-8") as f:
                for p in prompts:
                    f.write(json.dumps(p) + "\n")
        
        # Tool use
        tool_dir = EVALS_DIR / "tool_use"
        tool_dir.mkdir(parents=True, exist_ok=True)
        
        tool_prompts = tool_dir / "basic.jsonl"
        if not tool_prompts.exists():
            prompts = [
                {
                    "id": "json_output",
                    "type": "structured",
                    "prompt": "Output a JSON object with keys 'name' (string) and 'age' (number) for a person named John who is 30 years old. Only output the JSON.",
                    "expected_json_keys": ["name", "age"],
                    "difficulty": "easy",
                },
            ]
            with open(tool_prompts, "w", encoding="utf-8") as f:
                for p in prompts:
                    f.write(json.dumps(p) + "\n")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    def _call_model(
        self,
        model_id: str,
        prompt: str,
    ) -> Tuple[str, float, Optional[str]]:
        """
        Call a model via OpenRouter.
        
        Returns:
            (response_text, latency_ms, error_message)
        """
        if not self.api_key:
            return "", 0, "No API key"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0,  # Deterministic
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
                return "", latency_ms, f"HTTP {response.status_code}"
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return content.strip(), latency_ms, None
            
        except requests.Timeout:
            return "", self.timeout_seconds * 1000, "Timeout"
        except Exception as e:
            return "", 0, str(e)
    
    def _evaluate_response(
        self,
        response: str,
        prompt_spec: Dict[str, Any],
    ) -> Tuple[float, str]:
        """
        Evaluate a model response against expected criteria.
        
        Returns:
            (score 0-1, evaluation_note)
        """
        if not response:
            return 0.0, "No response"
        
        # Check exact match
        if "expected_exact" in prompt_spec:
            expected = prompt_spec["expected_exact"].lower().strip()
            actual = response.lower().strip()
            if expected == actual or expected in actual:
                return 1.0, "Exact match"
            return 0.0, f"Expected '{expected}'"
        
        # Check contains
        if "expected_contains" in prompt_spec:
            expected_list = prompt_spec["expected_contains"]
            matches = sum(1 for e in expected_list if e.lower() in response.lower())
            score = matches / len(expected_list)
            return score, f"Contains {matches}/{len(expected_list)}"
        
        # Check JSON keys
        if "expected_json_keys" in prompt_spec:
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[^{}]*\}', response)
                if json_match:
                    data = json.loads(json_match.group())
                    expected_keys = prompt_spec["expected_json_keys"]
                    matches = sum(1 for k in expected_keys if k in data)
                    return matches / len(expected_keys), f"JSON keys {matches}/{len(expected_keys)}"
            except:
                pass
            return 0.0, "Invalid JSON"
        
        # Default: non-empty response is partial success
        return 0.5, "Response received"
    
    def _initialize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Initialize provenance and metric columns if not present."""
        # Provenance columns
        for col in self.PROVENANCE_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        # Metric columns for each category
        for category in self._eval_prompts:
            for suffix in self.METRIC_COLUMN_SUFFIXES:
                col = f"eval_{category}{suffix}"
                if col not in df.columns:
                    df[col] = None
        
        return df
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Run evaluations on models with incremental/sticky behavior."""
        
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
                asof_column="eval_asof_date",
                metric_columns=self._get_metric_columns(),
                rank_column="derived_rank_overall",
                eligibility_filter="in_openrouter",
            )
            
            self.logger.info("[DRY RUN] Would evaluate %d models", len(cohort))
            self.logger.info("[DRY RUN] Cohort metadata: %s", metadata)
            self.logger.info("[DRY RUN] Sample cohort (first 10): %s", cohort[:10])
            result.warnings.append(f"Dry run - would evaluate {len(cohort)} models")
            return df
        
        if not self.api_key:
            result.warnings.append("No OPENROUTER_API_KEY - skipping evaluations")
            return df
        
        if not self._eval_prompts:
            result.warnings.append("No eval prompts found")
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
            asof_column="eval_asof_date",
            metric_columns=self._get_metric_columns(),
            rank_column="derived_rank_overall",
            eligibility_filter="in_openrouter",
        )
        
        self.logger.info("Eval cohort selected: %d models (seed=%s, ttl=%d days)",
                        len(cohort), metadata.get("seed_key"), self.ttl_days)
        
        # Mark non-cohort eligible models with skipped_budget outcome (only if no prior outcome)
        eligible_mask = df["in_openrouter"] == True
        for idx, row in df[eligible_mask].iterrows():
            slug = row.get("openrouter_slug")
            if pd.isna(slug) or slug in cohort:
                continue
            
            # Only set skipped outcome if not already set
            current_outcome = row.get("eval_outcome")
            if pd.isna(current_outcome) or current_outcome == "":
                df.at[idx, "eval_outcome"] = OUTCOME_SKIPPED_BUDGET
        
        if len(cohort) == 0:
            self.logger.info("No models need evaluation (all within TTL)")
            return df
        
        enriched_count = 0
        error_count = 0
        
        for slug in cohort:
            matches = df[df["openrouter_slug"] == slug]
            if len(matches) == 0:
                continue
            
            idx = matches.index[0]
            
            model_scores: Dict[str, List[float]] = {}
            model_errors: List[str] = []
            
            for category, prompts in self._eval_prompts.items():
                category_scores = []
                
                for prompt_spec in prompts[:3]:  # Limit prompts per category for cost control
                    try:
                        response, latency, error = self._call_model(
                            slug,
                            prompt_spec["prompt"],
                        )
                        
                        if error:
                            model_errors.append(f"{category}: {error}")
                            continue
                        
                        score, note = self._evaluate_response(response, prompt_spec)
                        category_scores.append(score)
                    except Exception as e:
                        model_errors.append(f"{category}: {str(e)[:100]}")
                
                if category_scores:
                    avg_score = sum(category_scores) / len(category_scores)
                    df.at[idx, f"eval_{category}_score"] = round(avg_score, 3)
                    df.at[idx, f"eval_{category}_trials"] = len(category_scores)
                    model_scores[category] = category_scores
            
            # Record provenance
            df.at[idx, "eval_attempted"] = True
            df.at[idx, "eval_asof_date"] = now_iso
            df.at[idx, "eval_run_id"] = run_id
            df.at[idx, "eval_source_name"] = self.source_name
            
            if model_errors:
                df.at[idx, "eval_error"] = model_errors[-1][:200]
                error_count += 1
                df.at[idx, "eval_outcome"] = OUTCOME_ERROR if not model_scores else OUTCOME_SUCCESS
            else:
                df.at[idx, "eval_error"] = None
                df.at[idx, "eval_outcome"] = OUTCOME_SUCCESS
            
            if model_scores:
                enriched_count += 1
            
            # Rate limiting
            time.sleep(0.5)
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = error_count
        
        self.logger.info(
            "Eval harness completed: %d/%d models evaluated successfully, %d with errors",
            enriched_count, len(cohort), error_count
        )
        
        return df
