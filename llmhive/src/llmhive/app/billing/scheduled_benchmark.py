"""Recognition of trusted scheduled HTTP benchmarks (GitHub Actions → production).

CI sends ``X-LLMHIVE-Scheduled-Benchmark-Secret`` matching environment variable
``LLMHIVE_SCHEDULED_BENCHMARK_SECRET`` (long random value, only on Cloud Run and
in Actions secrets). When the server has that env set and the header matches:

- ``/v1/chat`` skips the Firestore paid-subscription gate (no real customer user).
- Orchestration forces ``ModelTier.elite`` and skips :func:`record_elite_spend`,
  so benchmark traffic does not consume a subscriber's elite spend cap.

If ``LLMHIVE_SCHEDULED_BENCHMARK_SECRET`` is unset, the header is ignored and
behavior is unchanged (defense in depth: no bypass without explicit ops setup).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

logger = logging.getLogger(__name__)

SCHEDULED_BENCHMARK_HEADER_NAME = "X-LLMHIVE-Scheduled-Benchmark-Secret"

_internal_scheduled_benchmark: ContextVar[bool] = ContextVar(
    "_internal_scheduled_benchmark", default=False
)


def is_internal_scheduled_benchmark() -> bool:
    return _internal_scheduled_benchmark.get()


def set_internal_scheduled_benchmark(active: bool) -> object:
    return _internal_scheduled_benchmark.set(active)


def reset_internal_scheduled_benchmark(token: object) -> None:
    _internal_scheduled_benchmark.reset(token)


def _digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def scheduled_benchmark_request_valid(request: Request) -> bool:
    """True when this HTTP request is an authenticated scheduled benchmark."""
    configured = os.getenv("LLMHIVE_SCHEDULED_BENCHMARK_SECRET", "").strip()
    if not configured:
        return False
    header = (request.headers.get(SCHEDULED_BENCHMARK_HEADER_NAME) or "").strip()
    if not header:
        return False
    if not hmac.compare_digest(_digest(configured), _digest(header)):
        logger.debug("scheduled_benchmark: secret header mismatch")
        return False
    return True


class ScheduledBenchmarkMiddleware(BaseHTTPMiddleware):
    """Mark trusted CI benchmark requests for the duration of the HTTP call."""

    async def dispatch(
        self, request: StarletteRequest, call_next
    ) -> Response:
        token = None
        try:
            if scheduled_benchmark_request_valid(request):
                token = set_internal_scheduled_benchmark(True)
                logger.debug("scheduled_benchmark: internal CI request accepted")
            return await call_next(request)
        finally:
            if token is not None:
                reset_internal_scheduled_benchmark(token)
