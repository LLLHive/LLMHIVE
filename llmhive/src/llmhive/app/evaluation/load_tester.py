"""Enhanced Load Testing Framework for LLMHive.

Provides programmatic load testing beyond Locust for integration testing.

Usage:
    tester = LoadTester(base_url="http://localhost:8080")
    results = await tester.run_load_test(
        concurrent_users=100,
        duration_seconds=60,
    )
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    status_code: int
    latency_ms: float
    response_size: int
    error: Optional[str] = None
    tokens_used: int = 0


@dataclass
class LoadTestResult:
    """Aggregate load test results."""
    test_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    requests_per_second: float
    total_tokens: int
    error_breakdown: Dict[str, int]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "duration_seconds": round(self.duration_seconds, 2),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "requests_per_second": round(self.requests_per_second, 2),
            "total_tokens": self.total_tokens,
            "error_breakdown": self.error_breakdown,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def summary(self) -> str:
        return (
            f"Load Test: {self.success_rate:.1%} success rate "
            f"({self.successful_requests}/{self.total_requests}), "
            f"{self.requests_per_second:.1f} RPS, "
            f"p95={self.p95_latency_ms:.0f}ms"
        )
    
    def is_passing(
        self,
        min_success_rate: float = 0.99,
        max_p95_latency_ms: float = 5000,
    ) -> bool:
        """Check if results meet SLA requirements."""
        return (
            self.success_rate >= min_success_rate and
            self.p95_latency_ms <= max_p95_latency_ms
        )


# ==============================================================================
# Load Tester
# ==============================================================================

class LoadTester:
    """Load testing framework for LLMHive."""
    
    # Sample prompts
    SIMPLE_PROMPTS = [
        "What is 2 + 2?",
        "Hello, how are you?",
        "What time is it?",
    ]
    
    MEDIUM_PROMPTS = [
        "Explain what an API is in simple terms.",
        "What are the benefits of cloud computing?",
        "How does machine learning work?",
    ]
    
    COMPLEX_PROMPTS = [
        "Compare and contrast the economic policies of Keynesianism and monetarism.",
        "Explain the technical architecture of a modern recommendation system.",
        "Discuss the ethical implications of artificial general intelligence.",
    ]
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        output_dir: str = "./load_test_results",
    ):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for load testing")
        
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.getenv("LLMHIVE_API_KEY", "test-key")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[LoadTestResult] = []
    
    async def run_load_test(
        self,
        concurrent_users: int = 10,
        duration_seconds: int = 60,
        test_name: Optional[str] = None,
        warmup_seconds: int = 5,
    ) -> LoadTestResult:
        """
        Run a load test.
        
        Args:
            concurrent_users: Number of concurrent virtual users
            duration_seconds: How long to run the test
            test_name: Name for this test run
            warmup_seconds: Warmup period before measuring
            
        Returns:
            LoadTestResult with metrics
        """
        test_name = test_name or f"load_test_{concurrent_users}u_{duration_seconds}s"
        
        logger.info(f"Starting load test: {test_name}")
        logger.info(f"  Users: {concurrent_users}, Duration: {duration_seconds}s")
        
        # Warmup
        if warmup_seconds > 0:
            logger.info(f"  Warming up for {warmup_seconds}s...")
            await self._run_users(
                num_users=min(5, concurrent_users),
                duration_seconds=warmup_seconds,
            )
        
        # Actual test
        logger.info("  Running load test...")
        start_time = time.time()
        
        results = await self._run_users(
            num_users=concurrent_users,
            duration_seconds=duration_seconds,
        )
        
        actual_duration = time.time() - start_time
        
        # Calculate metrics
        load_result = self._calculate_metrics(
            test_name=test_name,
            results=results,
            duration=actual_duration,
        )
        
        self.results.append(load_result)
        self._save_result(load_result)
        
        logger.info(load_result.summary())
        
        return load_result
    
    async def run_stress_test(
        self,
        initial_users: int = 10,
        step_users: int = 10,
        max_users: int = 100,
        step_duration_seconds: int = 30,
    ) -> List[LoadTestResult]:
        """
        Run a stepped stress test to find breaking point.
        
        Gradually increases load until failure rate exceeds threshold.
        """
        logger.info("Starting stress test...")
        
        all_results = []
        current_users = initial_users
        
        while current_users <= max_users:
            result = await self.run_load_test(
                concurrent_users=current_users,
                duration_seconds=step_duration_seconds,
                test_name=f"stress_test_{current_users}u",
            )
            
            all_results.append(result)
            
            # Check if system is degrading
            if result.success_rate < 0.95:
                logger.warning(f"Success rate dropped to {result.success_rate:.1%} at {current_users} users")
                break
            
            if result.p95_latency_ms > 10000:  # 10 seconds
                logger.warning(f"P95 latency exceeded 10s at {current_users} users")
                break
            
            current_users += step_users
        
        # Summary
        logger.info("\nStress Test Summary:")
        for r in all_results:
            print(f"  {r.test_name}: {r.success_rate:.1%} success, p95={r.p95_latency_ms:.0f}ms")
        
        return all_results
    
    async def _run_users(
        self,
        num_users: int,
        duration_seconds: int,
    ) -> List[RequestResult]:
        """Run virtual users for specified duration."""
        all_results: List[RequestResult] = []
        stop_time = time.time() + duration_seconds
        
        async def user_loop(user_id: int):
            """Simulate a single user making requests."""
            user_results = []
            
            async with aiohttp.ClientSession() as session:
                while time.time() < stop_time:
                    result = await self._make_request(session)
                    user_results.append(result)
                    
                    # Small delay between requests
                    await asyncio.sleep(random.uniform(0.5, 2.0))
            
            return user_results
        
        # Run all users concurrently
        tasks = [user_loop(i) for i in range(num_users)]
        user_results = await asyncio.gather(*tasks)
        
        for results in user_results:
            all_results.extend(results)
        
        return all_results
    
    async def _make_request(self, session: aiohttp.ClientSession) -> RequestResult:
        """Make a single request to LLMHive."""
        # Randomly select prompt complexity
        prompt_pool = random.choice([
            self.SIMPLE_PROMPTS,
            self.MEDIUM_PROMPTS,
            self.MEDIUM_PROMPTS,  # Weight towards medium
            self.COMPLEX_PROMPTS,
        ])
        prompt = random.choice(prompt_pool)
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "gpt-4o-mini",
            "max_tokens": 100,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                body = await response.text()
                response_size = len(body)
                
                tokens_used = 0
                if response.status == 200:
                    try:
                        data = json.loads(body)
                        if "usage" in data:
                            tokens_used = data["usage"].get("total_tokens", 0)
                    except json.JSONDecodeError:
                        pass
                
                return RequestResult(
                    success=response.status == 200,
                    status_code=response.status,
                    latency_ms=latency_ms,
                    response_size=response_size,
                    tokens_used=tokens_used,
                    error=None if response.status == 200 else f"Status {response.status}",
                )
                
        except asyncio.TimeoutError:
            return RequestResult(
                success=False,
                status_code=0,
                latency_ms=(time.time() - start_time) * 1000,
                response_size=0,
                error="Timeout",
            )
        except Exception as e:
            return RequestResult(
                success=False,
                status_code=0,
                latency_ms=(time.time() - start_time) * 1000,
                response_size=0,
                error=str(e),
            )
    
    def _calculate_metrics(
        self,
        test_name: str,
        results: List[RequestResult],
        duration: float,
    ) -> LoadTestResult:
        """Calculate aggregate metrics from results."""
        if not results:
            return LoadTestResult(
                test_name=test_name,
                duration_seconds=duration,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                requests_per_second=0,
                total_tokens=0,
                error_breakdown={},
            )
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        latencies = sorted([r.latency_ms for r in results])
        
        # Error breakdown
        error_breakdown: Dict[str, int] = {}
        for r in failed:
            error = r.error or "Unknown"
            error_breakdown[error] = error_breakdown.get(error, 0) + 1
        
        def percentile(values: List[float], p: float) -> float:
            if not values:
                return 0
            idx = int(len(values) * p / 100)
            return values[min(idx, len(values) - 1)]
        
        return LoadTestResult(
            test_name=test_name,
            duration_seconds=duration,
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            success_rate=len(successful) / len(results),
            avg_latency_ms=sum(latencies) / len(latencies),
            p50_latency_ms=percentile(latencies, 50),
            p95_latency_ms=percentile(latencies, 95),
            p99_latency_ms=percentile(latencies, 99),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            requests_per_second=len(results) / duration if duration > 0 else 0,
            total_tokens=sum(r.tokens_used for r in results),
            error_breakdown=error_breakdown,
        )
    
    def _save_result(self, result: LoadTestResult) -> None:
        """Save test results."""
        filename = self.output_dir / f"{result.test_name}.json"
        
        with open(filename, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        logger.info(f"Results saved to {filename}")
    
    def print_summary(self) -> None:
        """Print summary of all load tests."""
        print("\n" + "=" * 70)
        print("LOAD TEST RESULTS SUMMARY")
        print("=" * 70)
        
        for result in self.results:
            print(f"\n{result.test_name}:")
            print(f"  Total Requests: {result.total_requests:,}")
            print(f"  Success Rate: {result.success_rate:.1%}")
            print(f"  RPS: {result.requests_per_second:.1f}")
            print(f"  Latency (p50/p95/p99): {result.p50_latency_ms:.0f}/{result.p95_latency_ms:.0f}/{result.p99_latency_ms:.0f}ms")
            print(f"  Tokens Used: {result.total_tokens:,}")
            
            if result.error_breakdown:
                print("  Errors:")
                for error, count in result.error_breakdown.items():
                    print(f"    {error}: {count}")
        
        print("\n" + "=" * 70)

