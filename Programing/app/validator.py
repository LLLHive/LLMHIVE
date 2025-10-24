"""Performs validation and safety checks for agent outputs."""

from typing import Dict, Any


class Validator:
    """Validates outputs for factual accuracy and policy compliance."""

    @staticmethod
    def validate_output(output: Dict[str, Any]) -> bool:
        """Validate the output for correctness and compliance."""
        # Example validation logic
        if "disallowed_content" in output:
            return False
        return True

    @staticmethod
    def format_check(output: Dict[str, Any]) -> bool:
        """Check if the output adheres to the requested format."""
        return "format" in output
