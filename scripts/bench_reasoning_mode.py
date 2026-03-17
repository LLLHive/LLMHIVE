"""Bench-only: OpenAPI reasoning_mode discovery to avoid 422 on schema drift."""
from __future__ import annotations

import os
from typing import List, Optional

_CACHE: Optional[List[str]] = None


def discover_reasoning_mode_enum(api_url: str, benchmark_mode: bool = True) -> List[str]:
    """Fetch OpenAPI and extract allowed reasoning_mode enum. Cached per process.
    Returns [] if discovery fails (caller should omit the field).
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not benchmark_mode:
        _CACHE = []
        return _CACHE
    try:
        import httpx
        url = f"{api_url.rstrip('/')}/openapi.json"
        with httpx.Client(timeout=10) as client:
            r = client.get(url)
            if r.status_code != 200:
                _CACHE = []
                return _CACHE
            data = r.json()
        schemas = data.get("components", {}).get("schemas", {})
        for name, schema in schemas.items():
            if "reasoning" in name.lower() and "mode" in name.lower():
                enum_vals = schema.get("enum")
                if isinstance(enum_vals, list) and enum_vals:
                    allowed = [str(v).lower() for v in enum_vals if isinstance(v, str)]
                    if allowed:
                        _CACHE = allowed
                        return _CACHE
            if "ReasoningMode" in name:
                enum_vals = schema.get("enum")
                if isinstance(enum_vals, list) and enum_vals:
                    allowed = [str(v).lower() for v in enum_vals if isinstance(v, str)]
                    if allowed:
                        _CACHE = allowed
                        return _CACHE
        _CACHE = []
    except Exception:
        _CACHE = []
    return _CACHE


def get_safe_reasoning_mode(
    requested: str,
    allowed: Optional[List[str]] = None,
) -> Optional[str]:
    """Return reasoning_mode to send, or None to omit (avoids 422).
    Uses BENCH_REASONING_MODE if set and allowed; else requested if allowed; else None.
    """
    override = os.getenv("BENCH_REASONING_MODE", "").strip().lower()
    to_check = override if override else requested.lower()
    if allowed is None:
        return None
    if to_check in allowed:
        return to_check
    return None
