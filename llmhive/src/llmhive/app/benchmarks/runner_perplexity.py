"""Perplexity baseline benchmark runner.

This runner supports two modes:
1. LIVE: Direct API calls if PERPLEXITY_API_KEY is set
2. IMPORT: Load pre-captured responses from JSON for offline comparison

IMPORTANT: This runner is OPTIONAL. It will gracefully skip if neither
API key nor import file is available.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .runner_base import (
    RunnerBase,
    RunConfig,
    BenchmarkCase,
    RunResult,
    RunMetadata,
    RunnerStatus,
)

logger = logging.getLogger(__name__)

# Check for HTTP client availability
HTTPX_AVAILABLE = False
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.debug("httpx not installed - Perplexity live mode unavailable")


class PerplexityRunner(RunnerBase):
    """Runner that compares against Perplexity responses.
    
    Supports two modes:
    - live: Direct API calls (requires PERPLEXITY_API_KEY)
    - import: Load pre-captured responses from JSON file
    """
    
    DEFAULT_MODEL = "llama-3.1-sonar-large-128k-online"
    IMPORT_FILE = "benchmarks/baselines/perplexity_responses.json"
    
    def __init__(
        self,
        config: Optional[RunConfig] = None,
        model: Optional[str] = None,
        import_file: Optional[str] = None,
    ):
        """Initialize the Perplexity runner.
        
        Args:
            config: Run configuration.
            model: Model to use for live mode.
            import_file: Path to JSON file for import mode.
        """
        super().__init__(config)
        self._model = model or os.getenv("PERPLEXITY_BENCHMARK_MODEL", self.DEFAULT_MODEL)
        self._api_key = os.getenv("PERPLEXITY_API_KEY")
        self._import_file = import_file or self.IMPORT_FILE
        self._imported_responses: Optional[Dict[str, Any]] = None
        self._mode: Optional[str] = None
    
    @property
    def system_name(self) -> str:
        return "Perplexity"
    
    @property
    def model_id(self) -> str:
        if self._mode == "import":
            return "perplexity-imported"
        return self._model
    
    def _get_version(self) -> str:
        return "1.0.0"
    
    def _get_description(self) -> str:
        mode_desc = "(imported responses)" if self._mode == "import" else "(live API)"
        return f"Perplexity {self._model} baseline {mode_desc}"
    
    def _get_capabilities(self) -> Dict[str, bool]:
        return {
            "tools": False,
            "rag": True,  # Perplexity has built-in search
            "mcp2": False,
            "streaming": True,
            "function_calling": False,
            "web_search": True,  # Key Perplexity feature
        }
    
    def is_available(self) -> bool:
        """Check if Perplexity runner is available.
        
        Returns True if:
        1. Live mode: PERPLEXITY_API_KEY is set and httpx is available
        2. Import mode: Import file exists
        """
        # Check live mode
        if self._api_key and HTTPX_AVAILABLE:
            self._mode = "live"
            return True
        
        # Check import mode
        import_path = Path(self._import_file)
        if import_path.exists():
            self._mode = "import"
            self._load_imported_responses()
            return self._imported_responses is not None
        
        logger.debug("Perplexity runner unavailable - no API key or import file")
        return False
    
    def _load_imported_responses(self):
        """Load pre-captured responses from JSON file."""
        try:
            with open(self._import_file, 'r') as f:
                data = json.load(f)
            self._imported_responses = {
                item['prompt_id']: item
                for item in data.get('responses', [])
            }
            logger.info(f"Loaded {len(self._imported_responses)} Perplexity responses from {self._import_file}")
        except Exception as e:
            logger.warning(f"Failed to load Perplexity import file: {e}")
            self._imported_responses = None
    
    async def run_case(
        self,
        case: BenchmarkCase,
        run_config: Optional[RunConfig] = None,
    ) -> RunResult:
        """Run a benchmark case against Perplexity.
        
        Args:
            case: The benchmark case to run.
            run_config: Optional config override.
        
        Returns:
            RunResult with response and metadata.
        """
        if not self.is_available():
            return self.skip_result(
                case.id,
                "Perplexity runner not available"
            )
        
        if self._mode == "import":
            return self._run_import(case)
        else:
            config = run_config or self.config
            return await self._run_live(case, config)
    
    def _run_import(self, case: BenchmarkCase) -> RunResult:
        """Run case using imported responses."""
        if self._imported_responses is None:
            return self.skip_result(case.id, "Import responses not loaded")
        
        # Look up pre-captured response
        response_data = self._imported_responses.get(case.id)
        
        if not response_data:
            return self.skip_result(
                case.id,
                f"No imported response found for prompt {case.id}"
            )
        
        return RunResult(
            system_name=self.system_name,
            model_id="perplexity-imported",
            prompt_id=case.id,
            status=RunnerStatus.SUCCESS,
            answer_text=response_data.get('answer_text', ''),
            latency_ms=response_data.get('latency_ms', 0),
            metadata=RunMetadata(
                models_used=[response_data.get('model', 'unknown')],
                sources_count=response_data.get('citations_count', 0),
            ),
            structured_answer=response_data,
        )
    
    async def _run_live(
        self,
        case: BenchmarkCase,
        config: RunConfig,
    ) -> RunResult:
        """Run case using live Perplexity API."""
        if not HTTPX_AVAILABLE:
            return self.skip_result(case.id, "httpx not installed")
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a helpful AI assistant. Answer questions accurately "
                                    "and cite sources when possible."
                                ),
                            },
                            {"role": "user", "content": case.prompt},
                        ],
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                    },
                )
                response.raise_for_status()
                data = response.json()
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response
            answer_text = ""
            if data.get("choices"):
                message = data["choices"][0].get("message", {})
                answer_text = message.get("content", "")
            
            # Count citations if available
            citations_count = len(data.get("citations", []))
            
            # Build metadata
            usage = data.get("usage", {})
            metadata = RunMetadata(
                models_used=[self._model],
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
                sources_count=citations_count,
            )
            
            return RunResult(
                system_name=self.system_name,
                model_id=self.model_id,
                prompt_id=case.id,
                status=RunnerStatus.SUCCESS,
                answer_text=answer_text,
                latency_ms=latency_ms,
                metadata=metadata,
                structured_answer={
                    "id": data.get("id"),
                    "model": data.get("model"),
                    "citations": data.get("citations", []),
                },
            )
            
        except asyncio.TimeoutError:
            return self.timeout_result(case.id, config.timeout_seconds)
        except Exception as e:
            # Never log API keys
            error_msg = str(e)
            if "pplx-" in error_msg or "api_key" in error_msg.lower():
                error_msg = "[REDACTED - potential key exposure]"
            
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Perplexity error for case {case.id}: {error_msg}")
            return self.error_result(case.id, error_msg, latency_ms)


def get_perplexity_runner(
    config: Optional[RunConfig] = None,
    model: Optional[str] = None,
    import_file: Optional[str] = None,
) -> PerplexityRunner:
    """Factory function to create a Perplexity runner.
    
    Args:
        config: Optional run configuration.
        model: Model to use for live mode.
        import_file: Path to JSON file for import mode.
    
    Returns:
        Configured PerplexityRunner instance.
    """
    return PerplexityRunner(config=config, model=model, import_file=import_file)

