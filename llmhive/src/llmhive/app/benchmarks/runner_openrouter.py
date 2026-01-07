"""OpenRouter Benchmark Runner.

Runs benchmark cases against OpenRouter-hosted models for baseline comparison.
This provides access to GPT-4, Claude, Gemini, and other models through a unified API.
"""
import asyncio
import logging
import os
import time
from typing import Dict, Any, Optional, List

from .runner_base import (
    RunnerBase,
    BenchmarkCase,
    RunConfig,
    RunResult,
    RunMetadata,
    RunnerStatus,
)

logger = logging.getLogger(__name__)


class OpenRouterRunner(RunnerBase):
    """Runner for OpenRouter-hosted models.
    
    Supports:
    - openai/gpt-4-turbo
    - openai/gpt-4o
    - anthropic/claude-3-opus
    - anthropic/claude-3.5-sonnet
    - google/gemini-pro
    - And many more via OpenRouter
    """
    
    AVAILABLE_MODELS = {
        "gpt-4-turbo": "openai/gpt-4-turbo",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "claude-3-opus": "anthropic/claude-3-opus",
        "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-3-haiku": "anthropic/claude-3-haiku",
        "gemini-pro": "google/gemini-pro",
        "gemini-1.5-pro": "google/gemini-pro-1.5",
        "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
        "mistral-large": "mistralai/mistral-large",
    }
    
    # Approximate costs per 1K tokens (input/output)
    MODEL_COSTS = {
        "openai/gpt-4-turbo": (0.01, 0.03),
        "openai/gpt-4o": (0.005, 0.015),
        "openai/gpt-4o-mini": (0.00015, 0.0006),
        "anthropic/claude-3-opus": (0.015, 0.075),
        "anthropic/claude-3.5-sonnet": (0.003, 0.015),
        "anthropic/claude-3-haiku": (0.00025, 0.00125),
        "google/gemini-pro": (0.000125, 0.000375),
        "google/gemini-pro-1.5": (0.00125, 0.005),
        "meta-llama/llama-3.1-70b-instruct": (0.0009, 0.0009),
        "mistralai/mistral-large": (0.002, 0.006),
    }
    
    def __init__(self, model: str = "gpt-4o"):
        """Initialize OpenRouter runner.
        
        Args:
            model: Model shorthand (e.g., "gpt-4o") or full OpenRouter ID
        """
        super().__init__()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Resolve model shorthand to full OpenRouter ID
        if model in self.AVAILABLE_MODELS:
            self._model_id = self.AVAILABLE_MODELS[model]
            self._model_name = model
        else:
            self._model_id = model
            self._model_name = model.split("/")[-1] if "/" in model else model
        
        self._client = None
    
    @property
    def system_name(self) -> str:
        return f"OpenRouter-{self._model_name}"
    
    @property
    def model_id(self) -> str:
        return self._model_id
    
    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self.api_key)
    
    def skip_reason(self) -> Optional[str]:
        """Return reason for skipping if not available."""
        if not self.api_key:
            return "OPENROUTER_API_KEY environment variable not set"
        return None
    
    def _get_client(self):
        """Get or create HTTP client for OpenRouter."""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.Client(
                    base_url="https://openrouter.ai/api/v1",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://llmhive.ai",
                        "X-Title": "LLMHive Benchmark",
                    },
                    timeout=120.0,
                )
            except ImportError:
                raise RuntimeError("httpx package required")
        return self._client
    
    async def run_case(
        self,
        case: BenchmarkCase,
        config: RunConfig,
    ) -> RunResult:
        """Run a benchmark case against OpenRouter model."""
        
        # Check availability
        if not self.is_available():
            return RunResult(
                system_name=self.system_name,
                model_id=self.model_id,
                prompt_id=case.id,
                status=RunnerStatus.SKIPPED,
                answer_text="",
                metadata=RunMetadata(skipped=True, skipped_reason=self.skip_reason()),
            )
        
        start_time = time.perf_counter()
        
        try:
            client = self._get_client()
            
            # Build messages
            messages = [{"role": "user", "content": case.prompt}]
            
            # Add system prompt if case specifies context
            if case.requirements and case.requirements.get("system_context"):
                messages.insert(0, {
                    "role": "system",
                    "content": case.requirements["system_context"]
                })
            
            # Build request payload
            payload = {
                "model": self._model_id,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens or 2000,
            }
            
            # Make API call in thread pool (httpx client is sync)
            loop = asyncio.get_event_loop()
            http_response = await loop.run_in_executor(
                None,
                lambda: client.post("/chat/completions", json=payload)
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Parse response
            if http_response.status_code != 200:
                raise RuntimeError(f"API error: {http_response.status_code} - {http_response.text[:200]}")
            
            response = http_response.json()
            
            # Extract answer
            answer = response.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            
            # Extract usage
            usage = response.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            
            # Calculate cost
            cost_usd = None
            if self.model_id in self.MODEL_COSTS:
                in_cost, out_cost = self.MODEL_COSTS[self.model_id]
                cost_usd = (tokens_in / 1000) * in_cost + (tokens_out / 1000) * out_cost
            
            return RunResult(
                system_name=self.system_name,
                model_id=self.model_id,
                prompt_id=case.id,
                status=RunnerStatus.SUCCESS,
                answer_text=answer,
                latency_ms=latency_ms,
                metadata=RunMetadata(
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                    raw_provider_payload={
                        "model": response.get("model", self._model_id),
                        "finish_reason": response.get("choices", [{}])[0].get("finish_reason", ""),
                    },
                ),
            )
            
        except asyncio.TimeoutError:
            return RunResult(
                system_name=self.system_name,
                model_id=self.model_id,
                prompt_id=case.id,
                status=RunnerStatus.TIMEOUT,
                answer_text="",
                latency_ms=(time.perf_counter() - start_time) * 1000,
                error_message="Request timed out",
                metadata=RunMetadata(),
            )
            
        except Exception as e:
            logger.error("OpenRouter run failed: %s", e)
            return RunResult(
                system_name=self.system_name,
                model_id=self.model_id,
                prompt_id=case.id,
                status=RunnerStatus.ERROR,
                answer_text="",
                latency_ms=(time.perf_counter() - start_time) * 1000,
                error_message=str(e),
                metadata=RunMetadata(),
            )


# Convenience aliases for common models
class GPT4TurboRunner(OpenRouterRunner):
    """Runner for GPT-4 Turbo via OpenRouter."""
    def __init__(self):
        super().__init__(model="gpt-4-turbo")


class GPT4oRunner(OpenRouterRunner):
    """Runner for GPT-4o via OpenRouter."""
    def __init__(self):
        super().__init__(model="gpt-4o")


class Claude3OpusRunner(OpenRouterRunner):
    """Runner for Claude 3 Opus via OpenRouter."""
    def __init__(self):
        super().__init__(model="claude-3-opus")


class Claude35SonnetRunner(OpenRouterRunner):
    """Runner for Claude 3.5 Sonnet via OpenRouter."""
    def __init__(self):
        super().__init__(model="claude-3.5-sonnet")


class GeminiProRunner(OpenRouterRunner):
    """Runner for Gemini Pro via OpenRouter."""
    def __init__(self):
        super().__init__(model="gemini-pro")

