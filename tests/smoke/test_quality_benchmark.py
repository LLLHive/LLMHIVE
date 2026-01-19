"""Quality benchmark smoke tests for LLMHive API.

These tests verify that the orchestration quality doesn't regress.
They run a small set of critical prompts and check for minimum quality thresholds.

Run with:
    pytest tests/smoke/test_quality_benchmark.py --production-url=URL --api-key=KEY -v
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import pytest
import requests

from .conftest import SmokeTestConfig, ResponseTimer

logger = logging.getLogger(__name__)


# =============================================================================
# Quality Benchmark Prompts - These are critical test cases
# =============================================================================

QUALITY_BENCHMARKS = [
    {
        "id": "math_basic",
        "prompt": "Calculate 15% of 250. Show your work.",
        "expected_elements": ["37.5", "15", "250"],
        "min_quality": 0.8,
        "category": "math",
    },
    {
        "id": "reasoning_logic",
        "prompt": "If all cats are animals and some animals are pets, can we conclude that all cats are pets? Explain.",
        "expected_elements": ["cannot", "some", "all"],
        "min_quality": 0.7,
        "category": "reasoning",
    },
    {
        "id": "code_simple",
        "prompt": "Write a Python function to check if a number is prime.",
        "expected_elements": ["def", "prime", "return"],
        "min_quality": 0.8,
        "category": "code",
    },
    {
        "id": "factual_basic",
        "prompt": "What is the capital of France?",
        "expected_elements": ["Paris"],
        "min_quality": 0.9,
        "category": "factual",
    },
]

# Minimum acceptable scores by category
CATEGORY_THRESHOLDS = {
    "math": 0.8,
    "reasoning": 0.7,
    "code": 0.8,
    "factual": 0.9,
    "creative": 0.7,
    "analysis": 0.8,
}


def calculate_quality_score(response: str, expected_elements: List[str]) -> float:
    """Calculate quality score based on expected elements present."""
    if not response or len(response.strip()) < 10:
        return 0.0
    
    response_lower = response.lower()
    found = sum(1 for elem in expected_elements if elem.lower() in response_lower)
    
    return found / len(expected_elements) if expected_elements else 0.5


def detect_template_leakage(response: str) -> bool:
    """Detect if response contains template leakage (indicates regression)."""
    leakage_patterns = [
        "=== Step 1:",
        "=== PROBLEM ===",
        "Phase 1 - Planning:",
        "IMPORTANT: This is a complex request",
        "You MUST address EVERY part",
        "Solve this problem. You MUST express confidence",
    ]
    return any(pattern in response for pattern in leakage_patterns)


def detect_stub_response(response: str) -> bool:
    """Detect if response is a stub/placeholder (indicates regression)."""
    stub_patterns = [
        "Stub response for:",
        "This is a placeholder response",
        "I'm unable to process this request",
        "Error: No providers available",
    ]
    return any(pattern in response for pattern in stub_patterns)


# =============================================================================
# Quality Benchmark Tests
# =============================================================================

@pytest.mark.smoke
@pytest.mark.quality
@pytest.mark.authenticated
class TestQualityBenchmarks:
    """Test orchestration quality doesn't regress."""
    
    @pytest.fixture(autouse=True)
    def check_api_key(self, smoke_config: SmokeTestConfig) -> None:
        """Skip tests if no API key provided."""
        if not smoke_config.api_key:
            pytest.skip("API key required for quality benchmark tests")
    
    @pytest.mark.parametrize("benchmark", QUALITY_BENCHMARKS, ids=lambda b: b["id"])
    def test_quality_benchmark(
        self,
        benchmark: Dict[str, Any],
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Test individual quality benchmark."""
        url = f"{smoke_config.base_url}/v1/chat"
        
        payload = {
            "prompt": benchmark["prompt"],
            "reasoning_mode": "standard",
            "domain_pack": "default",
            "max_tokens": 500,
            "stream": False,
            "orchestration": {
                "accuracy_level": 3,
            },
        }
        
        test_id = benchmark["id"]
        category = benchmark["category"]
        min_quality = benchmark.get("min_quality", CATEGORY_THRESHOLDS.get(category, 0.7))
        
        logger.info(f"Testing: {test_id} ({category})")
        
        with timer(f"POST /v1/chat ({test_id})"):
            response = http_client.post(
                url,
                json=payload,
                timeout=smoke_config.timeout,
            )
        
        # Check response status
        if response.status_code != 200:
            if response.status_code in [401, 403]:
                pytest.skip(f"Authentication issue: {response.status_code}")
            elif response.status_code == 429:
                pytest.skip("Rate limited")
            else:
                pytest.fail(f"Request failed: {response.status_code} - {response.text[:200]}")
        
        data = response.json()
        message = data.get("message", data.get("content", data.get("response", "")))
        
        # Critical checks - these indicate major regressions
        if detect_stub_response(message):
            pytest.fail(f"REGRESSION: Stub response detected in {test_id}")
        
        if detect_template_leakage(message):
            pytest.fail(f"REGRESSION: Template leakage detected in {test_id}")
        
        # Quality check
        quality = calculate_quality_score(message, benchmark["expected_elements"])
        
        logger.info(f"  Quality: {quality:.2f} (min: {min_quality:.2f})")
        logger.info(f"  Response preview: {message[:100]}...")
        
        # Log which elements were found/missing
        for elem in benchmark["expected_elements"]:
            if elem.lower() in message.lower():
                logger.debug(f"  ✓ Found: {elem}")
            else:
                logger.warning(f"  ✗ Missing: {elem}")
        
        assert quality >= min_quality, (
            f"Quality regression in {test_id}: {quality:.2f} < {min_quality:.2f}\n"
            f"Expected elements: {benchmark['expected_elements']}\n"
            f"Response: {message[:500]}"
        )
        
        logger.info(f"  ✅ {test_id} passed (quality: {quality:.2f})")
    
    def test_no_empty_responses(
        self,
        smoke_config: SmokeTestConfig,
        http_client: requests.Session,
        timer: type[ResponseTimer],
    ) -> None:
        """Verify we never return empty responses."""
        url = f"{smoke_config.base_url}/v1/chat"
        
        test_prompts = [
            "Hello, how are you?",
            "What is 2 + 2?",
            "Explain photosynthesis briefly.",
        ]
        
        for prompt in test_prompts:
            payload = {
                "prompt": prompt,
                "max_tokens": 100,
                "stream": False,
            }
            
            with timer(f"Empty response check"):
                response = http_client.post(
                    url,
                    json=payload,
                    timeout=smoke_config.timeout,
                )
            
            if response.status_code == 200:
                data = response.json()
                message = data.get("message", data.get("content", ""))
                
                assert message and len(message.strip()) > 0, (
                    f"Empty response for: {prompt}"
                )
                logger.info(f"✅ Non-empty response for: {prompt[:30]}...")
            elif response.status_code in [401, 429]:
                pytest.skip(f"Auth/rate limit: {response.status_code}")


@pytest.mark.smoke
@pytest.mark.quality
class TestQualitySummary:
    """Summary test that aggregates quality results."""
    
    def test_quality_summary(self) -> None:
        """This test exists to provide a summary marker in test output."""
        logger.info("=" * 60)
        logger.info("QUALITY BENCHMARK SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Benchmarks: {len(QUALITY_BENCHMARKS)}")
        logger.info(f"Categories: {list(CATEGORY_THRESHOLDS.keys())}")
        logger.info("=" * 60)
