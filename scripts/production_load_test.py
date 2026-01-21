#!/usr/bin/env python3
"""
LLMHive Production Load Test - January 2026
============================================

Comprehensive load testing for market launch validation.
Tests 100-1000 concurrent users against production orchestrator.

Usage:
    python scripts/production_load_test.py

Requirements:
    pip install aiohttp
"""
import asyncio
import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import random

try:
    import aiohttp
except ImportError:
    print("Please install aiohttp: pip install aiohttp")
    exit(1)

# ==============================================================================
# Configuration
# ==============================================================================

PRODUCTION_URL = "https://llmhive-orchestrator-792354158895.us-east1.run.app"
API_KEY = "llmhive-secret-key-2025-abc123xyz"

# Test prompts by category
TEST_PROMPTS = {
    "simple": [
        "What is 2+2?",
        "Say hello",
        "What color is the sky?",
        "Name a fruit",
        "What is the capital of France?",
    ],
    "medium": [
        "Explain how photosynthesis works in 2 sentences.",
        "What are the main benefits of exercise?",
        "Describe the water cycle briefly.",
        "What is machine learning?",
    ],
    "complex": [
        "Write a Python function to calculate the factorial of a number.",
        "Compare and contrast REST and GraphQL APIs.",
        "Explain the theory of relativity in simple terms.",
    ],
}

# SLO Targets
SLO_TARGETS = {
    "success_rate": 0.95,  # 95% success rate
    "p95_latency_simple_ms": 5000,  # 5 seconds for simple queries
    "p95_latency_medium_ms": 15000,  # 15 seconds for medium queries
    "p95_latency_complex_ms": 45000,  # 45 seconds for complex/orchestrated queries
    "error_rate": 0.05,  # Less than 5% errors
}


@dataclass
class RequestResult:
    """Result of a single request."""
    success: bool
    status_code: int
    latency_ms: float
    error: Optional[str] = None
    query_type: str = "simple"
    accuracy_level: int = 2


@dataclass
class LoadTestReport:
    """Aggregate load test report."""
    test_name: str
    concurrent_users: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    results: List[RequestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        return self.successful_requests / max(self.total_requests, 1)
    
    @property
    def latencies(self) -> List[float]:
        return [r.latency_ms for r in self.results if r.success]
    
    @property
    def p50_latency(self) -> float:
        if not self.latencies:
            return 0
        return statistics.quantiles(self.latencies, n=2)[0]
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        return statistics.quantiles(self.latencies, n=20)[18]
    
    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0
        return statistics.quantiles(self.latencies, n=100)[98]
    
    @property
    def avg_latency(self) -> float:
        if not self.latencies:
            return 0
        return statistics.mean(self.latencies)
    
    @property
    def duration_seconds(self) -> float:
        if not self.end_time:
            return 0
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def requests_per_second(self) -> float:
        if self.duration_seconds == 0:
            return 0
        return self.total_requests / self.duration_seconds
    
    def get_latencies_by_type(self, query_type: str) -> List[float]:
        return [r.latency_ms for r in self.results if r.success and r.query_type == query_type]


async def send_request(
    session: aiohttp.ClientSession,
    prompt: str,
    query_type: str,
    accuracy_level: int,
    request_id: int,
) -> RequestResult:
    """Send a single request to the orchestrator."""
    url = f"{PRODUCTION_URL}/v1/chat"
    
    payload = {
        "prompt": prompt,
        "max_tokens": 200 if query_type == "simple" else 500,
        "stream": False,
        "orchestration": {
            "accuracy_level": accuracy_level,
        },
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout
        async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status == 200:
                return RequestResult(
                    success=True,
                    status_code=response.status,
                    latency_ms=latency_ms,
                    query_type=query_type,
                    accuracy_level=accuracy_level,
                )
            else:
                text = await response.text()
                return RequestResult(
                    success=False,
                    status_code=response.status,
                    latency_ms=latency_ms,
                    error=text[:100],
                    query_type=query_type,
                    accuracy_level=accuracy_level,
                )
    except asyncio.TimeoutError:
        return RequestResult(
            success=False,
            status_code=0,
            latency_ms=(time.time() - start_time) * 1000,
            error="Timeout",
            query_type=query_type,
            accuracy_level=accuracy_level,
        )
    except Exception as e:
        return RequestResult(
            success=False,
            status_code=0,
            latency_ms=(time.time() - start_time) * 1000,
            error=str(e)[:100],
            query_type=query_type,
            accuracy_level=accuracy_level,
        )


async def run_load_test(
    test_name: str,
    concurrent_users: int,
    requests_per_user: int = 3,
) -> LoadTestReport:
    """Run a load test with specified concurrency."""
    
    total_requests = concurrent_users * requests_per_user
    print(f"\n{'='*60}")
    print(f"LOAD TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Concurrent Users: {concurrent_users}")
    print(f"Requests per User: {requests_per_user}")
    print(f"Total Requests: {total_requests}")
    print(f"Target: {PRODUCTION_URL}")
    print(f"{'='*60}")
    
    report = LoadTestReport(
        test_name=test_name,
        concurrent_users=concurrent_users,
        total_requests=total_requests,
        successful_requests=0,
        failed_requests=0,
    )
    
    # Prepare request queue
    # Distribution: 60% simple, 30% medium, 10% complex
    requests_queue = []
    for i in range(total_requests):
        r = random.random()
        if r < 0.6:
            query_type = "simple"
            accuracy_level = 2
        elif r < 0.9:
            query_type = "medium"
            accuracy_level = 3
        else:
            query_type = "complex"
            accuracy_level = 4
        
        prompt = random.choice(TEST_PROMPTS[query_type])
        requests_queue.append((i, prompt, query_type, accuracy_level))
    
    # Run with concurrency control
    semaphore = asyncio.Semaphore(concurrent_users)
    progress_lock = asyncio.Lock()
    completed = [0]
    
    async def bounded_request(request_id: int, prompt: str, query_type: str, accuracy_level: int) -> RequestResult:
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                result = await send_request(session, prompt, query_type, accuracy_level, request_id)
                async with progress_lock:
                    completed[0] += 1
                    if completed[0] % 10 == 0 or completed[0] == total_requests:
                        pct = completed[0] / total_requests * 100
                        print(f"  Progress: {completed[0]}/{total_requests} ({pct:.0f}%)")
                return result
    
    print(f"\nStarting load test at {datetime.now().strftime('%H:%M:%S')}...")
    report.start_time = datetime.now()
    
    # Execute all requests
    tasks = [
        bounded_request(req_id, prompt, query_type, accuracy_level)
        for req_id, prompt, query_type, accuracy_level in requests_queue
    ]
    
    results = await asyncio.gather(*tasks)
    
    report.end_time = datetime.now()
    report.results = results
    report.successful_requests = sum(1 for r in results if r.success)
    report.failed_requests = sum(1 for r in results if not r.success)
    
    return report


def check_slo_compliance(report: LoadTestReport) -> Dict[str, Any]:
    """Check if results meet SLO targets."""
    # Get latencies by query type
    simple_latencies = report.get_latencies_by_type("simple")
    medium_latencies = report.get_latencies_by_type("medium")
    complex_latencies = report.get_latencies_by_type("complex")
    
    def get_p95(latencies: List[float]) -> float:
        if len(latencies) < 2:
            return latencies[0] if latencies else 0
        return statistics.quantiles(latencies, n=20)[18]
    
    simple_p95 = get_p95(simple_latencies) if simple_latencies else 0
    medium_p95 = get_p95(medium_latencies) if medium_latencies else 0
    complex_p95 = get_p95(complex_latencies) if complex_latencies else 0
    
    results = {
        "success_rate": {
            "target": f"{SLO_TARGETS['success_rate']*100:.0f}%",
            "actual": f"{report.success_rate*100:.1f}%",
            "pass": report.success_rate >= SLO_TARGETS['success_rate'],
        },
        "simple_p95_latency": {
            "target": f"{SLO_TARGETS['p95_latency_simple_ms']}ms",
            "actual": f"{simple_p95:.0f}ms",
            "pass": simple_p95 < SLO_TARGETS['p95_latency_simple_ms'] if simple_p95 > 0 else True,
        },
        "medium_p95_latency": {
            "target": f"{SLO_TARGETS['p95_latency_medium_ms']}ms",
            "actual": f"{medium_p95:.0f}ms",
            "pass": medium_p95 < SLO_TARGETS['p95_latency_medium_ms'] if medium_p95 > 0 else True,
        },
        "complex_p95_latency": {
            "target": f"{SLO_TARGETS['p95_latency_complex_ms']}ms",
            "actual": f"{complex_p95:.0f}ms",
            "pass": complex_p95 < SLO_TARGETS['p95_latency_complex_ms'] if complex_p95 > 0 else True,
        },
    }
    
    results["overall_pass"] = all(r["pass"] for r in results.values() if isinstance(r, dict))
    
    return results


def print_report(report: LoadTestReport, slo_check: Dict[str, Any]) -> None:
    """Print load test report."""
    print(f"\n{'='*60}")
    print(f"LOAD TEST REPORT: {report.test_name}")
    print(f"{'='*60}")
    
    print(f"\n📊 SUMMARY")
    print(f"  Duration:       {report.duration_seconds:.1f} seconds")
    print(f"  Total Requests: {report.total_requests}")
    print(f"  Successful:     {report.successful_requests}")
    print(f"  Failed:         {report.failed_requests}")
    print(f"  Success Rate:   {report.success_rate*100:.1f}%")
    print(f"  RPS:            {report.requests_per_second:.2f}")
    
    print(f"\n⏱️ LATENCY (successful requests)")
    print(f"  Average: {report.avg_latency:.0f}ms")
    print(f"  p50:     {report.p50_latency:.0f}ms")
    print(f"  p95:     {report.p95_latency:.0f}ms")
    print(f"  p99:     {report.p99_latency:.0f}ms")
    
    # By query type
    for qt in ["simple", "medium", "complex"]:
        lats = report.get_latencies_by_type(qt)
        if lats:
            avg = statistics.mean(lats)
            print(f"  {qt.capitalize():8s}: avg={avg:.0f}ms, count={len(lats)}")
    
    print(f"\n✅ SLO COMPLIANCE")
    for key, check in slo_check.items():
        if isinstance(check, dict):
            status = "✅ PASS" if check["pass"] else "❌ FAIL"
            print(f"  {key}: {check['actual']} (target: {check['target']}) {status}")
    
    overall = "✅ ALL SLOs MET" if slo_check.get("overall_pass") else "❌ SLO VIOLATIONS"
    print(f"\n{overall}")
    
    # Error breakdown
    errors = [r.error for r in report.results if not r.success and r.error]
    if errors:
        print(f"\n⚠️ ERROR BREAKDOWN")
        error_counts: Dict[str, int] = {}
        for e in errors:
            error_counts[e[:50]] = error_counts.get(e[:50], 0) + 1
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"  {count}x: {err}")


async def main():
    """Run comprehensive load tests."""
    print("=" * 70)
    print("🐝 LLMHIVE PRODUCTION LOAD TEST - JANUARY 2026")
    print("=" * 70)
    print(f"Target: {PRODUCTION_URL}")
    print(f"Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_results = []
    
    # Test 1: 100 concurrent users (warm-up)
    print("\n🔥 TEST 1: 100 Concurrent Users (Warm-up)")
    report_100 = await run_load_test(
        test_name="100 Concurrent Users",
        concurrent_users=100,
        requests_per_user=2,
    )
    slo_100 = check_slo_compliance(report_100)
    print_report(report_100, slo_100)
    all_results.append(("100 users", report_100, slo_100))
    
    # Brief pause
    print("\n⏳ Pausing 10 seconds before next test...")
    await asyncio.sleep(10)
    
    # Test 2: 250 concurrent users
    print("\n🔥 TEST 2: 250 Concurrent Users")
    report_250 = await run_load_test(
        test_name="250 Concurrent Users",
        concurrent_users=250,
        requests_per_user=2,
    )
    slo_250 = check_slo_compliance(report_250)
    print_report(report_250, slo_250)
    all_results.append(("250 users", report_250, slo_250))
    
    # Brief pause
    print("\n⏳ Pausing 10 seconds before next test...")
    await asyncio.sleep(10)
    
    # Test 3: 500 concurrent users
    print("\n🔥 TEST 3: 500 Concurrent Users")
    report_500 = await run_load_test(
        test_name="500 Concurrent Users",
        concurrent_users=500,
        requests_per_user=2,
    )
    slo_500 = check_slo_compliance(report_500)
    print_report(report_500, slo_500)
    all_results.append(("500 users", report_500, slo_500))
    
    # Brief pause
    print("\n⏳ Pausing 15 seconds before stress test...")
    await asyncio.sleep(15)
    
    # Test 4: 1000 concurrent users (stress test)
    print("\n🔥 TEST 4: 1000 Concurrent Users (STRESS TEST)")
    report_1000 = await run_load_test(
        test_name="1000 Concurrent Users (Stress)",
        concurrent_users=1000,
        requests_per_user=1,  # 1 request each to avoid overwhelming
    )
    slo_1000 = check_slo_compliance(report_1000)
    print_report(report_1000, slo_1000)
    all_results.append(("1000 users", report_1000, slo_1000))
    
    # Final Summary
    print("\n" + "=" * 70)
    print("📊 FINAL LOAD TEST SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Test':<20} {'Requests':<10} {'Success':<10} {'Avg Lat':<12} {'p95 Lat':<12} {'SLO'}")
    print("-" * 70)
    
    for name, report, slo in all_results:
        status = "✅" if slo.get("overall_pass") else "❌"
        print(f"{name:<20} {report.total_requests:<10} {report.success_rate*100:.1f}%{'':<5} {report.avg_latency:.0f}ms{'':<5} {report.p95_latency:.0f}ms{'':<5} {status}")
    
    # Overall assessment
    all_passed = all(slo.get("overall_pass") for _, _, slo in all_results)
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🏆 ALL LOAD TESTS PASSED - READY FOR PRODUCTION TRAFFIC")
    else:
        failing = [name for name, _, slo in all_results if not slo.get("overall_pass")]
        print(f"⚠️ SOME TESTS FAILED: {', '.join(failing)}")
        print("   Review capacity and scaling before high-traffic launch")
    print("=" * 70)
    
    # Save results to file
    results_file = f"artifacts/load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(results_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "target": PRODUCTION_URL,
                "results": [
                    {
                        "name": name,
                        "concurrent_users": report.concurrent_users,
                        "total_requests": report.total_requests,
                        "successful": report.successful_requests,
                        "failed": report.failed_requests,
                        "success_rate": report.success_rate,
                        "avg_latency_ms": report.avg_latency,
                        "p95_latency_ms": report.p95_latency,
                        "duration_seconds": report.duration_seconds,
                        "slo_passed": slo.get("overall_pass"),
                    }
                    for name, report, slo in all_results
                ],
            }, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")
    except Exception as e:
        print(f"\n⚠️ Could not save results: {e}")


if __name__ == "__main__":
    asyncio.run(main())
