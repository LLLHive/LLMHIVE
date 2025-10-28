"""Lightweight guardrail system for validating generated content."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(slots=True)
class GuardrailReport:
    """Result of running guardrail checks against content."""

    passed: bool
    issues: List[str]
    sanitized_content: str
    advisories: List[str]


class SafetyValidator:
    """Applies basic safety and factuality heuristics to model output."""

    def __init__(self, banned_phrases: Iterable[str] | None = None) -> None:
        self.banned_patterns = [re.compile(re.escape(phrase), re.IGNORECASE) for phrase in (banned_phrases or [])]
        # Default banned phrases reflect operational policies
        if not self.banned_patterns:
            self.banned_patterns = [
                re.compile(r"\bexecute\s+malware\b", re.IGNORECASE),
                re.compile(r"\bcredit\s*card\s*number\b", re.IGNORECASE),
            ]

    def inspect(self, content: str) -> GuardrailReport:
        issues: List[str] = []
        sanitized = content

        for pattern in self.banned_patterns:
            if pattern.search(sanitized):
                issues.append(f"Removed sensitive fragment matching pattern '{pattern.pattern}'.")
                sanitized = pattern.sub("[REDACTED]", sanitized)

        advisories: List[str] = []
        if len(sanitized.strip()) < 5:
            issues.append("Response is unexpectedly short; potential generation failure.")
        if "citation" in sanitized.lower() and "http" not in sanitized.lower():
            advisories.append("Consider providing explicit sources for cited information.")

        passed = not issues
        return GuardrailReport(passed=passed, issues=issues, sanitized_content=sanitized, advisories=advisories)
