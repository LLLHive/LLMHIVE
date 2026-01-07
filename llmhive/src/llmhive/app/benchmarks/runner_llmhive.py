"""LLMHive benchmark runner.

This runner executes benchmark cases through the same request path
as the frontend, either in local mode (direct Python call) or HTTP mode
(calling the FastAPI endpoint).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from .runner_base import (
    RunnerBase,
    RunConfig,
    BenchmarkCase,
    RunResult,
    RunMetadata,
    RunnerStatus,
    ToolTrace,
    RetrievalTrace,
    PlannerTrace,
    SystemInfo,
    get_git_commit_hash,
)

logger = logging.getLogger(__name__)


class LLMHiveRunner(RunnerBase):
    """Runner that executes prompts through LLMHive orchestration.
    
    Supports two modes:
    - local: Direct Python invocation of the orchestrator (faster, no network)
    - http: HTTP calls to the FastAPI backend (production-like)
    """
    
    def __init__(
        self,
        config: Optional[RunConfig] = None,
        mode: str = "local",
        base_url: Optional[str] = None,
    ):
        """Initialize the LLMHive runner.
        
        Args:
            config: Run configuration.
            mode: "local" for direct invocation, "http" for API calls.
            base_url: Base URL for HTTP mode (default: http://localhost:8000).
        """
        super().__init__(config)
        self.mode = mode
        self.base_url = base_url or os.getenv(
            "LLMHIVE_BENCHMARK_URL",
            "http://localhost:8000"
        )
        self._version = get_git_commit_hash() or "dev"
        
        # Lazy-load local mode dependencies
        self._orchestrator_adapter = None
        self._chat_request_model = None
        self._chat_response_model = None
    
    @property
    def system_name(self) -> str:
        return "LLMHive"
    
    @property
    def model_id(self) -> str:
        # LLMHive uses multiple models, so we report the configuration
        return f"llmhive-orchestrator-v{self._version}"
    
    def _get_version(self) -> str:
        return self._version
    
    def _get_description(self) -> str:
        return (
            "LLMHive multi-model orchestration system with RAG, "
            "Tool Broker, MCP2 sandbox, and quality policies"
        )
    
    def _get_capabilities(self) -> Dict[str, bool]:
        return {
            "tools": True,
            "rag": True,
            "mcp2": True,
            "streaming": True,
            "function_calling": True,
            "hrm": True,
            "deep_consensus": True,
            "verification": True,
            "refinement": True,
        }
    
    def is_available(self) -> bool:
        """LLMHive is always available in the benchmark context."""
        if self.mode == "local":
            try:
                from ..services.orchestrator_adapter import run_orchestration
                from ..models.orchestration import ChatRequest
                return True
            except ImportError as e:
                logger.warning(f"LLMHive local mode unavailable: {e}")
                return False
        else:
            # HTTP mode - assume available if we have a URL
            return bool(self.base_url)
    
    def _get_local_dependencies(self):
        """Lazily import local mode dependencies."""
        if self._orchestrator_adapter is None:
            from ..services.orchestrator_adapter import run_orchestration
            from ..models.orchestration import (
                ChatRequest,
                ChatResponse,
                OrchestrationSettings,
                TuningOptions,
                ChatMetadata,
                ReasoningMode,
                DomainPack,
                AgentMode,
            )
            self._orchestrator_adapter = run_orchestration
            self._chat_request_model = ChatRequest
            self._orchestration_settings = OrchestrationSettings
            self._tuning_settings = TuningOptions
            self._chat_metadata = ChatMetadata
            self._reasoning_mode = ReasoningMode
            self._domain_pack = DomainPack
            self._agent_mode = AgentMode
        return (
            self._orchestrator_adapter,
            self._chat_request_model,
            self._orchestration_settings,
            self._tuning_settings,
            self._chat_metadata,
            self._reasoning_mode,
            self._domain_pack,
            self._agent_mode,
        )
    
    async def run_case(
        self,
        case: BenchmarkCase,
        run_config: Optional[RunConfig] = None,
    ) -> RunResult:
        """Run a benchmark case through LLMHive.
        
        Args:
            case: The benchmark case to run.
            run_config: Optional config override.
        
        Returns:
            RunResult with response and metadata.
        """
        config = run_config or self.config
        start_time = time.time()
        
        try:
            if self.mode == "local":
                result = await self._run_local(case, config)
            else:
                result = await self._run_http(case, config)
            
            result.latency_ms = (time.time() - start_time) * 1000
            return result
            
        except asyncio.TimeoutError:
            return self.timeout_result(case.id, config.timeout_seconds)
        except Exception as e:
            logger.exception(f"Error running case {case.id}")
            latency_ms = (time.time() - start_time) * 1000
            return self.error_result(case.id, str(e), latency_ms)
    
    async def _run_local(
        self,
        case: BenchmarkCase,
        config: RunConfig,
    ) -> RunResult:
        """Run case in local mode (direct Python invocation)."""
        (
            run_orchestration,
            ChatRequest,
            OrchestrationSettings,
            TuningSettings,
            ChatMetadata,
            ReasoningMode,
            DomainPack,
            AgentMode,
        ) = self._get_local_dependencies()
        
        # Build orchestration settings
        orchestration = OrchestrationSettings(
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            accuracy_level=config.accuracy_level,
            enable_hrm=config.enable_hrm,
            enable_deep_consensus=config.enable_deep_consensus,
            enable_tool_broker=config.enable_tools,
            enable_verification=True,
            enable_memory=config.enable_rag,
        )
        
        # Build tuning settings
        tuning = TuningSettings(
            prompt_optimization=True,
            output_validation=True,
            answer_structure=True,
            learn_from_chat=False,  # Disable learning for benchmarks
        )
        
        # Build metadata
        metadata = ChatMetadata(
            user_id="benchmark-runner",
            chat_id=f"benchmark-{case.id}",
            criteria={
                "accuracy": 100,
                "speed": 50,
                "creativity": 30,
            },
        )
        
        # Create request
        request = ChatRequest(
            prompt=case.prompt,
            reasoning_mode=ReasoningMode(config.reasoning_mode),
            domain_pack=DomainPack.default,
            agent_mode=AgentMode.team,
            orchestration=orchestration,
            tuning=tuning,
            metadata=metadata,
            history=[],
        )
        
        # Run orchestration with timeout
        response = await asyncio.wait_for(
            run_orchestration(request),
            timeout=config.timeout_seconds,
        )
        
        # Extract metadata from response
        run_metadata = self._extract_metadata(response)
        
        return RunResult(
            system_name=self.system_name,
            model_id=self.model_id,
            prompt_id=case.id,
            status=RunnerStatus.SUCCESS,
            answer_text=response.message,
            structured_answer=self._get_structured_answer(response),
            metadata=run_metadata,
        )
    
    async def _run_http(
        self,
        case: BenchmarkCase,
        config: RunConfig,
    ) -> RunResult:
        """Run case in HTTP mode (API call)."""
        payload = {
            "prompt": case.prompt,
            "reasoning_mode": config.reasoning_mode,
            "domain_pack": "default",
            "agent_mode": "team",
            "orchestration": {
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
                "accuracy_level": config.accuracy_level,
                "enable_hrm": config.enable_hrm,
                "enable_deep_consensus": config.enable_deep_consensus,
                "enable_tool_broker": config.enable_tools,
                "enable_verification": True,
            },
            "tuning": {
                "prompt_optimization": True,
                "output_validation": True,
                "answer_structure": True,
                "learn_from_chat": False,
            },
            "metadata": {
                "user_id": "benchmark-runner",
                "chat_id": f"benchmark-{case.id}",
            },
            "history": [],
        }
        
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        
        # Extract metadata from HTTP response
        run_metadata = RunMetadata(
            models_used=data.get("models_used", []),
            tokens_in=0,  # Not available in HTTP response
            tokens_out=data.get("tokens_used", 0),
            tools_used=data.get("extra", {}).get("tools_used", []),
            trace_id=data.get("extra", {}).get("trace_id"),
        )
        
        return RunResult(
            system_name=self.system_name,
            model_id=self.model_id,
            prompt_id=case.id,
            status=RunnerStatus.SUCCESS,
            answer_text=data.get("message", ""),
            structured_answer=data,
            metadata=run_metadata,
        )
    
    def _extract_metadata(self, response) -> RunMetadata:
        """Extract detailed metadata from orchestrator response."""
        extra = getattr(response, 'extra', {}) or {}
        
        # Extract tool traces
        tool_traces = []
        raw_tool_traces = extra.get('tool_traces', [])
        for t in raw_tool_traces:
            tool_traces.append(ToolTrace(
                tool_name=t.get('tool_name', 'unknown'),
                triggered=t.get('triggered', False),
                success=t.get('success', False),
                execution_time_ms=t.get('execution_time_ms', 0),
            ))
        
        # Extract retrieval trace
        retrieval_trace = None
        raw_retrieval = extra.get('retrieval_trace')
        if raw_retrieval:
            retrieval_trace = RetrievalTrace(
                documents_fetched=raw_retrieval.get('documents_fetched', 0),
                top_score=raw_retrieval.get('top_score', 0.0),
                query_used=raw_retrieval.get('query_used', ''),
                rerank_model=raw_retrieval.get('rerank_model'),
            )
        
        # Extract planner trace
        planner_trace = None
        raw_planner = extra.get('planner_trace')
        if raw_planner:
            planner_trace = PlannerTrace(
                steps_planned=raw_planner.get('steps_planned', 0),
                steps_executed=raw_planner.get('steps_executed', 0),
                strategy=raw_planner.get('strategy', 'unknown'),
            )
        
        # Determine strategy used
        strategy_used = None
        if extra.get('hrm_used'):
            strategy_used = 'hrm'
        elif extra.get('consensus_used'):
            strategy_used = 'consensus'
        elif tool_traces:
            strategy_used = 'tools'
        elif retrieval_trace:
            strategy_used = 'rag'
        else:
            strategy_used = 'direct'
        
        return RunMetadata(
            models_used=getattr(response, 'models_used', []) or [],
            strategy_used=strategy_used,
            verification_status=extra.get('verification_status'),
            verification_score=extra.get('verification_score'),
            confidence=extra.get('confidence'),
            sources_count=len(extra.get('sources', [])),
            tools_used=extra.get('tools_used', []),
            tokens_in=extra.get('tokens_in', 0),
            tokens_out=getattr(response, 'tokens_used', 0) or 0,
            tool_traces=tool_traces,
            retrieval_trace=retrieval_trace,
            planner_trace=planner_trace,
            trace_id=extra.get('trace_id'),
        )
    
    def _get_structured_answer(self, response) -> Optional[Dict[str, Any]]:
        """Extract structured answer data from response."""
        try:
            return {
                "message": response.message,
                "models_used": getattr(response, 'models_used', []),
                "reasoning_mode": str(getattr(response, 'reasoning_mode', '')),
                "reasoning_method": str(getattr(response, 'reasoning_method', '')),
                "tokens_used": getattr(response, 'tokens_used', 0),
                "latency_ms": getattr(response, 'latency_ms', 0),
            }
        except Exception:
            return None


def get_llmhive_runner(
    mode: str = "local",
    config: Optional[RunConfig] = None,
) -> LLMHiveRunner:
    """Factory function to create an LLMHive runner.
    
    Args:
        mode: "local" or "http"
        config: Optional run configuration.
    
    Returns:
        Configured LLMHiveRunner instance.
    """
    return LLMHiveRunner(config=config, mode=mode)

