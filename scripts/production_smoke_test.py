#!/usr/bin/env python3
"""
Production Smoke Test Suite for LLMHive

Comprehensive end-to-end tests for production readiness:
1. Health check endpoints
2. Authentication flow
3. Chat/orchestration flow
4. Billing/subscription endpoints
5. Support system
6. Admin endpoints

Usage:
    python scripts/production_smoke_test.py [--production-url URL]

Environment Variables:
    PRODUCTION_URL - Production backend URL (or pass via --production-url)
    API_KEY - API key for authenticated requests
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
import ssl

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    latency_ms: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class SmokeTestSuite:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results: List[TestResult] = []
        self.verify_ssl = not (
            os.environ.get("NO_SSL_VERIFY", "").lower() in {"1", "true", "yes"}
            or os.environ.get("PYTHONHTTPSVERIFY", "") == "0"
        )
        
    def _request(self, method: str, endpoint: str, data: Optional[dict] = None, 
                 timeout: int = 30, headers: Optional[dict] = None) -> tuple:
        """Make HTTP request and return (status_code, response_body, latency_ms)."""
        url = urljoin(self.base_url, endpoint)
        
        req_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.api_key:
            req_headers['X-API-Key'] = self.api_key
        if headers:
            req_headers.update(headers)
            
        req = Request(url, method=method, headers=req_headers)
        
        if data:
            req.data = json.dumps(data).encode('utf-8')
            
        start = time.time()
        try:
            context = None
            if not self.verify_ssl and urlparse(url).scheme == "https":
                context = ssl._create_unverified_context()
            with urlopen(req, timeout=timeout, context=context) as response:
                latency_ms = (time.time() - start) * 1000
                body = response.read().decode('utf-8')
                try:
                    body = json.loads(body)
                except:
                    pass
                return response.status, body, latency_ms
        except HTTPError as e:
            latency_ms = (time.time() - start) * 1000
            body = e.read().decode('utf-8') if e.fp else str(e.reason)
            return e.code, body, latency_ms
        except URLError as e:
            latency_ms = (time.time() - start) * 1000
            return None, str(e.reason), latency_ms
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return None, str(e), latency_ms

    def add_result(self, result: TestResult):
        self.results.append(result)
        status = f"{GREEN}✅{RESET}" if result.passed else f"{RED}❌{RESET}"
        latency = f"{result.latency_ms:.0f}ms"
        print(f"  {status} [{result.category}] {result.name} ({latency})")
        if result.error and not result.passed:
            print(f"      {RED}Error: {result.error}{RESET}")

    # =========================================================================
    # Health & Infrastructure Tests
    # =========================================================================
    
    def test_health_endpoint(self):
        """Test /health endpoint."""
        status, body, latency = self._request('GET', '/health')
        self.add_result(TestResult(
            name="Health Endpoint",
            category="Infrastructure",
            passed=status == 200,
            latency_ms=latency,
            status_code=status,
            error=body if status != 200 else None
        ))
        
    def test_readiness_endpoint(self):
        """Test readiness endpoint."""
        for endpoint in ['/health/ready', '/ready', '/healthz', '/api/health']:
            status, body, latency = self._request('GET', endpoint)
            if status == 200:
                self.add_result(TestResult(
                    name=f"Readiness Endpoint ({endpoint})",
                    category="Infrastructure",
                    passed=True,
                    latency_ms=latency,
                    status_code=status
                ))
                return
                
        self.add_result(TestResult(
            name="Readiness Endpoint",
            category="Infrastructure",
            passed=False,
            latency_ms=0,
            error="No readiness endpoint found"
        ))

    def test_api_docs(self):
        """Test API documentation endpoints."""
        for endpoint in ['/docs', '/openapi.json', '/redoc']:
            status, _, latency = self._request('GET', endpoint)
            if status == 200:
                self.add_result(TestResult(
                    name=f"API Docs ({endpoint})",
                    category="Infrastructure",
                    passed=True,
                    latency_ms=latency,
                    status_code=status
                ))
                return
                
        self.add_result(TestResult(
            name="API Docs",
            category="Infrastructure",
            passed=False,
            latency_ms=0,
            error="No API docs endpoint found"
        ))

    # =========================================================================
    # Orchestration Tests
    # =========================================================================
    
    def test_chat_endpoint(self):
        """Test basic chat/orchestration endpoint."""
        endpoints_to_try = [
            ('/v1/chat', {'prompt': 'Hello, this is a smoke test', 'model': 'auto'}),
            ('/api/v1/chat', {'message': 'Hello, this is a smoke test', 'accuracy_level': 'standard'}),
            ('/orchestrate', {'query': 'Hello, this is a smoke test'}),
            ('/v1/orchestrate', {'query': 'Hello, this is a smoke test'}),
        ]
        
        for endpoint, payload in endpoints_to_try:
            status, body, latency = self._request('POST', endpoint, data=payload, timeout=60)
            
            if status in [200, 201]:
                self.add_result(TestResult(
                    name=f"Chat/Orchestration ({endpoint})",
                    category="Orchestration",
                    passed=True,
                    latency_ms=latency,
                    status_code=status,
                    details={"response_preview": str(body)[:200] if body else None}
                ))
                return
            elif status == 401:
                # Auth required - that's okay, endpoint exists
                self.add_result(TestResult(
                    name=f"Chat/Orchestration ({endpoint})",
                    category="Orchestration",
                    passed=True,  # Endpoint exists, auth working
                    latency_ms=latency,
                    status_code=status,
                    details={"note": "Auth required - endpoint exists"}
                ))
                return
                
        self.add_result(TestResult(
            name="Chat/Orchestration",
            category="Orchestration",
            passed=False,
            latency_ms=0,
            error="No working chat endpoint found"
        ))

    def test_models_endpoint(self):
        """Test models listing endpoint."""
        for endpoint in ['/api/v1/openrouter/models', '/api/v1/models', '/models', '/v1/models']:
            status, body, latency = self._request('GET', endpoint)
            if status in [200, 401]:  # 401 means endpoint exists
                self.add_result(TestResult(
                    name=f"Models Listing ({endpoint})",
                    category="Orchestration",
                    passed=True,
                    latency_ms=latency,
                    status_code=status
                ))
                return
                
        self.add_result(TestResult(
            name="Models Listing",
            category="Orchestration",
            passed=False,
            latency_ms=0,
            error="No models endpoint found"
        ))

    # =========================================================================
    # Billing Tests
    # =========================================================================
    
    def test_billing_config(self):
        """Test billing configuration endpoint."""
        for endpoint in ['/api/billing/verify-config', '/api/billing/config']:
            status, body, latency = self._request('GET', endpoint)
            if status in [200, 401]:
                self.add_result(TestResult(
                    name=f"Billing Config ({endpoint})",
                    category="Billing",
                    passed=True,
                    latency_ms=latency,
                    status_code=status
                ))
                return
                
        # Try POST for verify-config
        status, body, latency = self._request('POST', '/api/billing/verify-config')
        self.add_result(TestResult(
            name="Billing Config",
            category="Billing",
            passed=status in [200, 401, 405],  # 405 means endpoint exists
            latency_ms=latency,
            status_code=status,
            error=body if status not in [200, 401, 405] else None
        ))

    def test_stripe_webhook(self):
        """Test Stripe webhook endpoint exists (should return 400 without proper payload)."""
        status, body, latency = self._request('POST', '/api/billing/webhooks', 
                                               data={"test": "payload"})
        # Webhook should reject invalid payload with 400
        self.add_result(TestResult(
            name="Stripe Webhook Endpoint",
            category="Billing",
            passed=status in [400, 401, 403],  # Should reject invalid request
            latency_ms=latency,
            status_code=status,
            details={"note": "Rejected invalid payload (expected behavior)"}
        ))

    # =========================================================================
    # Support System Tests
    # =========================================================================
    
    def test_support_endpoint(self):
        """Test support ticket endpoint."""
        # GET should list tickets (or require auth)
        status, body, latency = self._request('GET', '/api/support')
        self.add_result(TestResult(
            name="Support Tickets GET",
            category="Support",
            passed=status in [200, 401],
            latency_ms=latency,
            status_code=status
        ))
        
        # POST should create ticket
        ticket_data = {
            "name": "Smoke Test User",
            "email": "smoketest@example.com",
            "subject": "Smoke Test Ticket",
            "message": "This is an automated smoke test. Please ignore.",
            "type": "technical"
        }
        status, body, latency = self._request('POST', '/api/support', data=ticket_data)
        self.add_result(TestResult(
            name="Support Tickets POST",
            category="Support",
            passed=status in [200, 201, 401],
            latency_ms=latency,
            status_code=status,
            details={"ticket_id": body.get("ticketId") if isinstance(body, dict) else None}
        ))

    # =========================================================================
    # Admin Tests
    # =========================================================================
    
    def test_admin_stats(self):
        """Test admin stats endpoint."""
        status, body, latency = self._request('GET', '/api/admin/stats')
        self.add_result(TestResult(
            name="Admin Stats",
            category="Admin",
            passed=status in [200, 401, 403],  # Should require auth
            latency_ms=latency,
            status_code=status
        ))

    # =========================================================================
    # Run All Tests
    # =========================================================================
    
    def run_all(self, profile: str = "full") -> bool:
        """Run smoke tests and return True if all critical tests pass."""
        print(f"\n{BOLD}🐝 LLMHive Production Smoke Tests{RESET}")
        print(f"Target: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}\n")
        print(f"Profile: {profile}\n")
        
        # Infrastructure tests
        print(f"\n{BOLD}Infrastructure Tests:{RESET}")
        self.test_health_endpoint()
        self.test_readiness_endpoint()
        self.test_api_docs()
        
        # Orchestration tests
        print(f"\n{BOLD}Orchestration Tests:{RESET}")
        self.test_chat_endpoint()
        self.test_models_endpoint()
        if profile == "full":
            # Billing tests
            print(f"\n{BOLD}Billing Tests:{RESET}")
            self.test_billing_config()
            self.test_stripe_webhook()
            
            # Support tests
            print(f"\n{BOLD}Support System Tests:{RESET}")
            self.test_support_endpoint()
            
            # Admin tests
            print(f"\n{BOLD}Admin Tests:{RESET}")
            self.test_admin_stats()
        else:
            print(f"\n{YELLOW}Skipping Billing/Support/Admin for orchestrator profile{RESET}")
        
        # Summary
        return self._print_summary()
        
    def _print_summary(self) -> bool:
        """Print test summary and return True if all passed."""
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}{'SMOKE TEST SUMMARY'.center(60)}{RESET}")
        print(f"{BOLD}{'='*60}{RESET}\n")
        
        # Group by category
        by_category: Dict[str, List[TestResult]] = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)
        
        total_passed = 0
        total_failed = 0
        critical_failed = False
        
        for category, results in by_category.items():
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed
            total_passed += passed
            total_failed += failed
            
            if failed > 0 and category in ["Infrastructure", "Orchestration"]:
                critical_failed = True
            
            status = f"{GREEN}✅{RESET}" if failed == 0 else f"{RED}❌{RESET}"
            print(f"{status} {category}: {passed}/{len(results)} passed")
            
        print(f"\n{BOLD}Total: {total_passed} passed, {total_failed} failed{RESET}")
        
        # Latency stats
        latencies = [r.latency_ms for r in self.results if r.latency_ms > 0]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            print(f"\nLatency: avg={avg_latency:.0f}ms, max={max_latency:.0f}ms")
        
        # Final verdict
        if critical_failed:
            print(f"\n{RED}{BOLD}❌ SMOKE TEST FAILED - Critical issues found{RESET}")
            return False
        elif total_failed > 0:
            print(f"\n{YELLOW}{BOLD}⚠️  SMOKE TEST PASSED WITH WARNINGS{RESET}")
            return True
        else:
            print(f"\n{GREEN}{BOLD}✅ ALL SMOKE TESTS PASSED{RESET}")
            return True


def main():
    parser = argparse.ArgumentParser(description='LLMHive Production Smoke Tests')
    parser.add_argument('--production-url', '-u', 
                        default=os.environ.get('PRODUCTION_URL', 'https://llmhive-orchestrator-867263134607.us-east1.run.app'),
                        help='Production backend URL')
    parser.add_argument('--profile', choices=['orchestrator', 'full'],
                        default=None,
                        help='Test profile (default: auto-detect)')
    parser.add_argument('--api-key', '-k',
                        default=os.environ.get('API_KEY'),
                        help='API key for authenticated requests')
    
    args = parser.parse_args()
    
    suite = SmokeTestSuite(args.production_url, args.api_key)
    profile = args.profile or ("orchestrator" if "orchestrator" in suite.base_url else "full")
    success = suite.run_all(profile=profile)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
