"""Timing utilities and metrics helpers."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class StageTimer:
    """Utility to measure elapsed times for named stages."""

    _measurements: Dict[str, float] = field(default_factory=dict)

    @contextmanager
    def measure(self, stage: str):
        """Context manager that records the duration of the wrapped block."""

        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            self._measurements[stage] = elapsed

    def snapshot(self) -> Dict[str, float]:
        """Return a copy of the recorded measurements."""

        return dict(self._measurements)
