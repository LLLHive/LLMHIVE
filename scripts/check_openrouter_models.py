#!/usr/bin/env python3
"""OpenRouter Model Health Check Script.

This script verifies connectivity and routability to top models across
key categories. It can be run manually or as part of CI.

Usage:
    # Mocked mode (CI)
    python scripts/check_openrouter_models.py --mock
    
    # Live mode (manual)
    python scripts/check_openrouter_models.py --live
    
    # Check specific categories
    python scripts/check_openrouter_models.py --live --categories programming,research
    
    # Full report
    python scripts/check_openrouter_models.py --live --full

Requirements:
    - OPENROUTER_API_KEY environment variable (for live mode)
    - Database connection (optional, for catalog check)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

# Categories to check
DEFAULT_CATEGORIES = [
    "programming",
    "roleplay",
    "science",
    "marketing",
    "translation",
]

# Known frontier models to verify
FRONTIER_MODELS = [
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro-preview",
    "x-ai/grok-2",
    "meta-llama/llama-3.3-70b-instruct",
    "deepseek/deepseek-chat",
]

# Test prompt (safe, low-cost)
TEST_PROMPT = "Respond with only the word 'OK' to confirm connectivity."


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ModelCheckResult:
    """Result of checking a single model."""
    model_id: str
    status: str  # OK, FAIL, SKIP
    in_catalog: bool = False
    has_endpoint: bool = False
    ping_success: bool = False
    ping_latency_ms: Optional[float] = None
    estimated_cost: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "status": self.status,
            "in_catalog": self.in_catalog,
            "has_endpoint": self.has_endpoint,
            "ping_success": self.ping_success,
            "ping_latency_ms": self.ping_latency_ms,
            "estimated_cost": self.estimated_cost,
            "error": self.error_message,
        }


@dataclass
class HealthCheckReport:
    """Full health check report."""
    timestamp: str
    mode: str
    total_models: int = 0
    ok_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    results: List[ModelCheckResult] = field(default_factory=list)
    categories_checked: List[str] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_models == 0:
            return 0.0
        return self.ok_count / self.total_models
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "mode": self.mode,
            "summary": {
                "total": self.total_models,
                "ok": self.ok_count,
                "fail": self.fail_count,
                "skip": self.skip_count,
                "success_rate": f"{self.success_rate:.1%}",
            },
            "categories": self.categories_checked,
            "duration_seconds": self.total_duration_seconds,
            "results": [r.to_dict() for r in self.results],
        }
    
    def print_summary(self) -> None:
        """Print human-readable summary."""
        print("\n" + "=" * 60)
        print("OPENROUTER MODEL HEALTH CHECK REPORT")
        print("=" * 60)
        print(f"Timestamp: {self.timestamp}")
        print(f"Mode: {self.mode}")
        print(f"Categories: {', '.join(self.categories_checked)}")
        print(f"Duration: {self.total_duration_seconds:.2f}s")
        print()
        print("SUMMARY")
        print("-" * 40)
        print(f"  Total Models: {self.total_models}")
        print(f"  OK:           {self.ok_count} ({self.ok_count/max(1,self.total_models)*100:.0f}%)")
        print(f"  FAIL:         {self.fail_count}")
        print(f"  SKIP:         {self.skip_count}")
        print()
        
        # Show failures
        failures = [r for r in self.results if r.status == "FAIL"]
        if failures:
            print("FAILURES")
            print("-" * 40)
            for r in failures:
                print(f"  ❌ {r.model_id}")
                if r.error_message:
                    print(f"     Error: {r.error_message}")
            print()
        
        # Show top 10 successful
        successes = [r for r in self.results if r.status == "OK"][:10]
        if successes:
            print("TOP SUCCESSFUL MODELS")
            print("-" * 40)
            for r in successes:
                latency = f"{r.ping_latency_ms:.0f}ms" if r.ping_latency_ms else "N/A"
                cost = f"${r.estimated_cost:.4f}" if r.estimated_cost else "N/A"
                print(f"  ✅ {r.model_id:<40} {latency:<10} {cost}")
        
        print()
        print("=" * 60)


# =============================================================================
# Health Checker
# =============================================================================

class OpenRouterHealthChecker:
    """Health checker for OpenRouter models."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        mock_mode: bool = False,
        timeout: float = 30.0,
    ):
        """Initialize checker.
        
        Args:
            api_key: OpenRouter API key
            mock_mode: If True, don't make real API calls
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.mock_mode = mock_mode
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._models_cache: Dict[str, Any] = {}
    
    async def __aenter__(self) -> "OpenRouterHealthChecker":
        if not self.mock_mode:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://llmhive.com",
                    "X-Title": "LLMHive Health Check",
                },
            )
        return self
    
    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()
    
    async def run_health_check(
        self,
        categories: Optional[List[str]] = None,
        include_frontier: bool = True,
        ping_test: bool = True,
    ) -> HealthCheckReport:
        """Run full health check.
        
        Args:
            categories: Categories to check
            include_frontier: Include known frontier models
            ping_test: Run ping completion test
            
        Returns:
            HealthCheckReport
        """
        start_time = time.time()
        categories = categories or DEFAULT_CATEGORIES
        
        report = HealthCheckReport(
            timestamp=datetime.utcnow().isoformat(),
            mode="mock" if self.mock_mode else "live",
            categories_checked=categories,
        )
        
        # Collect models to check
        models_to_check: List[str] = []
        
        # Add frontier models
        if include_frontier:
            models_to_check.extend(FRONTIER_MODELS)
        
        # Add top models per category
        if not self.mock_mode:
            for category in categories:
                top_models = await self._get_top_models_for_category(category, limit=5)
                models_to_check.extend(top_models)
        
        # Deduplicate
        models_to_check = list(dict.fromkeys(models_to_check))
        
        logger.info("Checking %d models...", len(models_to_check))
        
        # Check each model
        for model_id in models_to_check:
            result = await self._check_model(model_id, ping_test=ping_test)
            report.results.append(result)
            report.total_models += 1
            
            if result.status == "OK":
                report.ok_count += 1
            elif result.status == "FAIL":
                report.fail_count += 1
            else:
                report.skip_count += 1
        
        report.total_duration_seconds = time.time() - start_time
        
        return report
    
    async def _check_model(
        self,
        model_id: str,
        ping_test: bool = True,
    ) -> ModelCheckResult:
        """Check a single model.
        
        Args:
            model_id: Model ID
            ping_test: Run ping completion test
            
        Returns:
            ModelCheckResult
        """
        if self.mock_mode:
            return ModelCheckResult(
                model_id=model_id,
                status="OK",
                in_catalog=True,
                has_endpoint=True,
                ping_success=True,
                ping_latency_ms=500 + (hash(model_id) % 1000),
                estimated_cost=0.0001,
            )
        
        result = ModelCheckResult(model_id=model_id, status="FAIL")
        
        try:
            # Step 1: Check if in catalog
            if model_id in self._models_cache:
                model_data = self._models_cache[model_id]
            else:
                model_data = await self._fetch_model_info(model_id)
            
            if model_data:
                result.in_catalog = True
                
                # Extract pricing for cost estimate
                pricing = model_data.get("pricing", {})
                prompt_price = float(pricing.get("prompt", 0))
                completion_price = float(pricing.get("completion", 0))
                
                # Estimate cost for ~100 tokens
                result.estimated_cost = (prompt_price * 50 + completion_price * 50)
            else:
                result.error_message = "Model not found in catalog"
                return result
            
            # Step 2: Check endpoint availability
            endpoint_available = await self._check_endpoint(model_id)
            result.has_endpoint = endpoint_available
            
            if not endpoint_available:
                result.error_message = "No available endpoint"
                return result
            
            # Step 3: Ping test (optional)
            if ping_test:
                ping_success, latency_ms, error = await self._ping_model(model_id)
                result.ping_success = ping_success
                result.ping_latency_ms = latency_ms
                
                if not ping_success:
                    result.error_message = error
                    return result
            else:
                result.ping_success = True
            
            result.status = "OK"
            
        except Exception as e:
            result.error_message = str(e)
            logger.error("Error checking %s: %s", model_id, e)
        
        return result
    
    async def _fetch_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Fetch model info from API."""
        if not self._client:
            return None
        
        try:
            response = await self._client.get(f"{OPENROUTER_API_BASE}/models")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("data", [])
            
            # Cache all models
            for model in models:
                self._models_cache[model.get("id")] = model
            
            return self._models_cache.get(model_id)
            
        except Exception as e:
            logger.warning("Failed to fetch models: %s", e)
            return None
    
    async def _check_endpoint(self, model_id: str) -> bool:
        """Check if model has available endpoint."""
        if not self._client:
            return True
        
        try:
            # Parse author/slug
            if "/" not in model_id:
                return False
            
            author, slug = model_id.split("/", 1)
            
            response = await self._client.get(
                f"{OPENROUTER_API_BASE}/models/{author}/{slug}/endpoints"
            )
            
            if response.status_code == 404:
                # Endpoint check might not be available, assume OK
                return True
            
            response.raise_for_status()
            data = response.json()
            
            endpoints = data.get("data", [])
            return len(endpoints) > 0
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return True  # Endpoint not found, but model might still work
            return False
        except Exception:
            return True  # Assume OK on error
    
    async def _ping_model(
        self,
        model_id: str,
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """Send ping completion to model.
        
        Returns:
            Tuple of (success, latency_ms, error_message)
        """
        if not self._client:
            return True, 100.0, None
        
        try:
            start = time.time()
            
            response = await self._client.post(
                f"{OPENROUTER_API_BASE}/chat/completions",
                json={
                    "model": model_id,
                    "messages": [
                        {"role": "user", "content": TEST_PROMPT}
                    ],
                    "max_tokens": 10,
                    "temperature": 0,
                },
            )
            
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code != 200:
                return False, latency_ms, f"HTTP {response.status_code}"
            
            data = response.json()
            
            # Check for valid response
            choices = data.get("choices", [])
            if not choices:
                return False, latency_ms, "No response content"
            
            return True, latency_ms, None
            
        except httpx.TimeoutException:
            return False, None, "Timeout"
        except Exception as e:
            return False, None, str(e)
    
    async def _get_top_models_for_category(
        self,
        category: str,
        limit: int = 5,
    ) -> List[str]:
        """Get top models for a category."""
        if not self._client:
            return []
        
        try:
            # Use category filter if supported
            response = await self._client.get(
                f"{OPENROUTER_API_BASE}/models",
                params={"category": category},
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            models = data.get("data", [])
            
            return [m.get("id") for m in models[:limit] if m.get("id")]
            
        except Exception:
            return []


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenRouter Model Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/check_openrouter_models.py --mock
  python scripts/check_openrouter_models.py --live
  python scripts/check_openrouter_models.py --live --categories programming,research
  python scripts/check_openrouter_models.py --live --full --output report.json
        """,
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (no real API calls)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run in live mode (requires OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        help="Comma-separated list of categories to check",
    )
    parser.add_argument(
        "--no-ping",
        action="store_true",
        help="Skip ping completion test",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include all frontier models",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON report to file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON only",
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.live:
        mock_mode = False
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("ERROR: OPENROUTER_API_KEY environment variable required for live mode")
            sys.exit(1)
    elif args.mock:
        mock_mode = True
    else:
        # Default to mock mode
        mock_mode = True
        print("INFO: Running in mock mode. Use --live for real API calls.")
    
    # Parse categories
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    
    async def run():
        async with OpenRouterHealthChecker(mock_mode=mock_mode) as checker:
            report = await checker.run_health_check(
                categories=categories,
                include_frontier=args.full or True,
                ping_test=not args.no_ping,
            )
            
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                report.print_summary()
            
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(report.to_dict(), f, indent=2)
                print(f"\nReport saved to {args.output}")
            
            # Exit with error if too many failures
            if report.fail_count > report.total_models * 0.5:
                sys.exit(1)
    
    asyncio.run(run())


if __name__ == "__main__":
    main()

