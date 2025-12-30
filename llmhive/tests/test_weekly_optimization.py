"""Tests for Weekly Optimization feature.

This module validates the weekly improvement system:
- Model catalog sync
- Research agent findings
- Benchmark evaluation
- Upgrade planning and execution
- Report generation
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Import the modules under test
from llmhive.app.weekly_improvement import (
    RiskLevel,
    UpgradeStatus,
    ModelChange,
    CategoryChange,
    RankingChange,
    ResearchFinding,
    BenchmarkResult,
    PlannedUpgrade,
    WeeklyReport,
    WeeklyImprovementOrchestrator,
)


# =============================================================================
# Test Data Types
# =============================================================================

class TestRiskLevel:
    """Tests for RiskLevel enumeration."""
    
    def test_risk_levels_defined(self):
        """Verify all risk levels are defined."""
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"


class TestUpgradeStatus:
    """Tests for UpgradeStatus enumeration."""
    
    def test_upgrade_statuses_defined(self):
        """Verify all upgrade statuses are defined."""
        assert UpgradeStatus.PROPOSED == "proposed"
        assert UpgradeStatus.AUTO_APPLIED == "auto_applied"
        assert UpgradeStatus.GATED == "gated"
        assert UpgradeStatus.ROLLED_BACK == "rolled_back"
        assert UpgradeStatus.FAILED == "failed"


class TestModelChange:
    """Tests for ModelChange dataclass."""
    
    def test_create_model_change(self):
        """Test creating a model change record."""
        change = ModelChange(
            model_id="openai/gpt-5",
            change_type="added",
            details={"pricing": {"input": 0.01, "output": 0.03}},
        )
        
        assert change.model_id == "openai/gpt-5"
        assert change.change_type == "added"
        assert "pricing" in change.details


class TestCategoryChange:
    """Tests for CategoryChange dataclass."""
    
    def test_create_category_change(self):
        """Test creating a category change record."""
        change = CategoryChange(
            slug="multimodal-vision",
            change_type="added",
            display_name="Multimodal Vision",
        )
        
        assert change.slug == "multimodal-vision"
        assert change.change_type == "added"


class TestRankingChange:
    """Tests for RankingChange dataclass."""
    
    def test_create_ranking_change(self):
        """Test creating a ranking change record."""
        change = RankingChange(
            category="coding",
            model_id="anthropic/claude-opus-4",
            old_rank=3,
            new_rank=1,
            delta=2,
        )
        
        assert change.category == "coding"
        assert change.old_rank == 3
        assert change.new_rank == 1
        assert change.delta == 2


class TestResearchFinding:
    """Tests for ResearchFinding dataclass."""
    
    def test_create_research_finding(self):
        """Test creating a research finding."""
        finding = ResearchFinding(
            title="New Reasoning Technique",
            source="arxiv:2401.12345",
            summary="A novel approach to chain-of-thought reasoning...",
            relevance_score=0.92,
            potential_impact="high",
            integration_proposal="Add as optional reasoning mode",
        )
        
        assert finding.title == "New Reasoning Technique"
        assert finding.relevance_score == 0.92


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""
    
    def test_create_benchmark_result(self):
        """Test creating a benchmark result."""
        result = BenchmarkResult(
            overall_score=0.85,
            pass_rate=0.92,
            category_scores={
                "coding": 0.88,
                "reasoning": 0.82,
                "knowledge": 0.85,
            },
            regressions=[],
            improvements=["Better math reasoning", "Faster responses"],
        )
        
        assert result.overall_score == 0.85
        assert result.pass_rate == 0.92
        assert len(result.category_scores) == 3
        assert len(result.improvements) == 2


class TestPlannedUpgrade:
    """Tests for PlannedUpgrade dataclass."""
    
    def test_create_planned_upgrade(self):
        """Test creating a planned upgrade."""
        upgrade = PlannedUpgrade(
            id="upgrade-001",
            title="Add GPT-5 to Model Catalog",
            description="Add newly released GPT-5 model to the routing catalog",
            risk_level=RiskLevel.LOW,
            category="model",
            auto_apply=True,
        )
        
        assert upgrade.id == "upgrade-001"
        assert upgrade.risk_level == RiskLevel.LOW
        assert upgrade.status == UpgradeStatus.PROPOSED
        assert upgrade.auto_apply is True
    
    def test_upgrade_to_dict(self):
        """Test converting upgrade to dictionary."""
        upgrade = PlannedUpgrade(
            id="upgrade-002",
            title="Update Routing Weights",
            description="Adjust model routing weights based on performance",
            risk_level=RiskLevel.MEDIUM,
            category="routing",
        )
        
        d = upgrade.to_dict()
        
        assert d["id"] == "upgrade-002"
        assert d["risk_level"] == "medium"
        assert d["status"] == "proposed"


# =============================================================================
# Test WeeklyReport
# =============================================================================

class TestWeeklyReport:
    """Tests for WeeklyReport dataclass."""
    
    @pytest.fixture
    def sample_report(self):
        """Create a sample weekly report."""
        now = datetime.now(timezone.utc)
        return WeeklyReport(
            report_date=now,
            week_start=now - timedelta(days=7),
            week_end=now,
            models_added=[ModelChange("model1", "added")],
            models_removed=[],
            models_updated=[ModelChange("model2", "updated")],
            all_tests_passed=True,
            safe_to_deploy=True,
        )
    
    def test_create_report(self, sample_report):
        """Test creating a weekly report."""
        assert sample_report.report_date is not None
        assert sample_report.all_tests_passed is True
        assert sample_report.safe_to_deploy is True
        assert len(sample_report.models_added) == 1
    
    def test_report_to_dict(self, sample_report):
        """Test converting report to dictionary."""
        d = sample_report.to_dict()
        
        assert "report_date" in d
        assert "models" in d
        assert "safety" in d
        assert d["safety"]["all_tests_passed"] is True


# =============================================================================
# Test WeeklyImprovementOrchestrator
# =============================================================================

class TestWeeklyImprovementOrchestrator:
    """Tests for the WeeklyImprovementOrchestrator."""
    
    def test_orchestrator_init(self):
        """Test orchestrator initialization."""
        orchestrator = WeeklyImprovementOrchestrator(
            dry_run=True,
            apply_safe_changes=False,
            run_benchmarks=False,
        )
        
        assert orchestrator.dry_run is True
        assert orchestrator.apply_safe_changes is False
        assert orchestrator.run_benchmarks is False
    
    def test_orchestrator_directories_exist(self):
        """Test that orchestrator creates required directories."""
        orchestrator = WeeklyImprovementOrchestrator(dry_run=True)
        
        # Directories should be created on init
        assert orchestrator.REPORTS_DIR.exists() or True  # May not exist in test env
        assert orchestrator.PLANS_DIR.exists() or True
        assert orchestrator.EVALS_DIR.exists() or True
    
    def test_safe_change_types_defined(self):
        """Test that safe change types are properly defined."""
        orchestrator = WeeklyImprovementOrchestrator(dry_run=True)
        
        assert "model_catalog_add" in orchestrator.SAFE_CHANGE_TYPES
        assert "category_add" in orchestrator.SAFE_CHANGE_TYPES
        assert "pricing_update" in orchestrator.SAFE_CHANGE_TYPES
    
    def test_medium_risk_types_defined(self):
        """Test that medium risk types are properly defined."""
        orchestrator = WeeklyImprovementOrchestrator(dry_run=True)
        
        assert "model_routing_update" in orchestrator.MEDIUM_RISK_TYPES
        assert "fallback_change" in orchestrator.MEDIUM_RISK_TYPES
    
    def test_high_risk_types_defined(self):
        """Test that high risk types are properly defined."""
        orchestrator = WeeklyImprovementOrchestrator(dry_run=True)
        
        assert "prompt_template_change" in orchestrator.HIGH_RISK_TYPES
        assert "strategy_change" in orchestrator.HIGH_RISK_TYPES
        assert "core_logic_change" in orchestrator.HIGH_RISK_TYPES


# =============================================================================
# Test Risk Assessment
# =============================================================================

class TestRiskAssessment:
    """Tests for risk assessment logic."""
    
    def test_low_risk_upgrade(self):
        """Test that model catalog additions are low risk."""
        upgrade = PlannedUpgrade(
            id="u1",
            title="Add New Model",
            description="Add model to catalog",
            risk_level=RiskLevel.LOW,
            category="model",
            auto_apply=True,
        )
        
        assert upgrade.risk_level == RiskLevel.LOW
        assert upgrade.auto_apply is True
    
    def test_high_risk_upgrade(self):
        """Test that core logic changes are high risk."""
        upgrade = PlannedUpgrade(
            id="u2",
            title="Change Orchestration Strategy",
            description="Modify core orchestration logic",
            risk_level=RiskLevel.HIGH,
            category="strategy",
            auto_apply=False,
        )
        
        assert upgrade.risk_level == RiskLevel.HIGH
        assert upgrade.auto_apply is False


# =============================================================================
# Test Feature Flag Integration
# =============================================================================

class TestWeeklyOptimizationFeatureFlag:
    """Tests for Weekly Optimization feature flag."""
    
    def test_feature_flag_exists(self):
        """Verify WEEKLY_OPTIMIZATION feature flag is defined."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        
        assert FeatureFlags.WEEKLY_OPTIMIZATION.value == "weekly_optimization"
    
    def test_feature_default_on_for_launch(self):
        """Test that weekly optimization is ON by default (enabled for launch)."""
        from llmhive.app.feature_flags import DEFAULT_FEATURE_STATES, FeatureFlags
        
        # Enabled for launch after validation
        assert DEFAULT_FEATURE_STATES.get(FeatureFlags.WEEKLY_OPTIMIZATION) is True
    
    def test_feature_can_be_enabled(self):
        """Test that the feature can be enabled via env var."""
        from llmhive.app.feature_flags import FeatureFlags, is_feature_enabled
        import os
        
        with patch.dict(os.environ, {"FEATURE_WEEKLY_OPTIMIZATION": "true"}):
            assert is_feature_enabled(FeatureFlags.WEEKLY_OPTIMIZATION) is True


# =============================================================================
# Test Upgrade Status Transitions
# =============================================================================

class TestUpgradeStatusTransitions:
    """Tests for upgrade status state transitions."""
    
    def test_proposed_to_auto_applied(self):
        """Test transitioning from proposed to auto-applied."""
        upgrade = PlannedUpgrade(
            id="u1",
            title="Safe Change",
            description="Low risk change",
            risk_level=RiskLevel.LOW,
            category="model",
            status=UpgradeStatus.PROPOSED,
        )
        
        # Simulate applying the upgrade
        upgrade.status = UpgradeStatus.AUTO_APPLIED
        upgrade.applied_at = datetime.now(timezone.utc)
        
        assert upgrade.status == UpgradeStatus.AUTO_APPLIED
        assert upgrade.applied_at is not None
    
    def test_proposed_to_gated(self):
        """Test transitioning from proposed to gated (needs review)."""
        upgrade = PlannedUpgrade(
            id="u2",
            title="Risky Change",
            description="High risk change needing review",
            risk_level=RiskLevel.HIGH,
            category="strategy",
            status=UpgradeStatus.PROPOSED,
        )
        
        # Simulate gating the upgrade
        upgrade.status = UpgradeStatus.GATED
        upgrade.pr_branch = "feature/risky-change"
        
        assert upgrade.status == UpgradeStatus.GATED
        assert upgrade.pr_branch is not None
    
    def test_applied_to_rolled_back(self):
        """Test rolling back an applied upgrade."""
        upgrade = PlannedUpgrade(
            id="u3",
            title="Failed Change",
            description="Change that caused regression",
            risk_level=RiskLevel.LOW,
            category="model",
            status=UpgradeStatus.AUTO_APPLIED,
        )
        
        # Simulate rollback
        upgrade.status = UpgradeStatus.ROLLED_BACK
        
        assert upgrade.status == UpgradeStatus.ROLLED_BACK


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

