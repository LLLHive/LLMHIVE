"""Enterprise-only single flagship model pick enforcement."""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from ..models.orchestration import AgentMode, ChatRequest

logger = logging.getLogger(__name__)

ENTERPRISE_SUBSCRIPTION_TIERS = frozenset({"enterprise", "maximum"})


def subscription_allows_single_flagship_pick(tier: Optional[str]) -> bool:
    return (tier or "free").lower().strip() in ENTERPRISE_SUBSCRIPTION_TIERS


def is_explicit_model_selection(models: Optional[List[str]]) -> bool:
    if not models:
        return False
    return not all(
        (m or "").lower().strip() in ("automatic", "auto", "")
        for m in models
    )


def apply_flagship_pick_policy(
    request: ChatRequest,
    subscription_tier: Optional[str],
) -> Tuple[ChatRequest, bool]:
    """Downgrade non-Enterprise requests to team + automatic model routing.

    Returns:
        (possibly updated request, gated flag)
    """
    if subscription_allows_single_flagship_pick(subscription_tier):
        return request, False

    gated = (
        request.agent_mode == AgentMode.single
        or is_explicit_model_selection(request.models)
    )
    if not gated:
        return request, False

    logger.info(
        "Flagship pick gated: tier=%s -> team/automatic (was agent_mode=%s models=%s)",
        subscription_tier,
        request.agent_mode.value,
        request.models,
    )
    return request.model_copy(
        update={
            "agent_mode": AgentMode.team,
            "models": None,
        }
    ), True
