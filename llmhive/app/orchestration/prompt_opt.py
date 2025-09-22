"""Prompt optimization and segmentation utilities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .equalizer import OrchestrationProfile


@dataclass
class PromptPlan:
    """Represents an optimized prompt decomposition."""

    core_prompt: str
    segments: List[str]
    competing_variants: List[str]


class PromptOptimizer:
    """Refine user queries into orchestrator-ready prompt plans."""

    def optimize(self, query: str, profile: OrchestrationProfile) -> PromptPlan:
        """Generate a refined prompt and optional sub-prompts."""

        normalized = query.strip()
        core_prompt = normalized

        segments = self._segment_query(normalized)
        competing_variants = self._build_variants(core_prompt, profile)

        return PromptPlan(core_prompt=core_prompt, segments=segments, competing_variants=competing_variants)

    def _segment_query(self, query: str) -> List[str]:
        """Split the query into domain-specific segments."""

        if len(query) < 120:
            return [query]
        sentences = re.split(r"(?<=[.!?])\s+", query)
        segments: List[str] = []
        bucket: list[str] = []
        for sentence in sentences:
            bucket.append(sentence)
            joined = " ".join(bucket).strip()
            if len(joined) > 200:
                segments.append(joined)
                bucket = []
        if bucket:
            segments.append(" ".join(bucket).strip())
        return segments or [query]

    def _build_variants(self, prompt: str, profile: OrchestrationProfile) -> List[str]:
        """Create competing prompt variants for self-consistency sampling."""

        variants = [prompt]
        if profile.creativity_boost > 0.2:
            variants.append(f"Take a structured approach: {prompt}")
        if profile.creativity_boost > 0.5:
            variants.append(f"Imagine alternative strategies before answering: {prompt}")
        if profile.creativity_boost > 0.8:
            variants.append(f"Provide two contrasting hypotheses then decide: {prompt}")
        return variants[: max(1, profile.num_samples)]
