#!/usr/bin/env python3
"""Continuous Quality Evaluation Script.

This script runs the quality evaluation test suite programmatically and computes aggregate scores.
It can be extended to run additional QA metrics on LLM outputs.
Outputs are logged to a file (or database) for tracking trends over time.

Usage:
    python tests/quality_eval/eval_quality.py

Environment Variables:
    QUALITY_LOG_FILE: Path to store results JSON (default: quality_eval_results.json)
    QUALITY_THRESHOLD: Minimum pass rate threshold (default: 0.7)
    MAX_FAILURES: Maximum allowed test failures before CI fails (default: 3)
"""
import pytest
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
LOG_FILE = os.getenv("QUALITY_LOG_FILE", "quality_eval_results.json")
QUALITY_THRESHOLD = float(os.getenv("QUALITY_THRESHOLD", "0.7"))
MAX_FAILURES = int(os.getenv("MAX_FAILURES", "3"))


class QualityMetricsCollector:
    """Collects and aggregates quality metrics from test runs."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.test_details = []
    
    def add_result(self, test_name: str, passed: bool, duration: float = 0, error: str = None):
        """Add a test result to the collection."""
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            if error:
                self.errors.append({"test": test_name, "error": error})
        
        self.test_details.append({
            "name": test_name,
            "passed": passed,
            "duration_ms": duration,
            "error": error
        })
    
    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped
    
    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.passed / self.total
    
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": self.total,
            "pass_rate": round(self.pass_rate, 4),
            "errors": self.errors,
            "test_details": self.test_details
        }


def run_test_suite() -> tuple[int, QualityMetricsCollector]:
    """Run the PyTest suite and collect metrics.
    
    Returns:
        tuple: (exit_code, metrics_collector)
    """
    # Get the directory of this script
    script_dir = Path(__file__).parent
    
    # Run pytest with verbose output and capture results
    # Using pytest's built-in result collection
    class ResultCollector:
        def __init__(self):
            self.results = []
        
        def pytest_runtest_logreport(self, report):
            if report.when == 'call':
                self.results.append({
                    'nodeid': report.nodeid,
                    'outcome': report.outcome,
                    'duration': report.duration,
                    'longrepr': str(report.longrepr) if report.longrepr else None
                })
    
    collector = ResultCollector()
    
    # Run the tests
    exit_code = pytest.main([
        "-q",
        "--tb=short",
        str(script_dir),
        "-p", "no:warnings"
    ], plugins=[collector])
    
    # Convert to our metrics format
    metrics = QualityMetricsCollector()
    for result in collector.results:
        metrics.add_result(
            test_name=result['nodeid'],
            passed=result['outcome'] == 'passed',
            duration=result['duration'] * 1000,  # Convert to ms
            error=result['longrepr'] if result['outcome'] != 'passed' else None
        )
    
    return exit_code, metrics


def load_historical_results() -> list:
    """Load previous test results from log file."""
    if not os.path.exists(LOG_FILE):
        return []
    
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, IOError):
        return []


def save_results(results_summary: dict):
    """Save test results to log file."""
    existing = load_historical_results()
    existing.append(results_summary)
    
    # Keep only last 100 runs
    if len(existing) > 100:
        existing = existing[-100:]
    
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(existing, f, indent=2)
        print(f"Results saved to {LOG_FILE}")
    except IOError as e:
        print(f"Warning: Could not write quality results to log: {e}")


def print_summary(metrics: QualityMetricsCollector):
    """Print a formatted summary of test results."""
    print("\n" + "=" * 60)
    print("LLMHIVE QUALITY EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Tests:    {metrics.total}")
    print(f"Passed:         {metrics.passed}")
    print(f"Failed:         {metrics.failed}")
    print(f"Skipped:        {metrics.skipped}")
    print(f"Pass Rate:      {metrics.pass_rate:.1%}")
    print("-" * 60)
    
    if metrics.errors:
        print("\nFailed Tests:")
        for err in metrics.errors[:5]:  # Show first 5 errors
            print(f"  - {err['test']}")
            if err['error']:
                # Truncate long error messages
                error_preview = err['error'][:200] + "..." if len(err['error']) > 200 else err['error']
                print(f"    Error: {error_preview}")
        
        if len(metrics.errors) > 5:
            print(f"  ... and {len(metrics.errors) - 5} more failures")
    
    print("=" * 60)


def main():
    """Main entry point for quality evaluation."""
    print("Running LLMHive Quality Evaluation Suite...")
    print(f"Threshold: {QUALITY_THRESHOLD:.0%} pass rate")
    print(f"Max allowed failures: {MAX_FAILURES}")
    print()
    
    # Run the test suite
    exit_code, metrics = run_test_suite()
    
    # Print summary
    print_summary(metrics)
    
    # Build results summary
    results_summary = {
        "timestamp": datetime.now().isoformat(),
        "pytest_exit_code": exit_code,
        "all_passed": metrics.failed == 0,
        "pass_rate": metrics.pass_rate,
        "metrics": metrics.to_dict(),
        "quality_threshold": QUALITY_THRESHOLD,
        "quality_gate_passed": (
            metrics.pass_rate >= QUALITY_THRESHOLD and 
            metrics.failed <= MAX_FAILURES
        )
    }
    
    # Save results
    save_results(results_summary)
    
    # Determine final exit code
    if results_summary["quality_gate_passed"]:
        print("\n✅ QUALITY GATE PASSED")
        final_exit = 0
    else:
        print("\n❌ QUALITY GATE FAILED")
        if metrics.pass_rate < QUALITY_THRESHOLD:
            print(f"   Pass rate {metrics.pass_rate:.1%} below threshold {QUALITY_THRESHOLD:.0%}")
        if metrics.failed > MAX_FAILURES:
            print(f"   {metrics.failed} failures exceed max allowed {MAX_FAILURES}")
        final_exit = 1
    
    sys.exit(final_exit)


if __name__ == "__main__":
    main()

