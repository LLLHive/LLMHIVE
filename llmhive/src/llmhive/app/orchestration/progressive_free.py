"""Progressive Free Orchestration — Staged Escalation for Lower Latency.

Replaces the always-3-model ensemble with a progressive escalation strategy:
  Stage 1: Call primary free model only → response + confidence
  Stage 2: If confidence < threshold → call 1 additional model; if agree → return
  Stage 3: If disagree → call 1 more; vote/aggregate; return

Strict tier enforcement is preserved: when FREE_TIER_STRICT=1, no paid model
may execute at any stage.

Flags (defaults):
  FREE_PROGRESSIVE=0              (OFF until validated)
  FREE_STAGE1_MODELS=1
  FREE_STAGE2_ENSEMBLE_SIZE=2
  FREE_STAGE3_ENSEMBLE_SIZE=3
  FREE_ESCALATE_CONFIDENCE=0.55
  FREE_EARLY_STOP_ON_AGREEMENT=1
  FREE_MAX_TOTAL_CALLS_PER_QUERY=3

Rollback: export FREE_PROGRESSIVE=0
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENV FLAGS
# ---------------------------------------------------------------------------
FREE_PROGRESSIVE = os.getenv("FREE_PROGRESSIVE", "0").lower() in ("1", "true")
FREE_STAGE1_MODELS = int(os.getenv("FREE_STAGE1_MODELS", "1"))
FREE_STAGE2_ENSEMBLE_SIZE = int(os.getenv("FREE_STAGE2_ENSEMBLE_SIZE", "2"))
FREE_STAGE3_ENSEMBLE_SIZE = int(os.getenv("FREE_STAGE3_ENSEMBLE_SIZE", "3"))
FREE_ESCALATE_CONFIDENCE = float(os.getenv("FREE_ESCALATE_CONFIDENCE", "0.55"))
FREE_EARLY_STOP_ON_AGREEMENT = os.getenv(
    "FREE_EARLY_STOP_ON_AGREEMENT", "1"
).lower() in ("1", "true")
FREE_MAX_TOTAL_CALLS = int(os.getenv("FREE_MAX_TOTAL_CALLS_PER_QUERY", "3"))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class StageResult:
    model: str
    answer: str
    confidence: float
    latency_ms: int
    error: Optional[str] = None


@dataclass
class ProgressiveResult:
    final_answer: str
    final_confidence: float
    stages_executed: int
    total_calls: int
    total_latency_ms: int
    stage_results: List[StageResult] = field(default_factory=list)
    early_stopped: bool = False
    models_used: List[str] = field(default_factory=list)

    def to_telemetry(self) -> Dict[str, Any]:
        return {
            "progressive_free": True,
            "stages_executed": self.stages_executed,
            "total_calls": self.total_calls,
            "total_latency_ms": self.total_latency_ms,
            "early_stopped": self.early_stopped,
            "final_confidence": round(self.final_confidence, 3),
            "models_used": self.models_used,
        }


# ---------------------------------------------------------------------------
# Confidence extraction
# ---------------------------------------------------------------------------
_CONFIDENCE_PATTERNS = [
    re.compile(r"confidence[:\s]+([0-9]*\.?[0-9]+)", re.IGNORECASE),
    re.compile(r"(?:I am|I\'m)\s+(\d{1,3})%\s+(?:confident|sure|certain)", re.IGNORECASE),
    re.compile(r"certainty[:\s]+([0-9]*\.?[0-9]+)", re.IGNORECASE),
]

_HIGH_CONFIDENCE_SIGNALS = [
    "definitely", "certainly", "absolutely", "clearly", "obviously",
    "without a doubt", "100%", "I am certain",
]
_LOW_CONFIDENCE_SIGNALS = [
    "I'm not sure", "I think", "possibly", "perhaps", "might be",
    "it's unclear", "approximately", "I believe",
]


def _extract_confidence(text: str) -> float:
    """Heuristic confidence extraction from model response."""
    for pattern in _CONFIDENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            val = float(match.group(1))
            if val > 1.0:
                val /= 100.0
            return max(0.0, min(1.0, val))

    text_lower = text.lower()
    high = sum(1 for s in _HIGH_CONFIDENCE_SIGNALS if s in text_lower)
    low = sum(1 for s in _LOW_CONFIDENCE_SIGNALS if s in text_lower)

    base = 0.6
    base += high * 0.08
    base -= low * 0.08
    return max(0.1, min(0.95, base))


def _normalize_for_comparison(text: str) -> str:
    """Normalize answer text for agreement comparison."""
    cleaned = re.sub(r"[^a-z0-9 ]", "", text.lower().strip())
    return cleaned[:300]


def _answers_agree(a: str, b: str) -> bool:
    """Check if two answers substantively agree."""
    na, nb = _normalize_for_comparison(a), _normalize_for_comparison(b)
    if not na or not nb:
        return False
    words_a = set(na.split())
    words_b = set(nb.split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b)
    union = len(words_a | words_b)
    jaccard = overlap / union if union else 0.0
    return jaccard >= 0.5


# ---------------------------------------------------------------------------
# Single-model call
# ---------------------------------------------------------------------------
async def _call_single_model(
    orchestrator: Any,
    prompt: str,
    model_id: str,
    timeout_s: float = 30.0,
) -> StageResult:
    """Call a single model and return a StageResult."""
    t0 = time.perf_counter()
    try:
        artifacts = await asyncio.wait_for(
            orchestrator.orchestrate(
                prompt,
                [model_id],
                use_hrm=False,
                use_adaptive_routing=False,
                use_deep_consensus=False,
                use_prompt_diffusion=False,
                accuracy_level=3,
                skip_injection_check=True,
            ),
            timeout=timeout_s,
        )
        answer = artifacts.final_response.content
        latency = int((time.perf_counter() - t0) * 1000)
        confidence = _extract_confidence(answer)
        return StageResult(
            model=model_id,
            answer=answer,
            confidence=confidence,
            latency_ms=latency,
        )
    except asyncio.TimeoutError:
        latency = int((time.perf_counter() - t0) * 1000)
        return StageResult(
            model=model_id, answer="", confidence=0.0,
            latency_ms=latency, error="timeout",
        )
    except Exception as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        return StageResult(
            model=model_id, answer="", confidence=0.0,
            latency_ms=latency, error=str(exc),
        )


def _vote(results: List[StageResult]) -> Tuple[str, float]:
    """Majority vote across stage results. Return (best_answer, confidence)."""
    valid = [r for r in results if r.answer and not r.error]
    if not valid:
        return "", 0.0
    if len(valid) == 1:
        return valid[0].answer, valid[0].confidence

    groups: Dict[str, List[StageResult]] = {}
    for r in valid:
        key = _normalize_for_comparison(r.answer)[:100]
        matched = False
        for gk in groups:
            if _answers_agree(r.answer, groups[gk][0].answer):
                groups[gk].append(r)
                matched = True
                break
        if not matched:
            groups[key] = [r]

    largest = max(groups.values(), key=len)
    best = max(largest, key=lambda r: r.confidence)
    agreement_ratio = len(largest) / len(valid)
    boosted = min(1.0, best.confidence + agreement_ratio * 0.1)
    return best.answer, boosted


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def run_progressive_free(
    prompt: str,
    models: List[str],
    orchestrator: Any,
) -> ProgressiveResult:
    """Run progressive free-tier orchestration.

    Args:
        prompt:       User query (already enhanced by PromptOps if applicable).
        models:       Ordered list of free models to use (from category routing).
        orchestrator: The base Orchestrator instance for making model calls.

    Returns:
        ProgressiveResult with the final answer and telemetry.
    """
    t0 = time.perf_counter()
    all_results: List[StageResult] = []
    calls_made = 0
    stages = 0

    if not models:
        return ProgressiveResult(
            final_answer="",
            final_confidence=0.0,
            stages_executed=0,
            total_calls=0,
            total_latency_ms=0,
        )

    # --- Stage 1: Primary model ---
    stages = 1
    primary = models[0]
    s1 = await _call_single_model(orchestrator, prompt, primary)
    all_results.append(s1)
    calls_made += 1

    logger.info(
        "PROGRESSIVE FREE Stage 1: model=%s conf=%.2f latency=%dms",
        primary, s1.confidence, s1.latency_ms,
    )

    if (
        s1.confidence >= FREE_ESCALATE_CONFIDENCE
        and s1.answer
        and not s1.error
    ):
        total_lat = int((time.perf_counter() - t0) * 1000)
        logger.info("PROGRESSIVE FREE: early stop at Stage 1 (conf=%.2f)", s1.confidence)
        return ProgressiveResult(
            final_answer=s1.answer,
            final_confidence=s1.confidence,
            stages_executed=1,
            total_calls=1,
            total_latency_ms=total_lat,
            stage_results=all_results,
            early_stopped=True,
            models_used=[primary],
        )

    # --- Stage 2: Add one model ---
    if calls_made < FREE_MAX_TOTAL_CALLS and len(models) >= 2:
        stages = 2
        second = models[1]
        s2 = await _call_single_model(orchestrator, prompt, second)
        all_results.append(s2)
        calls_made += 1

        logger.info(
            "PROGRESSIVE FREE Stage 2: model=%s conf=%.2f latency=%dms",
            second, s2.confidence, s2.latency_ms,
        )

        if (
            FREE_EARLY_STOP_ON_AGREEMENT
            and s1.answer
            and s2.answer
            and _answers_agree(s1.answer, s2.answer)
        ):
            best_answer, best_conf = _vote(all_results)
            total_lat = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "PROGRESSIVE FREE: early stop at Stage 2 (agreement, conf=%.2f)", best_conf
            )
            return ProgressiveResult(
                final_answer=best_answer,
                final_confidence=best_conf,
                stages_executed=2,
                total_calls=2,
                total_latency_ms=total_lat,
                stage_results=all_results,
                early_stopped=True,
                models_used=[primary, second],
            )

    # --- Stage 3: Add one more model ---
    if calls_made < FREE_MAX_TOTAL_CALLS and len(models) >= 3:
        stages = 3
        third = models[2]
        s3 = await _call_single_model(orchestrator, prompt, third)
        all_results.append(s3)
        calls_made += 1

        logger.info(
            "PROGRESSIVE FREE Stage 3: model=%s conf=%.2f latency=%dms",
            third, s3.confidence, s3.latency_ms,
        )

    # Final vote
    final_answer, final_conf = _vote(all_results)
    total_lat = int((time.perf_counter() - t0) * 1000)

    logger.info(
        "PROGRESSIVE FREE: completed %d stages, %d calls, conf=%.2f, latency=%dms",
        stages, calls_made, final_conf, total_lat,
    )

    return ProgressiveResult(
        final_answer=final_answer,
        final_confidence=final_conf,
        stages_executed=stages,
        total_calls=calls_made,
        total_latency_ms=total_lat,
        stage_results=all_results,
        early_stopped=False,
        models_used=[r.model for r in all_results],
    )
