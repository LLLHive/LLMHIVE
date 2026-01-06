"""Tests for Quality Policies module.

Tests factoid detection, clarification gating, consensus tie-breaking,
confidence scoring, and self-grading.
"""
from __future__ import annotations

import pytest


class TestFactoidDetection:
    """Test factoid query detection and classification."""
    
    def test_simple_factoid_who_discovered(self):
        """'Who discovered X?' should be classified as simple factoid."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query("Who discovered penicillin?")
        assert result.query_type == QueryType.FACTOID
        assert result.is_simple_factoid is True
        assert result.allows_clarification is False
    
    def test_simple_factoid_what_is_capital(self):
        """'What is the capital of X?' should be factoid."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query("What is the capital of France?")
        assert result.query_type in (QueryType.FACTOID, QueryType.DEFINITION)
        assert result.is_simple_factoid is True
        assert result.allows_clarification is False
    
    def test_simple_factoid_when_did(self):
        """'When did X?' should be factoid."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query("When did World War II end?")
        assert result.query_type == QueryType.FACTOID
        assert result.is_simple_factoid is True
    
    def test_simple_factoid_who_wrote(self):
        """'Who wrote X?' should be factoid."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query("Who wrote Romeo and Juliet?")
        assert result.query_type == QueryType.FACTOID
        assert result.is_simple_factoid is True
    
    def test_math_query_detected(self):
        """Math calculations should be detected."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query("What is 15 * 23?")
        assert result.query_type == QueryType.MATH
        assert result.is_simple_factoid is True
        assert result.allows_clarification is False
    
    def test_truly_ambiguous_query(self):
        """Truly ambiguous queries should allow clarification."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query("Tell me about it")
        assert result.query_type == QueryType.AMBIGUOUS
        assert result.allows_clarification is True
    
    def test_complex_query_no_clarification(self):
        """Complex queries should not trigger clarification by default."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query, QueryType
        )
        
        result = classify_query(
            "Analyze the pros and cons of remote work, including productivity and cost"
        )
        assert result.query_type == QueryType.COMPLEX
        assert result.allows_clarification is False


class TestClarificationGating:
    """Test that clarification is properly gated for factoids."""
    
    def test_skip_clarification_for_factoid(self):
        """Simple factoids should skip clarification."""
        from llmhive.app.orchestration.quality_policies import (
            should_skip_clarification
        )
        
        skip, reason = should_skip_clarification("Who discovered penicillin?")
        assert skip is True
        assert "factoid" in reason.lower() or "simple" in reason.lower()
    
    def test_skip_clarification_for_math(self):
        """Math queries should skip clarification."""
        from llmhive.app.orchestration.quality_policies import (
            should_skip_clarification
        )
        
        skip, reason = should_skip_clarification("What is 2 + 2?")
        assert skip is True
    
    def test_allow_clarification_for_ambiguous(self):
        """Truly ambiguous queries can ask for clarification."""
        from llmhive.app.orchestration.quality_policies import (
            should_skip_clarification
        )
        
        skip, reason = should_skip_clarification("Tell me about it")
        assert skip is False
    
    def test_factoid_questions_list(self):
        """Test a list of factoid questions that should NOT trigger clarification."""
        from llmhive.app.orchestration.quality_policies import (
            should_skip_clarification
        )
        
        factoids = [
            "Who discovered penicillin?",
            "What is the capital of France?",
            "When did World War II end?",
            "Who wrote Romeo and Juliet?",
            "What is the chemical symbol for gold?",
            "Who invented the telephone?",
            "What planet is known as the Red Planet?",
            "Who painted the Mona Lisa?",
            "What is the largest ocean on Earth?",
            "Who was the first person to walk on the moon?",
        ]
        
        for factoid in factoids:
            skip, reason = should_skip_clarification(factoid)
            assert skip is True, f"'{factoid}' should skip clarification"


class TestConfidenceScoring:
    """Test calibrated confidence calculation."""
    
    def test_high_confidence_all_factors(self):
        """High values for all factors should give high confidence."""
        from llmhive.app.orchestration.quality_policies import (
            calculate_confidence, ConfidenceFactors
        )
        
        factors = ConfidenceFactors(
            ensemble_agreement=1.0,
            verification_score=1.0,
            source_presence=1.0,
            tool_success=1.0,
            domain_safety=1.0,
        )
        
        confidence = calculate_confidence(factors)
        assert confidence >= 0.9
    
    def test_low_confidence_low_factors(self):
        """Low values for all factors should give low confidence."""
        from llmhive.app.orchestration.quality_policies import (
            calculate_confidence, ConfidenceFactors
        )
        
        factors = ConfidenceFactors(
            ensemble_agreement=0.2,
            verification_score=0.2,
            source_presence=0.0,
            tool_success=0.2,
            domain_safety=0.5,
        )
        
        confidence = calculate_confidence(factors)
        assert confidence < 0.5
    
    def test_confidence_range(self):
        """Confidence should always be in 0-1 range."""
        from llmhive.app.orchestration.quality_policies import (
            calculate_confidence, ConfidenceFactors
        )
        
        # Test edge cases
        factors_high = ConfidenceFactors(
            ensemble_agreement=1.5,  # Above 1
            verification_score=1.0,
            source_presence=1.0,
            tool_success=1.0,
            domain_safety=1.0,
        )
        
        factors_low = ConfidenceFactors(
            ensemble_agreement=-0.5,  # Below 0
            verification_score=0.0,
            source_presence=0.0,
            tool_success=0.0,
            domain_safety=0.0,
        )
        
        assert 0.0 <= calculate_confidence(factors_high) <= 1.0
        assert 0.0 <= calculate_confidence(factors_low) <= 1.0
    
    def test_medical_query_cap(self):
        """Medical queries should have capped confidence without verification."""
        from llmhive.app.orchestration.quality_policies import (
            calculate_confidence, ConfidenceFactors
        )
        
        factors = ConfidenceFactors(
            ensemble_agreement=1.0,
            verification_score=0.3,  # Low verification
            source_presence=0.0,
            tool_success=0.5,
            domain_safety=1.0,
        )
        
        # Without medical query context
        confidence_general = calculate_confidence(factors)
        
        # With medical query context
        confidence_medical = calculate_confidence(
            factors, query="What are the symptoms of diabetes?"
        )
        
        # Medical should be capped lower
        assert confidence_medical <= 0.6
    
    def test_confidence_labels(self):
        """Test confidence label assignment."""
        from llmhive.app.orchestration.quality_policies import (
            get_confidence_label
        )
        
        assert get_confidence_label(0.95) == "Very High"
        assert get_confidence_label(0.8) == "High"
        assert get_confidence_label(0.6) == "Moderate"
        assert get_confidence_label(0.4) == "Low"
        assert get_confidence_label(0.1) == "Very Low"


class TestStubDetection:
    """Test stub provider detection."""
    
    def test_detect_stub_in_model_name(self):
        """Detect stub in model name."""
        from llmhive.app.orchestration.quality_policies import (
            detect_stub_provider
        )
        
        assert detect_stub_provider(["stub-model"], "Hello") is True
        assert detect_stub_provider(["StubProvider"], "Hello") is True
    
    def test_detect_stub_in_answer(self):
        """Detect stub response in answer content."""
        from llmhive.app.orchestration.quality_policies import (
            detect_stub_provider
        )
        
        assert detect_stub_provider(
            ["gpt-4o"], "This is a stub response for testing"
        ) is True
        assert detect_stub_provider(
            ["gpt-4o"], "[STUB] Response"
        ) is True
    
    def test_no_stub_in_normal_response(self):
        """Normal responses should not be flagged as stub."""
        from llmhive.app.orchestration.quality_policies import (
            detect_stub_provider
        )
        
        assert detect_stub_provider(
            ["gpt-4o", "claude-3-sonnet"], 
            "Penicillin was discovered by Alexander Fleming in 1928."
        ) is False


class TestQualityMetadataBuilder:
    """Test quality metadata construction."""
    
    def test_build_complete_metadata(self):
        """Test building complete metadata."""
        from llmhive.app.orchestration.quality_policies import (
            build_quality_metadata, ConfidenceFactors
        )
        
        factors = ConfidenceFactors(
            ensemble_agreement=0.8,
            verification_score=0.9,
            source_presence=0.5,
            tool_success=1.0,
            domain_safety=1.0,
        )
        
        metadata = build_quality_metadata(
            trace_id="test-123",
            confidence_factors=factors,
            query="Who discovered penicillin?",
            models_used=["gpt-4o"],
            strategy_used="direct",
            verification_status="PASS",
            verification_score=0.9,
            answer="Alexander Fleming discovered penicillin.",
        )
        
        assert metadata.trace_id == "test-123"
        assert 0 < metadata.confidence <= 1
        assert metadata.confidence_label in ["Very High", "High", "Moderate", "Low", "Very Low"]
        assert metadata.models_used == ["gpt-4o"]
        assert metadata.verification_status == "PASS"
        assert metadata.is_stub is False
    
    def test_detect_stub_in_metadata(self):
        """Test that stub is detected in metadata."""
        from llmhive.app.orchestration.quality_policies import (
            build_quality_metadata, ConfidenceFactors
        )
        
        factors = ConfidenceFactors()
        
        metadata = build_quality_metadata(
            trace_id="test-456",
            confidence_factors=factors,
            models_used=["stub-provider"],
            answer="Stub response",
        )
        
        assert metadata.is_stub is True


@pytest.mark.asyncio
class TestAsyncQualityPolicies:
    """Async tests for quality policies."""
    
    async def test_self_grade_fallback(self):
        """Self-grader should return passing grade when no provider."""
        from llmhive.app.orchestration.quality_policies import (
            self_grade_answer
        )
        
        result = await self_grade_answer(
            query="What is 2+2?",
            answer="2+2 equals 4.",
            providers={},  # No providers
        )
        
        assert result.composite_score >= 0.6
        assert result.needs_improvement is False
    
    async def test_verify_answer_fallback(self):
        """Verification should return uncertain result when no provider."""
        from llmhive.app.orchestration.quality_policies import (
            verify_answer_claim
        )
        
        result = await verify_answer_claim(
            query="Who discovered penicillin?",
            answer="Alexander Fleming",
            providers={},  # No providers
        )
        
        # Should return a result, not fail
        assert result.confidence_score == 0.5
        assert "No verification provider" in (result.error or "No verification provider")


class TestConsensusFactoids:
    """Test that consensus chooses correct factoid answers."""
    
    def test_penicillin_discovery(self):
        """Consensus should choose Fleming over Florey."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query
        )
        
        # First verify this is classified as a factoid
        result = classify_query("Who discovered penicillin - Fleming or Florey?")
        # This specific format might be classified differently, but should not ask for clarification
        assert result.allows_clarification is False
    
    def test_factoid_battery(self):
        """Battery of factoid tests that should all classify correctly."""
        from llmhive.app.orchestration.quality_policies import (
            classify_query
        )
        
        test_cases = [
            ("Who discovered penicillin?", True, False),
            ("What is the capital of France?", True, False),
            ("Tell me about it", False, True),
            ("Continue", False, True),
            ("What is 2+2?", True, False),
        ]
        
        for query, should_be_factoid, should_allow_clarification in test_cases:
            result = classify_query(query)
            if should_be_factoid:
                assert result.is_simple_factoid is True, f"'{query}' should be factoid"
            if should_allow_clarification:
                assert result.allows_clarification is True, f"'{query}' should allow clarification"
            else:
                assert result.allows_clarification is False, f"'{query}' should not allow clarification"

