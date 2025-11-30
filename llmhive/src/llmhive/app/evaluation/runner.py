"""Comprehensive Evaluation Runner for LLMHive.

Orchestrates all evaluation tasks:
- Benchmarking
- A/B Testing
- Security Audit
- Load Testing

Usage:
    runner = EvaluationRunner()
    await runner.run_full_evaluation()
    
    # Or run specific tests
    await runner.run_benchmarks()
    await runner.run_security_audit()
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .benchmarks import BenchmarkRunner, BenchmarkResult
from .ab_testing import ABTester, ABTestResult, STANDARD_TEST_QUERIES
from .security_audit import SecurityAudit, AuditResult

logger = logging.getLogger(__name__)


# ==============================================================================
# Types
# ==============================================================================

@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    timestamp: datetime
    benchmarks: Dict[str, BenchmarkResult]
    ab_tests: List[ABTestResult]
    security_audit: Optional[AuditResult]
    load_tests: List[Dict[str, Any]]
    overall_status: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "benchmarks": {
                name: result.to_dict()
                for name, result in self.benchmarks.items()
            },
            "ab_tests": [test.to_dict() for test in self.ab_tests],
            "security_audit": self.security_audit.to_dict() if self.security_audit else None,
            "load_tests": self.load_tests,
            "overall_status": self.overall_status,
            "recommendations": self.recommendations,
        }
    
    def summary(self) -> str:
        lines = [
            "=" * 70,
            "LLMHIVE EVALUATION REPORT",
            "=" * 70,
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Status: {self.overall_status}",
            "",
        ]
        
        if self.benchmarks:
            lines.append("BENCHMARKS:")
            for name, result in self.benchmarks.items():
                lines.append(f"  {result.summary()}")
        
        if self.ab_tests:
            lines.append("\nA/B TESTS:")
            for test in self.ab_tests:
                lines.append(f"  {test.summary()}")
        
        if self.security_audit:
            lines.append(f"\nSECURITY: {self.security_audit.summary()}")
        
        if self.recommendations:
            lines.append("\nRECOMMENDATIONS:")
            for rec in self.recommendations:
                lines.append(f"  • {rec}")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# ==============================================================================
# Evaluation Runner
# ==============================================================================

class EvaluationRunner:
    """Orchestrates all evaluation tasks."""
    
    def __init__(
        self,
        llmhive_client: Optional[Any] = None,
        output_dir: str = "./evaluation_results",
    ):
        self.llmhive_client = llmhive_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.benchmark_runner = BenchmarkRunner(
            llmhive_client=llmhive_client,
            output_dir=str(self.output_dir / "benchmarks"),
        )
        self.ab_tester = ABTester(
            llmhive_client=llmhive_client,
            output_dir=str(self.output_dir / "ab_tests"),
        )
        self.security_audit = SecurityAudit(
            llmhive_client=llmhive_client,
            output_dir=str(self.output_dir / "security"),
        )
    
    async def run_full_evaluation(
        self,
        benchmark_sample_size: int = 50,
        run_ab_tests: bool = True,
        run_security: bool = True,
        run_load_tests: bool = False,
    ) -> EvaluationReport:
        """
        Run complete evaluation suite.
        
        Args:
            benchmark_sample_size: Number of samples per benchmark
            run_ab_tests: Whether to run A/B tests
            run_security: Whether to run security audit
            run_load_tests: Whether to run load tests
            
        Returns:
            Complete EvaluationReport
        """
        logger.info("Starting comprehensive evaluation...")
        
        # Run benchmarks
        benchmarks = await self.run_benchmarks(sample_size=benchmark_sample_size)
        
        # Run A/B tests
        ab_tests = []
        if run_ab_tests:
            ab_tests = await self.run_ab_tests()
        
        # Run security audit
        security_result = None
        if run_security:
            security_result = await self.run_security_audit()
        
        # Load tests
        load_tests = []
        if run_load_tests:
            load_tests = await self.run_load_tests()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            benchmarks, ab_tests, security_result, load_tests
        )
        
        # Determine overall status
        overall_status = self._determine_status(
            benchmarks, ab_tests, security_result, load_tests
        )
        
        # Create report
        report = EvaluationReport(
            timestamp=datetime.now(),
            benchmarks=benchmarks,
            ab_tests=ab_tests,
            security_audit=security_result,
            load_tests=load_tests,
            overall_status=overall_status,
            recommendations=recommendations,
        )
        
        # Save report
        self._save_report(report)
        
        # Print summary
        print(report.summary())
        
        return report
    
    async def run_benchmarks(
        self,
        sample_size: Optional[int] = None,
        benchmarks: Optional[List[str]] = None,
    ) -> Dict[str, BenchmarkResult]:
        """Run all benchmarks."""
        logger.info("Running benchmarks...")
        
        return await self.benchmark_runner.run_all(
            sample_size=sample_size,
            benchmarks=benchmarks,
        )
    
    async def run_ab_tests(
        self,
        baselines: Optional[List[str]] = None,
    ) -> List[ABTestResult]:
        """Run A/B tests against baselines."""
        logger.info("Running A/B tests...")
        
        baselines = baselines or ["gpt-4"]
        results = []
        
        for baseline in baselines:
            try:
                result = await self.ab_tester.compare(
                    queries=STANDARD_TEST_QUERIES,
                    baseline=baseline,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"A/B test against {baseline} failed: {e}")
        
        return results
    
    async def run_security_audit(self) -> AuditResult:
        """Run security audit."""
        logger.info("Running security audit...")
        
        return await self.security_audit.run_full_audit()
    
    async def run_load_tests(self) -> List[Dict[str, Any]]:
        """Run load tests."""
        logger.info("Running load tests...")
        
        # Note: Load tests require the server to be running
        # This returns placeholder data
        return [
            {
                "test": "basic_load",
                "users": 10,
                "duration_seconds": 60,
                "status": "pending",
                "note": "Run with: locust -f locustfile.py",
            }
        ]
    
    def _generate_recommendations(
        self,
        benchmarks: Dict[str, BenchmarkResult],
        ab_tests: List[ABTestResult],
        security: Optional[AuditResult],
        load_tests: List[Dict],
    ) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Benchmark recommendations
        for name, result in benchmarks.items():
            if result.accuracy < 0.8:
                recommendations.append(
                    f"Improve {name} accuracy (currently {result.accuracy:.1%})"
                )
            if result.avg_latency_ms > 3000:
                recommendations.append(
                    f"Reduce {name} latency (currently {result.avg_latency_ms:.0f}ms)"
                )
        
        # A/B test recommendations
        for test in ab_tests:
            if test.llmhive_win_rate < 0.4:
                recommendations.append(
                    f"Investigate why LLMHive underperforms vs {test.baseline_model}"
                )
        
        # Security recommendations
        if security:
            critical_count = len(security.critical_findings)
            if critical_count > 0:
                recommendations.append(
                    f"URGENT: Address {critical_count} critical security finding(s)"
                )
            
            if security.failed > 0:
                recommendations.append(
                    f"Fix {security.failed} failed security check(s)"
                )
        
        return recommendations
    
    def _determine_status(
        self,
        benchmarks: Dict[str, BenchmarkResult],
        ab_tests: List[ABTestResult],
        security: Optional[AuditResult],
        load_tests: List[Dict],
    ) -> str:
        """Determine overall evaluation status."""
        # Check for critical issues
        if security and len(security.critical_findings) > 0:
            return "CRITICAL - Security issues found"
        
        # Check benchmark performance
        avg_accuracy = sum(r.accuracy for r in benchmarks.values()) / len(benchmarks) if benchmarks else 0
        if avg_accuracy < 0.5:
            return "POOR - Low benchmark accuracy"
        
        # Check A/B performance
        if ab_tests:
            avg_win_rate = sum(t.llmhive_win_rate for t in ab_tests) / len(ab_tests)
            if avg_win_rate < 0.3:
                return "NEEDS_IMPROVEMENT - Underperforming baseline"
        
        if avg_accuracy >= 0.8:
            return "EXCELLENT - Ready for production"
        elif avg_accuracy >= 0.6:
            return "GOOD - Minor improvements recommended"
        else:
            return "FAIR - Several improvements needed"
    
    def _save_report(self, report: EvaluationReport) -> None:
        """Save evaluation report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"evaluation_report_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        logger.info(f"Report saved to {filename}")


# ==============================================================================
# CLI Entry Point
# ==============================================================================

async def run_evaluation(
    output_dir: str = "./evaluation_results",
    sample_size: int = 50,
    include_ab_tests: bool = True,
    include_security: bool = True,
) -> EvaluationReport:
    """
    Run evaluation from CLI.
    
    Usage:
        python -m llmhive.app.evaluation.runner
    """
    runner = EvaluationRunner(output_dir=output_dir)
    
    return await runner.run_full_evaluation(
        benchmark_sample_size=sample_size,
        run_ab_tests=include_ab_tests,
        run_security=include_security,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run LLMHive evaluation")
    parser.add_argument("--output-dir", default="./evaluation_results")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--no-ab-tests", action="store_true")
    parser.add_argument("--no-security", action="store_true")
    
    args = parser.parse_args()
    
    asyncio.run(run_evaluation(
        output_dir=args.output_dir,
        sample_size=args.sample_size,
        include_ab_tests=not args.no_ab_tests,
        include_security=not args.no_security,
    ))

