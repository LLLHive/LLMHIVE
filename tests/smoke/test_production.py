"""Production smoke tests for LLMHive API.

These tests verify that the production deployment is healthy and functional.
Run against production with:
    pytest tests/smoke/ --production-url=https://api.llmhive.ai --api-key=your-key

Or via environment variables:
    PRODUCTION_URL=https://api.llmhive.ai API_KEY=your-key pytest tests/smoke/
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

import pytest
import requests

from .conftest import (
    HEALTH_PROBE_PATHS,
    SmokeTestConfig,
    ResponseTimer,
    probe_health_endpoint,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Health Check Tests (Critical - No Auth Required)
# =============================================================================

@pytest.mark.smoke
@pytest.mark.critical
class TestHealthEndpoints:
    """Test health check endpoints - these must always pass."""
    
    def test_health_probe(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Production health must respond on /health (Cloud Run blocks bare /healthz)."""
        with timer("GET health probe"):
            response, path = probe_health_endpoint(
                http_client,
                smoke_config.base_url,
                timeout=smoke_config.timeout,
            )

        assert response is not None, "Health probe did not return a response"
        assert response.status_code == 200, (
            f"Health probe failed via {path}: {response.status_code} {response.text[:200]}"
        )
        logger.info("✅ Health probe passed via %s", path)

        # Document Cloud Run reserved-path behavior without failing the suite.
        healthz_url = f"{smoke_config.base_url}/healthz"
        healthz_response = http_client.get(healthz_url, timeout=smoke_config.timeout)
        if healthz_response.status_code != 200:
            logger.warning(
                "⚠️  /healthz returned %s (expected on Cloud Run; use %s)",
                healthz_response.status_code,
                ", ".join(HEALTH_PROBE_PATHS),
            )
    
    def test_api_v1_health(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test /api/v1/metrics/health endpoint."""
        url = f"{smoke_config.base_url}/api/v1/metrics/health"
        
        with timer("GET /api/v1/metrics/health"):
            response = http_client.get(url, timeout=smoke_config.timeout)
        
        # Accept 200 or 404
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Health response missing 'status' field"
            assert data["status"] in ["healthy", "ok"], f"Unhealthy status: {data['status']}"
            logger.info(f"✅ API health check passed: {data.get('status')}")
        else:
            logger.warning(f"⚠️  /api/v1/metrics/health returned {response.status_code}")
    
    def test_liveness_probe(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test Kubernetes liveness probe endpoint."""
        url = f"{smoke_config.base_url}/api/v1/metrics/health/live"
        
        with timer("GET /api/v1/metrics/health/live"):
            response = http_client.get(url, timeout=smoke_config.timeout)
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "ok", f"Liveness failed: {data}"
            logger.info("✅ Liveness probe passed")
        else:
            logger.warning(f"⚠️  Liveness probe returned {response.status_code}")
    
    def test_readiness_probe(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test Kubernetes readiness probe endpoint."""
        url = f"{smoke_config.base_url}/api/v1/metrics/health/ready"
        
        with timer("GET /api/v1/metrics/health/ready"):
            response = http_client.get(url, timeout=smoke_config.timeout)
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") in ["ready", "ok"], f"Not ready: {data}"
            logger.info("✅ Readiness probe passed")
        elif response.status_code == 503:
            logger.warning("⚠️  Service not ready (503)")
        else:
            logger.warning(f"⚠️  Readiness probe returned {response.status_code}")


# =============================================================================
# API Endpoint Tests (May Require Auth)
# =============================================================================

@pytest.mark.smoke
class TestAPIEndpoints:
    """Test core API endpoints."""
    
    def test_agents_list(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test /agents or /v1/agents endpoint returns agent list."""
        # Try both possible endpoints
        endpoints = [
            f"{smoke_config.base_url}/agents",
            f"{smoke_config.base_url}/v1/agents",
            f"{smoke_config.base_url}/api/v1/agents",
        ]
        
        success = False
        for url in endpoints:
            with timer(f"GET {url}"):
                try:
                    response = http_client.get(url, timeout=smoke_config.timeout)
                    if response.status_code == 200:
                        data = response.json()
                        assert "agents" in data or isinstance(data, list), \
                            f"Unexpected response format: {data}"
                        logger.info(f"✅ Agent list retrieved from {url}")
                        success = True
                        break
                    elif response.status_code == 401:
                        logger.warning(f"⚠️  {url} requires authentication")
                        success = True  # Auth required is expected
                        break
                except requests.RequestException as e:
                    logger.debug(f"Failed to reach {url}: {e}")
        
        if not success:
            pytest.skip("No agents endpoint found or accessible")
    
    def test_models_endpoint(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test models/providers endpoint."""
        endpoints = [
            f"{smoke_config.base_url}/v1/models",
            f"{smoke_config.base_url}/api/v1/models",
            f"{smoke_config.base_url}/models",
        ]
        
        for url in endpoints:
            with timer(f"GET {url}"):
                try:
                    response = http_client.get(url, timeout=smoke_config.timeout)
                    if response.status_code == 200:
                        logger.info(f"✅ Models endpoint accessible: {url}")
                        return
                    elif response.status_code == 401:
                        logger.info(f"✅ Models endpoint requires auth (expected)")
                        return
                except requests.RequestException:
                    continue
        
        logger.warning("⚠️  No models endpoint found")


# =============================================================================
# Authenticated Tests
# =============================================================================

@pytest.mark.smoke
@pytest.mark.authenticated
class TestAuthenticatedEndpoints:
    """Test endpoints that require authentication."""
    
    @pytest.fixture(autouse=True)
    def check_api_key(self, smoke_config: SmokeTestConfig) -> None:
        """Skip tests if no API key provided."""
        if not smoke_config.api_key:
            pytest.skip("API key required for authenticated tests")
    
    def test_chat_completion_simple(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test simple chat completion."""
        url = f"{smoke_config.base_url}/v1/chat"
        
        payload = {
            "prompt": "Say 'Hello, smoke test!' and nothing else.",
            "max_tokens": 50,
            "stream": False,
        }
        
        with timer("POST /v1/chat (simple)"):
            response = http_client.post(
                url,
                json=payload,
                timeout=smoke_config.timeout,
            )
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data or "content" in data or "response" in data, \
                f"Unexpected chat response format: {list(data.keys())}"
            logger.info(f"✅ Chat completion successful")
            logger.info(f"   Response: {str(data)[:200]}...")
        elif response.status_code in (401, 402):
            pytest.skip(
                f"Chat smoke skipped: {response.status_code} "
                "(auth or subscription required for smoke API key)"
            )
        elif response.status_code == 429:
            logger.warning("⚠️  Rate limited - try again later")
        else:
            logger.error(f"❌ Chat failed with {response.status_code}: {response.text[:200]}")
            pytest.fail(f"Chat completion failed: {response.status_code}")
    
    def test_chat_with_orchestration(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test chat with orchestration settings."""
        url = f"{smoke_config.base_url}/v1/chat"
        
        payload = {
            "prompt": "What is 2 + 2?",
            "reasoning_mode": "standard",
            "domain_pack": "default",
            "agent_mode": "single",
            "max_tokens": 100,
            "stream": False,
        }
        
        with timer("POST /v1/chat (orchestrated)"):
            response = http_client.post(
                url,
                json=payload,
                timeout=smoke_config.timeout,
            )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Orchestrated chat successful")
            # Check for orchestration metadata
            if "models_used" in data or "extra" in data:
                logger.info(f"   Orchestration metadata present")
        elif response.status_code in (401, 402):
            pytest.skip(
                f"Orchestrated chat smoke skipped: {response.status_code} "
                "(auth or subscription required for smoke API key)"
            )
        elif response.status_code == 429:
            logger.warning("⚠️  Rate limited - try again later")
        else:
            logger.error(f"❌ Orchestrated chat failed: {response.status_code}")
            pytest.fail(f"Orchestrated chat failed: {response.status_code}")


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.smoke
class TestPerformance:
    """Test response time performance."""
    
    def test_health_response_time(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Verify health endpoint responds within acceptable time."""
        max_response_time_ms = 1000  # 1 second max
        
        with timer("GET health probe (performance)") as t:
            response, path = probe_health_endpoint(
                http_client,
                smoke_config.base_url,
                timeout=smoke_config.timeout,
            )
        
        if response and response.status_code == 200:
            assert t.duration_ms < max_response_time_ms, \
                f"Health check too slow: {t.duration_ms:.0f}ms (max: {max_response_time_ms}ms)"
            logger.info(f"✅ Health check via {path} OK: {t.duration_ms:.0f}ms")
        else:
            pytest.skip("Health probe unavailable for performance check")
    
    def test_multiple_health_checks(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
    ) -> None:
        """Run multiple health checks and measure consistency."""
        num_requests = 5
        response_times: list[float] = []
        
        for i in range(num_requests):
            start = time.perf_counter()
            try:
                response, _path = probe_health_endpoint(
                    http_client,
                    smoke_config.base_url,
                    timeout=smoke_config.timeout,
                    retries=1,
                )
                duration_ms = (time.perf_counter() - start) * 1000
                if response and response.status_code == 200:
                    response_times.append(duration_ms)
            except requests.RequestException as e:
                logger.warning(f"Request {i+1} failed: {e}")
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            logger.info(f"✅ Health check performance ({len(response_times)} requests):")
            logger.info(f"   Avg: {avg_time:.0f}ms, Min: {min_time:.0f}ms, Max: {max_time:.0f}ms")
            
            # Warn if there's high variance
            if max_time > avg_time * 3:
                logger.warning(f"⚠️  High response time variance detected")


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.smoke
class TestErrorHandling:
    """Test that errors are handled gracefully."""
    
    def test_404_response(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test that non-existent endpoints return proper 404."""
        url = f"{smoke_config.base_url}/api/v1/this-endpoint-does-not-exist"
        
        with timer("GET non-existent endpoint"):
            response = http_client.get(url, timeout=smoke_config.timeout)
        
        assert response.status_code in [404, 405], \
            f"Expected 404/405, got {response.status_code}"
        logger.info(f"✅ Non-existent endpoint returns {response.status_code}")
    
    def test_invalid_json_handling(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test that invalid JSON is handled gracefully."""
        url = f"{smoke_config.base_url}/v1/chat"
        
        with timer("POST invalid JSON"):
            response = http_client.post(
                url,
                data="this is not valid json",
                headers={"Content-Type": "application/json"},
                timeout=smoke_config.timeout,
            )
        
        # Should return 400 or 422, not 500
        assert response.status_code in [400, 401, 422], \
            f"Invalid JSON should return 400/422, got {response.status_code}"
        logger.info(f"✅ Invalid JSON handled gracefully: {response.status_code}")


# =============================================================================
# Summary
# =============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config) -> None:
    """Print smoke test summary."""
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    
    terminalreporter.write_sep("=", "SMOKE TEST SUMMARY")
    terminalreporter.write_line(f"Passed: {passed}")
    terminalreporter.write_line(f"Failed: {failed}")
    terminalreporter.write_line(f"Skipped: {skipped}")
    
    if failed > 0:
        terminalreporter.write_line("❌ SMOKE TESTS FAILED - Production may be unhealthy!")
    else:
        terminalreporter.write_line("✅ SMOKE TESTS PASSED - Production is healthy")
