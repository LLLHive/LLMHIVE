"""OpenRouter Inference Gateway.

Provider adapter for running inference through OpenRouter:
- OpenAI-compatible request/response format
- Parameter validation against model capabilities
- Streaming support
- Tool/function calling
- Structured output
- Usage tracking and cost accounting
- Retry and circuit breaker patterns

Usage:
    from llmhive.app.openrouter import OpenRouterInferenceGateway
    
    gateway = OpenRouterInferenceGateway(db_session)
    response = await gateway.run_chat(
        model_id="openai/gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .client import OpenRouterClient, OpenRouterConfig
from .models import OpenRouterModel, OpenRouterUsageTelemetry, SavedRun

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================

class GatewayError(Exception):
    """Base gateway error."""
    pass


class ModelNotFoundError(GatewayError):
    """Model not found in catalog."""
    pass


class ModelUnavailableError(GatewayError):
    """Model temporarily unavailable."""
    pass


class ValidationError(GatewayError):
    """Parameter validation error."""
    pass


class CostLimitExceededError(GatewayError):
    """Cost limit exceeded."""
    pass


class CircuitOpenError(GatewayError):
    """Circuit breaker is open."""
    pass


class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ChatMessage:
    """Chat message."""
    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API format."""
        msg = {"role": self.role}
        if self.content is not None:
            msg["content"] = self.content
        if self.name:
            msg["name"] = self.name
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


@dataclass
class ChatResponse:
    """Chat completion response."""
    id: str
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None
    created: int = field(default_factory=lambda: int(time.time()))
    
    # Extended metadata
    provider: Optional[str] = None
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    generation_id: Optional[str] = None
    
    @property
    def content(self) -> Optional[str]:
        """Get first choice content."""
        if self.choices and self.choices[0].get("message"):
            return self.choices[0]["message"].get("content")
        return None
    
    @property
    def tool_calls(self) -> Optional[List[Dict[str, Any]]]:
        """Get tool calls from first choice."""
        if self.choices and self.choices[0].get("message"):
            return self.choices[0]["message"].get("tool_calls")
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "model": self.model,
            "choices": self.choices,
            "usage": self.usage,
            "created": self.created,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "generation_id": self.generation_id,
        }


@dataclass
class StreamChunk:
    """Streaming response chunk."""
    id: str
    model: str
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    
    @property
    def content_delta(self) -> Optional[str]:
        """Get content from delta."""
        return self.delta.get("content")
    
    @property
    def tool_calls_delta(self) -> Optional[List[Dict[str, Any]]]:
        """Get tool calls from delta."""
        return self.delta.get("tool_calls")


@dataclass
class GatewayConstraints:
    """Orchestrator constraints for gateway."""
    max_cost_usd: Optional[float] = None
    max_tokens: Optional[int] = None
    allowed_models: Optional[List[str]] = None
    denied_models: Optional[List[str]] = None
    tenant_id: Optional[str] = None
    redact_pii: bool = True
    log_content: bool = False


@dataclass
class CircuitBreaker:
    """Per-model circuit breaker."""
    model_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    open_until: Optional[float] = None
    
    # Configuration
    failure_threshold: int = 5
    reset_timeout_seconds: float = 60.0
    half_open_max_calls: int = 1
    half_open_calls: int = 0
    
    def record_success(self) -> None:
        """Record successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.half_open_calls = 0
    
    def record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.open_until = time.time() + self.reset_timeout_seconds
            logger.warning("Circuit opened for model %s", self.model_id)
    
    def allow_request(self) -> bool:
        """Check if request is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() > (self.open_until or 0):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        
        # Half-open
        if self.half_open_calls < self.half_open_max_calls:
            self.half_open_calls += 1
            return True
        return False


# =============================================================================
# Inference Gateway
# =============================================================================

class OpenRouterInferenceGateway:
    """Inference gateway for OpenRouter.
    
    Features:
    - Parameter validation against model capabilities
    - Streaming support with SSE
    - Tool/function calling
    - Structured output (JSON mode)
    - Circuit breaker for resilience
    - Cost tracking and limits
    - Telemetry recording
    
    Usage:
        gateway = OpenRouterInferenceGateway(db_session)
        
        # Simple chat
        response = await gateway.run_chat(
            model_id="openai/gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
        )
        
        # With tools
        response = await gateway.run_chat(
            model_id="openai/gpt-4o",
            messages=messages,
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "parameters": {...}
                }
            }],
        )
        
        # Streaming
        async for chunk in gateway.run_chat(
            model_id="openai/gpt-4o",
            messages=messages,
            stream=True,
        ):
            print(chunk.content_delta, end="")
    """
    
    def __init__(
        self,
        db_session: Session,
        client: Optional[OpenRouterClient] = None,
        config: Optional[OpenRouterConfig] = None,
    ):
        """Initialize gateway.
        
        Args:
            db_session: SQLAlchemy session
            client: OpenRouter client (created if not provided)
            config: Client config (loaded from env if not provided)
        """
        self.db = db_session
        self._client = client
        self._config = config
        self._owns_client = client is None
        
        # Circuit breakers per model
        self._circuits: Dict[str, CircuitBreaker] = {}
        
        # Model cache
        self._model_cache: Dict[str, OpenRouterModel] = {}
        self._cache_time: Optional[float] = None
        self._cache_ttl = 300  # 5 minutes
    
    async def _get_client(self) -> OpenRouterClient:
        """Get or create client."""
        if self._client is None:
            config = self._config or OpenRouterConfig.from_env()
            self._client = OpenRouterClient(config)
        return self._client
    
    def _get_circuit(self, model_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for model."""
        if model_id not in self._circuits:
            self._circuits[model_id] = CircuitBreaker(model_id=model_id)
        return self._circuits[model_id]
    
    def _get_model(self, model_id: str) -> Optional[OpenRouterModel]:
        """Get model from cache or database."""
        # Check cache
        now = time.time()
        if self._cache_time and (now - self._cache_time) > self._cache_ttl:
            self._model_cache.clear()
            self._cache_time = None
        
        if model_id in self._model_cache:
            return self._model_cache[model_id]
        
        # Query database
        model = self.db.query(OpenRouterModel).filter(
            OpenRouterModel.id == model_id,
            OpenRouterModel.is_active == True,
        ).first()
        
        if model:
            self._model_cache[model_id] = model
            self._cache_time = now
        
        return model
    
    def _validate_params(
        self,
        model: OpenRouterModel,
        params: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate and filter parameters against model capabilities.
        
        Args:
            model: Model from database
            params: Requested parameters
            tools: Tool definitions
            response_format: Response format spec
            
        Returns:
            Filtered/validated parameters
            
        Raises:
            ValidationError: If critical validation fails
        """
        supported = set(model.supported_params or [])
        validated = {}
        warnings = []
        
        # Standard parameters that are always passed
        always_allowed = {"model", "messages", "stream"}
        
        for key, value in params.items():
            if key in always_allowed:
                validated[key] = value
            elif key in supported:
                validated[key] = value
            else:
                # Drop unsupported params with warning
                warnings.append(f"Dropped unsupported param '{key}' for model {model.id}")
        
        if warnings:
            logger.warning("Parameter validation: %s", "; ".join(warnings))
        
        # Validate tools
        if tools:
            if not model.supports_tools:
                raise ValidationError(f"Model {model.id} does not support tools/functions")
            validated["tools"] = tools
        
        # Validate response format
        if response_format:
            if not model.supports_structured:
                raise ValidationError(f"Model {model.id} does not support structured output")
            validated["response_format"] = response_format
        
        return validated
    
    def _check_constraints(
        self,
        model: OpenRouterModel,
        constraints: GatewayConstraints,
        estimated_tokens: int = 0,
    ) -> None:
        """Check orchestrator constraints.
        
        Args:
            model: Model from database
            constraints: Orchestrator constraints
            estimated_tokens: Estimated input tokens
            
        Raises:
            ModelNotFoundError: If model is denied
            CostLimitExceededError: If cost would exceed limit
        """
        # Check allow/deny lists
        if constraints.denied_models and model.id in constraints.denied_models:
            raise ModelNotFoundError(f"Model {model.id} is denied by policy")
        
        if constraints.allowed_models and model.id not in constraints.allowed_models:
            raise ModelNotFoundError(f"Model {model.id} is not in allowed list")
        
        # Check cost limit
        if constraints.max_cost_usd and model.price_per_1m_prompt:
            estimated_cost = (estimated_tokens / 1_000_000) * float(model.price_per_1m_prompt)
            if estimated_cost > constraints.max_cost_usd:
                raise CostLimitExceededError(
                    f"Estimated cost ${estimated_cost:.4f} exceeds limit ${constraints.max_cost_usd}"
                )
        
        # Check token limit
        if constraints.max_tokens:
            if estimated_tokens > constraints.max_tokens:
                raise ValidationError(
                    f"Estimated tokens {estimated_tokens} exceeds limit {constraints.max_tokens}"
                )
    
    async def run_chat(
        self,
        model_id: str,
        messages: List[Union[Dict[str, Any], ChatMessage]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        constraints: Optional[GatewayConstraints] = None,
        save_run: bool = False,
        user_id: Optional[str] = None,
        **params,
    ) -> Union[ChatResponse, AsyncIterator[StreamChunk]]:
        """Run chat completion.
        
        Args:
            model_id: OpenRouter model ID
            messages: Chat messages
            tools: Tool definitions for function calling
            response_format: Response format (e.g., {"type": "json_object"})
            stream: Whether to stream response
            constraints: Orchestrator constraints
            save_run: Whether to save run metadata
            user_id: User ID for saved run
            **params: Additional model parameters
            
        Returns:
            ChatResponse or async iterator of StreamChunks
            
        Raises:
            ModelNotFoundError: Model not in catalog
            ModelUnavailableError: Model temporarily unavailable
            ValidationError: Invalid parameters
            CostLimitExceededError: Cost limit exceeded
            CircuitOpenError: Circuit breaker is open
        """
        constraints = constraints or GatewayConstraints()
        start_time = time.time()
        
        # Get model from database
        model = self._get_model(model_id)
        if not model:
            raise ModelNotFoundError(f"Model {model_id} not found in catalog")
        
        # Check circuit breaker
        circuit = self._get_circuit(model_id)
        if not circuit.allow_request():
            raise CircuitOpenError(f"Circuit breaker open for model {model_id}")
        
        # Normalize messages
        normalized_messages = [
            m.to_dict() if isinstance(m, ChatMessage) else m
            for m in messages
        ]
        
        # Estimate tokens (rough)
        estimated_tokens = sum(len(str(m.get("content", ""))) // 4 for m in normalized_messages)
        
        # Check constraints
        self._check_constraints(model, constraints, estimated_tokens)
        
        # Validate and filter params
        validated_params = self._validate_params(model, params, tools, response_format)
        
        try:
            client = await self._get_client()
            
            if stream:
                return self._stream_chat(
                    client=client,
                    model=model,
                    messages=normalized_messages,
                    params=validated_params,
                    circuit=circuit,
                    start_time=start_time,
                    constraints=constraints,
                    save_run=save_run,
                    user_id=user_id,
                )
            
            # Non-streaming
            response = await client.chat_completion(
                model=model_id,
                messages=normalized_messages,
                stream=False,
                **validated_params,
            )
            
            # Record success
            circuit.record_success()
            
            # Build response
            latency_ms = int((time.time() - start_time) * 1000)
            chat_response = ChatResponse(
                id=response.get("id", str(uuid.uuid4())),
                model=response.get("model", model_id),
                choices=response.get("choices", []),
                usage=response.get("usage"),
                created=response.get("created", int(time.time())),
                latency_ms=latency_ms,
                generation_id=response.get("id"),
            )
            
            # Calculate cost
            if chat_response.usage and model.pricing_prompt and model.pricing_completion:
                prompt_cost = (chat_response.usage.get("prompt_tokens", 0) / 1_000_000) * float(model.price_per_1m_prompt or 0)
                completion_cost = (chat_response.usage.get("completion_tokens", 0) / 1_000_000) * float(model.price_per_1m_completion or 0)
                chat_response.cost_usd = prompt_cost + completion_cost
            
            # Record telemetry
            await self._record_telemetry(
                model_id=model_id,
                success=True,
                latency_ms=latency_ms,
                usage=chat_response.usage,
                cost_usd=chat_response.cost_usd,
                tenant_id=constraints.tenant_id,
                used_tools=bool(chat_response.tool_calls),
                streamed=False,
            )
            
            # Save run if requested
            if save_run and user_id:
                await self._save_run(
                    user_id=user_id,
                    model_id=model_id,
                    response=chat_response,
                    messages=normalized_messages,
                    params=validated_params,
                    store_content=constraints.log_content,
                )
            
            return chat_response
            
        except Exception as e:
            circuit.record_failure()
            
            # Record failure telemetry
            await self._record_telemetry(
                model_id=model_id,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                tenant_id=constraints.tenant_id,
            )
            
            raise
    
    async def _stream_chat(
        self,
        client: OpenRouterClient,
        model: OpenRouterModel,
        messages: List[Dict[str, Any]],
        params: Dict[str, Any],
        circuit: CircuitBreaker,
        start_time: float,
        constraints: GatewayConstraints,
        save_run: bool,
        user_id: Optional[str],
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat completion.
        
        Yields:
            StreamChunk objects
        """
        accumulated_content = ""
        usage: Optional[Dict[str, int]] = None
        generation_id: Optional[str] = None
        
        try:
            async for chunk_data in await client.chat_completion(
                model=model.id,
                messages=messages,
                stream=True,
                **params,
            ):
                # Parse chunk
                chunk = StreamChunk(
                    id=chunk_data.get("id", ""),
                    model=chunk_data.get("model", model.id),
                    delta=chunk_data.get("choices", [{}])[0].get("delta", {}),
                    finish_reason=chunk_data.get("choices", [{}])[0].get("finish_reason"),
                    usage=chunk_data.get("usage"),
                )
                
                if chunk.content_delta:
                    accumulated_content += chunk.content_delta
                
                if chunk.usage:
                    usage = chunk.usage
                
                if not generation_id:
                    generation_id = chunk_data.get("id")
                
                yield chunk
            
            # Success
            circuit.record_success()
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate cost
            cost_usd = None
            if usage and model.pricing_prompt and model.pricing_completion:
                prompt_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * float(model.price_per_1m_prompt or 0)
                completion_cost = (usage.get("completion_tokens", 0) / 1_000_000) * float(model.price_per_1m_completion or 0)
                cost_usd = prompt_cost + completion_cost
            
            # Record telemetry
            await self._record_telemetry(
                model_id=model.id,
                success=True,
                latency_ms=latency_ms,
                usage=usage,
                cost_usd=cost_usd,
                tenant_id=constraints.tenant_id,
                streamed=True,
            )
            
        except Exception as e:
            circuit.record_failure()
            await self._record_telemetry(
                model_id=model.id,
                success=False,
                latency_ms=int((time.time() - start_time) * 1000),
                tenant_id=constraints.tenant_id,
            )
            raise
    
    async def _record_telemetry(
        self,
        model_id: str,
        success: bool,
        latency_ms: int,
        usage: Optional[Dict[str, int]] = None,
        cost_usd: Optional[float] = None,
        tenant_id: Optional[str] = None,
        used_tools: bool = False,
        streamed: bool = False,
    ) -> None:
        """Record usage telemetry for rankings."""
        try:
            # Get or create hourly bucket
            now = datetime.now(timezone.utc)
            bucket = now.replace(minute=0, second=0, microsecond=0)
            
            existing = self.db.query(OpenRouterUsageTelemetry).filter(
                OpenRouterUsageTelemetry.model_id == model_id,
                OpenRouterUsageTelemetry.tenant_id == tenant_id,
                OpenRouterUsageTelemetry.time_bucket == bucket,
            ).first()
            
            if existing:
                telemetry = existing
                telemetry.request_count += 1
                if success:
                    telemetry.success_count += 1
                else:
                    telemetry.error_count += 1
                telemetry.total_latency_ms += latency_ms
                telemetry.min_latency_ms = min(telemetry.min_latency_ms or latency_ms, latency_ms)
                telemetry.max_latency_ms = max(telemetry.max_latency_ms or 0, latency_ms)
            else:
                telemetry = OpenRouterUsageTelemetry(
                    model_id=model_id,
                    tenant_id=tenant_id,
                    time_bucket=bucket,
                    request_count=1,
                    success_count=1 if success else 0,
                    error_count=0 if success else 1,
                    total_latency_ms=latency_ms,
                    min_latency_ms=latency_ms,
                    max_latency_ms=latency_ms,
                )
                self.db.add(telemetry)
            
            if usage:
                telemetry.total_prompt_tokens += usage.get("prompt_tokens", 0)
                telemetry.total_completion_tokens += usage.get("completion_tokens", 0)
            
            if cost_usd:
                telemetry.total_cost_usd = Decimal(str(
                    float(telemetry.total_cost_usd or 0) + cost_usd
                ))
            
            if used_tools:
                telemetry.tool_call_count += 1
                if success:
                    telemetry.tool_success_count += 1
            
            if streamed:
                telemetry.streaming_request_count += 1
            
            self.db.commit()
            
        except Exception as e:
            logger.warning("Failed to record telemetry: %s", e)
            self.db.rollback()
    
    async def _save_run(
        self,
        user_id: str,
        model_id: str,
        response: ChatResponse,
        messages: List[Dict[str, Any]],
        params: Dict[str, Any],
        store_content: bool = False,
    ) -> None:
        """Save run metadata."""
        try:
            prompt_str = str(messages)
            response_str = response.content or ""
            
            run = SavedRun(
                id=str(uuid.uuid4()),
                user_id=user_id,
                model_id=model_id,
                run_at=datetime.now(timezone.utc),
                latency_ms=response.latency_ms,
                prompt_tokens=response.usage.get("prompt_tokens") if response.usage else None,
                completion_tokens=response.usage.get("completion_tokens") if response.usage else None,
                cost_usd=Decimal(str(response.cost_usd)) if response.cost_usd else None,
                success=True,
                params_used=params,
                store_content=store_content,
                prompt_hash=hashlib.sha256(prompt_str.encode()).hexdigest(),
                prompt_length=len(prompt_str),
                response_hash=hashlib.sha256(response_str.encode()).hexdigest(),
                response_length=len(response_str),
                generation_id=response.generation_id,
            )
            
            if store_content:
                run.prompt_content = prompt_str
                run.response_content = response_str
            
            self.db.add(run)
            self.db.commit()
            
        except Exception as e:
            logger.warning("Failed to save run: %s", e)
            self.db.rollback()
    
    async def run_completion(
        self,
        model_id: str,
        prompt: str,
        **params,
    ) -> Dict[str, Any]:
        """Run legacy completion (non-chat).
        
        Only for legacy workflows. Prefer run_chat for new code.
        """
        model = self._get_model(model_id)
        if not model:
            raise ModelNotFoundError(f"Model {model_id} not found")
        
        client = await self._get_client()
        return await client.legacy_completion(model_id, prompt, **params)
    
    async def close(self) -> None:
        """Close gateway and release resources."""
        if self._owns_client and self._client:
            await self._client.close()
            self._client = None

