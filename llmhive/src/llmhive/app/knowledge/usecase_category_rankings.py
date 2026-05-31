"""
UI use-case category rankings — derived from benchmark scores.

Canonical scores live in benchmark_rankings_jan2026.py (RANKINGS_MAY_2026).
This module exposes the same ordered lists for orchestration fallbacks.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from .benchmark_rankings_jan2026 import (
    USECASE_CATEGORY_ALIASES,
    USECASE_TO_BENCHMARK,
    get_all_usecase_benchmark_rankings,
    get_usecase_benchmark_rankings,
    _resolve_usecase_slug,
)

__all__ = [
    "USECASE_CATEGORY_ALIASES",
    "USECASE_TO_BENCHMARK",
    "build_category_rankings_document",
    "build_category_rankings_json",
    "get_usecase_category_rankings",
    "get_usecase_category_rankings_detailed",
    "domain_models_from_usecase",
]


def build_category_rankings_document(top_k: int = 10) -> Dict[str, object]:
    """Build the frontend category-rankings JSON document."""
    categories = get_all_usecase_benchmark_rankings(top_k=top_k)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "benchmark_rankings_jan2026.py::RANKINGS_MAY_2026",
        "description": (
            "Top 10 per UI category, sorted strictly by benchmark score "
            "(API-available models only)."
        ),
        "benchmark_mapping": {
            slug: bench.value for slug, bench in USECASE_TO_BENCHMARK.items()
        },
        "categories": categories,
    }


def build_category_rankings_json(top_k: int = 10) -> str:
    """Serialize category rankings for lib/marketing/usecase-category-rankings.generated.json."""
    return json.dumps(build_category_rankings_document(top_k=top_k), indent=2) + "\n"


def get_usecase_category_rankings(category: str, top_k: int = 10) -> List[str]:
    """Return model IDs for a use-case category (strict benchmark score order)."""
    detailed = get_usecase_benchmark_rankings(category, top_k=top_k)
    return [str(row["model_id"]) for row in detailed]


def get_usecase_category_rankings_detailed(
    category: str,
    top_k: int = 10,
) -> List[Dict[str, object]]:
    """Return ranked dicts matching the frontend category-rankings API shape."""
    return get_usecase_benchmark_rankings(category, top_k=top_k)


def domain_models_from_usecase(orchestrator_task_type: str, limit: int = 6) -> List[str]:
    """Map orchestrator task_type → use-case slug → top model IDs by benchmark score."""
    slug = _resolve_usecase_slug(orchestrator_task_type)
    if slug not in USECASE_TO_BENCHMARK:
        slug = "science"
    return get_usecase_category_rankings(slug, top_k=limit)
