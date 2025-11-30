"""Unit tests for Prompt Diffusion and Multi-Agent Refinement."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from llmhive.src.llmhive.app.orchestration.prompt_diffusion import (
    PromptDiffusion,
    PromptVersion,
    DiffusionResult,
    RefinementStep,
    RefinerRole,
    AmbiguityAnalysis,
    ROLE_PROMPTS,
    refine_prompt,
    quick_clarify,
)


class TestRefinerRoles:
    """Tests for refiner role definitions."""
    
    def test_all_roles_have_prompts(self):
        """Test all roles have prompt definitions."""
        for role in RefinerRole:
            assert role in ROLE_PROMPTS
            assert len(ROLE_PROMPTS[role]) > 50
    
    def test_clarifier_role_focuses_on_ambiguity(self):
        """Test clarifier role prompt mentions ambiguity."""
        prompt = ROLE_PROMPTS[RefinerRole.CLARIFIER]
        assert "ambig" in prompt.lower()
        assert "clarif" in prompt.lower()
    
    def test_expander_role_focuses_on_context(self):
        """Test expander role prompt mentions context."""
        prompt = ROLE_PROMPTS[RefinerRole.EXPANDER]
        assert "context" in prompt.lower()
        assert "example" in prompt.lower()
    
    def test_critic_role_focuses_on_weaknesses(self):
        """Test critic role prompt mentions weaknesses."""
        prompt = ROLE_PROMPTS[RefinerRole.CRITIC]
        assert "weakness" in prompt.lower() or "gap" in prompt.lower()
    
    def test_synthesizer_role_focuses_on_combining(self):
        """Test synthesizer role prompt mentions combining."""
        prompt = ROLE_PROMPTS[RefinerRole.SYNTHESIZER]
        assert "combine" in prompt.lower() or "integrat" in prompt.lower()


class TestPromptVersion:
    """Tests for PromptVersion data class."""
    
    def test_create_version(self):
        """Test creating a prompt version."""
        version = PromptVersion(
            version=1,
            prompt="Test prompt",
            author="gpt-4",
            role=RefinerRole.CLARIFIER,
            score=0.8,
            improvements=["Added clarity"],
        )
        
        assert version.version == 1
        assert version.prompt == "Test prompt"
        assert version.role == RefinerRole.CLARIFIER
        assert version.score == 0.8
    
    def test_version_with_parent(self):
        """Test version with parent reference."""
        version = PromptVersion(
            version=2,
            prompt="Refined prompt",
            author="claude-3",
            parent_version=1,
        )
        
        assert version.parent_version == 1


class TestDiffusionResult:
    """Tests for DiffusionResult data class."""
    
    def test_get_refinement_summary(self):
        """Test getting refinement summary."""
        versions = [
            PromptVersion(
                version=0,
                prompt="Original",
                author="user",
                improvements=[],
            ),
            PromptVersion(
                version=1,
                prompt="Refined",
                author="gpt-4",
                role=RefinerRole.CLARIFIER,
                improvements=["Added clarity", "Resolved ambiguity"],
            ),
        ]
        
        steps = [
            RefinementStep(
                role=RefinerRole.CLARIFIER,
                model="gpt-4",
                input_prompt="Original",
                output_prompt="Refined",
                score=0.85,
                reasoning="Added specific details",
            )
        ]
        
        result = DiffusionResult(
            original_prompt="Original",
            final_prompt="Refined",
            versions=versions,
            refinement_steps=steps,
            convergence_score=0.9,
            rounds_completed=1,
            best_version=versions[1],
            clarifications_added=["What specific type?"],
        )
        
        summary = result.get_refinement_summary()
        
        assert summary["original_prompt"] == "Original"
        assert summary["final_prompt"] == "Refined"
        assert summary["rounds_completed"] == 1
        assert summary["convergence_score"] == 0.9
        assert "Added clarity" in summary["improvements"]
        assert len(summary["refiners_used"]) == 1
        assert summary["refiners_used"][0]["role"] == "clarifier"


class TestPromptDiffusion:
    """Tests for PromptDiffusion class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock provider
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "REFINED PROMPT: This is a refined and clearer prompt."
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider, "stub": self.mock_provider}
        self.diffusion = PromptDiffusion(
            providers=self.providers,
            max_rounds=2,
            convergence_threshold=0.85,
        )
    
    def test_initialization(self):
        """Test diffusion initialization."""
        assert self.diffusion.max_rounds == 2
        assert self.diffusion.convergence_threshold == 0.85
        assert len(self.diffusion.providers) == 2
    
    def test_default_roles(self):
        """Test default refiner roles."""
        assert RefinerRole.CLARIFIER in self.diffusion.DEFAULT_ROLES
        assert RefinerRole.EXPANDER in self.diffusion.DEFAULT_ROLES
        assert RefinerRole.SYNTHESIZER in self.diffusion.DEFAULT_ROLES
    
    @pytest.mark.asyncio
    async def test_diffuse_basic(self):
        """Test basic diffusion process."""
        # Mock scoring to return good scores
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            if "rate" in prompt.lower() or "score" in prompt.lower():
                result.content = "0.85"
            else:
                result.content = "REFINED PROMPT: A clearer version of the original prompt with added specificity."
            return result
        
        self.mock_provider.complete = mock_complete
        
        result = await self.diffusion.diffuse(
            initial_prompt="What is the capital?",
            models=["gpt-4"],
            analyze_ambiguity=False,
        )
        
        assert result is not None
        assert result.original_prompt == "What is the capital?"
        assert result.final_prompt != ""
        assert len(result.versions) >= 1
        assert result.rounds_completed >= 0
    
    @pytest.mark.asyncio
    async def test_diffuse_with_context(self):
        """Test diffusion with context."""
        result = await self.diffusion.diffuse(
            initial_prompt="Explain the concept",
            models=["gpt-4"],
            context="For a beginner audience",
            analyze_ambiguity=False,
        )
        
        assert result is not None
        # Context should influence refinement
        assert result.final_prompt is not None
    
    @pytest.mark.asyncio
    async def test_diffuse_with_domain(self):
        """Test diffusion with domain specification."""
        result = await self.diffusion.diffuse(
            initial_prompt="How to optimize?",
            models=["gpt-4"],
            domain="machine learning",
            analyze_ambiguity=False,
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_quick_refine(self):
        """Test quick single-pass refinement."""
        refined, score = await self.diffusion.quick_refine(
            prompt="Explain this",
            model="gpt-4",
            focus=RefinerRole.CLARIFIER,
        )
        
        assert refined is not None
        assert isinstance(score, float)
    
    @pytest.mark.asyncio
    async def test_quick_refine_default_focus(self):
        """Test quick refinement with default focus."""
        refined, score = await self.diffusion.quick_refine(
            prompt="Help me understand",
            model="gpt-4",
        )
        
        assert refined is not None
    
    def test_extract_refined_prompt_with_marker(self):
        """Test extracting refined prompt with explicit marker."""
        content = """
        Reasoning: I improved clarity and added examples.
        REFINED PROMPT: What is the capital city of France, and what is it known for?
        """
        
        extracted = self.diffusion._extract_refined_prompt(content)
        
        assert "capital city of France" in extracted
        assert "Reasoning" not in extracted
    
    def test_extract_refined_prompt_quoted(self):
        """Test extracting refined prompt from quotes."""
        content = 'Here is the refined version: "A clearer and more specific prompt here."'
        
        extracted = self.diffusion._extract_refined_prompt(content)
        
        assert "clearer" in extracted.lower() or "specific" in extracted.lower()
    
    def test_extract_refined_prompt_plain(self):
        """Test extracting when no special format."""
        content = "A straightforward improved prompt without any markers."
        
        extracted = self.diffusion._extract_refined_prompt(content)
        
        assert len(extracted) > 0
    
    def test_extract_reasoning(self):
        """Test extracting reasoning from response."""
        content = """
        Reasoning: Added specific context and examples to make the prompt clearer.
        REFINED PROMPT: The improved prompt here.
        """
        
        reasoning = self.diffusion._extract_reasoning(content)
        
        assert "context" in reasoning.lower() or "example" in reasoning.lower()
    
    def test_extract_improvements_longer(self):
        """Test detecting length increase improvement."""
        original = "Short prompt"
        refined = "A much longer prompt with additional context and specific requirements"
        
        improvements = self.diffusion._extract_improvements(original, refined)
        
        assert any("detail" in imp.lower() for imp in improvements)
    
    def test_extract_improvements_concise(self):
        """Test detecting conciseness improvement."""
        original = "A very long and verbose prompt with lots of unnecessary words"
        refined = "Concise prompt"
        
        improvements = self.diffusion._extract_improvements(original, refined)
        
        assert any("concise" in imp.lower() for imp in improvements)
    
    def test_extract_improvements_examples(self):
        """Test detecting added examples."""
        original = "Explain the concept"
        refined = "Explain the concept. For example, consider case X."
        
        improvements = self.diffusion._extract_improvements(original, refined)
        
        assert any("example" in imp.lower() for imp in improvements)
    
    def test_calculate_convergence_initial(self):
        """Test convergence with single version."""
        versions = [PromptVersion(version=0, prompt="Test", author="user")]
        
        convergence = self.diffusion._calculate_convergence(versions)
        
        assert convergence == 0.0
    
    def test_calculate_convergence_similar(self):
        """Test convergence with similar versions."""
        versions = [
            PromptVersion(version=0, prompt="What is the capital of France?", author="user", score=0.5),
            PromptVersion(version=1, prompt="What is the capital city of France?", author="gpt-4", score=0.8),
        ]
        
        convergence = self.diffusion._calculate_convergence(versions)
        
        assert convergence > 0.5  # Similar prompts should show convergence
    
    def test_calculate_convergence_different(self):
        """Test convergence with very different versions."""
        versions = [
            PromptVersion(version=0, prompt="ABC", author="user", score=0.5),
            PromptVersion(version=1, prompt="XYZ completely different", author="gpt-4", score=0.6),
        ]
        
        convergence = self.diffusion._calculate_convergence(versions)
        
        # Lower convergence for different prompts
        assert convergence < 0.8
    
    def test_select_provider_openai(self):
        """Test provider selection for GPT models."""
        provider = self.diffusion._select_provider("gpt-4")
        assert provider == self.providers["openai"]
    
    def test_select_provider_fallback(self):
        """Test provider fallback."""
        provider = self.diffusion._select_provider("unknown-model")
        assert provider in self.providers.values()


class TestAmbiguityAnalysis:
    """Tests for ambiguity analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.providers = {"openai": self.mock_provider}
        self.diffusion = PromptDiffusion(providers=self.providers)
    
    @pytest.mark.asyncio
    async def test_analyze_ambiguity(self):
        """Test ambiguity analysis."""
        mock_result = MagicMock()
        mock_result.content = """
        AMBIGUITIES:
        - "Capital" could mean city or financial capital
        - No country specified
        
        SUGGESTED_CLARIFICATIONS:
        - Specify the country
        - Clarify if asking about capital city
        
        CLARITY_SCORE: 0.6
        NEEDS_USER_INPUT: NO
        """
        self.mock_provider.complete = AsyncMock(return_value=mock_result)
        
        analysis = await self.diffusion._analyze_ambiguity(
            "What is the capital?",
            "gpt-4"
        )
        
        assert len(analysis.ambiguities) >= 1
        assert analysis.clarity_score == 0.6
        assert analysis.needs_user_input is False
    
    def test_parse_ambiguity_analysis(self):
        """Test parsing ambiguity analysis response."""
        content = """
        AMBIGUITIES:
        - Term X is unclear
        - Missing context for Y
        
        SUGGESTED_CLARIFICATIONS:
        - Define X clearly
        - Add context about Y
        
        CLARITY_SCORE: 0.7
        NEEDS_USER_INPUT: YES
        """
        
        analysis = self.diffusion._parse_ambiguity_analysis(content)
        
        assert len(analysis.ambiguities) == 2
        assert len(analysis.suggested_clarifications) == 2
        assert analysis.clarity_score == 0.7
        assert analysis.needs_user_input is True


class TestRoleBasedRefinement:
    """Tests for role-based refinement."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "REFINED PROMPT: Improved version"
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider}
        self.diffusion = PromptDiffusion(providers=self.providers)
    
    def test_build_role_prompt_clarifier(self):
        """Test building clarifier role prompt."""
        prompt = self.diffusion._build_role_prompt(
            "Test prompt",
            RefinerRole.CLARIFIER,
            round_num=1,
        )
        
        assert "Clarification Specialist" in prompt
        assert "Test prompt" in prompt
        assert "Round 1" in prompt
    
    def test_build_role_prompt_with_context(self):
        """Test building role prompt with context."""
        prompt = self.diffusion._build_role_prompt(
            "Test prompt",
            RefinerRole.EXPANDER,
            round_num=2,
            context="Additional context here",
        )
        
        assert "Additional context here" in prompt
    
    def test_build_role_prompt_with_domain(self):
        """Test building role prompt with domain."""
        prompt = self.diffusion._build_role_prompt(
            "Test prompt",
            RefinerRole.SPECIALIST,
            round_num=1,
            domain="machine learning",
        )
        
        assert "machine learning" in prompt
    
    @pytest.mark.asyncio
    async def test_apply_role_refinement(self):
        """Test applying role refinement."""
        # Mock scoring response
        score_called = [False]
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            if "rate" in prompt.lower() or "scale" in prompt.lower():
                result.content = "0.8"
                score_called[0] = True
            else:
                result.content = "REFINED PROMPT: A much improved prompt with clarity."
            return result
        
        self.mock_provider.complete = mock_complete
        
        version, step = await self.diffusion._apply_role_refinement(
            prompt="Original prompt",
            role=RefinerRole.CLARIFIER,
            model="gpt-4",
            round_num=1,
        )
        
        assert version.prompt is not None
        assert version.role == RefinerRole.CLARIFIER
        assert step.role == RefinerRole.CLARIFIER
        assert step.model == "gpt-4"


class TestSynthesis:
    """Tests for version synthesis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.mock_result = MagicMock()
        self.mock_result.content = "Synthesized prompt combining all perspectives."
        self.mock_provider.complete = AsyncMock(return_value=self.mock_result)
        
        self.providers = {"openai": self.mock_provider}
        self.diffusion = PromptDiffusion(providers=self.providers)
    
    @pytest.mark.asyncio
    async def test_synthesize_versions(self):
        """Test synthesizing multiple versions."""
        versions = [
            PromptVersion(
                version=1,
                prompt="Version 1 with clarity",
                author="gpt-4",
                role=RefinerRole.CLARIFIER,
                score=0.7,
                improvements=["Added clarity"],
            ),
            PromptVersion(
                version=1,
                prompt="Version 2 with context",
                author="gpt-4",
                role=RefinerRole.EXPANDER,
                score=0.75,
                improvements=["Added context"],
            ),
        ]
        
        synthesized = await self.diffusion._synthesize_versions(
            versions, "gpt-4", round_num=1
        )
        
        assert synthesized.role == RefinerRole.SYNTHESIZER
        assert "Combined" in synthesized.improvements[0]
        # Score should be at least average
        assert synthesized.score >= 0.7


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_refine_prompt_function(self):
        """Test refine_prompt convenience function."""
        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "REFINED PROMPT: Better prompt here"
        mock_provider.complete = AsyncMock(return_value=mock_result)
        
        providers = {"openai": mock_provider}
        
        result = await refine_prompt(
            prompt="Original",
            providers=providers,
            models=["gpt-4"],
            max_rounds=1,
        )
        
        assert result.original_prompt == "Original"
        assert result.final_prompt is not None
    
    @pytest.mark.asyncio
    async def test_quick_clarify_function(self):
        """Test quick_clarify convenience function."""
        mock_provider = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "REFINED PROMPT: Clarified version"
        mock_provider.complete = AsyncMock(return_value=mock_result)
        
        refined = await quick_clarify(
            prompt="Unclear prompt",
            provider=mock_provider,
            model="gpt-4",
        )
        
        assert refined is not None


class TestIntegrationScenarios:
    """Integration tests for prompt diffusion scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_provider = MagicMock()
        self.providers = {"openai": self.mock_provider, "stub": self.mock_provider}
    
    @pytest.mark.asyncio
    async def test_ambiguous_query_refinement(self):
        """Test refining an ambiguous query.
        
        Scenario: "What is the capital?" is ambiguous - could mean:
        - Capital of what country?
        - Capital city or financial capital?
        """
        call_count = [0]
        
        async def mock_complete(prompt, model=None):
            call_count[0] += 1
            result = MagicMock()
            
            if "ambiguit" in prompt.lower():
                result.content = """
                AMBIGUITIES:
                - No country specified
                - Capital could mean city or financial
                
                SUGGESTED_CLARIFICATIONS:
                - Specify which country
                - Clarify type of capital
                
                CLARITY_SCORE: 0.4
                NEEDS_USER_INPUT: NO
                """
            elif "rate" in prompt.lower() or "scale" in prompt.lower():
                result.content = "0.85"
            else:
                result.content = """
                REFINED PROMPT: What is the capital city of France, and what are its notable landmarks?
                """
            return result
        
        self.mock_provider.complete = mock_complete
        
        diffusion = PromptDiffusion(providers=self.providers, max_rounds=2)
        
        result = await diffusion.diffuse(
            initial_prompt="What is the capital?",
            models=["gpt-4"],
            analyze_ambiguity=True,
        )
        
        # Should have refined the ambiguous prompt
        assert result.final_prompt != "What is the capital?"
        assert result.rounds_completed >= 1
    
    @pytest.mark.asyncio
    async def test_complex_technical_query(self):
        """Test refining a complex technical query."""
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            if "rate" in prompt.lower() or "scale" in prompt.lower():
                result.content = "0.88"
            else:
                result.content = """
                REFINED PROMPT: Explain the differences between supervised and unsupervised 
                machine learning, including: (1) key algorithms for each, (2) use cases, 
                (3) data requirements, and (4) when to choose one over the other.
                """
            return result
        
        self.mock_provider.complete = mock_complete
        
        diffusion = PromptDiffusion(providers=self.providers, max_rounds=2)
        
        result = await diffusion.diffuse(
            initial_prompt="Explain ML types",
            models=["gpt-4"],
            domain="machine learning",
            analyze_ambiguity=False,
        )
        
        # Should have expanded the prompt significantly
        assert len(result.final_prompt) > len("Explain ML types")
    
    @pytest.mark.asyncio
    async def test_convergence_detection(self):
        """Test that diffusion stops when converged."""
        iteration = [0]
        
        async def mock_complete(prompt, model=None):
            iteration[0] += 1
            result = MagicMock()
            
            if "rate" in prompt.lower() or "scale" in prompt.lower():
                # Return high score to indicate good refinement
                result.content = "0.92"
            else:
                # Return similar prompts to trigger convergence
                result.content = "REFINED PROMPT: A clear and specific prompt about the topic."
            return result
        
        self.mock_provider.complete = mock_complete
        
        diffusion = PromptDiffusion(
            providers=self.providers,
            max_rounds=5,
            convergence_threshold=0.8,
        )
        
        result = await diffusion.diffuse(
            initial_prompt="Initial prompt",
            models=["gpt-4"],
            analyze_ambiguity=False,
        )
        
        # Should converge before max rounds
        assert result.convergence_score > 0
    
    @pytest.mark.asyncio
    async def test_parallel_refinement(self):
        """Test parallel refinement with multiple roles."""
        roles_called = set()
        
        async def mock_complete(prompt, model=None):
            result = MagicMock()
            
            # Track which roles are called
            for role in RefinerRole:
                if role.value in prompt.lower():
                    roles_called.add(role.value)
            
            if "rate" in prompt.lower() or "scale" in prompt.lower():
                result.content = "0.8"
            else:
                result.content = "REFINED PROMPT: Improved prompt"
            return result
        
        self.mock_provider.complete = mock_complete
        
        diffusion = PromptDiffusion(
            providers=self.providers,
            max_rounds=1,
            enable_parallel_refinement=True,
        )
        
        result = await diffusion.diffuse(
            initial_prompt="Test prompt",
            models=["gpt-4", "claude-3"],
            roles=[RefinerRole.CLARIFIER, RefinerRole.EXPANDER],
            analyze_ambiguity=False,
        )
        
        # Should have called multiple roles
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

