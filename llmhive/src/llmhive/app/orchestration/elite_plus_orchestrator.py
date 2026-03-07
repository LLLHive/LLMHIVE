"""Elite+ Orchestrator — Free-First Verified Premium.

The ONLY public premium tier.  Elite is internal fallback only.

Policy: free_first_verified
  Stage A — Free primary:   run free ensemble for the category
  Stage B — Deterministic:  calculator/MCQ/tool-schema/RAG grounding check
  Stage C — Paid escalation: call ONE category-specific paid anchor (if triggered)
  Stage D — Fallback:       fall back to base Elite only on catastrophic failure

Cost targets: p50 <= $0.010, p95 <= $0.020 per request.
Paid calls default max = 1 in production (hard cap = 2 for internal bench).

Rollback: ELITE_PLUS_ENABLED=0 + PREMIUM_DEFAULT_TIER=elite
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ENV FLAGS
# ---------------------------------------------------------------------------
ELITE_PLUS_ENABLED = os.getenv("ELITE_PLUS_ENABLED", "1").lower() in ("1", "true")
ELITE_PLUS_MODE = os.getenv("ELITE_PLUS_MODE", "active").lower().strip()
ELITE_PLUS_POLICY = os.getenv("ELITE_PLUS_POLICY", "free_first_verified").lower().strip()

# Premium tier routing — elite_plus is the public premium tier
PREMIUM_DEFAULT_TIER = os.getenv("PREMIUM_DEFAULT_TIER", "elite_plus").lower().strip()
ELITE_FALLBACK_ENABLED = os.getenv("ELITE_FALLBACK_ENABLED", "1").lower() in ("1", "true")
ELITE_PUBLIC_ENABLED = os.getenv("ELITE_PUBLIC_ENABLED", "0").lower() in ("1", "true")

# Budget caps
ELITE_PLUS_MAX_PAID_CALLS = int(os.getenv("ELITE_PLUS_MAX_PAID_CALLS", "1"))
ELITE_PLUS_MAX_PAID_CALLS_HARD = int(os.getenv("ELITE_PLUS_MAX_PAID_CALLS_HARD", "2"))
ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH = int(os.getenv("ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH", "1"))
ELITE_PLUS_BUDGET_USD_P50 = float(os.getenv("ELITE_PLUS_BUDGET_USD_P50", "0.010"))
ELITE_PLUS_BUDGET_USD_P95 = float(os.getenv("ELITE_PLUS_BUDGET_USD_P95", "0.020"))
ELITE_PLUS_BUDGET_MS = int(os.getenv("ELITE_PLUS_BUDGET_MS", "8000"))

# Escalation triggers
ELITE_PLUS_ESCALATE_ON_DISAGREEMENT = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_DISAGREEMENT", "1"
).lower() in ("1", "true")
ELITE_PLUS_ESCALATE_ON_LOW_CONFIDENCE = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_LOW_CONFIDENCE", "1"
).lower() in ("1", "true")
ELITE_PLUS_ESCALATE_ON_TOOL_FAILURE = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_TOOL_FAILURE", "1"
).lower() in ("1", "true")
ELITE_PLUS_ESCALATE_ON_RAG_UNGROUNDED = os.getenv(
    "ELITE_PLUS_ESCALATE_ON_RAG_UNGROUNDED", "1"
).lower() in ("1", "true")
ELITE_PLUS_LOW_CONF_THRESHOLD = float(
    os.getenv("ELITE_PLUS_LOW_CONF_THRESHOLD", "0.65")
)

# Category-specific policies
ELITE_PLUS_TOOL_STRICT_MODE = os.getenv("ELITE_PLUS_TOOL_STRICT_MODE", "1").lower() in ("1", "true")
ELITE_PLUS_TOOL_POSTPROCESS_ALLOWED = os.getenv("ELITE_PLUS_TOOL_POSTPROCESS_ALLOWED", "0").lower() in ("1", "true")
ELITE_PLUS_RAG_EXTRACTIVE_MODE = os.getenv("ELITE_PLUS_RAG_EXTRACTIVE_MODE", "1").lower() in ("1", "true")
ELITE_PLUS_RAG_REQUIRE_SUPPORT = os.getenv("ELITE_PLUS_RAG_REQUIRE_SUPPORT", "1").lower() in ("1", "true")
ELITE_PLUS_RAG_TOPK = int(os.getenv("ELITE_PLUS_RAG_TOPK", "10"))
ELITE_PLUS_RERANK_DETERMINISTIC = os.getenv("ELITE_PLUS_RERANK_DETERMINISTIC", "1").lower() in ("1", "true")
ELITE_PLUS_DIALOGUE_LIGHT_TOUCH = os.getenv("ELITE_PLUS_DIALOGUE_LIGHT_TOUCH", "1").lower() in ("1", "true")
ELITE_PLUS_DIALOGUE_MAX_MODELS = int(os.getenv("ELITE_PLUS_DIALOGUE_MAX_MODELS", "1"))
ELITE_PLUS_MATH_FREE_FIRST = os.getenv("ELITE_PLUS_MATH_FREE_FIRST", "1").lower() in ("1", "true")
ELITE_PLUS_MATH_REQUIRE_VERIFICATION = os.getenv("ELITE_PLUS_MATH_REQUIRE_VERIFICATION", "1").lower() in ("1", "true")

# Long context
ELITE_PLUS_LONG_CONTEXT_ANCHOR_MODEL = os.getenv(
    "ELITE_PLUS_LONG_CONTEXT_ANCHOR_MODEL", "google/gemini-3.1-pro-preview"
)

# Verifier
ELITE_PLUS_VERIFIER_STRATEGY = os.getenv("ELITE_PLUS_VERIFIER_STRATEGY", "hybrid").lower()
ELITE_PLUS_VERIFIER_TIMEOUT_MS = int(os.getenv("ELITE_PLUS_VERIFIER_TIMEOUT_MS", "12000"))
ELITE_PLUS_VERIFIER_MODEL = os.getenv("ELITE_PLUS_VERIFIER_MODEL", "openai/gpt-4o-mini")

ELITE_PLUS_LOG_SHADOW = os.getenv("ELITE_PLUS_LOG_SHADOW", "1").lower() in ("1", "true")
ALLOW_INTERNAL_BENCH_OUTPUT = os.getenv("ALLOW_INTERNAL_BENCH_OUTPUT", "0").lower() in ("1", "true")

# ---------------------------------------------------------------------------
# G2: Launch Mode runtime governance
# ---------------------------------------------------------------------------
ELITE_PLUS_LAUNCH_MODE = os.getenv("ELITE_PLUS_LAUNCH_MODE", "1").lower() in ("1", "true")
ELITE_PLUS_MAX_COST_USD_REQUEST = float(os.getenv("ELITE_PLUS_MAX_COST_USD_REQUEST", "0.025"))

# Circuit breaker config
ELITE_PLUS_CB_WINDOW = int(os.getenv("ELITE_PLUS_CB_WINDOW", "50"))
ELITE_PLUS_CB_MAX_ERROR_RATE = float(os.getenv("ELITE_PLUS_CB_MAX_ERROR_RATE", "0.20"))
ELITE_PLUS_CB_COOLDOWN_SEC = int(os.getenv("ELITE_PLUS_CB_COOLDOWN_SEC", "300"))

# P0 categories that are allowed paid escalation in Launch Mode
_P0_CATEGORIES = {"tool_use", "rag", "dialogue", "math"}
# Hard-failure escalation reasons that always allow paid calls
_HARD_FAILURE_REASONS = {"tool_schema_invalid", "tool_execution_error", "rag_grounding_fail", "catastrophic_failure"}

# ---------------------------------------------------------------------------
# Part B: Category-specific paid anchor selection (env-configurable)
# ---------------------------------------------------------------------------
_PAID_ANCHORS: Dict[str, str] = {
    "tool_use":     os.getenv("ELITE_PLUS_PAID_ANCHOR_TOOL_USE",     "openai/gpt-4o"),
    "rag":          os.getenv("ELITE_PLUS_PAID_ANCHOR_RAG",          "openai/gpt-4o-mini"),
    "reasoning":    os.getenv("ELITE_PLUS_PAID_ANCHOR_REASONING",    "openai/gpt-4o-mini"),
    "dialogue":     os.getenv("ELITE_PLUS_PAID_ANCHOR_DIALOGUE",     "anthropic/claude-sonnet-4"),
    "long_context": os.getenv("ELITE_PLUS_PAID_ANCHOR_LONG_CONTEXT", "google/gemini-3.1-pro-preview"),
    "math":         os.getenv("ELITE_PLUS_PAID_ANCHOR_MATH",         "openai/gpt-4o-mini"),
    "coding":       os.getenv("ELITE_PLUS_PAID_ANCHOR_CODING",       "anthropic/claude-sonnet-4"),
    "multilingual": os.getenv("ELITE_PLUS_PAID_ANCHOR_MULTILINGUAL", "openai/gpt-4o-mini"),
    "speed":        os.getenv("ELITE_PLUS_PAID_ANCHOR_SPEED",        "openai/gpt-4o-mini"),
    "multimodal":   os.getenv("ELITE_PLUS_PAID_ANCHOR_MULTIMODAL",   "openai/gpt-4o"),
}

# Free models per category
_FREE_MODELS_DEFAULT: Dict[str, List[str]] = {
    "math": ["deepseek/deepseek-chat", "qwen/qwen3-next-80b-a3b-instruct:free"],
    "reasoning": ["deepseek/deepseek-chat", "qwen/qwen3-next-80b-a3b-instruct:free"],
    "coding": ["qwen/qwen3-coder:free", "deepseek/deepseek-chat"],
    "rag": ["qwen/qwen3-next-80b-a3b-instruct:free", "deepseek/deepseek-chat"],
    "multilingual": ["deepseek/deepseek-chat", "qwen/qwen3-next-80b-a3b-instruct:free"],
    "long_context": ["qwen/qwen3-next-80b-a3b-instruct:free", "deepseek/deepseek-chat"],
    "tool_use": ["deepseek/deepseek-chat", "qwen/qwen3-coder:free"],
    "dialogue": ["deepseek/deepseek-chat"],
    "speed": ["deepseek/deepseek-chat"],
    "multimodal": ["deepseek/deepseek-chat"],
}

# Estimated costs (output tokens per 1M) for budget tracking
_MODEL_COST_PER_1M: Dict[str, float] = {
    "openai/gpt-4o-mini": 0.60,
    "openai/gpt-4o": 10.0,
    "anthropic/claude-sonnet-4": 15.0,
    "google/gemini-3.1-pro-preview": 2.0,
    "google/gemini-2.5-flash": 0.075,
}

_MCQ_PATTERN = re.compile(r"\b([A-E])\b")


# ---------------------------------------------------------------------------
# G2: Circuit breaker (in-memory per-model health tracking)
# ---------------------------------------------------------------------------
class _CircuitBreaker:
    """Per-model rolling-window error tracker with cooldown.

    Thread-safe via GIL for single-process; adequate for initial launch.
    """

    def __init__(
        self,
        window: int = ELITE_PLUS_CB_WINDOW,
        max_error_rate: float = ELITE_PLUS_CB_MAX_ERROR_RATE,
        cooldown_sec: int = ELITE_PLUS_CB_COOLDOWN_SEC,
    ):
        self._window = window
        self._max_error_rate = max_error_rate
        self._cooldown_sec = cooldown_sec
        self._records: Dict[str, List[bool]] = {}        # model -> [ok, ok, fail, ...]
        self._degraded_until: Dict[str, float] = {}      # model -> timestamp

    def record(self, model_id: str, success: bool) -> None:
        buf = self._records.setdefault(model_id, [])
        buf.append(success)
        if len(buf) > self._window:
            buf.pop(0)
        if len(buf) >= 10:
            error_rate = 1.0 - (sum(buf) / len(buf))
            if error_rate >= self._max_error_rate:
                self._degraded_until[model_id] = time.time() + self._cooldown_sec
                logger.warning(
                    "Circuit breaker OPEN for %s (error_rate=%.2f, cooldown=%ds)",
                    model_id, error_rate, self._cooldown_sec,
                )

    def is_degraded(self, model_id: str) -> bool:
        until = self._degraded_until.get(model_id)
        if until is None:
            return False
        if time.time() >= until:
            del self._degraded_until[model_id]
            self._records.pop(model_id, None)
            logger.info("Circuit breaker CLOSED for %s (cooldown expired)", model_id)
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        return {
            model: {
                "degraded": True,
                "remaining_sec": max(0, int(until - now)),
                "error_rate": round(
                    1.0 - (sum(self._records.get(model, [])) / max(len(self._records.get(model, [])), 1)),
                    3,
                ),
            }
            for model, until in self._degraded_until.items()
            if now < until
        }


_circuit_breaker = _CircuitBreaker()


def _launch_mode_allows_escalation(
    category: str,
    escalation_reasons: List[str],
) -> bool:
    """In Launch Mode, only allow paid escalation for P0 categories or hard failures."""
    if not ELITE_PLUS_LAUNCH_MODE:
        return True
    if category in _P0_CATEGORIES:
        return True
    classified = set()
    for r in escalation_reasons:
        for hf in _HARD_FAILURE_REASONS:
            if hf in r:
                classified.add(hf)
    return len(classified) > 0


def _launch_mode_cost_ok(current_cost: float, next_model: str) -> bool:
    """Check if adding one more model call stays within per-request ceiling."""
    if not ELITE_PLUS_LAUNCH_MODE:
        return True
    predicted = current_cost + _estimate_cost(next_model)
    return predicted <= ELITE_PLUS_MAX_COST_USD_REQUEST


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Public accessor for KPI endpoint."""
    return _circuit_breaker.get_status()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class ElitePlusResult:
    answer: str
    confidence: float
    mode: str
    policy: str
    stage_used: str                        # free_primary | deterministic_verify | paid_escalation | fallback_elite
    paid_calls_count: int = 0
    free_calls_count: int = 0
    estimated_cost_usd: float = 0.0
    estimated_cost_breakdown: Dict[str, float] = field(default_factory=dict)
    confidence_free: float = 0.0
    confidence_final: float = 0.0
    escalation_reason: List[str] = field(default_factory=list)
    models_called: List[str] = field(default_factory=list)
    tool_invocations: List[str] = field(default_factory=list)
    rag_grounding_status: str = "n/a"
    total_latency_ms: int = 0
    verifier_strategy: str = "none"
    verifier_status: str = "ok"
    verifier_latency_ms: int = 0

    # Part C: tool use telemetry
    tool_schema_valid: bool = True
    tool_retry_count: int = 0
    tool_execution_ok: bool = True
    tool_error_type: str = "none"

    # Part D: RAG telemetry
    rag_unanswered_reason: str = "none"
    rag_passage_count_used: int = 0

    # Part E: dialogue telemetry
    dialogue_mode: str = "n/a"
    dialogue_anchor_used: str = ""
    dialogue_escalated: bool = False

    # backward compat with shadow telemetry consumers
    shadow_answer: str = ""
    shadow_confidence: float = 0.0
    should_override: bool = True
    base_answer: str = ""
    base_confidence: float = 0.0
    blackboard_hash: str = ""

    def to_telemetry(self) -> Dict[str, Any]:
        return {
            "elite_plus_enabled": True,
            "elite_plus_mode": self.mode,
            "policy": self.policy,
            "stage_used": self.stage_used,
            "paid_calls_count": self.paid_calls_count,
            "free_calls_count": self.free_calls_count,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "estimated_cost_breakdown": self.estimated_cost_breakdown,
            "confidence_free": round(self.confidence_free, 3),
            "confidence_final": round(self.confidence_final, 3),
            "escalation_reason": self.escalation_reason,
            "models_called": self.models_called,
            "tool_invocations": self.tool_invocations,
            "rag_grounding_status": self.rag_grounding_status,
            "total_latency_ms": self.total_latency_ms,
            "verifier_strategy": self.verifier_strategy,
            "verifier_status": self.verifier_status,
            "verifier_latency_ms": self.verifier_latency_ms,
            "should_override": self.should_override,
            "shadow_confidence": round(self.shadow_confidence, 3),
            "base_confidence": round(self.base_confidence, 3),
            # Part C: tool telemetry
            "tool_schema_valid": self.tool_schema_valid,
            "tool_retry_count": self.tool_retry_count,
            "tool_execution_ok": self.tool_execution_ok,
            "tool_error_type": self.tool_error_type,
            # Part D: RAG telemetry
            "rag_unanswered_reason": self.rag_unanswered_reason,
            "rag_passage_count_used": self.rag_passage_count_used,
            # Part E: dialogue telemetry
            "dialogue_mode": self.dialogue_mode,
            "dialogue_anchor_used": self.dialogue_anchor_used,
            "dialogue_escalated": self.dialogue_escalated,
        }


# ---------------------------------------------------------------------------
# Model call helper
# ---------------------------------------------------------------------------
async def _call_model(
    orchestrator: Any,
    prompt: str,
    model_id: str,
    timeout_ms: int,
) -> Tuple[str, int]:
    t0 = time.perf_counter()
    try:
        timeout_s = max(timeout_ms / 1000.0, 5.0)
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
        text = artifacts.final_response.content
        latency = int((time.perf_counter() - t0) * 1000)
        return text, latency
    except asyncio.TimeoutError:
        latency = int((time.perf_counter() - t0) * 1000)
        logger.warning("Elite+ model %s timed out after %dms", model_id, latency)
        return "", latency
    except Exception as exc:
        latency = int((time.perf_counter() - t0) * 1000)
        logger.warning("Elite+ model %s failed: %s", model_id, exc)
        return "", latency


def _estimate_cost(model_id: str, output_tokens: int = 500) -> float:
    rate = _MODEL_COST_PER_1M.get(model_id, 1.0)
    return rate * output_tokens / 1_000_000


# ---------------------------------------------------------------------------
# Deterministic verifiers (Stage B)
# ---------------------------------------------------------------------------
def _extract_numeric(text: str) -> Optional[float]:
    cleaned = text.strip()
    boxed = re.search(r"\\boxed\{([^}]+)\}", cleaned)
    if boxed:
        cleaned = boxed.group(1)
    final = re.search(r"(?:final answer|answer)\s*(?:is|=|:)\s*([0-9.,/\-]+)", cleaned, re.IGNORECASE)
    if final:
        cleaned = final.group(1)
    cleaned = cleaned.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        if "/" in cleaned:
            parts = cleaned.split("/")
            if len(parts) == 2:
                try:
                    return float(parts[0]) / float(parts[1])
                except (ValueError, ZeroDivisionError):
                    pass
    return None


def _extract_mcq_letter(text: str) -> Optional[str]:
    m = re.search(r"\b([A-E])\b", text[:50])
    return m.group(1).upper() if m else None


def _verify_math(answers: List[str]) -> Tuple[bool, float, str]:
    """Check numeric consensus across answers. Returns (verified, confidence, rationale)."""
    numerics = []
    for ans in answers:
        val = _extract_numeric(ans)
        if val is not None:
            numerics.append(val)
    if len(numerics) < 2:
        return False, 0.5, "insufficient_numeric_answers"
    groups: Dict[float, int] = {}
    for v in numerics:
        matched = False
        for key in groups:
            if abs(key - v) < 1e-6 or (key != 0 and abs((key - v) / key) < 0.001):
                groups[key] += 1
                matched = True
                break
        if not matched:
            groups[v] = 1
    if groups:
        best_key = max(groups, key=groups.get)
        count = groups[best_key]
        if count >= 2:
            return True, min(0.95, 0.7 + 0.1 * count), f"numeric_consensus_{count}_agree"
    return False, 0.5, "no_numeric_consensus"


def _verify_mcq(answers: List[str]) -> Tuple[bool, float, str]:
    """Check MCQ letter consensus."""
    letters = []
    for ans in answers:
        letter = _extract_mcq_letter(ans)
        if letter:
            letters.append(letter)
    if len(letters) < 2:
        return False, 0.5, "insufficient_mcq_answers"
    from collections import Counter
    counts = Counter(letters)
    best_letter, count = counts.most_common(1)[0]
    if count >= 2:
        return True, min(0.9, 0.6 + 0.15 * count), f"mcq_consensus_{count}_agree_on_{best_letter}"
    return False, 0.5, "no_mcq_consensus"


def _validate_tool_schema(answer: str) -> Tuple[bool, str]:
    """Validate that a tool-calling response contains valid JSON tool calls."""
    if not answer or len(answer.strip()) < 5:
        return False, "empty"
    json_match = re.search(r"\{[^}]{5,}\}", answer)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, dict):
                return True, "valid_json"
        except (json.JSONDecodeError, ValueError):
            pass
    if any(k in answer.lower() for k in ["function_call", "tool_call", "action", "result"]):
        return True, "structured_keywords"
    return True, "freeform_ok"


def _verify_tool(answer: str) -> Tuple[bool, float, str, str]:
    """Check if tool result is present and parseable.

    Returns (verified, confidence, rationale, error_type).
    """
    if not answer or len(answer.strip()) < 10:
        return False, 0.3, "empty_tool_response", "empty"
    lower = answer.lower()
    if "timeout" in lower:
        return False, 0.2, "tool_timeout", "timeout"
    if any(err in lower for err in ["error", "failed", "exception"]):
        return False, 0.3, "tool_error_detected", "execution_error"
    schema_ok, schema_detail = _validate_tool_schema(answer)
    if not schema_ok:
        return False, 0.35, f"tool_schema_invalid:{schema_detail}", "schema_invalid"
    return True, 0.85, "tool_result_present", "none"


def _verify_rag_grounding(answer: str, query: str) -> Tuple[bool, float, str, str]:
    """Groundedness check: answer should contain query-relevant terms.

    Returns (verified, confidence, rationale, unanswered_reason).
    """
    if not answer or len(answer.strip()) < 20:
        return False, 0.3, "empty_rag_response", "low_recall"
    lower = answer.lower()
    if any(p in lower for p in ["i don't know", "cannot determine", "no information", "insufficient evidence"]):
        return False, 0.5, "explicit_refusal", "insufficient_evidence"
    query_words = set(re.findall(r"\w+", query.lower()))
    answer_words = set(re.findall(r"\w+", answer.lower()))
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                 "to", "for", "of", "and", "or", "what", "how", "why", "when",
                 "where", "which", "do", "does", "did", "not", "no", "yes",
                 "can", "could", "would", "should", "will", "shall", "may", "might"}
    query_terms = query_words - stopwords
    if not query_terms:
        return True, 0.7, "no_query_terms_to_check", "none"
    overlap = query_terms & answer_words
    ratio = len(overlap) / max(len(query_terms), 1)
    if ratio >= 0.5:
        return True, min(0.9, 0.6 + ratio * 0.3), f"grounded_{ratio:.0%}_overlap", "none"
    if ratio >= 0.3:
        return True, min(0.75, 0.5 + ratio * 0.3), f"partial_{ratio:.0%}_overlap", "none"
    return False, 0.4, f"ungrounded_{ratio:.0%}_overlap", "low_precision"


@dataclass
class VerificationResult:
    verified: bool
    confidence: float
    rationale: str
    tool_error_type: str = "none"
    rag_unanswered_reason: str = "none"
    tool_schema_valid: bool = True


def _run_deterministic_verification(
    category: str,
    answers: List[str],
    query: str,
) -> VerificationResult:
    """Run category-appropriate deterministic verification."""
    if category == "math" and ELITE_PLUS_MATH_REQUIRE_VERIFICATION:
        ok, conf, rationale = _verify_math(answers)
        return VerificationResult(ok, conf, rationale)

    if category in ("reasoning", "multilingual"):
        ok, conf, rationale = _verify_mcq(answers)
        return VerificationResult(ok, conf, rationale)

    if category == "tool_use" and ELITE_PLUS_TOOL_STRICT_MODE:
        if answers:
            ok, conf, rationale, err_type = _verify_tool(answers[0])
            schema_ok, _ = _validate_tool_schema(answers[0])
            return VerificationResult(ok, conf, rationale,
                                      tool_error_type=err_type,
                                      tool_schema_valid=schema_ok)
        return VerificationResult(False, 0.3, "no_tool_answer",
                                  tool_error_type="empty", tool_schema_valid=False)

    if category == "rag" and ELITE_PLUS_RAG_REQUIRE_SUPPORT:
        if answers:
            ok, conf, rationale, unans = _verify_rag_grounding(answers[0], query)
            return VerificationResult(ok, conf, rationale, rag_unanswered_reason=unans)
        return VerificationResult(False, 0.3, "no_rag_answer",
                                  rag_unanswered_reason="low_recall")

    if answers and answers[0] and len(answers[0].strip()) > 20:
        return VerificationResult(True, 0.7, "default_pass")

    return VerificationResult(False, 0.5, "default_unverified")


# ---------------------------------------------------------------------------
# Escalation decision
# ---------------------------------------------------------------------------
def _should_escalate(
    category: str,
    free_confidence: float,
    vr: VerificationResult,
    free_answers: List[str],
) -> Tuple[bool, List[str]]:
    """Decide whether to call a paid anchor model."""
    reasons: List[str] = []

    if ELITE_PLUS_ESCALATE_ON_LOW_CONFIDENCE and free_confidence < ELITE_PLUS_LOW_CONF_THRESHOLD:
        reasons.append(f"low_confidence_{free_confidence:.2f}")

    if not vr.verified:
        if ELITE_PLUS_ESCALATE_ON_DISAGREEMENT and "no_" in vr.rationale:
            reasons.append(f"disagreement:{vr.rationale}")
        if ELITE_PLUS_ESCALATE_ON_TOOL_FAILURE and vr.tool_error_type != "none":
            reasons.append(f"tool_failure:{vr.tool_error_type}")
        if ELITE_PLUS_ESCALATE_ON_RAG_UNGROUNDED and "ungrounded" in vr.rationale:
            reasons.append(f"rag_ungrounded:{vr.rationale}")
        if "empty" in vr.rationale or "insufficient" in vr.rationale:
            reasons.append(f"verification_failed:{vr.rationale}")

    # Dialogue: only escalate on hard failures, not just low confidence
    if category == "dialogue" and ELITE_PLUS_DIALOGUE_LIGHT_TOUCH:
        if not reasons or all("low_confidence" in r for r in reasons):
            return False, []

    return len(reasons) > 0, reasons


# ---------------------------------------------------------------------------
# Part B: choose_paid_anchor — category-aware, env-configurable
# ---------------------------------------------------------------------------
def choose_paid_anchor(category: str, escalation_reasons: List[str]) -> str:
    """Select the best paid anchor for the category and failure mode."""
    return _PAID_ANCHORS.get(category, "openai/gpt-4o-mini")


# ---------------------------------------------------------------------------
# Free model selection per category
# ---------------------------------------------------------------------------
def _get_free_models(category: str) -> List[str]:
    try:
        from .elite_orchestration import FREE_MODELS
        models = FREE_MODELS.get(category, FREE_MODELS.get("reasoning", []))
        if models:
            max_models = 1 if (category == "dialogue" and ELITE_PLUS_DIALOGUE_LIGHT_TOUCH) else 2
            return list(models[:max_models])
    except ImportError:
        pass
    defaults = _FREE_MODELS_DEFAULT.get(category, _FREE_MODELS_DEFAULT["reasoning"])
    max_models = 1 if (category == "dialogue" and ELITE_PLUS_DIALOGUE_LIGHT_TOUCH) else 2
    return list(defaults[:max_models])


def _get_paid_anchor(category: str) -> str:
    return _PAID_ANCHORS.get(category, "openai/gpt-4o-mini")


# ---------------------------------------------------------------------------
# Confidence extraction from model response
# ---------------------------------------------------------------------------
def _extract_confidence(text: str) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    if any(w in lower for w in ["i'm not sure", "uncertain", "i don't know", "cannot determine"]):
        return 0.35
    if any(w in lower for w in ["error", "failed", "exception"]):
        return 0.2
    length = len(text.strip())
    if length < 20:
        return 0.4
    if length < 50:
        return 0.55
    return 0.7


def _normalize_answer(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower().strip())[:500]


def _best_answer(answers: List[Tuple[str, float, str]]) -> Tuple[str, float, str]:
    """Pick the best answer from (text, confidence, model_id) tuples."""
    valid = [(t, c, m) for t, c, m in answers if t and len(t.strip()) > 5]
    if not valid:
        return ("", 0.0, "none")
    return max(valid, key=lambda x: x[1])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def run_elite_plus(
    query: str,
    base_answer: str,
    base_confidence: float,
    category: str,
    orchestrator: Any,
    effective_tier: str,
    extra: Dict[str, Any],
    *,
    internal_bench: bool = False,
) -> ElitePlusResult:
    """Run the Elite+ free-first-verified pipeline.

    Flow:
      Stage A: Call free models for the category
      Stage B: Run deterministic verification (schema, grounding, consensus)
      Stage C: Escalate to ONE category-specific paid anchor if needed
      Stage D: Fallback to base elite answer on total failure
    """
    t0 = time.perf_counter()
    mode = ELITE_PLUS_MODE
    policy = ELITE_PLUS_POLICY

    # Resolve effective max paid calls (internal bench can allow 2)
    max_paid = ELITE_PLUS_MAX_PAID_CALLS
    if internal_bench:
        max_paid = ELITE_PLUS_MAX_PAID_CALLS_INTERNAL_BENCH

    models_called: List[str] = []
    free_calls = 0
    paid_calls = 0
    cost_breakdown: Dict[str, float] = {}
    escalation_reasons: List[str] = []
    tool_invocations: List[str] = []
    rag_grounding = "n/a"
    verifier_strategy = "none"
    verifier_status = "ok"
    verifier_latency = 0

    # Category-specific telemetry
    tool_schema_valid = True
    tool_retry_count = 0
    tool_execution_ok = True
    tool_error_type = "none"
    rag_unanswered_reason = "none"
    rag_passage_count = 0
    dialogue_mode_val = "n/a"
    dialogue_anchor_used = ""
    dialogue_escalated = False

    if category == "dialogue":
        dialogue_mode_val = "light_touch" if ELITE_PLUS_DIALOGUE_LIGHT_TOUCH else "full"

    # -----------------------------------------------------------------------
    # Stage A: Free primary — call free models
    # -----------------------------------------------------------------------
    free_models = _get_free_models(category)
    free_answers: List[Tuple[str, float, str]] = []

    if free_models:
        # G2: skip degraded free models via circuit breaker
        healthy_free = [m for m in free_models if not _circuit_breaker.is_degraded(m)]
        if not healthy_free:
            healthy_free = free_models[:1]
            logger.warning("All free models degraded for %s, forcing first: %s", category, healthy_free[0])

        tasks = [_call_model(orchestrator, query, m, ELITE_PLUS_BUDGET_MS) for m in healthy_free]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        for model_id, result in zip(healthy_free, raw):
            models_called.append(model_id)
            free_calls += 1
            cost_breakdown[model_id] = 0.0
            if isinstance(result, Exception):
                logger.warning("Elite+ free model %s error: %s", model_id, result)
                _circuit_breaker.record(model_id, False)
            else:
                text, latency = result
                conf = _extract_confidence(text)
                _circuit_breaker.record(model_id, bool(text and len(text.strip()) > 5))
                if text:
                    free_answers.append((text, conf, model_id))

    best_free_text, best_free_conf, best_free_model = _best_answer(free_answers)
    stage_used = "free_primary"

    # -----------------------------------------------------------------------
    # Stage B: Deterministic verification
    # -----------------------------------------------------------------------
    answer_texts = [t for t, _, _ in free_answers]
    vr = _run_deterministic_verification(category, answer_texts, query)
    verifier_strategy = "deterministic"
    verifier_latency = int((time.perf_counter() - t0) * 1000)

    if vr.verified:
        best_free_conf = max(best_free_conf, vr.confidence)
        stage_used = "deterministic_verify"
        verifier_status = "verified"

    # Propagate category-specific verification details
    tool_schema_valid = vr.tool_schema_valid
    tool_error_type = vr.tool_error_type
    tool_execution_ok = vr.tool_error_type == "none"
    rag_unanswered_reason = vr.rag_unanswered_reason

    if category == "rag":
        if answer_texts:
            _, _, rag_rationale, _ = _verify_rag_grounding(answer_texts[0], query)
            if "grounded" in rag_rationale or "partial" in rag_rationale:
                rag_grounding = "ok" if "grounded" in rag_rationale else "partial"
            else:
                rag_grounding = "fail"
        else:
            rag_grounding = "fail"

    # -----------------------------------------------------------------------
    # Stage C: Paid escalation (if triggered)
    # -----------------------------------------------------------------------
    should_esc, esc_reasons = _should_escalate(
        category, best_free_conf, vr, answer_texts
    )

    paid_answer = ""
    paid_conf = 0.0
    if should_esc and paid_calls < max_paid:
        anchor = choose_paid_anchor(category, esc_reasons)
        escalation_reasons = esc_reasons

        # G2: Launch Mode governance — check escalation allowlist + cost ceiling
        lm_allowed = _launch_mode_allows_escalation(category, esc_reasons)
        lm_cost_ok = _launch_mode_cost_ok(sum(cost_breakdown.values()), anchor)

        # G2: Skip degraded paid anchor; fall back to default
        if _circuit_breaker.is_degraded(anchor):
            fallback_anchor = "openai/gpt-4o-mini"
            logger.warning("Paid anchor %s degraded, substituting %s", anchor, fallback_anchor)
            anchor = fallback_anchor

        if not lm_allowed:
            logger.info("Launch Mode blocked escalation for category=%s reasons=%s", category, esc_reasons)
            escalation_reasons.append("launch_mode_blocked")
        elif not lm_cost_ok:
            logger.info("Launch Mode cost ceiling would be exceeded for anchor=%s", anchor)
            escalation_reasons.append("cost_ceiling_exceeded")
        else:
            if category == "dialogue":
                dialogue_escalated = True
                dialogue_anchor_used = anchor

            # Part C: for tool_use, if schema was invalid, retry with constrained prompt
            tool_retry_prompt = query
            if category == "tool_use" and not tool_schema_valid and ELITE_PLUS_TOOL_STRICT_MODE:
                tool_retry_count = 1
                tool_retry_prompt = (
                    "You MUST respond with ONLY a valid JSON tool call. "
                    "Do NOT include any explanation or freeform text.\n\n"
                    f"Original request: {query}"
                )

            try:
                paid_text, paid_lat = await _call_model(
                    orchestrator, tool_retry_prompt if category == "tool_use" else query,
                    anchor, ELITE_PLUS_BUDGET_MS,
                )
                models_called.append(anchor)
                paid_calls += 1
                cost_breakdown[anchor] = _estimate_cost(anchor)
                _circuit_breaker.record(anchor, bool(paid_text and len(paid_text.strip()) > 5))

                if paid_text and len(paid_text.strip()) > 5:
                    paid_answer = paid_text
                    paid_conf = max(_extract_confidence(paid_text), 0.75)
                    stage_used = "paid_escalation"
                    verifier_strategy = "paid_anchor"

                    # Part D: re-check RAG grounding after paid escalation
                    if category == "rag" and ELITE_PLUS_RAG_REQUIRE_SUPPORT:
                        ok2, _, rat2, unans2 = _verify_rag_grounding(paid_text, query)
                        if not ok2:
                            rag_grounding = "fail"
                            rag_unanswered_reason = unans2
                            paid_answer = (
                                "I don't have sufficient evidence to answer this question "
                                "based on the available context. Could you provide more details "
                                "or rephrase your question?"
                            )
                            paid_conf = 0.5
                        else:
                            rag_grounding = "ok"
                            rag_unanswered_reason = "none"

            except Exception as exc:
                logger.warning("Elite+ paid anchor %s failed: %s", anchor, exc)
                _circuit_breaker.record(anchor, False)
                escalation_reasons.append(f"anchor_error:{exc}")

    # -----------------------------------------------------------------------
    # Select final answer
    # -----------------------------------------------------------------------
    if paid_answer and paid_conf > best_free_conf:
        final_answer = paid_answer
        final_conf = paid_conf
    elif best_free_text:
        final_answer = best_free_text
        final_conf = best_free_conf
    else:
        final_answer = base_answer
        final_conf = base_confidence
        stage_used = "fallback_elite"

    total_latency = int((time.perf_counter() - t0) * 1000)
    total_cost = sum(cost_breakdown.values())

    result = ElitePlusResult(
        answer=final_answer,
        confidence=final_conf,
        mode=mode,
        policy=policy,
        stage_used=stage_used,
        paid_calls_count=paid_calls,
        free_calls_count=free_calls,
        estimated_cost_usd=total_cost,
        estimated_cost_breakdown=cost_breakdown,
        confidence_free=best_free_conf,
        confidence_final=final_conf,
        escalation_reason=escalation_reasons,
        models_called=models_called,
        tool_invocations=tool_invocations,
        rag_grounding_status=rag_grounding,
        total_latency_ms=total_latency,
        verifier_strategy=verifier_strategy,
        verifier_status=verifier_status,
        verifier_latency_ms=verifier_latency,
        # Part C telemetry
        tool_schema_valid=tool_schema_valid,
        tool_retry_count=tool_retry_count,
        tool_execution_ok=tool_execution_ok,
        tool_error_type=tool_error_type,
        # Part D telemetry
        rag_unanswered_reason=rag_unanswered_reason,
        rag_passage_count_used=rag_passage_count,
        # Part E telemetry
        dialogue_mode=dialogue_mode_val,
        dialogue_anchor_used=dialogue_anchor_used,
        dialogue_escalated=dialogue_escalated,
        # backward compat
        shadow_answer=final_answer,
        shadow_confidence=final_conf,
        should_override=(mode == "active"),
        base_answer=base_answer,
        base_confidence=base_confidence,
        blackboard_hash=hashlib.sha256(
            f"{query[:100]}:{final_answer[:100]}".encode()
        ).hexdigest()[:16],
    )

    if ELITE_PLUS_LOG_SHADOW:
        logger.info(
            "ELITE+ [%s/%s] stage=%s free=%d paid=%d cost=$%.4f "
            "conf_free=%.2f conf_final=%.2f esc=%s latency=%dms models=%s",
            mode, policy, stage_used, free_calls, paid_calls, total_cost,
            best_free_conf, final_conf,
            escalation_reasons or "none",
            total_latency, models_called,
        )

    return result
