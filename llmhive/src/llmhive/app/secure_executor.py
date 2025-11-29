"""Security: Secure wrapper for provider calls.

This module allows the orchestrator to route provider calls through a thin
sanitisation boundary. In the current implementation this lives in-process,
but it can be extended to launch subprocesses or delegate to sidecar
services if stronger isolation is required.
"""
from __future__ import annotations

import logging
from typing import Iterable, Mapping, Optional, Sequence

from .guardrails import (
    ExecutionSandbox,
    RiskAssessment,
    SafetyValidator,
    assess_query_risk,
    filter_output,
    filter_query,
)

from .services.base import LLMProvider, LLMResult

logger = logging.getLogger(__name__)


class SecureProviderExecutor:
    """Security: Applies guardrails before and after provider calls."""

    def __init__(
        self,
        safety: SafetyValidator | None = None,
        is_external: bool = True,
        enable_sandbox: bool = True,
    ) -> None:
        self.safety = safety or SafetyValidator()
        self.is_external = is_external  # Security: Whether provider is external/untrusted
        self.sandbox: Optional[ExecutionSandbox] = (
            ExecutionSandbox() if enable_sandbox else None
        )  # Security: Execution sandbox for code/tool execution

    def _sanitize_prompt(self, prompt: str) -> str:
        """Security: Sanitize prompt by filtering sensitive content for external models."""
        if self.is_external:
            # Security: Filter sensitive content (PII) before sending to external models
            filtered = filter_query(prompt, is_external=True)
            if filtered != prompt:
                logger.info("Security: Input scrubbing applied to prompt for external model")
            return filtered
        # Security: Local models don't need scrubbing
        return prompt

    def _inspect_result(self, result: LLMResult) -> LLMResult:
        """Security: Inspect and filter model output for disallowed content."""
        # Security: First apply safety validator
        report = self.safety.inspect(result.content)
        sanitized = report.sanitized_content
        
        # Security: Then apply output filtering
        filtered, content_removed, issues = filter_output(sanitized, severity_threshold="medium")
        
        if filtered != result.content:
            return LLMResult(
                content=filtered,
                model=result.model,
                tokens=result.tokens,
                cost=result.cost,
            )
        return result

    async def complete(self, provider: LLMProvider, prompt: str, *, model: str) -> LLMResult:
        """Security: Complete with input scrubbing and output filtering."""
        safe_prompt = self._sanitize_prompt(prompt)
        result = await provider.complete(safe_prompt, model=model)
        return self._inspect_result(result)

    async def critique(
        self,
        provider: LLMProvider,
        subject: str,
        *,
        target_answer: str,
        author: str,
        model: str,
    ) -> LLMResult:
        """Security: Critique with input scrubbing and output filtering."""
        safe_subject = self._sanitize_prompt(subject)
        safe_target = self._sanitize_prompt(target_answer)
        result = await provider.critique(
            safe_subject,
            target_answer=safe_target,
            author=author,
            model=model,
        )
        return self._inspect_result(result)

    async def improve(
        self,
        provider: LLMProvider,
        subject: str,
        *,
        previous_answer: str,
        critiques: Sequence[str],
        model: str,
    ) -> LLMResult:
        """Security: Improve with input scrubbing and output filtering."""
        safe_subject = self._sanitize_prompt(subject)
        safe_prev = self._sanitize_prompt(previous_answer)
        safe_critiques = [self._sanitize_prompt(c) for c in critiques]
        result = await provider.improve(
            safe_subject,
            previous_answer=safe_prev,
            critiques=safe_critiques,
            model=model,
        )
        return self._inspect_result(result)


