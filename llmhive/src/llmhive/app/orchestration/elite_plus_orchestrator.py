"""Thin compatibility layer for benchmark ensemble guardrails.

Historically used by orchestration tests; keeps voting thresholds in one place.
"""
from __future__ import annotations

from typing import Optional


def _benchmark_free_majority_can_override_base(
    base_letter: Optional[str],
    majority_letter: Optional[str],
    majority_count: int,
    total_count: int,
) -> bool:
    """Whether a free-model majority may override a locked benchmark base letter.

    When ``base_letter`` is set and disagrees with ``majority_letter``, override is
    allowed only if the majority strictly exceeds two-thirds of ``total_count``.
    Matching base and majority never requires an override; no base defers to normal majority.
    """
    if base_letter is None:
        return True
    if majority_letter is None or total_count <= 0:
        return False
    if base_letter.strip().upper() == majority_letter.strip().upper():
        return False
    return majority_count * 3 > 2 * total_count
