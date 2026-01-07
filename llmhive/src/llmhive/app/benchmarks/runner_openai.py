"""OpenAI baseline benchmark runner.

This runner provides a clean baseline comparison against OpenAI GPT-4 Turbo
without any orchestration enhancements.

IMPORTANT: This runner is OPTIONAL and only activates if OPENAI_API_KEY is set.
It will NEVER fail CI or expose API keys in logs.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
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

# Check for OpenAI availability
OPENAI_AVAILABLE = False
openai = None
AsyncOpenAI = None

try:
    import openai as openai_module
    from openai import AsyncOpenAI as _AsyncOpenAI
    openai = openai_module
    AsyncOpenAI = _AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    logger.debug("OpenAI SDK not installed - runner will be skipped")


class OpenAIRunner(RunnerBase):
    """Runner that executes prompts directly against OpenAI API.
    
    This provides a clean baseline without any orchestration overhead.
    Tools and RAG are NOT enabled to ensure fair comparison with raw model.
    """
    
    DEFAULT_MODEL = "gpt-4-turbo"
    
    def __init__(
        self,
        config: Optional[RunConfig] = None,
        model: Optional[str] = None,
    ):
        """Initialize the OpenAI runner.
        
        Args:
            config: Run configuration.
            model: Model to use (default: gpt-4-turbo).
        """
        super().__init__(config)
        self._model = model or os.getenv("OPENAI_BENCHMARK_MODEL", self.DEFAULT_MODEL)
        self._client: Optional[Any] = None
        self._api_key = os.getenv("OPENAI_API_KEY")
    
    @property
    def system_name(self) -> str:
        return "OpenAI"
    
    @property
    def model_id(self) -> str:
        return self._model
    
    def _get_version(self) -> str:
        if openai:
            return getattr(openai, '__version__', 'unknown')
        return "unavailable"
    
    def _get_description(self) -> str:
        return f"OpenAI {self._model} baseline (no orchestration)"
    
    def _get_capabilities(self) -> Dict[str, bool]:
        return {
            "tools": False,  # Disabled for fair baseline
            "rag": False,
            "mcp2": False,
            "streaming": True,
            "function_calling": True,  # Available but not used
        }
    
    def is_available(self) -> bool:
        """Check if OpenAI runner is available.
        
        Returns True only if:
        1. OpenAI SDK is installed
        2. OPENAI_API_KEY environment variable is set
        """
        if not OPENAI_AVAILABLE:
            return False
        if not self._api_key:
            logger.debug("OPENAI_API_KEY not set - OpenAI runner unavailable")
            return False
        return True
    
    def _get_client(self):
        """Lazily create the OpenAI client."""
        if self._client is None and OPENAI_AVAILABLE and self._api_key:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client
    
    async def run_case(
        self,
        case: BenchmarkCase,
        run_config: Optional[RunConfig] = None,
    ) -> RunResult:
        """Run a benchmark case against OpenAI.
        
        Args:
            case: The benchmark case to run.
            run_config: Optional config override.
        
        Returns:
            RunResult with response and metadata.
        """
        if not self.is_available():
            return self.skip_result(
                case.id,
                "OpenAI runner not available (missing SDK or API key)"
            )
        
        config = run_config or self.config
        client = self._get_client()
        
        if not client:
            return self.skip_result(case.id, "Failed to initialize OpenAI client")
        
        start_time = time.time()
        
        try:
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant. Answer questions accurately "
                        "and concisely. If you don't know something, say so."
                    ),
                },
                {"role": "user", "content": case.prompt},
            ]
            
            # Make API call with timeout
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    top_p=config.top_p,
                ),
                timeout=config.timeout_seconds,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response
            answer_text = response.choices[0].message.content or ""
            
            # Build metadata
            usage = response.usage
            metadata = RunMetadata(
                models_used=[self._model],
                tokens_in=usage.prompt_tokens if usage else 0,
                tokens_out=usage.completion_tokens if usage else 0,
                # Estimate cost (GPT-4 Turbo pricing as of 2024)
                cost_usd=self._estimate_cost(usage) if usage else None,
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
                    "id": response.id,
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason,
                },
            )
            
        except asyncio.TimeoutError:
            return self.timeout_result(case.id, config.timeout_seconds)
        except Exception as e:
            # Never log API keys - redact any potential key exposure
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "sk-" in error_msg:
                error_msg = "[REDACTED - potential key exposure]"
            
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"OpenAI error for case {case.id}: {error_msg}")
            return self.error_result(case.id, error_msg, latency_ms)
    
    def _estimate_cost(self, usage) -> float:
        """Estimate cost in USD based on usage.
        
        Uses GPT-4 Turbo pricing (as of 2024):
        - Input: $0.01 per 1K tokens
        - Output: $0.03 per 1K tokens
        """
        if not usage:
            return 0.0
        
        # Pricing varies by model - use GPT-4 Turbo as baseline
        input_cost = (usage.prompt_tokens / 1000) * 0.01
        output_cost = (usage.completion_tokens / 1000) * 0.03
        return round(input_cost + output_cost, 6)


def get_openai_runner(
    config: Optional[RunConfig] = None,
    model: Optional[str] = None,
) -> OpenAIRunner:
    """Factory function to create an OpenAI runner.
    
    Args:
        config: Optional run configuration.
        model: Model to use (default: gpt-4-turbo).
    
    Returns:
        Configured OpenAIRunner instance.
    """
    return OpenAIRunner(config=config, model=model)

