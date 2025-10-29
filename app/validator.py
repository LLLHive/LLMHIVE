"""Validation helpers used by the orchestrator tests."""

from __future__ import annotations

from typing import Any, Dict


class Validator:
    """Performs lightweight safety and formatting checks."""

    @staticmethod
    def validate_output(output: Dict[str, Any]) -> bool:
        if not isinstance(output, dict):  # pragma: no cover - defensive branch
            return False

        if "disallowed_content" in output:
            return False

        final_response = output.get("final_response")
        if final_response is None:
            return True

        return isinstance(final_response, str) and bool(final_response.strip())

    @staticmethod
    def format_check(output: Dict[str, Any]) -> bool:
        format_value = output.get("format")
        return isinstance(format_value, str) and bool(format_value)
