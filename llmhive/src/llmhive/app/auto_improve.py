"""Auto-Improve CI scaffold: collect feedback, plan fixes, track status, and gate safe application."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .firestore_db import FirestoreFeedbackService
except Exception:  # pragma: no cover
    FirestoreFeedbackService = None  # type: ignore

try:
    from .performance_tracker import performance_tracker
except Exception:  # pragma: no cover
    performance_tracker = None  # type: ignore

logger = logging.getLogger(__name__)

PLAN_PATH = Path(__file__).parent / "auto_improve_plan.json"
BASELINE_METRICS_PATH = Path.home() / ".llmhive" / "performance_metrics.json"


@dataclass
class ImprovementItem:
    id: str
    description: str
    status: str = "planned"  # planned | applied_pending_test | done | failed
    priority: str = "medium"  # low | medium | high | critical
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImprovementData:
    common_failures: List[str] = field(default_factory=list)
    user_requests: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    samples: List[Dict[str, Any]] = field(default_factory=list)


def _load_plan() -> List[ImprovementItem]:
    if not PLAN_PATH.exists():
        return []
    try:
        raw = json.loads(PLAN_PATH.read_text())
        return [ImprovementItem(**item) for item in raw]
    except Exception as e:
        logger.warning("Failed to load improvement plan: %s", e)
        return []


def _save_plan(items: List[ImprovementItem]) -> None:
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps([asdict(i) for i in items], indent=2))
    logger.info("Saved improvement plan to %s", PLAN_PATH)


def gather_improvement_data(
    lookback_days: int = 7,
    max_feedback: int = 200,
) -> ImprovementData:
    """Aggregate user feedback and performance telemetry into a summary."""
    data = ImprovementData()

    if FirestoreFeedbackService:
        try:
            svc = FirestoreFeedbackService()
            since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            feedback = (
                svc.db.collection(svc.COLLECTION)
                .where("created_at", ">=", since)
                .limit(max_feedback)
                .stream()
                if svc.db
                else []
            )
            for doc in feedback:
                f = doc.to_dict()
                ftype = f.get("feedback_type")
                rating = f.get("rating")
                if ftype == "thumbs_down" or (rating is not None and rating < 0.5):
                    reason = f.get("reason") or f.get("comment") or "negative_feedback"
                    data.common_failures.append(reason)
                    data.samples.append({"query": f.get("query", ""), "issue": reason})
                if ftype == "feature_request":
                    req = f.get("comment") or f.get("query") or "feature_request"
                    data.user_requests.append(req)
        except Exception as e:
            logger.debug("Feedback collection failed: %s", e)

    if performance_tracker:
        try:
            snapshot = performance_tracker.snapshot()
            slow_models = []
            failing_models = []
            for name, perf in snapshot.items():
                if getattr(perf, "success_rate", 1.0) < 0.6:
                    failing_models.append(name)
                if getattr(perf, "avg_latency_ms", 0) > 4000:
                    slow_models.append(name)
            if failing_models:
                data.common_failures.append(f"Low success rate: {failing_models}")
            if slow_models:
                data.common_failures.append(f"High latency: {slow_models}")
            data.metrics["models_tracked"] = len(snapshot)
        except Exception as e:
            logger.debug("Performance snapshot failed: %s", e)

    if BASELINE_METRICS_PATH.exists():
        try:
            baseline = json.loads(BASELINE_METRICS_PATH.read_text())
            data.metrics["baseline"] = baseline
        except Exception:
            pass

    return data


KNOWN_RULES = {
    "hallucination": "Tighten factual prompts and enable verification for factual domains.",
    "legal": "Adjust legal domain prompts or prefer high-accuracy legal model.",
    "web_search": "Increase tool timeout and add partial-result handling for web_search.",
    "latency": "Route low-priority queries to faster models; enable caching.",
    "math": "Use calculator/tool more aggressively for numeric queries.",
}


def plan_improvements(data: ImprovementData) -> List[ImprovementItem]:
    """Generate a set of improvement items from gathered signals."""
    plan = _load_plan()
    existing = {p.description: p for p in plan}
    new_items: List[ImprovementItem] = []

    def add_item(desc: str, priority: str = "medium", meta: Optional[Dict[str, Any]] = None):
        if desc in existing:
            return
        item = ImprovementItem(
            id=f"imp-{len(plan) + len(new_items) + 1}",
            description=desc,
            priority=priority,
            metadata=meta or {},
        )
        new_items.append(item)

    for failure in data.common_failures:
        lowered = str(failure).lower()
        for key, fix in KNOWN_RULES.items():
            if key in lowered:
                add_item(fix, priority="high", meta={"source": failure})
                break
        else:
            add_item(f"Investigate issue: {failure}", priority="medium", meta={"source": failure})

    for req in data.user_requests:
        add_item(f"Feature request: {req}", priority="low", meta={"source": "user_request"})

    if "High latency" in " ".join(data.common_failures):
        add_item("Optimize slow models or reduce max context where possible", priority="medium")

    plan.extend(new_items)
    if new_items:
        _save_plan(plan)
    return plan


SAFE_CONFIG_KEYS = {"WEB_SEARCH_TIMEOUT", "DEFAULT_TOOL_TIMEOUT"}


def apply_config_change(config: Dict[str, Any], key: str, value: Any) -> bool:
    """Apply a simple config change in-memory if allowed."""
    auto_apply = os.getenv("AUTO_IMPROVE_APPLY", "false").lower() in {"1", "true", "yes"}
    if key not in SAFE_CONFIG_KEYS:
        logger.info("Config key %s not whitelisted for auto-apply; logging suggestion only", key)
        return False
    if not auto_apply:
        logger.info("AUTO_IMPROVE_APPLY is disabled; suggestion: set %s = %s", key, value)
        return False
    config[key] = value
    logger.info("Applied config change: %s=%s (auto-apply enabled)", key, value)
    return True


async def verify_improvements(
    plan: List[ImprovementItem],
    run_benchmarks_fn=None,
) -> List[ImprovementItem]:
    """Mark applied_pending_test items as done/failed based on benchmark results."""
    updated = []
    for item in plan:
        if item.status != "applied_pending_test":
            updated.append(item)
            continue
        if run_benchmarks_fn is None:
            item.status = "planned"
            item.metadata["note"] = "No verifier available; reverting to planned"
            updated.append(item)
            continue
        try:
            exit_code = await run_benchmarks_fn()
            if exit_code == 0:
                item.status = "done"
            else:
                item.status = "failed"
                item.metadata["note"] = f"Verification failed (exit_code={exit_code})"
        except Exception as e:
            item.status = "failed"
            item.metadata["note"] = f"Verification error: {e}"
        updated.append(item)
    _save_plan(updated)
    return updated


async def run_auto_improve_cycle(
    config: Optional[Dict[str, Any]] = None,
    apply_safe_changes: bool = False,
    run_verifier=None,
) -> List[ImprovementItem]:
    """One cycle: gather data -> plan -> optionally apply safe tweaks -> optionally verify."""
    summary = gather_improvement_data()
    plan = plan_improvements(summary)

    if apply_safe_changes and config is not None:
        for item in plan:
            if "timeout" in item.description.lower():
                if apply_config_change(config, "WEB_SEARCH_TIMEOUT", 15):
                    item.status = "applied_pending_test"

    if run_verifier:
        plan = await verify_improvements(plan, run_benchmarks_fn=run_verifier)
    else:
        _save_plan(plan)
    return plan


if __name__ == "__main__":  # pragma: no cover
    import asyncio

    async def _noop():
        return 0

    asyncio.run(run_auto_improve_cycle(config={}, apply_safe_changes=False, run_verifier=_noop))
