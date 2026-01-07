"""Anthropic Claude baseline benchmark runner.

This runner provides a clean baseline comparison against Anthropic Claude
without any orchestration enhancements.

IMPORTANT: This runner is OPTIONAL and only activates if ANTHROPIC_API_KEY is set.
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

# Check for Anthropic availability
ANTHROPIC_AVAILABLE = False
anthropic = None
AsyncAnthropic = None

try:
    import anthropic as anthropic_module
    from anthropic import AsyncAnthropic as _AsyncAnthropic
    anthropic = anthropic_module
    AsyncAnthropic = _AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    logger.debug("Anthropic SDK not installed - runner will be skipped")


class AnthropicRunner(RunnerBase):
    """Runner that executes prompts directly against Anthropic API.
    
    This provides a clean baseline without any orchestration overhead.
    Tools and RAG are NOT enabled to ensure fair comparison with raw model.
    """
    
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    
    def __init__(
        self,
        config: Optional[RunConfig] = None,
        model: Optional[str] = None,
    ):
        """Initialize the Anthropic runner.
        
        Args:
            config: Run configuration.
            model: Model to use (default: claude-3-5-sonnet).
        """
        super().__init__(config)
        self._model = model or os.getenv("ANTHROPIC_BENCHMARK_MODEL", self.DEFAULT_MODEL)
        self._client: Optional[Any] = None
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
    
    @property
    def system_name(self) -> str:
        return "Anthropic"
    
    @property
    def model_id(self) -> str:
        return self._model
    
    def _get_version(self) -> str:
        if anthropic:
            return getattr(anthropic, '__version__', 'unknown')
        return "unavailable"
    
    def _get_description(self) -> str:
        return f"Anthropic {self._model} baseline (no orchestration)"
    
    def _get_capabilities(self) -> Dict[str, bool]:
        return {
            "tools": False,  # Disabled for fair baseline
            "rag": False,
            "mcp2": False,
            "streaming": True,
            "function_calling": True,  # Available but not used
        }
    
    def is_available(self) -> bool:
        """Check if Anthropic runner is available.
        
        Returns True only if:
        1. Anthropic SDK is installed
        2. ANTHROPIC_API_KEY environment variable is set
        """
        if not ANTHROPIC_AVAILABLE:
            return False
        if not self._api_key:
            logger.debug("ANTHROPIC_API_KEY not set - Anthropic runner unavailable")
            return False
        return True
    
    def _get_client(self):
        """Lazily create the Anthropic client."""
        if self._client is None and ANTHROPIC_AVAILABLE and self._api_key:
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client
    
    async def run_case(
        self,
        case: BenchmarkCase,
        run_config: Optional[RunConfig] = None,
    ) -> RunResult:
        """Run a benchmark case against Anthropic.
        
        Args:
            case: The benchmark case to run.
            run_config: Optional config override.
        
        Returns:
            RunResult with response and metadata.
        """
        if not self.is_available():
            return self.skip_result(
                case.id,
                "Anthropic runner not available (missing SDK or API key)"
            )
        
        config = run_config or self.config
        client = self._get_client()
        
        if not client:
            return self.skip_result(case.id, "Failed to initialize Anthropic client")
        
        start_time = time.time()
        
        try:
            # Make API call with timeout
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self._model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                    system=(
                        "You are a helpful AI assistant. Answer questions accurately "
                        "and concisely. If you don't know something, say so."
                    ),
                    messages=[
                        {"role": "user", "content": case.prompt},
                    ],
                ),
                timeout=config.timeout_seconds,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response text
            answer_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    answer_text += block.text
            
            # Build metadata
            metadata = RunMetadata(
                models_used=[self._model],
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                # Estimate cost (Claude 3.5 Sonnet pricing)
                cost_usd=self._estimate_cost(response.usage),
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
                    "stop_reason": response.stop_reason,
                },
            )
            
        except asyncio.TimeoutError:
            return self.timeout_result(case.id, config.timeout_seconds)
        except Exception as e:
            # Never log API keys - redact any potential key exposure
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "sk-ant-" in error_msg:
                error_msg = "[REDACTED - potential key exposure]"
            
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"Anthropic error for case {case.id}: {error_msg}")
            return self.error_result(case.id, error_msg, latency_ms)
    
    def _estimate_cost(self, usage) -> float:
        """Estimate cost in USD based on usage.
        
        Uses Claude 3.5 Sonnet pricing (as of 2024):
        - Input: $0.003 per 1K tokens
        - Output: $0.015 per 1K tokens
        """
        if not usage:
            return 0.0
        
        input_cost = (usage.input_tokens / 1000) * 0.003
        output_cost = (usage.output_tokens / 1000) * 0.015
        return round(input_cost + output_cost, 6)


def get_anthropic_runner(
    config: Optional[RunConfig] = None,
    model: Optional[str] = None,
) -> AnthropicRunner:
    """Factory function to create an Anthropic runner.
    
    Args:
        config: Optional run configuration.
        model: Model to use (default: claude-3-5-sonnet).
    
    Returns:
        Configured AnthropicRunner instance.
    """
    return AnthropicRunner(config=config, model=model)

