"""Tests for reasoning_mode OpenAPI discovery (bench-only, avoids 422)."""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path for import
_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))


def test_discover_reasoning_mode_from_openapi():
    """When OpenAPI has ReasoningMode enum, helper returns allowed values."""
    import bench_reasoning_mode as mod
    mod._CACHE = None

    mock_openapi = {
        "components": {
            "schemas": {
                "llmhive__app__models__orchestration__ReasoningMode": {
                    "type": "string",
                    "enum": ["fast", "standard", "deep"],
                }
            }
        }
    }

    with patch("httpx.Client") as mock_client:
        mock_resp = mock_client.return_value.__enter__.return_value.get.return_value
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_openapi

        result = mod.discover_reasoning_mode_enum("https://example.com", benchmark_mode=True)
        assert result == ["fast", "standard", "deep"]


def test_discover_fails_returns_empty():
    """When discovery fails, returns empty list (caller should omit field)."""
    import bench_reasoning_mode as mod
    mod._CACHE = None

    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection refused")

        result = mod.discover_reasoning_mode_enum("https://example.com", benchmark_mode=True)
        assert result == []


def test_get_safe_reasoning_mode_valid_uses_value():
    """When value is in allowed list, returns it."""
    import bench_reasoning_mode as mod

    assert mod.get_safe_reasoning_mode("deep", ["fast", "standard", "deep"]) == "deep"
    assert mod.get_safe_reasoning_mode("standard", ["fast", "standard", "deep"]) == "standard"


def test_get_safe_reasoning_mode_invalid_omits():
    """When value not in allowed list, returns None (omit from payload)."""
    import bench_reasoning_mode as mod

    assert mod.get_safe_reasoning_mode("deep", ["fast", "standard"]) is None


def test_get_safe_reasoning_mode_discovery_failed_omits():
    """When discovery failed (empty allowed), returns None."""
    import bench_reasoning_mode as mod

    assert mod.get_safe_reasoning_mode("deep", []) is None
    assert mod.get_safe_reasoning_mode("deep", None) is None


def test_bench_reasoning_mode_override_env():
    """BENCH_REASONING_MODE override is used when in allowed list."""
    import bench_reasoning_mode as mod

    with patch.dict(os.environ, {"BENCH_REASONING_MODE": "fast"}):
        assert mod.get_safe_reasoning_mode("deep", ["fast", "standard", "deep"]) == "fast"
