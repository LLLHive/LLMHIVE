"""Pytest configuration for smoke tests.

Usage:
    pytest tests/smoke/ --production-url=https://api.llmhive.ai
    pytest tests/smoke/ --production-url=https://api.llmhive.ai --api-key=your-api-key
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Generator, Optional

import pytest
import requests

# Configure logging for smoke tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options for smoke tests."""
    parser.addoption(
        "--production-url",
        action="store",
        default=os.environ.get("PRODUCTION_URL", "http://localhost:8000"),
        help="Production API URL to test against",
    )
    parser.addoption(
        "--api-key",
        action="store",
        default=os.environ.get("API_KEY", os.environ.get("LLMHIVE_API_KEY", "")),
        help="API key for authentication",
    )
    parser.addoption(
        "--smoke-timeout",
        action="store",
        default=os.environ.get("SMOKE_TIMEOUT", "60"),
        help="Timeout in seconds for smoke test requests",
    )


@dataclass
class SmokeTestConfig:
    """Configuration for smoke tests."""
    base_url: str
    api_key: str
    timeout: int
    
    @property
    def headers(self) -> dict:
        """Get default headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        return headers


@pytest.fixture(scope="session")
def smoke_config(request: pytest.FixtureRequest) -> SmokeTestConfig:
    """Get smoke test configuration from command line options."""
    base_url = request.config.getoption("--production-url").rstrip("/")
    api_key = request.config.getoption("--api-key")
    timeout = int(request.config.getoption("--smoke-timeout"))
    
    logger.info(f"Smoke test configuration:")
    logger.info(f"  Base URL: {base_url}")
    logger.info(f"  API Key: {'***' + api_key[-4:] if api_key else 'Not provided'}")
    logger.info(f"  Timeout: {timeout}s")
    
    return SmokeTestConfig(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )


@pytest.fixture(scope="session")
def http_client(smoke_config: SmokeTestConfig) -> Generator[requests.Session, None, None]:
    """Create HTTP client session for smoke tests."""
    session = requests.Session()
    session.headers.update(smoke_config.headers)
    yield session
    session.close()


class ResponseTimer:
    """Context manager to measure response time."""
    
    def __init__(self, name: str = "request"):
        self.name = name
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration_ms: float = 0
    
    def __enter__(self) -> "ResponseTimer":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        logger.info(f"⏱️  {self.name}: {self.duration_ms:.2f}ms")


@pytest.fixture
def timer() -> type[ResponseTimer]:
    """Provide ResponseTimer class for measuring response times."""
    return ResponseTimer


# Markers for smoke tests
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test"
    )
    config.addinivalue_line(
        "markers", "critical: mark test as critical (must pass for deployment)"
    )
    config.addinivalue_line(
        "markers", "authenticated: mark test as requiring authentication"
    )
