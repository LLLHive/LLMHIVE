"""Integration tests for verification pipeline.

Tests code/math/fact verification to catch LLM hallucinations.

Run from llmhive directory: pytest tests/integration/test_verification.py -v
"""
from __future__ import annotations

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
from enum import Enum, auto

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Try to import verification components
try:
    from llmhive.app.orchestration.tool_verification import (
        ToolVerifier,
        VerificationResult,
        VerificationType,
        FactualClaim,
        get_verification_pipeline,
    )
    VERIFICATION_AVAILABLE = True
except ImportError:
    VERIFICATION_AVAILABLE = False
    # Create stub enum for type hints
    class VerificationType(Enum):
        MATH = auto()
        CODE = auto()
        FACTUAL = auto()
        LOGICAL = auto()
        FORMAT = auto()


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
    if not VERIFICATION_AVAILABLE:
        pytest.skip("Verification not available")
    return ToolVerifier(
        web_search_fn=mock_web_search,
        code_executor_fn=mock_code_executor,
    )


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
    async def test_claim_extraction(self, verifier):
        """Test factual claim extraction."""
        answer = """
        France is a country in Europe. Its capital is Paris.
        The Eiffel Tower is located in Paris and was built in 1889.
        """
        
        claims = verifier.extract_claims(answer)
        
        # Should extract multiple claims
        assert len(claims) >= 1


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
    async def test_very_long_answer(self, verifier):
        """Test handling of very long answer."""
        long_answer = "The result is 1. " * 100
        
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
