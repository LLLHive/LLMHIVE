"""Map user slider settings to orchestration profiles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - avoids circular import at runtime
    from .orchestrator import OrchestrationOptions


@dataclass
class OrchestrationProfile:
    """Derived orchestration configuration used by downstream modules."""

    num_models: int
    num_samples: int
    challenge_rounds: int
    factcheck_enabled: bool
    creativity_boost: float
    max_tokens: int
    json_mode: bool


class Equalizer:
    """Translate user preferences into execution depth."""

    def map_options(self, options: "OrchestrationOptions") -> OrchestrationProfile:
        """Convert slider values into orchestration parameters."""

        num_models = max(1, min(4, round(1 + options.accuracy * 3 - options.speed)))
        num_samples = max(1, min(5, round(1 + options.accuracy * 2 + options.creativity * 2)))
        challenge_rounds = 1 if options.accuracy > 0.6 and options.cost > 0.2 else 0
        if options.speed > 0.7:
            challenge_rounds = 0
            num_samples = max(1, num_samples - 1)
        factcheck_enabled = options.accuracy >= 0.5
        if options.cost < 0.3:
            num_models = max(1, num_models - 1)
            factcheck_enabled = False
        creativity_boost = options.creativity

        profile = OrchestrationProfile(
            num_models=num_models,
            num_samples=num_samples,
            challenge_rounds=challenge_rounds,
            factcheck_enabled=factcheck_enabled,
            creativity_boost=creativity_boost,
            max_tokens=options.max_tokens,
            json_mode=options.json_mode,
        )
        return profile
