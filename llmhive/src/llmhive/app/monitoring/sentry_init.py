"""Optional Sentry initialization for the FastAPI backend.

Dormant by default. Becomes live when **both** of the following are true:

1. ``SENTRY_DSN`` (or ``LLMHIVE_SENTRY_DSN``) is set in the environment.
2. The ``sentry-sdk`` Python package is importable.

If the DSN is set but the package is missing, we log a one-line warning and
continue without raising. This way the deploy never fails because Sentry
hasn't been installed yet — flipping the env var is enough to activate it.

Public API:

- :func:`is_sentry_configured` — env-var check, used by tests/diagnostics.
- :func:`init_sentry_if_configured` — call once at startup. Returns ``True``
  if Sentry was initialized, ``False`` otherwise.
- :func:`capture_exception` — safe wrapper around ``sentry_sdk.capture_exception``
  that no-ops when Sentry isn't initialized.

Sample rates and environment metadata respect ``SENTRY_TRACES_SAMPLE_RATE``
(default 0.1) and ``ENVIRONMENT`` (default ``production``).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_initialized = False


def _resolve_dsn() -> Optional[str]:
    for key in ("SENTRY_DSN", "LLMHIVE_SENTRY_DSN"):
        dsn = os.getenv(key, "").strip()
        if dsn and not dsn.startswith("http://example") and "@..." not in dsn:
            return dsn
    return None


def _resolve_sample_rate(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(0.0, min(1.0, value))


def is_sentry_configured() -> bool:
    """True when a usable Sentry DSN is set in the environment."""
    return _resolve_dsn() is not None


def init_sentry_if_configured() -> bool:
    """Initialize Sentry if a DSN is configured and the SDK is installed.

    Idempotent: calling it twice does not re-init.
    """
    global _initialized
    if _initialized:
        return True

    dsn = _resolve_dsn()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except Exception as exc:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk could not be imported (%s). "
            "Run: pip install 'sentry-sdk[fastapi]' to activate error reporting.",
            exc,
        )
        return False

    integrations: list[Any] = [
        LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
    ]

    try:
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        integrations.extend(
            [FastApiIntegration(), StarletteIntegration()]
        )
    except Exception:
        pass

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("BUILD_COMMIT") or os.getenv("GIT_SHA") or None,
        traces_sample_rate=_resolve_sample_rate("SENTRY_TRACES_SAMPLE_RATE", 0.1),
        profiles_sample_rate=_resolve_sample_rate("SENTRY_PROFILES_SAMPLE_RATE", 0.0),
        send_default_pii=False,
        integrations=integrations,
    )
    _initialized = True
    logger.info("sentry: initialized (dsn host=%s)", dsn.split("@")[-1].split("/")[0])
    return True


def capture_exception(exc: BaseException, **scope: Any) -> None:
    """Capture an exception via Sentry if initialized; otherwise no-op."""
    if not _initialized:
        return
    try:
        import sentry_sdk
    except Exception:
        return
    try:
        if scope:
            with sentry_sdk.push_scope() as s:
                for key, value in scope.items():
                    s.set_extra(key, value)
                sentry_sdk.capture_exception(exc)
        else:
            sentry_sdk.capture_exception(exc)
    except Exception as inner:
        logger.warning("sentry.capture_exception failed: %s", inner)
