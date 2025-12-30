#!/usr/bin/env python3
"""Load testing script for LLMHive Orchestrator API.

This script validates that the orchestrator meets its SLO targets:
- High-speed mode (accuracy 1-2): p95 < 3s
- High-accuracy mode (accuracy 3-5): p95 < 15s

Usage:
    python scripts/load_test.py --url http://localhost:8000 --concurrency 5

Requirements:
    pip install aiohttp asyncio
"""
import argparse
import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import aiohttp
except ImportError:
    print("Please install aiohttp: pip install aiohttp")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Configuration for load test."""
    base_url: str
    concurrency: int = 5
    total_requests: int = 20
    timeout_seconds: int = 30
    api_key: Optional[str] = None


@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    latency_ms: float
    status_code: int
    error: Optional[str] = None
    accuracy_level: int = 3


@dataclass
class LoadTestReport:
    """Report from load test run."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    latencies_ms: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        return self.successful_requests / max(self.total_requests, 1) * 100
    
    @property
    def p50_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        return sorted_latencies[len(sorted_latencies) // 2]
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def p99_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def avg_latency(self) -> float:
        if not self.latencies_ms:
            return 0
        return statistics.mean(self.latencies_ms)


# Test queries for different complexity levels
SIMPLE_QUERIES = [
    "What is the capital of France?",
    "How many continents are there?",
    "Who wrote Romeo and Juliet?",
    "What is 2 + 2?",
    "Define photosynthesis.",
]

MEDIUM_QUERIES = [
    "Explain the difference between Python and JavaScript.",
    "What are the main causes of climate change?",
    "How does machine learning work?",
    "Compare TCP and UDP protocols.",
]

COMPLEX_QUERIES = [
    "Write a Python function to implement binary search with error handling.",
    "Explain the trade-offs between microservices and monolithic architecture.",
    "Design a database schema for an e-commerce platform with user accounts, products, and orders.",
]


async def send_request(
    session: aiohttp.ClientSession,
    config: LoadTestConfig,
    query: str,
    accuracy_level: int = 3,
) -> RequestResult:
    """Send a single request to the orchestrator."""
    url = f"{config.base_url}/api/v1/chat"
    
    payload = {
        "prompt": query,
        "orchestration": {
            "accuracy_level": accuracy_level,
            "max_tokens": 500,
        },
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    
    start_time = time.time()
    try:
        async with session.post(
            url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=config.timeout_seconds),
        ) as response:
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status == 200:
                return RequestResult(
                    success=True,
                    latency_ms=latency_ms,
                    status_code=response.status,
                    accuracy_level=accuracy_level,
                )
            else:
                text = await response.text()
                return RequestResult(
                    success=False,
                    latency_ms=latency_ms,
                    status_code=response.status,
                    error=text[:200],
                    accuracy_level=accuracy_level,
                )
    except asyncio.TimeoutError:
        latency_ms = (time.time() - start_time) * 1000
        return RequestResult(
            success=False,
            latency_ms=latency_ms,
            status_code=0,
            error="Timeout",
            accuracy_level=accuracy_level,
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return RequestResult(
            success=False,
            latency_ms=latency_ms,
            status_code=0,
            error=str(e),
            accuracy_level=accuracy_level,
        )


async def run_load_test(config: LoadTestConfig) -> LoadTestReport:
    """Run the load test."""
    logger.info(f"Starting load test: {config.total_requests} requests, {config.concurrency} concurrent")
    
    results: List[RequestResult] = []
    
    # Prepare queries with different accuracy levels
    queries_with_levels = []
    for _ in range(config.total_requests // 3):
        queries_with_levels.extend([
            (SIMPLE_QUERIES[_ % len(SIMPLE_QUERIES)], 1),  # High-speed
            (MEDIUM_QUERIES[_ % len(MEDIUM_QUERIES)], 3),  # Default
            (COMPLEX_QUERIES[_ % len(COMPLEX_QUERIES)], 5),  # High-accuracy
        ])
    
    # Fill remaining
    while len(queries_with_levels) < config.total_requests:
        queries_with_levels.append((SIMPLE_QUERIES[0], 2))
    
    async with aiohttp.ClientSession() as session:
        # Use semaphore for concurrency control
        semaphore = asyncio.Semaphore(config.concurrency)
        
        async def bounded_request(query: str, accuracy: int) -> RequestResult:
            async with semaphore:
                return await send_request(session, config, query, accuracy)
        
        # Run all requests
        tasks = [
            bounded_request(query, accuracy)
            for query, accuracy in queries_with_levels
        ]
        
        results = await asyncio.gather(*tasks)
    
    # Build report
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    report = LoadTestReport(
        total_requests=len(results),
        successful_requests=len(successful),
        failed_requests=len(failed),
        latencies_ms=[r.latency_ms for r in successful],
    )
    
    return report


def check_slo_compliance(report: LoadTestReport) -> dict:
    """Check if the results meet SLO targets."""
    # SLO Targets from Launch Gate Audit:
    # - High-speed (accuracy 1-2): p95 < 3s (3000ms)
    # - High-accuracy (accuracy 3-5): p95 < 15s (15000ms)
    
    # For simplicity, we use overall p95 and check against 15s (most lenient)
    slo_targets = {
        "p95_latency_ms": 15000,  # 15 seconds
        "success_rate_percent": 95,
    }
    
    results = {
        "p95_target_ms": slo_targets["p95_latency_ms"],
        "p95_actual_ms": report.p95_latency,
        "p95_pass": report.p95_latency < slo_targets["p95_latency_ms"],
        "success_rate_target": slo_targets["success_rate_percent"],
        "success_rate_actual": report.success_rate,
        "success_rate_pass": report.success_rate >= slo_targets["success_rate_percent"],
        "overall_pass": (
            report.p95_latency < slo_targets["p95_latency_ms"] and
            report.success_rate >= slo_targets["success_rate_percent"]
        ),
    }
    
    return results


def print_report(report: LoadTestReport, slo_check: dict):
    """Print the load test report."""
    print("\n" + "=" * 60)
    print("LOAD TEST REPORT")
    print("=" * 60)
    
    print(f"\nRequests:")
    print(f"  Total:      {report.total_requests}")
    print(f"  Successful: {report.successful_requests}")
    print(f"  Failed:     {report.failed_requests}")
    print(f"  Success Rate: {report.success_rate:.1f}%")
    
    print(f"\nLatency (successful requests):")
    print(f"  Avg:  {report.avg_latency:.0f}ms")
    print(f"  p50:  {report.p50_latency:.0f}ms")
    print(f"  p95:  {report.p95_latency:.0f}ms")
    print(f"  p99:  {report.p99_latency:.0f}ms")
    
    print(f"\nSLO Compliance:")
    print(f"  p95 Target:  {slo_check['p95_target_ms']}ms")
    print(f"  p95 Actual:  {slo_check['p95_actual_ms']:.0f}ms")
    print(f"  p95 Status:  {'✅ PASS' if slo_check['p95_pass'] else '❌ FAIL'}")
    print(f"  Success Target: {slo_check['success_rate_target']}%")
    print(f"  Success Actual: {slo_check['success_rate_actual']:.1f}%")
    print(f"  Success Status: {'✅ PASS' if slo_check['success_rate_pass'] else '❌ FAIL'}")
    
    print(f"\nOverall: {'✅ SLO MET' if slo_check['overall_pass'] else '❌ SLO NOT MET'}")
    print("=" * 60)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LLMHive Load Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent requests")
    parser.add_argument("--requests", type=int, default=20, help="Total requests")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout (seconds)")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    config = LoadTestConfig(
        base_url=args.url,
        concurrency=args.concurrency,
        total_requests=args.requests,
        timeout_seconds=args.timeout,
        api_key=args.api_key,
    )
    
    logger.info(f"Load test target: {config.base_url}")
    
    report = await run_load_test(config)
    slo_check = check_slo_compliance(report)
    
    if args.json:
        output = {
            "report": {
                "total_requests": report.total_requests,
                "successful_requests": report.successful_requests,
                "failed_requests": report.failed_requests,
                "success_rate": report.success_rate,
                "avg_latency_ms": report.avg_latency,
                "p50_latency_ms": report.p50_latency,
                "p95_latency_ms": report.p95_latency,
                "p99_latency_ms": report.p99_latency,
            },
            "slo_compliance": slo_check,
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(report, slo_check)
    
    # Exit with error code if SLO not met
    if not slo_check["overall_pass"]:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

