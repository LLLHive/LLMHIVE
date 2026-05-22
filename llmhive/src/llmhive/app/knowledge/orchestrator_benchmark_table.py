"""
Benchmark leaderboard access for orchestrators (May 2026 certification basis).

Sources locked per artifacts/launch_freeze/final_go_to_market_plan_20260404.md:
- category_benchmarks_free_20260331.json
- category_benchmarks_elite_20260401.json

In-code table: benchmark_rankings_jan2026.RANKINGS_MAY_2026
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from .benchmark_rankings_jan2026 import (
        BenchmarkCategory,
        RANKINGS_MAY_2026,
        get_benchmark_leaderboard,
        get_usecase_benchmark_rankings,
        get_all_usecase_benchmark_rankings,
        resolve_routable_slug,
    )
    BENCHMARK_TABLE_AVAILABLE = True
except ImportError:
    BENCHMARK_TABLE_AVAILABLE = False
    RANKINGS_MAY_2026 = {}
    BenchmarkCategory = None  # type: ignore

    def get_benchmark_leaderboard(*_a, **_k):  # type: ignore
        return []

    def get_usecase_benchmark_rankings(*_a, **_k):  # type: ignore
        return []

    def get_all_usecase_benchmark_rankings(*_a, **_k):  # type: ignore
        return {}

    def resolve_routable_slug(model_id: str) -> str:
        return model_id


def get_orchestrator_benchmark_snapshot(top_k: int = 10) -> Dict[str, Any]:
    """Snapshot for orchestrator logging / model selection hints."""
    if not BENCHMARK_TABLE_AVAILABLE:
        return {"available": False, "categories": {}}
    return {
        "available": True,
        "source": "benchmark_rankings_jan2026.RANKINGS_MAY_2026",
        "categories": {
            cat.value: [
                {
                    "model_id": row.model_id,
                    "provider": row.provider,
                    "score": row.score,
                    "benchmark": row.benchmark_name,
                }
                for row in get_benchmark_leaderboard(cat, top_k=top_k)
            ]
            for cat in BenchmarkCategory
        },
        "use_cases": get_all_usecase_benchmark_rankings(top_k=top_k),
    }


def best_models_for_usecase(usecase_slug: str, top_k: int = 5) -> List[str]:
    """Return routable model IDs ordered by benchmark score for a UI category."""
    rows = get_usecase_benchmark_rankings(usecase_slug, top_k=top_k)
    return [resolve_routable_slug(str(r["model_id"])) for r in rows]
