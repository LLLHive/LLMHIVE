"""Weekly Improvement System for LLMHive.

Fully automated weekly improvement pipeline that:
1. Syncs OpenRouter model catalog and rankings
2. Runs Research Agent to find new AI developments
3. Runs Benchmark Agent to evaluate current performance
4. Uses Planning Agent to decide on safe improvements
5. Applies safe upgrades via Upgrade Agent
6. Generates comprehensive weekly report

Schedule: Sunday 3am UTC (configurable via Cloud Scheduler or cron)

Usage:
    # Full weekly run
    python -m llmhive.app.weekly_improvement --run
    
    # Dry run (no changes applied)
    python -m llmhive.app.weekly_improvement --run --dry-run
    
    # Generate report only
    python -m llmhive.app.weekly_improvement --report-only
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

class RiskLevel(str, Enum):
    """Risk level for an improvement."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UpgradeStatus(str, Enum):
    """Status of an upgrade."""
    PROPOSED = "proposed"
    AUTO_APPLIED = "auto_applied"
    GATED = "gated"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class ModelChange:
    """A change to the model catalog."""
    model_id: str
    change_type: str  # added, removed, updated
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryChange:
    """A change to categories."""
    slug: str
    change_type: str  # added, removed, updated
    display_name: str = ""


@dataclass
class RankingChange:
    """A change in rankings."""
    category: str
    model_id: str
    old_rank: Optional[int]
    new_rank: Optional[int]
    delta: int = 0


@dataclass
class ResearchFinding:
    """A finding from the Research Agent."""
    title: str
    source: str
    summary: str
    relevance_score: float
    potential_impact: str
    integration_proposal: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Results from benchmark evaluation."""
    overall_score: float
    pass_rate: float
    category_scores: Dict[str, float] = field(default_factory=dict)
    regressions: List[Dict[str, Any]] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)


@dataclass
class PlannedUpgrade:
    """An upgrade planned by the Planning Agent."""
    id: str
    title: str
    description: str
    risk_level: RiskLevel
    category: str  # model, routing, prompt, strategy, ui
    status: UpgradeStatus = UpgradeStatus.PROPOSED
    auto_apply: bool = False
    pr_branch: Optional[str] = None
    applied_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "category": self.category,
            "status": self.status.value,
            "auto_apply": self.auto_apply,
            "pr_branch": self.pr_branch,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "metadata": self.metadata,
        }


@dataclass
class WeeklyReport:
    """Complete weekly improvement report."""
    report_date: datetime
    week_start: datetime
    week_end: datetime
    
    # OpenRouter sync results
    models_added: List[ModelChange] = field(default_factory=list)
    models_removed: List[ModelChange] = field(default_factory=list)
    models_updated: List[ModelChange] = field(default_factory=list)
    category_changes: List[CategoryChange] = field(default_factory=list)
    ranking_highlights: List[RankingChange] = field(default_factory=list)
    
    # Research findings
    research_findings: List[Dict[str, Any]] = field(default_factory=list)
    high_impact_proposals: List[str] = field(default_factory=list)
    
    # Benchmark results
    benchmark_before: Optional[BenchmarkResult] = None
    benchmark_after: Optional[BenchmarkResult] = None
    regression_alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Upgrades
    upgrades_applied: List[PlannedUpgrade] = field(default_factory=list)
    upgrades_gated: List[PlannedUpgrade] = field(default_factory=list)
    upgrades_failed: List[PlannedUpgrade] = field(default_factory=list)
    
    # Safety status
    all_tests_passed: bool = True
    safe_to_deploy: bool = True
    safety_notes: List[str] = field(default_factory=list)
    
    # Metrics
    total_duration_seconds: float = 0
    sync_duration_seconds: float = 0
    research_duration_seconds: float = 0
    benchmark_duration_seconds: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_date": self.report_date.isoformat(),
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "models": {
                "added": [asdict(m) for m in self.models_added],
                "removed": [asdict(m) for m in self.models_removed],
                "updated": len(self.models_updated),
            },
            "categories": {
                "changes": [asdict(c) for c in self.category_changes],
            },
            "rankings": {
                "highlights": [asdict(r) for r in self.ranking_highlights],
            },
            "research": {
                "findings_count": len(self.research_findings),
                "high_impact_proposals": self.high_impact_proposals,
            },
            "benchmarks": {
                "before": asdict(self.benchmark_before) if self.benchmark_before else None,
                "after": asdict(self.benchmark_after) if self.benchmark_after else None,
                "regressions": self.regression_alerts,
            },
            "upgrades": {
                "applied": [u.to_dict() for u in self.upgrades_applied],
                "gated": [u.to_dict() for u in self.upgrades_gated],
                "failed": [u.to_dict() for u in self.upgrades_failed],
            },
            "safety": {
                "all_tests_passed": self.all_tests_passed,
                "safe_to_deploy": self.safe_to_deploy,
                "notes": self.safety_notes,
            },
            "duration": {
                "total_seconds": self.total_duration_seconds,
                "sync_seconds": self.sync_duration_seconds,
                "research_seconds": self.research_duration_seconds,
                "benchmark_seconds": self.benchmark_duration_seconds,
            },
        }


# =============================================================================
# Weekly Improvement Orchestrator
# =============================================================================

class WeeklyImprovementOrchestrator:
    """Orchestrates the weekly improvement cycle.
    
    Phases:
    1. OpenRouter Sync - Update model catalog and rankings
    2. Research - Scan for new AI developments
    3. Benchmark (Pre) - Establish baseline performance
    4. Plan - Analyze findings and create upgrade plan
    5. Apply - Execute safe upgrades
    6. Benchmark (Post) - Verify no regressions
    7. Report - Generate comprehensive weekly report
    """
    
    # Paths for storing weekly data
    WEEKLY_DIR = Path(__file__).parent / "weekly"
    REPORTS_DIR = WEEKLY_DIR / "reports"
    PLANS_DIR = WEEKLY_DIR / "plans"
    EVALS_DIR = WEEKLY_DIR / "evals"
    RESEARCH_DIR = Path(__file__).parent.parent.parent.parent.parent / "research"
    
    # Risk assessment thresholds
    SAFE_CHANGE_TYPES = {"model_catalog_add", "category_add", "pricing_update"}
    MEDIUM_RISK_TYPES = {"model_routing_update", "fallback_change"}
    HIGH_RISK_TYPES = {"prompt_template_change", "strategy_change", "core_logic_change"}
    
    def __init__(
        self,
        dry_run: bool = False,
        apply_safe_changes: bool = True,
        run_benchmarks: bool = True,
    ):
        """Initialize the orchestrator.
        
        Args:
            dry_run: If True, don't apply any changes
            apply_safe_changes: If True, auto-apply low-risk changes
            run_benchmarks: If True, run benchmark suites
        """
        self.dry_run = dry_run
        self.apply_safe_changes = apply_safe_changes
        self.run_benchmarks = run_benchmarks
        
        # Create directories
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.PLANS_DIR.mkdir(parents=True, exist_ok=True)
        self.EVALS_DIR.mkdir(parents=True, exist_ok=True)
        self.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        
        # Agent instances (lazy loaded)
        self._research_agent = None
        self._planning_agent = None
        self._benchmark_agent = None
        self._blackboard = None
        
        # State
        self._report: Optional[WeeklyReport] = None
        self._planned_upgrades: List[PlannedUpgrade] = []
        
        logger.info(
            "WeeklyImprovementOrchestrator initialized "
            f"(dry_run={dry_run}, apply_safe={apply_safe_changes})"
        )
    
    @property
    def research_agent(self):
        """Lazy load Research Agent."""
        if self._research_agent is None:
            from .agents.research_agent import ResearchAgent
            self._research_agent = ResearchAgent()
        return self._research_agent
    
    @property
    def planning_agent(self):
        """Lazy load Planning Agent."""
        if self._planning_agent is None:
            from .agents.planning_agent import PlanningAgent
            self._planning_agent = PlanningAgent()
        return self._planning_agent
    
    @property
    def benchmark_agent(self):
        """Lazy load Benchmark Agent."""
        if self._benchmark_agent is None:
            from .agents.benchmark_agent import BenchmarkAgent
            self._benchmark_agent = BenchmarkAgent()
        return self._benchmark_agent
    
    @property
    def blackboard(self):
        """Get shared blackboard."""
        if self._blackboard is None:
            from .agents.blackboard import get_global_blackboard
            self._blackboard = get_global_blackboard()
        return self._blackboard
    
    async def run_full_cycle(self) -> WeeklyReport:
        """Run the complete weekly improvement cycle.
        
        Returns:
            WeeklyReport with all results
        """
        start_time = datetime.now(timezone.utc)
        
        # Initialize report
        week_end = start_time
        week_start = week_end - timedelta(days=7)
        self._report = WeeklyReport(
            report_date=start_time,
            week_start=week_start,
            week_end=week_end,
        )
        
        logger.info("=" * 60)
        logger.info("WEEKLY IMPROVEMENT CYCLE STARTED")
        logger.info(f"Week: {week_start.date()} to {week_end.date()}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info("=" * 60)
        
        try:
            # Phase 1: OpenRouter Sync
            await self._phase_openrouter_sync()
            
            # Phase 2: Research Agent
            await self._phase_research()
            
            # Phase 3: Pre-change Benchmark
            if self.run_benchmarks:
                await self._phase_benchmark_pre()
            
            # Phase 4: Planning
            await self._phase_planning()
            
            # Phase 5: Apply Safe Upgrades
            if self.apply_safe_changes and not self.dry_run:
                await self._phase_apply_upgrades()
            
            # Phase 6: Post-change Benchmark
            if self.run_benchmarks and self._report.upgrades_applied:
                await self._phase_benchmark_post()
            
            # Phase 7: Generate Report
            await self._phase_generate_report()
            
        except Exception as e:
            logger.error(f"Weekly cycle failed: {e}", exc_info=True)
            self._report.safe_to_deploy = False
            self._report.safety_notes.append(f"CRITICAL: Cycle failed with error: {e}")
        
        # Finalize
        self._report.total_duration_seconds = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds()
        
        logger.info("=" * 60)
        logger.info("WEEKLY IMPROVEMENT CYCLE COMPLETED")
        logger.info(f"Duration: {self._report.total_duration_seconds:.1f}s")
        logger.info(f"Safe to deploy: {self._report.safe_to_deploy}")
        logger.info("=" * 60)
        
        return self._report
    
    async def _phase_openrouter_sync(self) -> None:
        """Phase 1: Sync OpenRouter model catalog and rankings."""
        logger.info("\n📥 PHASE 1: OpenRouter Sync")
        phase_start = datetime.now(timezone.utc)
        
        try:
            # Import sync modules
            from .openrouter.rankings_sync import RankingsSync
            from .openrouter.sync import OpenRouterModelSync
            from .db import get_db_session
            
            db_session = get_db_session()
            
            try:
                # 1. Sync models
                logger.info("  Syncing models from OpenRouter API...")
                model_sync = OpenRouterModelSync(db_session)
                model_report = await model_sync.run(
                    dry_run=self.dry_run,
                    enrich_endpoints=True,
                )
                
                # Track model changes
                for model_id in getattr(model_report, 'new_model_ids', []):
                    self._report.models_added.append(
                        ModelChange(model_id=model_id, change_type="added")
                    )
                
                for model_id in getattr(model_report, 'inactive_model_ids', []):
                    self._report.models_removed.append(
                        ModelChange(model_id=model_id, change_type="removed")
                    )
                
                # 2. Sync categories and rankings (weekly full sync)
                logger.info("  Syncing categories and rankings...")
                rankings_sync = RankingsSync(db_session)
                rankings_report = await rankings_sync.run_full_sync(
                    dry_run=self.dry_run
                )
                
                # Track category changes
                for cat in getattr(rankings_report, 'new_categories', []):
                    self._report.category_changes.append(
                        CategoryChange(
                            slug=cat.get('slug', ''),
                            display_name=cat.get('display_name', ''),
                            change_type="added",
                        )
                    )
                
                logger.info(
                    f"  ✅ Sync complete: "
                    f"{len(self._report.models_added)} added, "
                    f"{len(self._report.models_removed)} removed"
                )
                
            finally:
                db_session.close()
                
        except ImportError as e:
            logger.warning(f"  ⚠️ Sync modules not available: {e}")
        except Exception as e:
            logger.error(f"  ❌ Sync failed: {e}")
            self._report.safety_notes.append(f"OpenRouter sync failed: {e}")
        
        self._report.sync_duration_seconds = (
            datetime.now(timezone.utc) - phase_start
        ).total_seconds()
    
    async def _phase_research(self) -> None:
        """Phase 2: Run Research Agent to find new developments."""
        logger.info("\n🔬 PHASE 2: Research Agent")
        phase_start = datetime.now(timezone.utc)
        
        try:
            # Run research agent
            result = await self.research_agent.execute()
            
            if result.success:
                findings = result.output.get("findings", []) if isinstance(result.output, dict) else []
                self._report.research_findings = findings
                
                # Extract high-impact proposals
                for finding in findings:
                    if finding.get("potential_impact") == "high":
                        proposal = finding.get("integration_proposal")
                        if proposal:
                            self._report.high_impact_proposals.append(proposal)
                
                logger.info(
                    f"  ✅ Research complete: "
                    f"{len(findings)} findings, "
                    f"{len(self._report.high_impact_proposals)} high-impact"
                )
            else:
                logger.warning(f"  ⚠️ Research agent returned error: {result.error}")
                
        except Exception as e:
            logger.error(f"  ❌ Research failed: {e}")
        
        self._report.research_duration_seconds = (
            datetime.now(timezone.utc) - phase_start
        ).total_seconds()
    
    async def _phase_benchmark_pre(self) -> None:
        """Phase 3: Run benchmarks to establish baseline."""
        logger.info("\n📊 PHASE 3: Pre-change Benchmark")
        phase_start = datetime.now(timezone.utc)
        
        try:
            from .agents.base import AgentTask
            
            task = AgentTask(
                task_id="weekly-benchmark-pre",
                task_type="run_benchmark",
                payload={"mode": "full"},
            )
            result = await self.benchmark_agent.execute(task)
            
            if result.success and isinstance(result.output, dict):
                metrics = result.output.get("metrics", {})
                self._report.benchmark_before = BenchmarkResult(
                    overall_score=metrics.get("overall_score", 0),
                    pass_rate=metrics.get("pass_rate", 0),
                    category_scores=metrics.get("category_scores", {}),
                )
                
                # Check for regressions
                regressions = result.output.get("regressions", [])
                if regressions:
                    self._report.regression_alerts = regressions
                    self._report.safety_notes.append(
                        f"Pre-existing regressions detected: {len(regressions)}"
                    )
                
                logger.info(
                    f"  ✅ Baseline: score={metrics.get('overall_score', 0):.2f}, "
                    f"pass_rate={metrics.get('pass_rate', 0):.1%}"
                )
            else:
                logger.warning(f"  ⚠️ Benchmark failed: {result.error}")
                
        except Exception as e:
            logger.error(f"  ❌ Benchmark failed: {e}")
        
        self._report.benchmark_duration_seconds = (
            datetime.now(timezone.utc) - phase_start
        ).total_seconds()
    
    async def _phase_planning(self) -> None:
        """Phase 4: Create improvement plan using Planning Agent."""
        logger.info("\n📋 PHASE 4: Planning")
        
        try:
            # Gather all inputs for planning
            planning_inputs = {
                "model_changes": {
                    "added": len(self._report.models_added),
                    "removed": len(self._report.models_removed),
                },
                "research_proposals": self._report.high_impact_proposals,
                "benchmark_regressions": self._report.regression_alerts,
                "category_changes": [asdict(c) for c in self._report.category_changes],
            }
            
            # Create upgrades based on changes
            self._planned_upgrades = []
            
            # Auto-apply: New models added to catalog
            for model in self._report.models_added:
                upgrade = PlannedUpgrade(
                    id=f"model-add-{model.model_id[:20]}",
                    title=f"Add model: {model.model_id}",
                    description=f"New model {model.model_id} discovered on OpenRouter",
                    risk_level=RiskLevel.LOW,
                    category="model",
                    auto_apply=True,
                    metadata={"model_id": model.model_id},
                )
                self._planned_upgrades.append(upgrade)
            
            # Auto-apply: New categories
            for cat in self._report.category_changes:
                if cat.change_type == "added":
                    upgrade = PlannedUpgrade(
                        id=f"category-add-{cat.slug}",
                        title=f"Add category: {cat.display_name}",
                        description=f"New category {cat.slug} discovered on OpenRouter",
                        risk_level=RiskLevel.LOW,
                        category="model",
                        auto_apply=True,
                        metadata={"slug": cat.slug},
                    )
                    self._planned_upgrades.append(upgrade)
            
            # Gated: High-impact research proposals
            for i, proposal in enumerate(self._report.high_impact_proposals[:3]):
                upgrade = PlannedUpgrade(
                    id=f"research-{i+1}",
                    title=f"Research proposal #{i+1}",
                    description=proposal[:200],
                    risk_level=RiskLevel.HIGH,
                    category="strategy",
                    auto_apply=False,  # Requires review
                    metadata={"proposal": proposal},
                )
                self._planned_upgrades.append(upgrade)
            
            # Gated: Model routing changes based on rankings
            if self._report.ranking_highlights:
                upgrade = PlannedUpgrade(
                    id="routing-update",
                    title="Update model routing based on rankings",
                    description="Adjust primary/fallback models based on latest OpenRouter rankings",
                    risk_level=RiskLevel.MEDIUM,
                    category="routing",
                    auto_apply=False,
                    metadata={"highlights": len(self._report.ranking_highlights)},
                )
                self._planned_upgrades.append(upgrade)
            
            logger.info(
                f"  ✅ Planned {len(self._planned_upgrades)} upgrades "
                f"({sum(1 for u in self._planned_upgrades if u.auto_apply)} auto-apply)"
            )
            
        except Exception as e:
            logger.error(f"  ❌ Planning failed: {e}")
    
    async def _phase_apply_upgrades(self) -> None:
        """Phase 5: Apply safe upgrades."""
        logger.info("\n🚀 PHASE 5: Apply Upgrades")
        
        for upgrade in self._planned_upgrades:
            if not upgrade.auto_apply:
                # Gate high-risk changes
                upgrade.status = UpgradeStatus.GATED
                self._report.upgrades_gated.append(upgrade)
                logger.info(f"  ⏸️ Gated: {upgrade.title} (risk: {upgrade.risk_level.value})")
                continue
            
            try:
                # Apply the upgrade
                if upgrade.category == "model":
                    # Model catalog changes are already synced
                    upgrade.status = UpgradeStatus.AUTO_APPLIED
                    upgrade.applied_at = datetime.now(timezone.utc)
                    self._report.upgrades_applied.append(upgrade)
                    logger.info(f"  ✅ Applied: {upgrade.title}")
                else:
                    # For other categories, prepare but don't auto-apply
                    upgrade.status = UpgradeStatus.GATED
                    self._report.upgrades_gated.append(upgrade)
                    logger.info(f"  ⏸️ Gated (needs review): {upgrade.title}")
                    
            except Exception as e:
                upgrade.status = UpgradeStatus.FAILED
                upgrade.metadata["error"] = str(e)
                self._report.upgrades_failed.append(upgrade)
                logger.error(f"  ❌ Failed: {upgrade.title} - {e}")
    
    async def _phase_benchmark_post(self) -> None:
        """Phase 6: Run post-change benchmarks to verify no regressions."""
        logger.info("\n📊 PHASE 6: Post-change Benchmark")
        
        try:
            from .agents.base import AgentTask
            
            task = AgentTask(
                task_id="weekly-benchmark-post",
                task_type="run_benchmark",
                payload={"mode": "quick"},
            )
            result = await self.benchmark_agent.execute(task)
            
            if result.success and isinstance(result.output, dict):
                metrics = result.output.get("metrics", {})
                self._report.benchmark_after = BenchmarkResult(
                    overall_score=metrics.get("overall_score", 0),
                    pass_rate=metrics.get("pass_rate", 0),
                    category_scores=metrics.get("category_scores", {}),
                )
                
                # Compare with baseline
                if self._report.benchmark_before:
                    before_score = self._report.benchmark_before.overall_score
                    after_score = self._report.benchmark_after.overall_score
                    delta = after_score - before_score
                    
                    if delta < -0.05:  # 5% regression threshold
                        self._report.all_tests_passed = False
                        self._report.safe_to_deploy = False
                        self._report.safety_notes.append(
                            f"REGRESSION: Score dropped from {before_score:.2f} to {after_score:.2f}"
                        )
                        logger.warning(f"  ⚠️ Regression detected: {delta:+.2f}")
                    else:
                        logger.info(f"  ✅ No regression: {delta:+.2f}")
                
                # Check for new regressions
                new_regressions = result.output.get("regressions", [])
                if new_regressions:
                    self._report.regression_alerts.extend(new_regressions)
                    self._report.all_tests_passed = False
                    logger.warning(f"  ⚠️ New regressions: {len(new_regressions)}")
                
        except Exception as e:
            logger.error(f"  ❌ Post-benchmark failed: {e}")
            self._report.safety_notes.append(f"Post-benchmark failed: {e}")
    
    async def _phase_generate_report(self) -> None:
        """Phase 7: Generate and save the weekly report."""
        logger.info("\n📝 PHASE 7: Generate Report")
        
        timestamp = self._report.report_date.strftime("%Y-%m-%d")
        
        # Save JSON report
        json_path = self.REPORTS_DIR / f"{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(self._report.to_dict(), f, indent=2, default=str)
        logger.info(f"  📄 JSON: {json_path}")
        
        # Generate markdown report
        md_content = self._generate_markdown_report()
        md_path = self.REPORTS_DIR / f"{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(md_content)
        logger.info(f"  📄 Markdown: {md_path}")
        
        # Save plan
        plan_path = self.PLANS_DIR / f"{timestamp}.json"
        with open(plan_path, "w") as f:
            json.dump(
                [u.to_dict() for u in self._planned_upgrades],
                f, indent=2, default=str
            )
        logger.info(f"  📄 Plan: {plan_path}")
        
        # Save research findings
        if self._report.research_findings:
            findings_dir = self.RESEARCH_DIR / "findings"
            findings_dir.mkdir(parents=True, exist_ok=True)
            findings_path = findings_dir / f"{timestamp}.md"
            with open(findings_path, "w") as f:
                f.write(f"# Research Findings - {timestamp}\n\n")
                for finding in self._report.research_findings:
                    f.write(f"## {finding.get('title', 'Unknown')}\n")
                    f.write(f"**Source:** {finding.get('source', 'Unknown')}\n")
                    f.write(f"**Impact:** {finding.get('potential_impact', 'Unknown')}\n\n")
                    f.write(f"{finding.get('summary', '')}\n\n")
                    if finding.get("integration_proposal"):
                        f.write(f"**Proposal:** {finding['integration_proposal']}\n\n")
                    f.write("---\n\n")
            logger.info(f"  📄 Findings: {findings_path}")
    
    def _generate_markdown_report(self) -> str:
        """Generate a markdown weekly report."""
        r = self._report
        
        # Determine status emoji
        if r.safe_to_deploy:
            status = "✅ SAFE=true"
        else:
            status = "❌ SAFE=false"
        
        lines = [
            f"# LLMHive Weekly Improvement Report",
            f"",
            f"**Week:** {r.week_start.strftime('%Y-%m-%d')} to {r.week_end.strftime('%Y-%m-%d')}",
            f"**Generated:** {r.report_date.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Status:** {status}",
            f"",
            f"---",
            f"",
            f"## 📊 Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Models Added | {len(r.models_added)} |",
            f"| Models Removed | {len(r.models_removed)} |",
            f"| Category Changes | {len(r.category_changes)} |",
            f"| Research Findings | {len(r.research_findings)} |",
            f"| Upgrades Applied | {len(r.upgrades_applied)} |",
            f"| Upgrades Gated | {len(r.upgrades_gated)} |",
            f"| Total Duration | {r.total_duration_seconds:.1f}s |",
            f"",
        ]
        
        # Top 3 Upgrades
        all_upgrades = r.upgrades_applied + r.upgrades_gated
        if all_upgrades:
            lines.extend([
                f"## 🚀 Top Upgrades This Week",
                f"",
            ])
            for i, upgrade in enumerate(all_upgrades[:3], 1):
                status_icon = "✅" if upgrade.status == UpgradeStatus.AUTO_APPLIED else "⏸️"
                lines.append(f"{i}. {status_icon} **{upgrade.title}** ({upgrade.risk_level.value} risk)")
            lines.append("")
        
        # Model Changes
        if r.models_added or r.models_removed:
            lines.extend([
                f"## 📦 Model Catalog Changes",
                f"",
            ])
            if r.models_added:
                lines.append(f"### Added ({len(r.models_added)})")
                for model in r.models_added[:10]:
                    lines.append(f"- `{model.model_id}`")
                if len(r.models_added) > 10:
                    lines.append(f"- *...and {len(r.models_added) - 10} more*")
                lines.append("")
            if r.models_removed:
                lines.append(f"### Removed ({len(r.models_removed)})")
                for model in r.models_removed[:10]:
                    lines.append(f"- `{model.model_id}`")
                lines.append("")
        
        # Category Changes
        if r.category_changes:
            lines.extend([
                f"## 📁 Category Updates",
                f"",
            ])
            for cat in r.category_changes:
                icon = "➕" if cat.change_type == "added" else "➖" if cat.change_type == "removed" else "🔄"
                lines.append(f"- {icon} **{cat.display_name}** (`{cat.slug}`)")
            lines.append("")
        
        # Benchmark Results
        if r.benchmark_before or r.benchmark_after:
            lines.extend([
                f"## 📈 Benchmark Results",
                f"",
            ])
            if r.benchmark_before and r.benchmark_after:
                before = r.benchmark_before.overall_score
                after = r.benchmark_after.overall_score
                delta = after - before
                delta_icon = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
                lines.extend([
                    f"| Metric | Before | After | Change |",
                    f"|--------|--------|-------|--------|",
                    f"| Overall Score | {before:.2f} | {after:.2f} | {delta_icon} {delta:+.2f} |",
                    f"| Pass Rate | {r.benchmark_before.pass_rate:.1%} | {r.benchmark_after.pass_rate:.1%} | |",
                    f"",
                ])
            elif r.benchmark_before:
                lines.extend([
                    f"**Baseline Score:** {r.benchmark_before.overall_score:.2f}",
                    f"**Pass Rate:** {r.benchmark_before.pass_rate:.1%}",
                    f"",
                ])
        
        # Regression Alerts
        if r.regression_alerts:
            lines.extend([
                f"## ⚠️ Regression Alerts",
                f"",
            ])
            for alert in r.regression_alerts:
                severity = alert.get("severity", "unknown")
                category = alert.get("category", "unknown")
                lines.append(f"- **{severity.upper()}**: {category} - {alert.get('delta', 0):+.3f}")
            lines.append("")
        
        # Research Findings
        if r.research_findings:
            lines.extend([
                f"## 🔬 Research Highlights",
                f"",
            ])
            high_impact = [f for f in r.research_findings if f.get("potential_impact") == "high"]
            for finding in high_impact[:3]:
                lines.append(f"### {finding.get('title', 'Unknown')}")
                lines.append(f"*Source: {finding.get('source', 'Unknown')}*")
                lines.append(f"")
                lines.append(f"{finding.get('summary', '')[:200]}...")
                lines.append(f"")
        
        # Safety Notes
        if r.safety_notes:
            lines.extend([
                f"## 🛡️ Safety Notes",
                f"",
            ])
            for note in r.safety_notes:
                lines.append(f"- {note}")
            lines.append("")
        
        # Footer
        lines.extend([
            f"---",
            f"",
            f"*Report generated by LLMHive Weekly Improvement System*",
        ])
        
        return "\n".join(lines)


# =============================================================================
# API Endpoints for Cloud Scheduler
# =============================================================================

try:
    from fastapi import APIRouter, BackgroundTasks
    from pydantic import BaseModel
    
    router = APIRouter(prefix="/weekly", tags=["weekly-improvement"])
    
    class WeeklyRunRequest(BaseModel):
        """Request for weekly run."""
        dry_run: bool = False
        apply_safe_changes: bool = True
        run_benchmarks: bool = True
        full: bool = False  # Full weekly sync with rankings
    
    class WeeklyRunResponse(BaseModel):
        """Response from weekly run."""
        status: str
        message: str
        report_path: Optional[str] = None
        triggered_at: str
    
    _running = False
    
    @router.post("/run", response_model=WeeklyRunResponse)
    async def trigger_weekly_run(
        request: WeeklyRunRequest,
        background_tasks: BackgroundTasks,
    ) -> WeeklyRunResponse:
        """Trigger weekly improvement cycle.
        
        This endpoint is designed to be called by Cloud Scheduler.
        """
        global _running
        
        if _running:
            return WeeklyRunResponse(
                status="skipped",
                message="Weekly cycle already running",
                triggered_at=datetime.now(timezone.utc).isoformat(),
            )
        
        _running = True
        
        async def run_cycle():
            global _running
            try:
                orchestrator = WeeklyImprovementOrchestrator(
                    dry_run=request.dry_run,
                    apply_safe_changes=request.apply_safe_changes,
                    run_benchmarks=request.run_benchmarks,
                )
                await orchestrator.run_full_cycle()
            finally:
                _running = False
        
        background_tasks.add_task(run_cycle)
        
        return WeeklyRunResponse(
            status="triggered",
            message="Weekly improvement cycle started",
            triggered_at=datetime.now(timezone.utc).isoformat(),
        )
    
    @router.get("/status")
    async def get_weekly_status() -> dict:
        """Get status of weekly improvement system."""
        global _running
        
        orchestrator = WeeklyImprovementOrchestrator()
        
        # Find latest report
        reports = sorted(orchestrator.REPORTS_DIR.glob("*.json"), reverse=True)
        latest_report = None
        if reports:
            with open(reports[0]) as f:
                latest_report = json.load(f)
        
        return {
            "running": _running,
            "latest_report_date": latest_report["report_date"] if latest_report else None,
            "latest_safe_to_deploy": latest_report["safety"]["safe_to_deploy"] if latest_report else None,
        }

except ImportError:
    # FastAPI not available
    router = None


# =============================================================================
# CLI Entry Point
# =============================================================================

def cli_main():
    """CLI entry point for weekly improvement."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLMHive Weekly Improvement System")
    parser.add_argument("--run", action="store_true", help="Run full weekly cycle")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no changes)")
    parser.add_argument("--no-benchmarks", action="store_true", help="Skip benchmarks")
    parser.add_argument("--report-only", action="store_true", help="Generate report from latest data")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    if args.run or args.report_only:
        async def main():
            orchestrator = WeeklyImprovementOrchestrator(
                dry_run=args.dry_run,
                apply_safe_changes=not args.dry_run,
                run_benchmarks=not args.no_benchmarks,
            )
            report = await orchestrator.run_full_cycle()
            
            print("\n" + "=" * 60)
            print("WEEKLY IMPROVEMENT COMPLETE")
            print("=" * 60)
            print(f"Safe to deploy: {report.safe_to_deploy}")
            print(f"Models added: {len(report.models_added)}")
            print(f"Upgrades applied: {len(report.upgrades_applied)}")
            print(f"Upgrades gated: {len(report.upgrades_gated)}")
            if report.safety_notes:
                print("\nSafety Notes:")
                for note in report.safety_notes:
                    print(f"  - {note}")
        
        asyncio.run(main())
    else:
        parser.print_help()


if __name__ == "__main__":
    cli_main()

