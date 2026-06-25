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

# Cloud Run reserves URL paths ending in "z" (e.g. /healthz) at the edge; probes must use /health.
HEALTH_PROBE_PATHS = ("/health", "/_ah/health")
HEALTH_PROBE_RETRIES = 3
HEALTH_PROBE_RETRY_DELAY_S = 2.0

# Post-deploy readiness: generous per-attempt timeout while instances cold-start.
WARMUP_REQUEST_TIMEOUT_S = 15
WARMUP_MAX_ATTEMPTS = 12
WARMUP_RETRY_DELAY_S = 5.0
WARMUP_MAX_WAIT_S = WARMUP_MAX_ATTEMPTS * (WARMUP_REQUEST_TIMEOUT_S + WARMUP_RETRY_DELAY_S)

# Steady-state SLO probes (after warm-up) — short timeout; cold start is not steady state.
PERF_PROBE_TIMEOUT_S = 10
STEADY_STATE_SLO_MS = 1000
STEADY_STATE_MULTI_MAX_MS = 2000
STEADY_STATE_MULTI_MIN_SAMPLES = 4
STEADY_STATE_MULTI_SAMPLE_COUNT = 5

# Same header as llmhive.app.billing.scheduled_benchmark (production CI benchmarks).
SCHEDULED_BENCHMARK_HEADER = "X-LLMHIVE-Scheduled-Benchmark-Secret"


def probe_health_endpoint(
    session: requests.Session,
    base_url: str,
    *,
    timeout: int,
    retries: int = HEALTH_PROBE_RETRIES,
) -> tuple[Optional[requests.Response], str]:
    """Return the first successful health response, or the last attempt."""
    last_response: Optional[requests.Response] = None
    last_path = HEALTH_PROBE_PATHS[0]

    for attempt in range(retries):
        for path in HEALTH_PROBE_PATHS:
            url = f"{base_url.rstrip('/')}{path}"
            try:
                response = session.get(url, timeout=timeout)
            except requests.RequestException as exc:
                logger.warning("Health probe %s failed (attempt %s): %s", path, attempt + 1, exc)
                continue
            last_response = response
            last_path = path
            if response.status_code == 200:
                return response, path
        if attempt + 1 < retries:
            time.sleep(HEALTH_PROBE_RETRY_DELAY_S)

    return last_response, last_path


def warm_up_production(
    session: requests.Session,
    base_url: str,
    *,
    max_attempts: int = WARMUP_MAX_ATTEMPTS,
    request_timeout_s: int = WARMUP_REQUEST_TIMEOUT_S,
    retry_delay_s: float = WARMUP_RETRY_DELAY_S,
) -> tuple[str, float]:
    """Block until production health returns 200 or attempts are exhausted.

    Used after Cloud Run deploys so smoke tests measure steady-state SLO, not
    cold-start latency.
    """
    last_path = HEALTH_PROBE_PATHS[0]
    last_latency_ms = 0.0

    for attempt in range(1, max_attempts + 1):
        start = time.perf_counter()
        response, path = probe_health_endpoint(
            session,
            base_url,
            timeout=request_timeout_s,
            retries=1,
        )
        last_latency_ms = (time.perf_counter() - start) * 1000
        last_path = path

        if response is not None and response.status_code == 200:
            logger.info(
                "Production warm-up succeeded via %s on attempt %s/%s (%.0fms)",
                path,
                attempt,
                max_attempts,
                last_latency_ms,
            )
            return path, last_latency_ms

        logger.warning(
            "Production warm-up attempt %s/%s via %s: status=%s latency=%.0fms",
            attempt,
            max_attempts,
            path,
            getattr(response, "status_code", "n/a"),
            last_latency_ms,
        )
        if attempt < max_attempts:
            time.sleep(retry_delay_s)

    raise RuntimeError(
        f"Production not ready after {max_attempts} warm-up attempts "
        f"(~{max_attempts * (request_timeout_s + retry_delay_s):.0f}s budget)"
    )


def measure_steady_state_health_latency(
    session: requests.Session,
    base_url: str,
    *,
    timeout_s: int = PERF_PROBE_TIMEOUT_S,
) -> tuple[requests.Response, str, float]:
    """Single health GET for SLO measurement (call only after warm_up_production)."""
    start = time.perf_counter()
    response, path = probe_health_endpoint(
        session,
        base_url,
        timeout=timeout_s,
        retries=1,
    )
    latency_ms = (time.perf_counter() - start) * 1000
    if response is None:
        raise RuntimeError("Steady-state health probe returned no response")
    return response, path, latency_ms


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
    parser.addoption(
        "--smoke-chat-max-ms",
        action="store",
        default=os.environ.get("SMOKE_CHAT_MAX_MS", "55000"),
        help="Max allowed /v1/chat latency in ms for launch smoke (below request timeout)",
    )
    parser.addoption(
        "--smoke-user-id",
        action="store",
        default=os.environ.get("SMOKE_TEST_USER_ID", ""),
        help="Clerk user_id for /v1/chat paid-subscription gate (metadata.user_id)",
    )


@dataclass
class SmokeTestConfig:
    """Configuration for smoke tests."""
    base_url: str
    api_key: str
    timeout: int
    chat_max_ms: int
    smoke_user_id: str = ""
    scheduled_benchmark_secret: str = ""

    def can_run_paid_chat(self) -> bool:
        """True when /v1/chat can pass the paid-subscription gate."""
        return bool(self.scheduled_benchmark_secret or self.smoke_user_id)

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
        if self.scheduled_benchmark_secret:
            headers[SCHEDULED_BENCHMARK_HEADER] = self.scheduled_benchmark_secret
        return headers


def build_smoke_chat_payload(smoke_config: SmokeTestConfig, **fields: object) -> dict:
    """Build /v1/chat JSON with optional metadata.user_id for paid gate."""
    payload = dict(fields)
    if smoke_config.smoke_user_id:
        meta = dict(payload.get("metadata") or {})
        meta.setdefault("user_id", smoke_config.smoke_user_id)
        payload["metadata"] = meta
    return payload


def require_chat_smoke_gate(smoke_config: SmokeTestConfig) -> None:
    """Skip chat tests when neither benchmark bypass nor user_id is configured."""
    if not smoke_config.can_run_paid_chat():
        pytest.skip(
            "Chat smoke needs LLMHIVE_SCHEDULED_BENCHMARK_SECRET "
            "(GCP scheduled-benchmark-secret) or SMOKE_TEST_USER_ID"
        )


def assert_chat_latency(chat_timer: "ResponseTimer", smoke_config: SmokeTestConfig) -> None:
    assert chat_timer.duration_ms <= smoke_config.chat_max_ms, (
        f"Chat latency {chat_timer.duration_ms:.0f}ms exceeds launch budget "
        f"{smoke_config.chat_max_ms}ms"
    )


@pytest.fixture(scope="session")
def production_warmed(
    http_client: requests.Session,
    smoke_config: SmokeTestConfig,
) -> dict[str, float | str]:
    """Ensure Cloud Run is warm before performance SLO tests run."""
    path, warmup_ms = warm_up_production(http_client, smoke_config.base_url)
    return {"path": path, "warmup_ms": warmup_ms}


@pytest.fixture(scope="session")
def smoke_config(request: pytest.FixtureRequest) -> SmokeTestConfig:
    """Get smoke test configuration from command line options."""
    base_url = request.config.getoption("--production-url").rstrip("/")
    api_key = request.config.getoption("--api-key")
    timeout = int(request.config.getoption("--smoke-timeout"))
    chat_max_ms = int(request.config.getoption("--smoke-chat-max-ms"))
    smoke_user_id = (request.config.getoption("--smoke-user-id") or "").strip()
    bench_secret = os.environ.get("LLMHIVE_SCHEDULED_BENCHMARK_SECRET", "").strip()

    logger.info("Smoke test configuration:")
    logger.info(f"  Base URL: {base_url}")
    logger.info(f"  API Key: {'***' + api_key[-4:] if api_key else 'Not provided'}")
    logger.info(f"  Timeout: {timeout}s")
    logger.info(f"  Chat max latency: {chat_max_ms}ms")
    logger.info(
        f"  Chat gate: benchmark_secret={'yes' if bench_secret else 'no'}, "
        f"user_id={'set' if smoke_user_id else 'not set'}"
    )

    return SmokeTestConfig(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        chat_max_ms=chat_max_ms,
        smoke_user_id=smoke_user_id,
        scheduled_benchmark_secret=bench_secret,
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
