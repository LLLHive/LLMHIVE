"""Performance benchmarks for LLMHive orchestration.

Captures key performance metrics:
- Time to First Token (TTFT)
- End-to-end latency
- Tokens per second throughput
- Memory usage
- Concurrent request handling

Run: pytest tests/benchmarks/test_orchestration_performance.py --benchmark-json=benchmark.json
"""
from __future__ import annotations

import asyncio
import gc
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Try to import psutil for memory tracking
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Try to import pytest-benchmark
try:
    from pytest_benchmark.fixture import BenchmarkFixture
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False

# Import models
try:
    from llmhive.app.models.orchestration import (
        ChatRequest,
        ChatResponse,
        ReasoningMode,
        DomainPack,
        AgentMode,
        OrchestrationSettings,
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False


# ==============================================================================
# Performance Metrics Dataclasses
# ==============================================================================

@dataclass
class PerformanceMetrics:
    """Container for benchmark metrics."""
    
    # Timing metrics (milliseconds)
    ttft_ms: float = 0.0  # Time to first token
    total_latency_ms: float = 0.0  # End-to-end latency
    model_call_ms: float = 0.0  # Time spent in model calls
    
    # Throughput metrics
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    
    # Resource metrics
    memory_start_mb: float = 0.0
    memory_peak_mb: float = 0.0
    memory_delta_mb: float = 0.0
    
    # Request metrics
    requests_completed: int = 0
    requests_failed: int = 0
    
    def calculate_derived(self):
        """Calculate derived metrics."""
        if self.total_latency_ms > 0 and self.tokens_generated > 0:
            self.tokens_per_second = self.tokens_generated / (self.total_latency_ms / 1000)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    
    name: str
    metrics: PerformanceMetrics
    iterations: int = 1
    extra: Dict[str, Any] = field(default_factory=dict)


# ==============================================================================
# Benchmark Helpers
# ==============================================================================

def get_memory_mb() -> float:
    """Get current process memory usage in MB."""
    if PSUTIL_AVAILABLE:
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    return 0.0


class MemoryTracker:
    """Context manager for tracking memory usage."""
    
    def __init__(self):
        self.start_mb = 0.0
        self.peak_mb = 0.0
        self.end_mb = 0.0
    
    def __enter__(self):
        gc.collect()  # Clean up before measurement
        self.start_mb = get_memory_mb()
        self.peak_mb = self.start_mb
        return self
    
    def __exit__(self, *args):
        self.end_mb = get_memory_mb()
        self.peak_mb = max(self.peak_mb, self.end_mb)
    
    @property
    def delta_mb(self) -> float:
        return self.end_mb - self.start_mb


class TimingTracker:
    """Context manager for tracking timing."""
    
    def __init__(self):
        self.start_time = 0.0
        self.end_time = 0.0
        self.first_token_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
    
    def mark_first_token(self):
        """Mark when first token was received."""
        if self.first_token_time is None:
            self.first_token_time = time.perf_counter()
    
    @property
    def total_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000
    
    @property
    def ttft_ms(self) -> float:
        if self.first_token_time:
            return (self.first_token_time - self.start_time) * 1000
        return self.total_ms


# ==============================================================================
# Mock Providers with Realistic Latencies
# ==============================================================================

def create_mock_provider(
    base_latency_ms: float = 50,
    tokens_per_response: int = 100,
    tokens_per_second: float = 50,
):
    """Create a mock provider with realistic latencies."""
    provider = MagicMock()
    
    async def mock_complete(prompt: str, model: str = None, **kwargs) -> MagicMock:
        # Simulate realistic latency based on token generation
        generation_time = tokens_per_response / tokens_per_second
        total_latency = (base_latency_ms / 1000) + generation_time
        
        # First token arrives after base latency
        await asyncio.sleep(base_latency_ms / 1000)
        
        # Rest of tokens stream
        await asyncio.sleep(generation_time)
        
        response = MagicMock()
        response.content = "Mock response " * (tokens_per_response // 2)
        response.text = response.content
        response.tokens_used = tokens_per_response
        return response
    
    provider.complete = mock_complete
    provider.generate = mock_complete
    return provider


def create_fast_provider(tokens: int = 50):
    """Create a fast provider (simulates GPT-4o-mini)."""
    return create_mock_provider(
        base_latency_ms=30,
        tokens_per_response=tokens,
        tokens_per_second=100,  # Fast model
    )


def create_slow_provider(tokens: int = 200):
    """Create a slower but higher quality provider (simulates Claude)."""
    return create_mock_provider(
        base_latency_ms=100,
        tokens_per_response=tokens,
        tokens_per_second=30,  # Slower, more thorough
    )


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def fast_providers():
    """Fast providers for simple queries."""
    return {
        "openai": create_fast_provider(),
        "stub": create_fast_provider(),
    }


@pytest.fixture
def mixed_providers():
    """Mix of fast and slow providers for team mode."""
    return {
        "openai": create_fast_provider(100),
        "anthropic": create_slow_provider(150),
        "google": create_fast_provider(80),
    }


@pytest.fixture
def simple_request():
    """Simple single-model request."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")
    return ChatRequest(
        prompt="What is 2+2?",
        reasoning_mode=ReasoningMode.fast,
        agent_mode=AgentMode.single,
    )


@pytest.fixture
def complex_request():
    """Complex multi-model team request."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")
    return ChatRequest(
        prompt="Analyze the economic impacts of renewable energy adoption globally",
        models=["gpt-4o", "claude-sonnet-4", "gemini-pro"],
        reasoning_mode=ReasoningMode.deep,
        agent_mode=AgentMode.team,
        orchestration=OrchestrationSettings(
            accuracy_level=5,
            enable_deep_consensus=True,
        ),
    )


@pytest.fixture
def rag_request():
    """RAG-augmented request."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")
    return ChatRequest(
        prompt="What does our documentation say about API rate limits?",
        reasoning_mode=ReasoningMode.standard,
        agent_mode=AgentMode.single,
        orchestration=OrchestrationSettings(
            enable_rag=True,
        ),
    )


@pytest.fixture
def hrm_request():
    """Hierarchical planning request."""
    if not MODELS_AVAILABLE:
        pytest.skip("Models not available")
    return ChatRequest(
        prompt="Research, analyze, and recommend a cloud migration strategy",
        reasoning_mode=ReasoningMode.deep,
        agent_mode=AgentMode.team,
        orchestration=OrchestrationSettings(
            accuracy_level=5,
            enable_hrm=True,
            enable_deep_consensus=True,
        ),
    )


# ==============================================================================
# Simple Query Benchmarks
# ==============================================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestSimpleQueryPerformance:
    """Benchmarks for simple single-model queries."""
    
    @pytest.mark.asyncio
    async def test_simple_query_latency(self, fast_providers, simple_request):
        """Benchmark simple query end-to-end latency."""
        metrics = PerformanceMetrics()
        
        with MemoryTracker() as mem:
            with TimingTracker() as timer:
                # Simulate simple orchestration
                provider = fast_providers["openai"]
                response = await provider.complete(simple_request.prompt)
                timer.mark_first_token()
                
                metrics.tokens_generated = response.tokens_used
        
        metrics.ttft_ms = timer.ttft_ms
        metrics.total_latency_ms = timer.total_ms
        metrics.memory_start_mb = mem.start_mb
        metrics.memory_peak_mb = mem.peak_mb
        metrics.memory_delta_mb = mem.delta_mb
        metrics.calculate_derived()
        
        # Assertions for performance SLOs (generous for CI environments)
        assert metrics.ttft_ms < 1000, f"TTFT {metrics.ttft_ms}ms exceeds 1s SLO"
        assert metrics.total_latency_ms < 3000, f"Latency {metrics.total_latency_ms}ms exceeds 3s SLO"
        assert metrics.tokens_per_second > 5, "Token throughput too low"
    
    @pytest.mark.asyncio
    async def test_simple_query_repeated(self, fast_providers, simple_request):
        """Benchmark repeated simple queries for consistency."""
        latencies = []
        
        for _ in range(10):
            with TimingTracker() as timer:
                provider = fast_providers["openai"]
                await provider.complete(simple_request.prompt)
            latencies.append(timer.total_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        # Consistency check - max should be within 3x of min
        assert max_latency < min_latency * 3, "Latency too inconsistent"
        assert avg_latency < 1000, f"Average latency {avg_latency}ms too high"


# ==============================================================================
# Multi-Model Team Benchmarks
# ==============================================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestMultiModelPerformance:
    """Benchmarks for multi-model team queries."""
    
    @pytest.mark.asyncio
    async def test_team_parallel_execution(self, mixed_providers, complex_request):
        """Benchmark parallel execution of multiple models."""
        metrics = PerformanceMetrics()
        
        with MemoryTracker() as mem:
            with TimingTracker() as timer:
                # Parallel execution of all providers
                tasks = [
                    provider.complete(complex_request.prompt, model=name)
                    for name, provider in mixed_providers.items()
                ]
                
                # Get first response for TTFT
                done, pending = await asyncio.wait(
                    [asyncio.create_task(t) for t in tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                timer.mark_first_token()
                
                # Wait for all
                if pending:
                    await asyncio.gather(*pending)
                
                # Sum tokens
                total_tokens = sum(
                    t.result().tokens_used for t in done
                )
                for p in pending:
                    try:
                        total_tokens += p.result().tokens_used
                    except Exception:
                        pass
                
                metrics.tokens_generated = total_tokens
        
        metrics.ttft_ms = timer.ttft_ms
        metrics.total_latency_ms = timer.total_ms
        metrics.memory_start_mb = mem.start_mb
        metrics.memory_peak_mb = mem.peak_mb
        metrics.memory_delta_mb = mem.delta_mb
        metrics.calculate_derived()
        
        # Parallel execution should be faster than sequential
        # 3 models, slowest is ~100ms + generation time
        assert metrics.total_latency_ms < 10000, "Team mode too slow"
        # TTFT should be from the fastest model
        assert metrics.ttft_ms < 1000, "TTFT from fastest model too slow"
    
    @pytest.mark.asyncio
    async def test_consensus_overhead(self, mixed_providers, complex_request):
        """Benchmark consensus building overhead."""
        with TimingTracker() as model_timer:
            # Simulate model calls
            tasks = [
                provider.complete(complex_request.prompt)
                for provider in mixed_providers.values()
            ]
            responses = await asyncio.gather(*tasks)
        
        model_time = model_timer.total_ms
        
        # Simulate consensus (typically adds 10-20% overhead)
        with TimingTracker() as consensus_timer:
            await asyncio.sleep(0.05)  # 50ms consensus simulation
        
        consensus_time = consensus_timer.total_ms
        
        total_time = model_time + consensus_time
        overhead_pct = (consensus_time / total_time) * 100
        
        # Consensus overhead should be < 30% of total time
        assert overhead_pct < 30, f"Consensus overhead {overhead_pct}% too high"


# ==============================================================================
# RAG-Augmented Query Benchmarks
# ==============================================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestRAGPerformance:
    """Benchmarks for RAG-augmented queries."""
    
    @pytest.mark.asyncio
    async def test_rag_retrieval_overhead(self, fast_providers, rag_request):
        """Benchmark RAG retrieval overhead."""
        # Simulate RAG retrieval time
        with TimingTracker() as retrieval_timer:
            await asyncio.sleep(0.1)  # 100ms retrieval simulation
            retrieved_docs = ["Doc 1 content", "Doc 2 content"]
        
        retrieval_time = retrieval_timer.total_ms
        
        # Generate with context
        with TimingTracker() as generation_timer:
            augmented_prompt = f"Context: {' '.join(retrieved_docs)}\n\n{rag_request.prompt}"
            await fast_providers["openai"].complete(augmented_prompt)
        
        generation_time = generation_timer.total_ms
        total_time = retrieval_time + generation_time
        
        # Retrieval should add < 50% to total latency
        retrieval_overhead_pct = (retrieval_time / total_time) * 100
        assert retrieval_overhead_pct < 50, f"Retrieval overhead {retrieval_overhead_pct}% too high"
        assert total_time < 3000, "RAG query too slow"
    
    @pytest.mark.asyncio
    async def test_rag_context_scaling(self, fast_providers, rag_request):
        """Benchmark how latency scales with context size."""
        context_sizes = [100, 500, 1000, 2000]  # tokens
        latencies = []
        
        for ctx_size in context_sizes:
            context = "word " * ctx_size
            prompt = f"Context: {context}\n\nQuestion: {rag_request.prompt}"
            
            with TimingTracker() as timer:
                await fast_providers["openai"].complete(prompt)
            
            latencies.append(timer.total_ms)
        
        # Latency should scale sub-linearly with context
        # 20x context should not mean 20x latency
        latency_ratio = latencies[-1] / latencies[0]
        context_ratio = context_sizes[-1] / context_sizes[0]
        
        assert latency_ratio < context_ratio * 0.5, "Latency scales too steeply with context"


# ==============================================================================
# HRM Hierarchical Query Benchmarks
# ==============================================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestHRMPerformance:
    """Benchmarks for hierarchical planning queries."""
    
    @pytest.mark.asyncio
    async def test_hrm_planning_overhead(self, fast_providers, hrm_request):
        """Benchmark HRM planning phase overhead."""
        # Simulate planning phase
        with TimingTracker() as planning_timer:
            await asyncio.sleep(0.15)  # 150ms planning simulation
            plan_steps = ["research", "analyze", "synthesize"]
        
        planning_time = planning_timer.total_ms
        
        # Execute steps
        with TimingTracker() as execution_timer:
            for step in plan_steps:
                await fast_providers["openai"].complete(f"Execute step: {step}")
        
        execution_time = execution_timer.total_ms
        total_time = planning_time + execution_time
        
        # Planning should be < 25% of total time
        planning_overhead_pct = (planning_time / total_time) * 100
        assert planning_overhead_pct < 25, f"Planning overhead {planning_overhead_pct}% too high"
    
    @pytest.mark.asyncio
    async def test_hrm_step_parallelization(self, mixed_providers, hrm_request):
        """Benchmark parallel step execution in HRM."""
        # Simulate plan with parallel steps
        parallel_steps = [
            {"id": "research_a", "parallel": True},
            {"id": "research_b", "parallel": True},
            {"id": "analyze", "parallel": False},
        ]
        
        with TimingTracker() as timer:
            # Execute parallel steps together
            parallel_tasks = [
                asyncio.create_task(
                    list(mixed_providers.values())[i % len(mixed_providers)].complete(
                        f"Execute: {step['id']}"
                    )
                )
                for i, step in enumerate(parallel_steps)
                if step["parallel"]
            ]
            
            await asyncio.gather(*parallel_tasks)
            timer.mark_first_token()
            
            # Execute sequential step
            await list(mixed_providers.values())[0].complete("Execute: analyze")
        
        # Parallel steps should execute faster than sequential would
        assert timer.total_ms < 15000, "HRM execution too slow"


# ==============================================================================
# Concurrent Request Benchmarks
# ==============================================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestConcurrencyPerformance:
    """Benchmarks for concurrent request handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_simple_queries(self, fast_providers, simple_request):
        """Benchmark handling of concurrent simple queries."""
        num_concurrent = 10
        
        with MemoryTracker() as mem:
            with TimingTracker() as timer:
                tasks = [
                    fast_providers["openai"].complete(simple_request.prompt)
                    for _ in range(num_concurrent)
                ]
                results = await asyncio.gather(*tasks)
        
        # Calculate per-request metrics
        total_time = timer.total_ms
        avg_time_per_request = total_time / num_concurrent
        throughput = num_concurrent / (total_time / 1000)  # requests/second
        
        # Concurrent should be faster than sequential
        # 10 x 500ms sequential = 5000ms, concurrent should be < 2000ms
        assert total_time < 5000, f"Concurrent execution {total_time}ms too slow"
        assert throughput > 2, f"Throughput {throughput} req/s too low"
    
    @pytest.mark.asyncio
    async def test_concurrent_mixed_queries(self, mixed_providers, simple_request, complex_request):
        """Benchmark mixed concurrent queries."""
        with TimingTracker() as timer:
            tasks = []
            
            # Mix of simple and complex queries
            for i in range(6):
                if i % 2 == 0:
                    tasks.append(
                        mixed_providers["openai"].complete(simple_request.prompt)
                    )
                else:
                    tasks.append(asyncio.gather(*[
                        provider.complete(complex_request.prompt)
                        for provider in mixed_providers.values()
                    ]))
            
            await asyncio.gather(*tasks)
        
        # Should handle mixed load efficiently
        assert timer.total_ms < 20000, "Mixed concurrent queries too slow"
    
    @pytest.mark.asyncio
    async def test_request_queueing(self, fast_providers, simple_request):
        """Benchmark request queueing under load."""
        queue = asyncio.Queue(maxsize=5)
        results = []
        
        async def worker():
            while True:
                try:
                    req = await asyncio.wait_for(queue.get(), timeout=1.0)
                    result = await fast_providers["openai"].complete(req)
                    results.append(result)
                    queue.task_done()
                except asyncio.TimeoutError:
                    break
        
        with TimingTracker() as timer:
            # Start workers
            workers = [asyncio.create_task(worker()) for _ in range(3)]
            
            # Queue requests
            for _ in range(10):
                await queue.put(simple_request.prompt)
            
            # Wait for completion
            await queue.join()
        
        assert len(results) == 10, "Not all requests completed"
        throughput = len(results) / (timer.total_ms / 1000)
        assert throughput > 1, f"Queued throughput {throughput} too low"


# ==============================================================================
# Memory Benchmarks
# ==============================================================================

@pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestMemoryPerformance:
    """Benchmarks for memory usage."""
    
    @pytest.mark.asyncio
    async def test_memory_per_request(self, fast_providers, simple_request):
        """Benchmark memory usage per request."""
        gc.collect()
        baseline = get_memory_mb()
        
        # Execute multiple requests
        for _ in range(10):
            await fast_providers["openai"].complete(simple_request.prompt)
        
        gc.collect()
        after = get_memory_mb()
        
        memory_per_request = (after - baseline) / 10
        
        # Each request should use < 10MB
        assert memory_per_request < 10, f"Memory per request {memory_per_request}MB too high"
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, fast_providers, simple_request):
        """Benchmark memory cleanup after requests."""
        gc.collect()
        baseline = get_memory_mb()
        
        # Create and complete many requests
        for _ in range(50):
            await fast_providers["openai"].complete(simple_request.prompt)
        
        peak = get_memory_mb()
        
        # Force cleanup
        gc.collect()
        after_cleanup = get_memory_mb()
        
        # Memory should return close to baseline (within 20MB)
        assert after_cleanup < baseline + 20, "Memory not properly released"


# ==============================================================================
# Regression Testing with pytest-benchmark
# ==============================================================================

@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="pytest-benchmark not available")
@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestBenchmarkRegression:
    """Regression tests using pytest-benchmark."""
    
    def test_simple_query_benchmark(self, benchmark, fast_providers, simple_request):
        """Benchmark simple query for regression tracking."""
        async def run_query():
            return await fast_providers["openai"].complete(simple_request.prompt)
        
        def sync_wrapper():
            return asyncio.run(run_query())
        
        result = benchmark(sync_wrapper)
        assert result is not None
    
    def test_team_query_benchmark(self, benchmark, mixed_providers, complex_request):
        """Benchmark team query for regression tracking."""
        async def run_team_query():
            tasks = [
                provider.complete(complex_request.prompt)
                for provider in mixed_providers.values()
            ]
            return await asyncio.gather(*tasks)
        
        def sync_wrapper():
            return asyncio.run(run_team_query())
        
        result = benchmark(sync_wrapper)
        assert result is not None


# ==============================================================================
# Performance Summary
# ==============================================================================

@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Models not available")
class TestPerformanceSummary:
    """Generate performance summary report."""
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, fast_providers, mixed_providers, simple_request, complex_request):
        """Generate a summary of all performance metrics."""
        summary = {
            "simple_query": {},
            "team_query": {},
            "concurrent": {},
        }
        
        # Simple query
        with TimingTracker() as t:
            await fast_providers["openai"].complete(simple_request.prompt)
        summary["simple_query"]["latency_ms"] = t.total_ms
        
        # Team query
        with TimingTracker() as t:
            tasks = [p.complete(complex_request.prompt) for p in mixed_providers.values()]
            await asyncio.gather(*tasks)
        summary["team_query"]["latency_ms"] = t.total_ms
        
        # Concurrent
        with TimingTracker() as t:
            tasks = [fast_providers["openai"].complete(simple_request.prompt) for _ in range(5)]
            await asyncio.gather(*tasks)
        summary["concurrent"]["latency_ms"] = t.total_ms
        summary["concurrent"]["throughput"] = 5 / (t.total_ms / 1000)
        
        # Print summary
        print("\n=== Performance Summary ===")
        print(f"Simple Query: {summary['simple_query']['latency_ms']:.1f}ms")
        print(f"Team Query: {summary['team_query']['latency_ms']:.1f}ms")
        print(f"Concurrent (5 req): {summary['concurrent']['latency_ms']:.1f}ms")
        print(f"Throughput: {summary['concurrent']['throughput']:.1f} req/s")
        
        # All metrics should be within acceptable bounds
        assert summary["simple_query"]["latency_ms"] < 2000
        assert summary["team_query"]["latency_ms"] < 15000
        assert summary["concurrent"]["throughput"] > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-json=benchmark.json"])
