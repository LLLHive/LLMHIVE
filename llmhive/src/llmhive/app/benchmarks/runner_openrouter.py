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
        # =================================================================
        # TOP TIER: Latest Flagship Models (2025)
        # =================================================================
        # Anthropic Claude 4 Series
        "claude-opus-4": "anthropic/claude-opus-4",
        "claude-opus-4.5": "anthropic/claude-opus-4.5",
        "claude-sonnet-4": "anthropic/claude-sonnet-4",
        "claude-sonnet-4.5": "anthropic/claude-sonnet-4.5",
        "claude-haiku-4.5": "anthropic/claude-haiku-4.5",
        
        # Google Gemini 2.5/3 Series
        "gemini-2.5-pro": "google/gemini-2.5-pro",
        "gemini-2.5-flash": "google/gemini-2.5-flash",
        "gemini-3-pro": "google/gemini-3-pro-preview",
        "gemini-3-flash": "google/gemini-3-flash-preview",
        
        # DeepSeek R1 (Reasoning)
        "deepseek-r1": "deepseek/deepseek-r1",
        "deepseek-v3.2": "deepseek/deepseek-v3.2",
        "deepseek-v3": "deepseek/deepseek-chat",
        
        # OpenAI o1/o3 Reasoning
        "o1": "openai/o1",
        "o1-mini": "openai/o1-mini",
        "o1-preview": "openai/o1-preview",
        "o3-mini": "openai/o3-mini",
        
        # =================================================================
        # HIGH TIER: Current Generation Flagships
        # =================================================================
        # OpenAI GPT-4 Series
        "gpt-4o": "openai/gpt-4o",
        "gpt-4-turbo": "openai/gpt-4-turbo",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        
        # Anthropic Claude 3.x Series
        "claude-3.7-sonnet": "anthropic/claude-3.7-sonnet",
        "claude-3.5-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-3.5-haiku": "anthropic/claude-3.5-haiku",
        "claude-3-haiku": "anthropic/claude-3-haiku",
        
        # Google Gemini 2.0+ Series (1.5 series deprecated on OpenRouter)
        "gemini-2.0-flash": "google/gemini-2.0-flash-001",
        "gemini-2.5-flash": "google/gemini-2.5-flash",
        "gemini-2.5-pro": "google/gemini-2.5-pro",
        # Legacy aliases (mapped to newer versions)
        "gemini-1.5-pro": "google/gemini-2.5-pro",
        "gemini-1.5-flash": "google/gemini-2.5-flash",
        "gemini-pro": "google/gemini-2.5-pro",
        "gemini-flash": "google/gemini-2.5-flash",
        
        # =================================================================
        # STRONG TIER: Open Source & Specialized
        # =================================================================
        # Meta/Llama Models
        "llama-3.1-70b": "meta-llama/llama-3.1-70b-instruct",
        "llama-3.1-405b": "meta-llama/llama-3.1-405b-instruct",
        "llama-3.2-90b": "meta-llama/llama-3.2-90b-vision-instruct",
        
        # Mistral Models
        "mistral-large": "mistralai/mistral-large",
        "codestral": "mistralai/codestral-latest",
        "mixtral-8x22b": "mistralai/mixtral-8x22b-instruct",
        
        # Cohere Models
        "command-r-plus": "cohere/command-r-plus-08-2024",
        "command-a": "cohere/command-a",
        
        # Qwen Models
        "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct",
        "qwen-2.5-coder": "qwen/qwen-2.5-coder-32b-instruct",
        
        # xAI Grok
        "grok-2": "x-ai/grok-2-1212",
        "grok-beta": "x-ai/grok-beta",
        
        # Nous Research
        "hermes-3-70b": "nousresearch/hermes-3-llama-3.1-70b",
    }
    
    # Approximate costs per 1K tokens (input/output)
    MODEL_COSTS = {
        # OpenAI
        "openai/gpt-4-turbo": (0.01, 0.03),
        "openai/gpt-4o": (0.005, 0.015),
        "openai/gpt-4o-mini": (0.00015, 0.0006),
        "openai/o1": (0.015, 0.06),
        "openai/o1-mini": (0.003, 0.012),
        "openai/o1-preview": (0.015, 0.06),
        # Anthropic
        "anthropic/claude-opus-4": (0.015, 0.075),
        "anthropic/claude-opus-4.5": (0.015, 0.075),
        "anthropic/claude-sonnet-4": (0.003, 0.015),
        "anthropic/claude-sonnet-4.5": (0.003, 0.015),
        "anthropic/claude-haiku-4.5": (0.0008, 0.004),
        "anthropic/claude-3.7-sonnet": (0.003, 0.015),
        "anthropic/claude-3.5-sonnet": (0.003, 0.015),
        "anthropic/claude-3.5-haiku": (0.0008, 0.004),
        "anthropic/claude-3-opus": (0.015, 0.075),
        "anthropic/claude-3-sonnet": (0.003, 0.015),
        "anthropic/claude-3-haiku": (0.00025, 0.00125),
        # Google (2.0+ series - 1.5 deprecated on OpenRouter)
        "google/gemini-2.0-flash-001": (0.0001, 0.0004),
        "google/gemini-2.5-pro": (0.00125, 0.005),
        "google/gemini-2.5-flash": (0.0001, 0.0004),
        "google/gemini-2.5-pro-preview": (0.00125, 0.005),
        "google/gemini-3-pro-preview": (0.0015, 0.006),
        "google/gemini-3-flash-preview": (0.0001, 0.0004),
        # Meta
        "meta-llama/llama-3.1-70b-instruct": (0.0009, 0.0009),
        "meta-llama/llama-3.1-405b-instruct": (0.003, 0.003),
        "meta-llama/llama-3.2-90b-vision-instruct": (0.0009, 0.0009),
        # Mistral
        "mistralai/mistral-large": (0.002, 0.006),
        "mistralai/mistral-medium": (0.0027, 0.0081),
        "mistralai/codestral-latest": (0.001, 0.003),
        "mistralai/mixtral-8x22b-instruct": (0.0009, 0.0009),
        # DeepSeek
        "deepseek/deepseek-chat": (0.00014, 0.00028),
        "deepseek/deepseek-r1": (0.00055, 0.00219),
        "deepseek/deepseek-v3.2": (0.00027, 0.00110),
        "deepseek/deepseek-reasoner": (0.00055, 0.00219),
        "deepseek/deepseek-coder": (0.00014, 0.00028),
        # Cohere
        "cohere/command-r-plus": (0.003, 0.015),
        "cohere/command-r": (0.0005, 0.0015),
        # Qwen
        "qwen/qwen-2.5-72b-instruct": (0.0004, 0.0004),
        "qwen/qwen-2.5-coder-32b-instruct": (0.00015, 0.00015),
        # xAI
        "x-ai/grok-2-1212": (0.002, 0.01),
        "x-ai/grok-beta": (0.005, 0.015),
        # Nous
        "nousresearch/hermes-3-llama-3.1-70b": (0.0004, 0.0004),
        # Other
        "01-ai/yi-large": (0.0003, 0.0003),
        "microsoft/phi-3-medium-128k-instruct": (0.00014, 0.00014),
        "databricks/dbrx-instruct": (0.00075, 0.00075),
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
                error_message=self.skip_reason(),
                metadata=RunMetadata(),
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
            http_response = await asyncio.get_running_loop().run_in_executor(
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
    """Runner for Gemini 2.5 Pro via OpenRouter."""
    def __init__(self):
        super().__init__(model="gemini-2.5-pro")

