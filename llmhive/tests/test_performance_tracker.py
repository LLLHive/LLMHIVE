from llmhive.app.performance_tracker import performance_tracker, ModelPerformance
from llmhive.app.orchestrator import UsageSummary, ModelUsage


def test_performance_tracker_records_usage():
    usage = UsageSummary(
        total_tokens=100,
        total_cost=0.01,
        response_count=2,
        per_model={"model-a": ModelUsage(tokens=100, cost=0.01, responses=2)},
    )

    performance_tracker.record_usage(usage, quality_by_model={"model-a": 0.8})
    snap = performance_tracker.snapshot()
    perf = snap["model-a"]

    assert perf.total_tokens == 100
    assert perf.total_cost == 0.01
    assert perf.calls == 2
    assert perf.avg_quality > 0.0


def test_performance_tracker_success_rate():
    performance_tracker.mark_outcome("model-b", success=True)
    performance_tracker.mark_outcome("model-b", success=False)
    snap = performance_tracker.snapshot()
    perf = snap["model-b"]

    assert perf.success_rate == 0.5


