"""
Eval Harness Enricher

Runs deterministic evaluations on models via OpenRouter API.
Measures language and programming language capabilities.
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

logger = logging.getLogger(__name__)

# Eval prompt storage
EVALS_DIR = Path(__file__).parent.parent / "evals"

# OpenRouter API
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


class EvalHarnessEnricher(BaseEnricher):
    """
    Enricher that runs deterministic evaluations on models.
    
    Evaluates:
    - Natural language understanding (multiple languages)
    - Programming language capabilities
    - Tool use / structured output
    
    All evaluations use fixed prompts with verifiable answers.
    """
    
    name = "eval_harness"
    source_name = "LLMHive Eval Harness"
    source_url = ""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        dry_run: bool = False,
        cache_dir: Optional[str] = None,
        max_models: int = 0,  # 0 = no limit
        skip_expensive: bool = False,
        timeout_seconds: int = 30,
        max_cost_usd: float = 0.0,  # 0 = no limit
    ):
        super().__init__(dry_run=dry_run, cache_dir=cache_dir)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.max_models = max_models
        self.skip_expensive = skip_expensive
        self.timeout_seconds = timeout_seconds
        self.max_cost_usd = max_cost_usd
        self._eval_prompts: Dict[str, List[Dict[str, Any]]] = {}
        self._load_eval_prompts()
    
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
    
    def _do_enrich(self, df: pd.DataFrame, result: EnricherResult) -> pd.DataFrame:
        """Run evaluations on models."""
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would run evaluations")
            result.warnings.append("Dry run - no evaluations run")
            return df
        
        if not self.api_key:
            result.warnings.append("No OPENROUTER_API_KEY - skipping evaluations")
            return df
        
        if not self._eval_prompts:
            result.warnings.append("No eval prompts found")
            return df
        
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Initialize columns for each category
        eval_columns = [
            "eval_retrieved_at",
            "eval_source_name",
            "eval_confidence",
            "eval_error_count",
            "eval_last_error",
        ]
        
        # Add score columns for each category
        for category in self._eval_prompts:
            eval_columns.append(f"eval_{category}_score")
            eval_columns.append(f"eval_{category}_trials")
        
        for col in eval_columns:
            if col not in df.columns:
                df[col] = None
        
        # Filter models to evaluate
        models_to_eval = df[df["in_openrouter"] == True]["openrouter_slug"].dropna().tolist()
        
        if self.max_models > 0:
            models_to_eval = models_to_eval[:self.max_models]
        
        if self.skip_expensive:
            # Skip models with high input costs
            expensive_threshold = 10.0  # $10 per 1M tokens
            models_to_eval = [
                m for m in models_to_eval
                if float(df[df["openrouter_slug"] == m]["price_input_usd_per_1m"].iloc[0] or 0) < expensive_threshold
            ]
        
        self.logger.info("Evaluating %d models", len(models_to_eval))
        
        enriched_count = 0
        error_count = 0
        
        for slug in models_to_eval:
            idx = df[df["openrouter_slug"] == slug].index[0]
            
            model_scores: Dict[str, List[float]] = {}
            model_errors: List[str] = []
            
            for category, prompts in self._eval_prompts.items():
                category_scores = []
                
                for prompt_spec in prompts[:3]:  # Limit prompts per category for cost control
                    response, latency, error = self._call_model(
                        slug,
                        prompt_spec["prompt"],
                    )
                    
                    if error:
                        model_errors.append(f"{category}: {error}")
                        continue
                    
                    score, note = self._evaluate_response(response, prompt_spec)
                    category_scores.append(score)
                
                if category_scores:
                    avg_score = sum(category_scores) / len(category_scores)
                    df.at[idx, f"eval_{category}_score"] = round(avg_score, 3)
                    df.at[idx, f"eval_{category}_trials"] = len(category_scores)
                    model_scores[category] = category_scores
            
            # Record errors
            df.at[idx, "eval_error_count"] = len(model_errors)
            if model_errors:
                df.at[idx, "eval_last_error"] = model_errors[-1][:200]
                error_count += 1
            
            if model_scores:
                enriched_count += 1
            
            df.at[idx, "eval_retrieved_at"] = now_iso
            df.at[idx, "eval_source_name"] = self.source_name
            df.at[idx, "eval_confidence"] = "high" if not model_errors else "medium"
            
            # Rate limiting
            time.sleep(0.5)
        
        result.rows_enriched = enriched_count
        result.rows_with_gaps = error_count
        
        self.logger.info(
            "Eval harness completed: %d models evaluated, %d with errors",
            enriched_count, error_count
        )
        
        return df

