"""Sampling helpers for ensemble strategies."""
from __future__ import annotations


def compute_samples(num_models: int, desired_samples: int) -> int:
    """Return the number of samples per model."""

    if num_models <= 0:
        return 1
    ratio = desired_samples / max(1, num_models)
    return max(1, int(round(ratio)))
