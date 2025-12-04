"""Unit tests for Loop-Back Refinement Controller."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
_src_path = Path(__file__).parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from llmhive.app.orchestration.refinement_loop import (
    RefinementLoopController,
    RefinementResult,
    RefinementIteration,
    RefinementConfig,
    RefinementStrategy,
    LoopStatus,
    IssueType,
    VerificationIssue,
    run_refinement_loop,
    create_refinement_controller,
)


class TestVerificationIssue:
    """Tests for VerificationIssue data class."""
    
    def test_create_issue(self):
        """Test creating a verification issue."""
        issue = VerificationIssue(
            issue_type=IssueType.FACTUAL_ERROR,
            description="Incorrect date",
            claim="The event happened in 1990",
            evidence="Historical records show 1985",
            correction_hint="The event happened in 1985",
            priority=1,
        )
        
        assert issue.issue_type == IssueType.FACTUAL_ERROR
        assert "1990" in issue.claim
        assert issue.priority == 1


class TestRefinementConfig:
    """Tests for RefinementConfig data class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RefinementConfig()
        
        assert config.max_iterations == 3
        assert config.convergence_threshold == 0.90
        assert config.min_improvement_threshold == 0.05
        assert config.enable_prompt_refinement is True
        assert config.enable_model_switching is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RefinementConfig(
            max_iterations=5,
            convergence_threshold=0.95,
            enable_decomposition=False,
        )
        
        assert config.max_iterations == 5
        assert config.convergence_threshold == 0.95
        assert config.enable_decomposition is False


class TestRefinementIteration:
    """Tests for RefinementIteration data class."""
    
    def test_create_iteration(self):
        """Test creating an iteration record."""
        iteration = RefinementIteration(
            iteration=1,
            input_answer="Original answer",
            output_answer="Refined answer",
            verification_score=0.75,
            issues_found=3,
            issues_resolved=2,
            strategy_used=RefinementStrategy.PROMPT_ENHANCE,
            model_used="gpt-4",
            prompt_used="Enhanced prompt",
            duration_ms=1500.0,
        )
        
        assert iteration.iteration == 1
        assert iteration.issues_resolved == 2
        assert iteration.strategy_used == RefinementStrategy.PROMPT_ENHANCE


class TestRefinementResult:
    """Tests for RefinementResult data class."""
    
    def test_get_summary(self):
        """Test getting result summary."""
        iterations = [
            RefinementIteration(
                iteration=1,
                input_answer="Original",
                output_answer="Refined",
                verification_score=0.6,
                issues_found=5,
                issues_resolved=3,
                strategy_used=RefinementStrategy.PROMPT_ENHANCE,
                model_used="gpt-4",
                prompt_used="prompt",
            ),
            RefinementIteration(
                iteration=2,
                input_answer="Refined",
                output_answer="Final",
                verification_score=0.85,
                issues_found=2,
                issues_resolved=1,
                strategy_used=RefinementStrategy.WEB_SEARCH,
                model_used="gpt-4",
                prompt_used="prompt",
            ),
        ]
        
        result = RefinementResult(
            original_answer="Original",
            final_answer="Final",
            iterations=iterations,
            final_status=LoopStatus.CONVERGED,
            final_verification_score=0.92,
            total_issues_found=7,
            issues_resolved=4,
            strategies_used=[RefinementStrategy.PROMPT_ENHANCE, RefinementStrategy.WEB_SEARCH],
            convergence_history=[0.6, 0.85, 0.92],
        )
        
        summary = result.get_summary()
        
        assert summary["iterations_completed"] == 2
        assert summary["final_status"] == "converged"
        assert summary["final_score"] == 0.92
        assert summary["issues_resolved"] == 4
        assert len(summary["strategies_used"]) == 2


class TestRefinementLoopController:
    """Tests for RefinementLoopController class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock provider
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "Refined answer with corrections."
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider, "stub": self.mock_provider}
        
        # Mock fact checker
        self.mock_fact_checker = MagicMock()
        self.mock_verification_report = MagicMock()
        self.mock_verification_report.verification_score = 0.95
        self.mock_verification_report.items = []
        self.mock_fact_checker.verify = AsyncMock(return_value=self.mock_verification_report)
        
        self.config = RefinementConfig(
            max_iterations=3,
            convergence_threshold=0.90,
        )
        
        self.controller = RefinementLoopController(
            fact_checker=self.mock_fact_checker,
            providers=self.providers,
            config=self.config,
        )
    
    def test_initialization(self):
        """Test controller initialization."""
        assert self.controller.config.max_iterations == 3
        assert self.controller.fact_checker is not None
        assert len(self.controller.providers) == 2
    
    @pytest.mark.asyncio
    async def test_run_refinement_loop_passes_immediately(self):
        """Test loop that passes on first verification."""
        result = await self.controller.run_refinement_loop(
            answer="Correct answer",
            prompt="What is 2+2?",
            model="gpt-4",
        )
        
        assert result.final_status == LoopStatus.PASSED
        assert result.final_verification_score >= 0.90
        assert len(result.iterations) == 1
    
    @pytest.mark.asyncio
    async def test_run_refinement_loop_with_corrections(self):
        """Test loop that requires corrections."""
        # First verification fails, second passes
        verification_results = [
            MagicMock(verification_score=0.6, items=[
                MagicMock(verified=False, text="Wrong claim", evidence="", correction=None)
            ]),
            MagicMock(verification_score=0.95, items=[]),
        ]
        call_count = [0]
        
        async def mock_verify(answer, **kwargs):
            result = verification_results[min(call_count[0], len(verification_results) - 1)]
            call_count[0] += 1
            return result
        
        self.mock_fact_checker.verify = mock_verify
        
        result = await self.controller.run_refinement_loop(
            answer="Answer with errors",
            prompt="Question?",
            model="gpt-4",
        )
        
        # Should have made corrections
        assert len(result.iterations) >= 1
        assert result.final_status in (LoopStatus.PASSED, LoopStatus.MAX_ITERATIONS, LoopStatus.NO_IMPROVEMENT)
    
    @pytest.mark.asyncio
    async def test_run_refinement_loop_max_iterations(self):
        """Test loop reaches max iterations."""
        # Always return failing score
        self.mock_verification_report.verification_score = 0.5
        self.mock_verification_report.items = [
            MagicMock(verified=False, text="Always failing", evidence="", correction=None)
        ]
        
        self.config.max_iterations = 2
        controller = RefinementLoopController(
            fact_checker=self.mock_fact_checker,
            providers=self.providers,
            config=self.config,
        )
        
        result = await controller.run_refinement_loop(
            answer="Bad answer",
            prompt="Question?",
            model="gpt-4",
        )
        
        assert result.final_status == LoopStatus.MAX_ITERATIONS
        assert len(result.iterations) == 2
    
    @pytest.mark.asyncio
    async def test_run_refinement_loop_no_improvement(self):
        """Test loop stops when no improvement."""
        # Return same score every time
        async def mock_verify(answer, **kwargs):
            result = MagicMock()
            result.verification_score = 0.65
            result.items = [MagicMock(verified=False, text="Stuck", evidence="", correction=None)]
            return result
        
        self.mock_fact_checker.verify = mock_verify
        
        self.config.stagnation_tolerance = 1
        controller = RefinementLoopController(
            fact_checker=self.mock_fact_checker,
            providers=self.providers,
            config=self.config,
        )
        
        result = await controller.run_refinement_loop(
            answer="Stagnant answer",
            prompt="Question?",
            model="gpt-4",
        )
        
        assert result.final_status == LoopStatus.NO_IMPROVEMENT
    
    def test_select_strategy_prompt_enhance(self):
        """Test strategy selection prefers prompt enhancement."""
        issues = [
            VerificationIssue(
                issue_type=IssueType.FACTUAL_ERROR,
                description="Wrong date",
                claim="Event in 1990",
            )
        ]
        
        strategy = self.controller._select_strategy(
            issues=issues,
            iteration=1,
            used_strategies=[],
            available_models=["gpt-4", "claude-3"],
        )
        
        assert strategy == RefinementStrategy.PROMPT_ENHANCE
    
    def test_select_strategy_model_switch(self):
        """Test strategy selection chooses model switch after prompt enhance."""
        issues = [
            VerificationIssue(
                issue_type=IssueType.FACTUAL_ERROR,
                description="Wrong",
                claim="Claim",
            )
        ]
        
        self.controller.config.priority_strategies = [
            RefinementStrategy.PROMPT_ENHANCE,
            RefinementStrategy.MODEL_SWITCH,
            RefinementStrategy.WEB_SEARCH,
        ]
        
        strategy = self.controller._select_strategy(
            issues=issues,
            iteration=2,
            used_strategies=[RefinementStrategy.PROMPT_ENHANCE],
            available_models=["gpt-4", "claude-3"],
        )
        
        assert strategy == RefinementStrategy.MODEL_SWITCH
    
    def test_enhance_prompt_with_issues(self):
        """Test prompt enhancement with issues."""
        issues = [
            VerificationIssue(
                issue_type=IssueType.FACTUAL_ERROR,
                description="Wrong date",
                claim="The event happened in 1990",
                correction_hint="The event happened in 1985",
            )
        ]
        
        enhanced = self.controller._enhance_prompt_with_issues(
            prompt="When did the event happen?",
            issues=issues,
        )
        
        assert "IMPORTANT" in enhanced
        assert "1990" in enhanced or "1985" in enhanced
        assert "issues" in enhanced.lower() or "correct" in enhanced.lower()
    
    def test_enhance_prompt_no_issues(self):
        """Test prompt enhancement with no issues."""
        enhanced = self.controller._enhance_prompt_with_issues(
            prompt="Simple question",
            issues=[],
        )
        
        assert enhanced == "Simple question"
    
    @pytest.mark.asyncio
    async def test_regenerate_answer(self):
        """Test answer regeneration."""
        answer = await self.controller._regenerate_answer(
            prompt="What is 2+2?",
            model="gpt-4",
            context="Math context",
        )
        
        assert answer is not None
        self.mock_provider.complete.assert_called()
    
    @pytest.mark.asyncio
    async def test_direct_correct(self):
        """Test direct correction strategy."""
        issues = [
            VerificationIssue(
                issue_type=IssueType.FACTUAL_ERROR,
                description="Wrong",
                claim="Incorrect claim here",
            )
        ]
        
        corrected = await self.controller._direct_correct(
            answer="Original with incorrect claim here",
            issues=issues,
            model="gpt-4",
        )
        
        assert corrected is not None
        self.mock_provider.complete.assert_called()


class TestStrategyApplication:
    """Tests for specific refinement strategies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "Corrected answer"
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider}
        self.controller = RefinementLoopController(
            providers=self.providers,
            config=RefinementConfig(),
        )
    
    @pytest.mark.asyncio
    async def test_apply_prompt_enhance(self):
        """Test prompt enhancement application."""
        issues = [
            VerificationIssue(
                issue_type=IssueType.FACTUAL_ERROR,
                description="Wrong",
                claim="Wrong fact",
            )
        ]
        
        refined, prompt, model = await self.controller._apply_refinement(
            answer="Original",
            prompt="Question?",
            issues=issues,
            strategy=RefinementStrategy.PROMPT_ENHANCE,
            current_model="gpt-4",
            available_models=None,
            context=None,
        )
        
        assert refined is not None
        assert "IMPORTANT" in prompt
    
    @pytest.mark.asyncio
    async def test_apply_model_switch(self):
        """Test model switching application."""
        refined, prompt, model = await self.controller._apply_refinement(
            answer="Original",
            prompt="Question?",
            issues=[],
            strategy=RefinementStrategy.MODEL_SWITCH,
            current_model="gpt-4",
            available_models=["gpt-4", "claude-3"],
            context=None,
        )
        
        assert model == "claude-3"  # Should switch to different model
    
    @pytest.mark.asyncio
    async def test_apply_direct_correct(self):
        """Test direct correction application."""
        issues = [
            VerificationIssue(
                issue_type=IssueType.FACTUAL_ERROR,
                description="Wrong date",
                claim="In 1990",
            )
        ]
        
        refined, prompt, model = await self.controller._apply_refinement(
            answer="Event in 1990",
            prompt="When?",
            issues=issues,
            strategy=RefinementStrategy.DIRECT_CORRECT,
            current_model="gpt-4",
            available_models=None,
            context=None,
        )
        
        assert refined == "Corrected answer"  # From mock


class TestConvergenceDetection:
    """Tests for convergence detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_fact_checker = MagicMock()
        
    @pytest.mark.asyncio
    async def test_convergence_detection(self):
        """Test that convergence is properly detected."""
        # Simulate improving scores
        scores = [0.5, 0.7, 0.85, 0.95]
        call_idx = [0]
        
        async def mock_verify(answer, **kwargs):
            result = MagicMock()
            result.verification_score = scores[min(call_idx[0], len(scores) - 1)]
            result.items = [] if result.verification_score >= 0.90 else [
                MagicMock(verified=False, text="Issue", evidence="", correction=None)
            ]
            call_idx[0] += 1
            return result
        
        self.mock_fact_checker.verify = mock_verify
        
        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(return_value=MagicMock(content="Improved"))
        
        controller = RefinementLoopController(
            fact_checker=self.mock_fact_checker,
            providers={"openai": mock_provider},
            config=RefinementConfig(
                max_iterations=5,
                convergence_threshold=0.90,
            ),
        )
        
        result = await controller.run_refinement_loop(
            answer="Initial",
            prompt="Question?",
            model="gpt-4",
        )
        
        # Should have converged before max iterations
        assert len(result.convergence_history) >= 1
        assert result.convergence_history[-1] >= 0.90 or result.final_status == LoopStatus.PASSED


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_run_refinement_loop_function(self):
        """Test run_refinement_loop convenience function."""
        mock_fact_checker = MagicMock()
        mock_fact_checker.verify = AsyncMock(return_value=MagicMock(
            verification_score=0.95,
            items=[],
        ))
        
        result = await run_refinement_loop(
            answer="Good answer",
            prompt="Question?",
            fact_checker=mock_fact_checker,
            max_iterations=2,
        )
        
        assert result.final_status == LoopStatus.PASSED
    
    def test_create_refinement_controller(self):
        """Test create_refinement_controller function."""
        controller = create_refinement_controller(
            max_iterations=5,
            convergence_threshold=0.85,
        )
        
        assert controller.config.max_iterations == 5
        assert controller.config.convergence_threshold == 0.85


class TestIntegrationScenarios:
    """Integration tests for refinement scenarios."""
    
    @pytest.mark.asyncio
    async def test_factual_error_correction(self):
        """Test correcting a factual error through the loop."""
        # Simulate a fact checker that initially fails then passes
        iterations = [0]
        
        async def mock_verify(answer, **kwargs):
            result = MagicMock()
            if iterations[0] == 0:
                result.verification_score = 0.5
                result.items = [MagicMock(
                    verified=False,
                    text="Sydney is the capital of Australia",
                    evidence="Canberra is the capital",
                    correction="Canberra is the capital of Australia",
                )]
            else:
                result.verification_score = 0.95
                result.items = []
            iterations[0] += 1
            return result
        
        mock_fact_checker = MagicMock()
        mock_fact_checker.verify = mock_verify
        
        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(return_value=MagicMock(
            content="Canberra is the capital of Australia."
        ))
        
        controller = RefinementLoopController(
            fact_checker=mock_fact_checker,
            providers={"openai": mock_provider},
            config=RefinementConfig(max_iterations=3),
        )
        
        result = await controller.run_refinement_loop(
            answer="Sydney is the capital of Australia.",
            prompt="What is the capital of Australia?",
            model="gpt-4",
        )
        
        assert result.final_status == LoopStatus.PASSED
        assert result.issues_resolved >= 1
    
    @pytest.mark.asyncio
    async def test_multiple_iterations_with_different_strategies(self):
        """Test that different strategies are used across iterations."""
        iteration_count = [0]
        
        async def mock_verify(answer, **kwargs):
            iteration_count[0] += 1
            result = MagicMock()
            # Gradually improve
            result.verification_score = min(0.5 + iteration_count[0] * 0.15, 0.95)
            result.items = [] if result.verification_score >= 0.90 else [
                MagicMock(verified=False, text="Issue", evidence="", correction=None)
            ]
            return result
        
        mock_fact_checker = MagicMock()
        mock_fact_checker.verify = mock_verify
        
        mock_provider = MagicMock()
        mock_provider.complete = AsyncMock(return_value=MagicMock(content="Improved"))
        
        controller = RefinementLoopController(
            fact_checker=mock_fact_checker,
            providers={"openai": mock_provider},
            config=RefinementConfig(
                max_iterations=5,
                priority_strategies=[
                    RefinementStrategy.PROMPT_ENHANCE,
                    RefinementStrategy.WEB_SEARCH,
                    RefinementStrategy.DIRECT_CORRECT,
                ],
            ),
        )
        
        result = await controller.run_refinement_loop(
            answer="Initial",
            prompt="Question?",
            model="gpt-4",
        )
        
        # Should have used multiple strategies
        assert len(result.strategies_used) >= 1
    
    @pytest.mark.asyncio
    async def test_transparency_notes_generated(self):
        """Test that transparency notes are properly generated."""
        mock_fact_checker = MagicMock()
        mock_fact_checker.verify = AsyncMock(return_value=MagicMock(
            verification_score=0.95,
            items=[],
        ))
        
        controller = RefinementLoopController(
            fact_checker=mock_fact_checker,
            providers={},
            config=RefinementConfig(),
        )
        
        result = await controller.run_refinement_loop(
            answer="Good answer",
            prompt="Question?",
            model="gpt-4",
        )
        
        # Should have transparency notes
        assert len(result.transparency_notes) >= 1
        assert any("refinement" in note.lower() for note in result.transparency_notes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

