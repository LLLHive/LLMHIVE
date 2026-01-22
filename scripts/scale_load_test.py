#!/usr/bin/env python3
"""
Scale Load Test for LLMHive Production

Tests system performance under high load (100-1000 concurrent users).
Uses thread pooling for reliable concurrent connections.

Usage:
    python scripts/scale_load_test.py --users 100 --duration 60
    python scripts/scale_load_test.py --users 500 --duration 120
    python scripts/scale_load_test.py --users 1000 --duration 180

Environment Variables:
    PRODUCTION_URL - Production backend URL
    API_KEY - API key for authenticated requests
"""

import argparse
import json
import os
import random
import sys
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import ssl

# Create unverified SSL context for testing (Cloud Run has valid certs)
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Test queries for different categories
TEST_QUERIES = [
    # Simple queries (should be fast)
    {"query": "What is 2 + 2?", "accuracy": "budget", "category": "math"},
    {"query": "Hello, how are you?", "accuracy": "budget", "category": "dialogue"},
    {"query": "What is Python?", "accuracy": "standard", "category": "general"},
    
    # Medium complexity
    {"query": "Explain how photosynthesis works", "accuracy": "standard", "category": "science"},
    {"query": "Write a function to reverse a string", "accuracy": "standard", "category": "coding"},
    
    # Complex queries
    {"query": "Compare and contrast supervised and unsupervised learning in machine learning", "accuracy": "elite", "category": "reasoning"},
]

@dataclass
class RequestResult:
    success: bool
    latency_ms: float
    status_code: Optional[int]
    error: Optional[str] = None
    query_category: str = "unknown"

@dataclass
class LoadTestStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def requests_per_second(self) -> float:
        if self.duration_seconds == 0:
            return 0.0
        return self.total_requests / self.duration_seconds
    
    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)
    
    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return statistics.median(self.latencies)
    
    @property
    def p95_latency_ms(self) -> float:
        if len(self.latencies) < 2:
            return self.avg_latency_ms
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]
    
    @property
    def p99_latency_ms(self) -> float:
        if len(self.latencies) < 2:
            return self.avg_latency_ms
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[idx]


class LoadTester:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.stats = LoadTestStats()
        self.lock = threading.Lock()
        self.running = True
        
    def make_request(self, query_info: dict, timeout: int = 60) -> RequestResult:
        """Make a single request to the orchestration endpoint."""
        url = f"{self.base_url}/v1/chat"  # LLMHive chat endpoint
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key
            
        payload = {
            "prompt": query_info["query"],  # /v1/chat uses 'prompt' not 'query'
            "accuracy_level": query_info.get("accuracy", "standard"),
        }
        
        req = Request(url, method='POST', headers=headers)
        req.data = json.dumps(payload).encode('utf-8')
        
        start = time.time()
        try:
            with urlopen(req, timeout=timeout, context=SSL_CONTEXT) as response:
                latency_ms = (time.time() - start) * 1000
                return RequestResult(
                    success=True,
                    latency_ms=latency_ms,
                    status_code=response.status,
                    query_category=query_info.get("category", "unknown")
                )
        except HTTPError as e:
            latency_ms = (time.time() - start) * 1000
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=e.code,
                error=f"HTTP {e.code}",
                query_category=query_info.get("category", "unknown")
            )
        except URLError as e:
            latency_ms = (time.time() - start) * 1000
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=None,
                error=f"URL Error: {e.reason}",
                query_category=query_info.get("category", "unknown")
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return RequestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=None,
                error=str(e),
                query_category=query_info.get("category", "unknown")
            )
    
    def record_result(self, result: RequestResult):
        """Thread-safe recording of request result."""
        with self.lock:
            self.stats.total_requests += 1
            if result.success:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1
                error_key = result.error or "Unknown"
                self.stats.errors[error_key] = self.stats.errors.get(error_key, 0) + 1
            self.stats.latencies.append(result.latency_ms)
            self.stats.total_latency_ms += result.latency_ms
    
    def worker(self, worker_id: int, duration_seconds: int, ramp_up_delay: float):
        """Worker thread that continuously makes requests."""
        # Stagger start times for gradual ramp-up
        time.sleep(ramp_up_delay)
        
        end_time = time.time() + duration_seconds - ramp_up_delay
        requests_made = 0
        
        while self.running and time.time() < end_time:
            query_info = random.choice(TEST_QUERIES)
            result = self.make_request(query_info)
            self.record_result(result)
            requests_made += 1
            
            # Small delay between requests from same worker
            time.sleep(random.uniform(0.1, 0.5))
        
        return requests_made
    
    def run_load_test(self, num_users: int, duration_seconds: int) -> LoadTestStats:
        """Run the load test with specified number of concurrent users."""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}{'LLMHive Scale Load Test'.center(60)}{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")
        
        print(f"Target URL: {self.base_url}")
        print(f"Concurrent Users: {num_users}")
        print(f"Duration: {duration_seconds}s")
        print(f"Start Time: {datetime.now().isoformat()}\n")
        
        # Calculate ramp-up time (10% of duration, max 30 seconds)
        ramp_up_time = min(duration_seconds * 0.1, 30)
        
        self.stats = LoadTestStats()
        self.stats.start_time = time.time()
        self.running = True
        
        # Progress display
        def progress_reporter():
            last_count = 0
            while self.running:
                time.sleep(5)
                with self.lock:
                    current = self.stats.total_requests
                    success = self.stats.successful_requests
                    failed = self.stats.failed_requests
                    
                rps = (current - last_count) / 5
                last_count = current
                
                elapsed = time.time() - self.stats.start_time
                print(f"  [{elapsed:.0f}s] Requests: {current}, Success: {success}, Failed: {failed}, RPS: {rps:.1f}")
        
        progress_thread = threading.Thread(target=progress_reporter, daemon=True)
        progress_thread.start()
        
        print(f"{CYAN}Starting {num_users} workers with {ramp_up_time:.1f}s ramp-up...{RESET}\n")
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = []
            for i in range(num_users):
                # Stagger worker start times
                ramp_delay = (i / num_users) * ramp_up_time
                future = executor.submit(self.worker, i, duration_seconds, ramp_delay)
                futures.append(future)
            
            # Wait for all workers to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"{RED}Worker error: {e}{RESET}")
        
        self.running = False
        self.stats.end_time = time.time()
        
        return self.stats
    
    def print_results(self):
        """Print detailed test results."""
        stats = self.stats
        
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}{'LOAD TEST RESULTS'.center(60)}{RESET}")
        print(f"{BOLD}{'='*60}{RESET}\n")
        
        # Summary
        print(f"{BOLD}Summary:{RESET}")
        print(f"  Duration: {stats.duration_seconds:.1f}s")
        print(f"  Total Requests: {stats.total_requests}")
        print(f"  Successful: {stats.successful_requests}")
        print(f"  Failed: {stats.failed_requests}")
        
        # Success rate with color
        success_rate = stats.success_rate
        if success_rate >= 99:
            rate_color = GREEN
        elif success_rate >= 95:
            rate_color = YELLOW
        else:
            rate_color = RED
        print(f"  Success Rate: {rate_color}{success_rate:.1f}%{RESET}")
        
        # Throughput
        print(f"\n{BOLD}Throughput:{RESET}")
        print(f"  Requests/Second: {stats.requests_per_second:.2f}")
        
        # Latency
        print(f"\n{BOLD}Latency:{RESET}")
        print(f"  Average: {stats.avg_latency_ms:.0f}ms")
        print(f"  P50 (median): {stats.p50_latency_ms:.0f}ms")
        print(f"  P95: {stats.p95_latency_ms:.0f}ms")
        print(f"  P99: {stats.p99_latency_ms:.0f}ms")
        
        # Latency evaluation
        if stats.p99_latency_ms < 10000:  # 10s
            print(f"  {GREEN}✅ P99 latency within acceptable range (<10s){RESET}")
        else:
            print(f"  {RED}❌ P99 latency exceeds target (>10s){RESET}")
        
        # Errors
        if stats.errors:
            print(f"\n{BOLD}Errors:{RESET}")
            for error, count in sorted(stats.errors.items(), key=lambda x: -x[1]):
                print(f"  {error}: {count}")
        
        # Final verdict
        print(f"\n{BOLD}{'='*60}{RESET}")
        if success_rate >= 99 and stats.p99_latency_ms < 10000:
            print(f"{GREEN}{BOLD}✅ LOAD TEST PASSED{RESET}")
            print(f"System handled {stats.total_requests} requests with {success_rate:.1f}% success rate")
        elif success_rate >= 95:
            print(f"{YELLOW}{BOLD}⚠️  LOAD TEST PASSED WITH WARNINGS{RESET}")
            print(f"Success rate {success_rate:.1f}% - some requests failed under load")
        else:
            print(f"{RED}{BOLD}❌ LOAD TEST FAILED{RESET}")
            print(f"Success rate {success_rate:.1f}% is below acceptable threshold (95%)")
        print(f"{BOLD}{'='*60}{RESET}\n")
        
        return success_rate >= 95


def main():
    parser = argparse.ArgumentParser(description='LLMHive Scale Load Test')
    parser.add_argument('--production-url', '-u',
                        default=os.environ.get('PRODUCTION_URL', 'https://llmhive-orchestrator-867263134607.us-east1.run.app'),
                        help='Production backend URL')
    parser.add_argument('--api-key', '-k',
                        default=os.environ.get('API_KEY'),
                        help='API key for authenticated requests')
    parser.add_argument('--users', '-n', type=int, default=100,
                        help='Number of concurrent users (default: 100)')
    parser.add_argument('--duration', '-d', type=int, default=60,
                        help='Test duration in seconds (default: 60)')
    parser.add_argument('--quick', action='store_true',
                        help='Quick test with fewer users/shorter duration')
    
    args = parser.parse_args()
    
    if args.quick:
        args.users = 10
        args.duration = 30
    
    tester = LoadTester(args.production_url, args.api_key)
    tester.run_load_test(args.users, args.duration)
    success = tester.print_results()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
