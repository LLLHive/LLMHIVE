"""Internal-only request authentication.

An internal request must satisfy BOTH:
  1. A trusted auth condition (secret header matches INTERNAL_ADMIN_OVERRIDE_KEY), AND
  2. The ALLOW_INTERNAL_BENCH env flag is enabled.

External requests can never trigger internal bench behaviors (extra paid calls,
bench output headers, internal KPI endpoints) regardless of headers.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_INTERNAL_KEY = os.getenv("INTERNAL_ADMIN_OVERRIDE_KEY", "")
_ALLOW_INTERNAL_BENCH = os.getenv("ALLOW_INTERNAL_BENCH", "0").lower() in ("1", "true")
_INTERNAL_HEADER = "X-LLMHive-Internal-Key"


def is_internal_request(
    headers: Optional[dict] = None,
    *,
    request: Any = None,
) -> bool:
    """Check if a request is authenticated as internal/admin.

    Returns True only when BOTH conditions are met:
      1. ALLOW_INTERNAL_BENCH=1 in env
      2. The request carries a valid X-LLMHive-Internal-Key header
         that matches INTERNAL_ADMIN_OVERRIDE_KEY (constant-time comparison)

    Never trusts X-LLMHIVE-INTERNAL-BENCH or similar convenience headers
    on their own.
    """
    if not _ALLOW_INTERNAL_BENCH:
        return False

    if not _INTERNAL_KEY:
        return False

    provided = ""
    if headers:
        provided = headers.get(_INTERNAL_HEADER, headers.get(
            _INTERNAL_HEADER.lower(), ""))

    if not provided and request is not None:
        try:
            provided = request.headers.get(_INTERNAL_HEADER, "")
        except Exception:
            pass

    if not provided:
        return False

    return hmac.compare_digest(provided, _INTERNAL_KEY)


def sanitize_internal_flags(
    headers: Optional[dict],
    *,
    request: Any = None,
) -> dict:
    """Return a dict of internal flags, zeroing any that aren't authenticated.

    Call this early in the request path so that downstream code can trust
    the returned flags without re-checking auth.
    """
    internal = is_internal_request(headers, request=request)

    return {
        "is_internal": internal,
        "allow_bench_output": internal,
        "allow_extra_paid_calls": internal,
        "max_paid_calls_override": 2 if internal else None,
    }
