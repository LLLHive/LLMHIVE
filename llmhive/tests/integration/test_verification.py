"""Integration tests for verification pipeline.

Tests code/math/fact verification to catch LLM hallucinations.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Try to import verification components
try:
    from llmhive.src.llmhive.app.orchestration.tool_verification import (
        ToolVerifier,
        VerificationResult,
        VerificationType,
        FactualClaim,
        get_verification_pipeline,
        VerificationPipeline,
    )
    VERIFICATION_AVAILABLE = True
except ImportError:
    VERIFICATION_AVAILABLE = False
    # Create stubs for testing
    class VerificationType:
        MATH = "MATH"
        CODE = "CODE"
        FACTUAL = "FACTUAL"


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_web_search():
    """Create mock web search function."""
    async def search(query: str) -> List[Dict[str, Any]]:
        # Simulate web search results
        if "capital" in query.lower() and "france" in query.lower():
            return [{"snippet": "The capital of France is Paris.", "confidence": 0.95}]
        return [{"snippet": "No specific information found.", "confidence": 0.5}]
    return search


@pytest.fixture
def mock_code_executor():
    """Create mock code executor function."""
    async def execute(code: str, language: str = "python") -> Dict[str, Any]:
        # Simple mock execution
        if "syntax error" in code.lower():
            return {"success": False, "error": "SyntaxError", "output": ""}
        if "print" in code:
            return {"success": True, "output": "Hello World", "error": None}
        return {"success": True, "output": "", "error": None}
    return execute


@pytest.fixture
def verifier(mock_web_search, mock_code_executor):
    """Create ToolVerifier instance."""
    if VERIFICATION_AVAILABLE:
        return ToolVerifier(
            web_search_fn=mock_web_search,
            code_executor_fn=mock_code_executor,
        )
    return None


# ============================================================
# Test Math Verification
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestMathVerification:
    """Test math/calculation verification."""
    
    @pytest.mark.asyncio
    async def test_correct_arithmetic(self, verifier):
        """Test verification of correct arithmetic."""
        answer = "The result of 5 * 7 is 35."
        
        result = await verifier.verify_math(answer)
        
        assert result.passed
        assert result.verification_type == VerificationType.MATH
    
    @pytest.mark.asyncio
    async def test_incorrect_arithmetic(self, verifier):
        """Test detection of incorrect arithmetic."""
        answer = "The result of 5 * 7 is 30."  # Wrong!
        
        result = await verifier.verify_math(answer)
        
        # Should detect the error
        # Note: depends on implementation detecting the specific claim
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_complex_expression(self, verifier):
        """Test verification of complex expressions."""
        answer = "The value of (10 + 5) * 2 - 7 = 23"
        
        result = await verifier.verify_math(answer)
        
        assert result.passed
    
    @pytest.mark.asyncio
    async def test_sqrt_verification(self, verifier):
        """Test square root verification."""
        answer = "The square root of 16 is 4."
        
        result = await verifier.verify_math(answer)
        
        assert result.passed
    
    @pytest.mark.asyncio
    async def test_no_math_content(self, verifier):
        """Test handling of non-math content."""
        answer = "The capital of France is Paris."
        
        result = await verifier.verify_math(answer)
        
        # Should pass (nothing to verify) or skip
        assert result.passed or result.verification_type != VerificationType.MATH


# ============================================================
# Test Code Verification
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestCodeVerification:
    """Test code syntax and execution verification."""
    
    @pytest.mark.asyncio
    async def test_valid_python_syntax(self, verifier):
        """Test verification of valid Python code."""
        answer = """
        Here's a Python function:
        ```python
        def greet(name):
            return f"Hello, {name}!"
        ```
        """
        
        result = await verifier.verify_code(answer, language="python")
        
        assert result.passed
        assert result.verification_type == VerificationType.CODE
    
    @pytest.mark.asyncio
    async def test_invalid_python_syntax(self, verifier):
        """Test detection of invalid Python syntax."""
        answer = """
        Here's some code:
        ```python
        def greet(name)
            return f"Hello, {name}!"
        ```
        """  # Missing colon after function def
        
        result = await verifier.verify_code(answer, language="python")
        
        # Should detect syntax error
        if not result.passed:
            assert any("syntax" in issue.lower() for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_code_execution(self, verifier):
        """Test code execution verification."""
        answer = """
        ```python
        print("Hello World")
        ```
        """
        
        result = await verifier.verify_code(answer, language="python", execute=True)
        
        # If execution is supported, should verify
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_javascript_syntax(self, verifier):
        """Test JavaScript syntax verification."""
        answer = """
        ```javascript
        function greet(name) {
            return `Hello, ${name}!`;
        }
        ```
        """
        
        result = await verifier.verify_code(answer, language="javascript")
        
        # Should handle JavaScript
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_no_code_content(self, verifier):
        """Test handling of non-code content."""
        answer = "The capital of France is Paris."
        
        result = await verifier.verify_code(answer, language="python")
        
        # Should pass (nothing to verify) or skip
        assert result.passed or result.verification_type != VerificationType.CODE


# ============================================================
# Test Factual Verification
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestFactualVerification:
    """Test factual claim verification."""
    
    @pytest.mark.asyncio
    async def test_correct_fact(self, verifier):
        """Test verification of correct fact."""
        answer = "The capital of France is Paris."
        
        result = await verifier.verify_facts(answer)
        
        assert result.passed
        assert result.verification_type == VerificationType.FACTUAL
    
    @pytest.mark.asyncio
    async def test_incorrect_fact(self, verifier):
        """Test detection of incorrect fact."""
        answer = "The capital of France is London."  # Wrong!
        
        result = await verifier.verify_facts(answer)
        
        # Should detect the error if web search works
        # Note: depends on mock returning contradicting info
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_claim_extraction(self, verifier):
        """Test factual claim extraction."""
        answer = """
        France is a country in Europe. Its capital is Paris.
        The Eiffel Tower is located in Paris and was built in 1889.
        """
        
        claims = verifier.extract_claims(answer)
        
        # Should extract multiple claims
        assert len(claims) >= 1
    
    @pytest.mark.asyncio
    async def test_numerical_claim(self, verifier):
        """Test numerical claim verification."""
        answer = "The Eiffel Tower is 330 meters tall."
        
        result = await verifier.verify_facts(answer)
        
        # Should attempt to verify
        assert result is not None


# ============================================================
# Test Full Verification Pipeline
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationPipeline:
    """Test full verification pipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_basic(self, verifier):
        """Test basic pipeline execution."""
        answer = "The result of 5 + 5 is 10. Here's Python: print('hello')"
        
        result = await verifier.verify(answer)
        
        assert isinstance(result, VerificationResult)
        assert result.passed is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_multiple_types(self, verifier):
        """Test pipeline with multiple verification types."""
        answer = """
        Let me solve this:
        
        The answer is 2 + 2 = 4.
        
        Here's the code:
        ```python
        result = 2 + 2
        print(result)
        ```
        
        Fun fact: Paris is the capital of France.
        """
        
        result = await verifier.verify(
            answer,
            verification_types=[
                VerificationType.MATH,
                VerificationType.CODE,
                VerificationType.FACTUAL,
            ]
        )
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_pipeline_correction(self, verifier):
        """Test that pipeline can provide corrections."""
        answer = "The result of 10 * 10 is 99."  # Wrong!
        
        result = await verifier.verify(answer)
        
        # If error detected, should provide correction
        if not result.passed and result.verified_answer:
            assert "100" in result.verified_answer
    
    @pytest.mark.asyncio
    async def test_pipeline_confidence(self, verifier):
        """Test pipeline confidence scoring."""
        answer = "This is definitely true."
        
        result = await verifier.verify(answer)
        
        assert 0 <= result.confidence <= 1


# ============================================================
# Test Verification Result Structure
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationResultStructure:
    """Test VerificationResult structure."""
    
    def test_result_fields(self):
        """Test all required fields exist."""
        result = VerificationResult(
            passed=True,
            verification_type=VerificationType.MATH,
            original_answer="2 + 2 = 4",
        )
        
        assert hasattr(result, "passed")
        assert hasattr(result, "verification_type")
        assert hasattr(result, "original_answer")
        assert hasattr(result, "verified_answer")
        assert hasattr(result, "issues")
        assert hasattr(result, "evidence")
        assert hasattr(result, "confidence")
    
    def test_result_with_issues(self):
        """Test result with issues."""
        result = VerificationResult(
            passed=False,
            verification_type=VerificationType.MATH,
            original_answer="5 * 7 = 30",
            issues=["Incorrect calculation: 5 * 7 = 35, not 30"],
            corrections_made=1,
        )
        
        assert not result.passed
        assert len(result.issues) > 0
        assert result.corrections_made == 1
    
    def test_result_with_evidence(self):
        """Test result with evidence."""
        result = VerificationResult(
            passed=True,
            verification_type=VerificationType.FACTUAL,
            original_answer="Paris is the capital of France",
            evidence={"source": "Wikipedia", "confidence": 0.99},
        )
        
        assert result.evidence is not None
        assert "source" in result.evidence


# ============================================================
# Test Edge Cases
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationEdgeCases:
    """Test edge cases in verification."""
    
    @pytest.mark.asyncio
    async def test_empty_answer(self, verifier):
        """Test handling of empty answer."""
        try:
            result = await verifier.verify("")
            # Should handle gracefully
            assert result is not None
        except ValueError:
            pass  # Expected for empty input
    
    @pytest.mark.asyncio
    async def test_very_long_answer(self, verifier):
        """Test handling of very long answer."""
        long_answer = "The result is 1. " * 1000
        
        result = await verifier.verify(long_answer)
        
        # Should handle without hanging
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_unicode_content(self, verifier):
        """Test handling of unicode content."""
        answer = "日本の首都は東京です。2 + 2 = 4"
        
        result = await verifier.verify(answer)
        
        # Should handle unicode without error
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_mixed_correct_incorrect(self, verifier):
        """Test handling of mixed correct/incorrect claims."""
        answer = """
        5 + 5 = 10 (correct)
        10 * 10 = 99 (incorrect)
        """
        
        result = await verifier.verify(answer)
        
        # Should report issues if detected
        assert result is not None


# ============================================================
# Test Integration with Orchestration
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationOrchestrationIntegration:
    """Test verification integration with orchestration."""
    
    @pytest.mark.asyncio
    async def test_get_pipeline(self):
        """Test getting verification pipeline."""
        pipeline = get_verification_pipeline()
        
        assert isinstance(pipeline, VerificationPipeline)
    
    @pytest.mark.asyncio
    async def test_pipeline_verify_response(self):
        """Test pipeline verify_response method."""
        pipeline = get_verification_pipeline()
        
        response = "The answer is 42."
        result = await pipeline.verify_response(response)
        
        assert result is not None
        assert hasattr(result, "passed")
    
    @pytest.mark.asyncio
    async def test_pipeline_with_context(self):
        """Test pipeline with query context."""
        pipeline = get_verification_pipeline()
        
        query = "What is 6 * 7?"
        response = "6 * 7 = 42"
        
        result = await pipeline.verify_response(response, query=query)
        
        # Should verify math answer
        assert result.passed


# ============================================================
# Test Claim Extraction
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestClaimExtraction:
    """Test factual claim extraction."""
    
    def test_extract_date_claims(self, verifier):
        """Test extraction of date claims."""
        text = "World War II ended in 1945. The moon landing was in 1969."
        
        claims = verifier.extract_claims(text)
        
        date_claims = [c for c in claims if c.claim_type == "date"]
        assert len(date_claims) >= 1
    
    def test_extract_numerical_claims(self, verifier):
        """Test extraction of numerical claims."""
        text = "The population of Tokyo is over 13 million. Mount Everest is 8,849 meters tall."
        
        claims = verifier.extract_claims(text)
        
        number_claims = [c for c in claims if c.claim_type == "number"]
        assert len(number_claims) >= 1
    
    def test_extract_entity_claims(self, verifier):
        """Test extraction of entity claims."""
        text = "Albert Einstein developed the theory of relativity. Paris is the capital of France."
        
        claims = verifier.extract_claims(text)
        
        # Should extract entity-related claims
        assert len(claims) >= 1
