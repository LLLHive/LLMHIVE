#!/usr/bin/env python3
"""Live Prompt Audit - Production-representative quality regression testing.

This script runs golden prompts through the actual LLMHive system to detect
quality regressions that unit tests might miss.

Usage:
    # Local mode (in-process orchestration)
    python tests/quality_eval/live_prompt_audit.py --mode=local

    # Staging mode (HTTP calls to staging)
    python tests/quality_eval/live_prompt_audit.py --mode=staging --url=https://staging.llmhive.ai

    # Production mode (HTTP calls to production)
    python tests/quality_eval/live_prompt_audit.py --mode=prod --url=https://api.llmhive.ai

    # Limit prompts for quick check
    python tests/quality_eval/live_prompt_audit.py --mode=local --max-prompts=10

Environment Variables:
    LLMHIVE_API_URL: Default API URL for HTTP modes
    LLMHIVE_API_KEY: API key for authentication
    LLMHIVE_STAGING_URL: Staging URL
    LLMHIVE_PROD_URL: Production URL
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class GoldenPrompt:
    """A golden prompt test case."""
    id: str
    category: str
    prompt: str
    expected_contains: Optional[str] = None
    expected_regex: Optional[str] = None
    expected_not_contains: Optional[str] = None
    critical: bool = False
    requirements: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class AuditResult:
    """Result of auditing a single prompt."""
    prompt_id: str
    category: str
    prompt_text: str
    passed: bool
    final_answer: str
    trace_id: Optional[str] = None
    models_used: List[str] = field(default_factory=list)
    strategy_used: Optional[str] = None
    verification_status: Optional[str] = None
    verification_score: Optional[float] = None
    confidence: Optional[float] = None
    sources_count: int = 0
    tools_used: List[str] = field(default_factory=list)
    latency_ms: float = 0
    tokens_used: int = 0
    error: Optional[str] = None
    failure_reason: Optional[str] = None
    critical: bool = False


@dataclass
class AuditReport:
    """Complete audit report."""
    timestamp: str
    mode: str
    url: Optional[str]
    total_prompts: int
    passed: int
    failed: int
    critical_failed: int
    pass_rate: float
    results: List[AuditResult] = field(default_factory=list)
    summary_by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)


def load_golden_prompts(path: Path) -> List[GoldenPrompt]:
    """Load golden prompts from YAML file."""
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    
    prompts = []
    for p in data.get('prompts', []):
        prompts.append(GoldenPrompt(
            id=p['id'],
            category=p['category'],
            prompt=p['prompt'],
            expected_contains=p.get('expected_contains'),
            expected_regex=p.get('expected_regex'),
            expected_not_contains=p.get('expected_not_contains'),
            critical=p.get('critical', False),
            requirements=p.get('requirements', {}),
            notes=p.get('notes', ''),
        ))
    
    logger.info(f"Loaded {len(prompts)} golden prompts")
    return prompts


def evaluate_response(prompt: GoldenPrompt, answer: str) -> tuple[bool, Optional[str]]:
    """Evaluate if a response meets the expected criteria.
    
    Returns:
        tuple: (passed, failure_reason)
    """
    answer_lower = answer.lower()
    
    # Check expected_contains
    if prompt.expected_contains:
        if prompt.expected_contains.lower() not in answer_lower:
            return False, f"Missing expected content: '{prompt.expected_contains}'"
    
    # Check expected_regex
    if prompt.expected_regex:
        if not re.search(prompt.expected_regex, answer, re.IGNORECASE):
            return False, f"Does not match expected pattern: '{prompt.expected_regex}'"
    
    # Check expected_not_contains (anti-clarification)
    if prompt.expected_not_contains:
        if prompt.expected_not_contains.lower() in answer_lower:
            return False, f"Contains forbidden content: '{prompt.expected_not_contains}'"
    
    # Check for stub responses (critical failure indicator)
    if prompt.requirements.get('requires_real_provider'):
        if 'stub' in answer_lower or 'stub response' in answer_lower:
            return False, "Stub provider detected - real provider required"
    
    return True, None


class LocalModeExecutor:
    """Execute prompts using local in-process orchestration."""
    
    def __init__(self):
        self.orchestrator = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the local orchestrator."""
        if self._initialized:
            return
        
        try:
            # Add the llmhive package to path
            llmhive_path = Path(__file__).parent.parent.parent / 'llmhive' / 'src'
            if str(llmhive_path) not in sys.path:
                sys.path.insert(0, str(llmhive_path))
            
            from llmhive.app.orchestrator import get_orchestrator
            self.orchestrator = await get_orchestrator()
            self._initialized = True
            logger.info("Local orchestrator initialized")
        except ImportError as e:
            logger.error(f"Failed to import orchestrator: {e}")
            raise RuntimeError("Local mode requires llmhive package to be installed")
    
    async def execute(self, prompt: GoldenPrompt) -> AuditResult:
        """Execute a prompt through the local orchestrator."""
        if not self._initialized:
            await self.initialize()
        
        start_time = time.perf_counter()
        
        try:
            # Configure for deterministic factoid responses
            kwargs = {
                "temperature": 0,  # Deterministic for factoids
                "accuracy_level": 3,  # Medium accuracy
                "use_verification": prompt.category == "factoid",
            }
            
            # Execute through orchestrator
            result = await self.orchestrator.orchestrate(
                prompt.prompt,
                **kwargs
            )
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract response data
            final_answer = ""
            if hasattr(result, 'final_response'):
                if hasattr(result.final_response, 'content'):
                    final_answer = result.final_response.content
                else:
                    final_answer = str(result.final_response)
            elif isinstance(result, dict):
                final_answer = result.get('content', result.get('answer', str(result)))
            else:
                final_answer = str(result)
            
            # Extract metadata
            trace_id = getattr(result, 'trace_id', None)
            models_used = getattr(result, 'models_used', [])
            strategy_used = None
            if hasattr(result, 'consensus_notes'):
                for note in result.consensus_notes:
                    if 'HRM' in note:
                        strategy_used = 'hrm'
                    elif 'consensus' in note.lower():
                        strategy_used = 'consensus'
                    elif 'tool' in note.lower():
                        strategy_used = 'tools'
            
            verification_status = getattr(result, 'verification_status', None)
            verification_score = getattr(result, 'verification_score', None)
            confidence = getattr(result, 'confidence', None)
            sources = getattr(result, 'sources', [])
            tools_used = getattr(result, 'tools_used', [])
            tokens_used = 0
            if hasattr(result, 'final_response') and hasattr(result.final_response, 'tokens_used'):
                tokens_used = result.final_response.tokens_used
            
            # Evaluate the response
            passed, failure_reason = evaluate_response(prompt, final_answer)
            
            return AuditResult(
                prompt_id=prompt.id,
                category=prompt.category,
                prompt_text=prompt.prompt,
                passed=passed,
                final_answer=final_answer[:500],  # Truncate for report
                trace_id=trace_id,
                models_used=models_used if isinstance(models_used, list) else [models_used],
                strategy_used=strategy_used,
                verification_status=verification_status,
                verification_score=verification_score,
                confidence=confidence,
                sources_count=len(sources) if sources else 0,
                tools_used=tools_used if isinstance(tools_used, list) else [],
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                failure_reason=failure_reason,
                critical=prompt.critical,
            )
            
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error executing prompt {prompt.id}: {e}")
            return AuditResult(
                prompt_id=prompt.id,
                category=prompt.category,
                prompt_text=prompt.prompt,
                passed=False,
                final_answer="",
                error=str(e),
                failure_reason=f"Execution error: {e}",
                latency_ms=latency_ms,
                critical=prompt.critical,
            )


class HTTPModeExecutor:
    """Execute prompts using HTTP calls to staging/production."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    async def initialize(self):
        """Initialize HTTP session."""
        import aiohttp
        self.session = aiohttp.ClientSession(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
                **({"X-API-Key": self.api_key} if self.api_key else {}),
            }
        )
        logger.info(f"HTTP executor initialized for {self.base_url}")
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
    
    async def execute(self, prompt: GoldenPrompt) -> AuditResult:
        """Execute a prompt through HTTP API."""
        if not self.session:
            await self.initialize()
        
        start_time = time.perf_counter()
        
        try:
            # Build request payload
            payload = {
                "prompt": prompt.prompt,
                "temperature": 0,  # Deterministic
                "max_tokens": 500,
                "stream": False,
            }
            
            # Add audit mode header
            headers = {"X-Audit-Mode": "true"}
            
            async with self.session.post(
                f"{self.base_url}/v1/chat",
                json=payload,
                headers=headers,
                timeout=60
            ) as response:
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                if response.status != 200:
                    error_text = await response.text()
                    return AuditResult(
                        prompt_id=prompt.id,
                        category=prompt.category,
                        prompt_text=prompt.prompt,
                        passed=False,
                        final_answer="",
                        error=f"HTTP {response.status}: {error_text[:200]}",
                        failure_reason=f"API error: {response.status}",
                        latency_ms=latency_ms,
                        critical=prompt.critical,
                    )
                
                data = await response.json()
                
                # Extract response content
                final_answer = (
                    data.get('content') or 
                    data.get('message') or 
                    data.get('response') or 
                    data.get('answer', '')
                )
                
                # Extract metadata
                metadata = data.get('metadata', data.get('extra', {}))
                
                # Evaluate
                passed, failure_reason = evaluate_response(prompt, final_answer)
                
                return AuditResult(
                    prompt_id=prompt.id,
                    category=prompt.category,
                    prompt_text=prompt.prompt,
                    passed=passed,
                    final_answer=final_answer[:500],
                    trace_id=data.get('trace_id') or metadata.get('trace_id'),
                    models_used=data.get('models_used', metadata.get('models_used', [])),
                    strategy_used=data.get('strategy_used') or metadata.get('strategy_used'),
                    verification_status=data.get('verification_status') or metadata.get('verification_status'),
                    verification_score=data.get('verification_score') or metadata.get('verification_score'),
                    confidence=data.get('confidence') or metadata.get('confidence'),
                    sources_count=len(data.get('sources', [])),
                    tools_used=data.get('tools_used', metadata.get('tools_used', [])),
                    latency_ms=latency_ms,
                    tokens_used=data.get('tokens_used', metadata.get('tokens_used', 0)),
                    failure_reason=failure_reason,
                    critical=prompt.critical,
                )
                
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Error executing prompt {prompt.id}: {e}")
            return AuditResult(
                prompt_id=prompt.id,
                category=prompt.category,
                prompt_text=prompt.prompt,
                passed=False,
                final_answer="",
                error=str(e),
                failure_reason=f"Request error: {e}",
                latency_ms=latency_ms,
                critical=prompt.critical,
            )


async def run_audit(
    mode: str,
    url: Optional[str],
    api_key: Optional[str],
    max_prompts: Optional[int],
    categories: Optional[List[str]],
    critical_only: bool,
) -> AuditReport:
    """Run the full audit."""
    
    # Load golden prompts
    prompts_path = Path(__file__).parent / 'golden_prompts.yaml'
    if not prompts_path.exists():
        raise FileNotFoundError(f"Golden prompts file not found: {prompts_path}")
    
    prompts = load_golden_prompts(prompts_path)
    
    # Filter prompts
    if categories:
        prompts = [p for p in prompts if p.category in categories]
    if critical_only:
        prompts = [p for p in prompts if p.critical]
    if max_prompts:
        prompts = prompts[:max_prompts]
    
    logger.info(f"Running audit with {len(prompts)} prompts in {mode} mode")
    
    # Create executor
    if mode == 'local':
        executor = LocalModeExecutor()
    else:
        if not url:
            url = os.environ.get(
                'LLMHIVE_STAGING_URL' if mode == 'staging' else 'LLMHIVE_PROD_URL',
                os.environ.get('LLMHIVE_API_URL', 'http://localhost:8000')
            )
        api_key = api_key or os.environ.get('LLMHIVE_API_KEY')
        executor = HTTPModeExecutor(url, api_key)
    
    try:
        await executor.initialize()
        
        results: List[AuditResult] = []
        for i, prompt in enumerate(prompts):
            logger.info(f"[{i+1}/{len(prompts)}] Testing: {prompt.id}")
            result = await executor.execute(prompt)
            results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            logger.info(f"  {status}: {result.failure_reason or 'OK'}")
        
        # Close HTTP session if needed
        if hasattr(executor, 'close'):
            await executor.close()
        
    except Exception as e:
        logger.error(f"Audit execution failed: {e}")
        raise
    
    # Build report
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    critical_failed = sum(1 for r in results if not r.passed and r.critical)
    
    # Summary by category
    summary_by_category: Dict[str, Dict[str, int]] = {}
    for r in results:
        if r.category not in summary_by_category:
            summary_by_category[r.category] = {'total': 0, 'passed': 0, 'failed': 0}
        summary_by_category[r.category]['total'] += 1
        if r.passed:
            summary_by_category[r.category]['passed'] += 1
        else:
            summary_by_category[r.category]['failed'] += 1
    
    report = AuditReport(
        timestamp=datetime.now().isoformat(),
        mode=mode,
        url=url if mode != 'local' else None,
        total_prompts=len(results),
        passed=passed,
        failed=failed,
        critical_failed=critical_failed,
        pass_rate=passed / len(results) if results else 0,
        results=results,
        summary_by_category=summary_by_category,
    )
    
    return report


def print_report(report: AuditReport):
    """Print a formatted report to console."""
    print("\n" + "=" * 70)
    print("LLMHIVE LIVE PROMPT AUDIT REPORT")
    print("=" * 70)
    print(f"Timestamp: {report.timestamp}")
    print(f"Mode: {report.mode}")
    if report.url:
        print(f"URL: {report.url}")
    print("-" * 70)
    print(f"Total Prompts: {report.total_prompts}")
    print(f"Passed: {report.passed}")
    print(f"Failed: {report.failed}")
    print(f"Critical Failed: {report.critical_failed}")
    print(f"Pass Rate: {report.pass_rate:.1%}")
    print("-" * 70)
    
    print("\nResults by Category:")
    for category, stats in report.summary_by_category.items():
        rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {category}: {stats['passed']}/{stats['total']} ({rate:.0%})")
    
    # Show failures
    failures = [r for r in report.results if not r.passed]
    if failures:
        print("\n" + "-" * 70)
        print("FAILED PROMPTS:")
        for r in failures:
            critical_marker = " [CRITICAL]" if r.critical else ""
            print(f"\n  {r.prompt_id}{critical_marker}")
            print(f"  Prompt: {r.prompt_text[:60]}...")
            print(f"  Reason: {r.failure_reason or r.error}")
            if r.final_answer:
                print(f"  Answer: {r.final_answer[:100]}...")
    
    print("\n" + "=" * 70)
    
    if report.critical_failed > 0:
        print("❌ AUDIT FAILED - Critical prompts did not pass")
    else:
        print("✅ AUDIT PASSED - No critical failures")
    print("=" * 70)


def save_report(report: AuditReport, output_path: Path):
    """Save report to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict
    report_dict = asdict(report)
    
    with open(output_path, 'w') as f:
        json.dump(report_dict, f, indent=2, default=str)
    
    logger.info(f"Report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='LLMHive Live Prompt Audit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--mode',
        choices=['local', 'staging', 'prod'],
        default='local',
        help='Execution mode (default: local)'
    )
    parser.add_argument(
        '--url',
        help='API URL for staging/prod modes'
    )
    parser.add_argument(
        '--api-key',
        help='API key for authentication'
    )
    parser.add_argument(
        '--max-prompts',
        type=int,
        help='Maximum number of prompts to run'
    )
    parser.add_argument(
        '--categories',
        nargs='+',
        help='Only run specific categories'
    )
    parser.add_argument(
        '--critical-only',
        action='store_true',
        help='Only run critical prompts'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('artifacts/quality/live_audit_report.json'),
        help='Output path for JSON report'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Skip saving report to file'
    )
    
    args = parser.parse_args()
    
    # Run audit
    try:
        report = asyncio.run(run_audit(
            mode=args.mode,
            url=args.url,
            api_key=args.api_key,
            max_prompts=args.max_prompts,
            categories=args.categories,
            critical_only=args.critical_only,
        ))
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        sys.exit(1)
    
    # Print report
    print_report(report)
    
    # Save report
    if not args.no_save:
        save_report(report, args.output)
    
    # Exit with appropriate code
    if report.critical_failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()

