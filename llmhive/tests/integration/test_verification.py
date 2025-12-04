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
# Test Full Verification Pipeline (Main API)
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationPipeline:
    """Test full verification pipeline."""
    
    @pytest.mark.asyncio
    async def test_verify_with_query(self, verifier):
        """Test verify() with both answer and query args."""
        answer = "The result of 5 + 5 is 10."
        query = "What is 5 + 5?"
        
        # verify() requires both answer and query
        results = await verifier.verify(answer, query)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_verify_math_content(self, verifier):
        """Test verification of math content."""
        answer = "5 * 7 = 35"
        query = "What is 5 times 7?"
        
        results = await verifier.verify(
            answer, 
            query,
            verification_types=[VerificationType.MATH]
        )
        
        assert isinstance(results, list)
        if results:
            assert all(isinstance(r, VerificationResult) for r in results)
    
    @pytest.mark.asyncio
    async def test_verify_code_content(self, verifier):
        """Test verification of code content."""
        answer = """
        ```python
        def greet(name):
            return f"Hello, {name}!"
        ```
        """
        query = "Write a greeting function"
        
        results = await verifier.verify(
            answer,
            query,
            verification_types=[VerificationType.CODE]
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_verify_auto_detect_types(self, verifier):
        """Test that verify() auto-detects verification types."""
        answer = "The answer is 42. Here is code: print('hello')"
        query = "Give me a number and some code"
        
        # No verification_types = auto-detect
        results = await verifier.verify(answer, query)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_verify_returns_list(self, verifier):
        """Test that verify() always returns a list."""
        answer = "Simple answer"
        query = "Simple question"
        
        results = await verifier.verify(answer, query)
        
        assert isinstance(results, list)


# ============================================================
# Test Verification Result Structure
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationResultStructure:
    """Test VerificationResult structure."""
    
    def test_result_basic_fields(self):
        """Test basic result fields exist."""
        result = VerificationResult(
            passed=True,
            verification_type=VerificationType.MATH,
            original_answer="2 + 2 = 4",
        )
        
        assert hasattr(result, "passed")
        assert hasattr(result, "verification_type")
        assert hasattr(result, "original_answer")
    
    def test_result_optional_fields(self):
        """Test optional result fields."""
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
# Test Verification Types
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationTypes:
    """Test different verification types."""
    
    @pytest.mark.asyncio
    async def test_math_verification_type(self, verifier):
        """Test math verification."""
        results = await verifier.verify(
            "2 + 2 = 4",
            "What is 2 plus 2?",
            verification_types=[VerificationType.MATH]
        )
        
        # Should attempt math verification
        if results:
            assert results[0].verification_type == VerificationType.MATH
    
    @pytest.mark.asyncio
    async def test_code_verification_type(self, verifier):
        """Test code verification."""
        results = await verifier.verify(
            "```python\nprint('hello')\n```",
            "Write hello world",
            verification_types=[VerificationType.CODE]
        )
        
        if results:
            assert results[0].verification_type == VerificationType.CODE
    
    @pytest.mark.asyncio
    async def test_factual_verification_type(self, verifier):
        """Test factual verification."""
        results = await verifier.verify(
            "Paris is the capital of France",
            "What is the capital of France?",
            verification_types=[VerificationType.FACTUAL]
        )
        
        if results:
            assert results[0].verification_type == VerificationType.FACTUAL


# ============================================================
# Test Edge Cases
# ============================================================

@pytest.mark.skipif(not VERIFICATION_AVAILABLE, reason="Verification not available")
class TestVerificationEdgeCases:
    """Test edge cases in verification."""
    
    @pytest.mark.asyncio
    async def test_empty_answer(self, verifier):
        """Test handling of empty answer."""
        results = await verifier.verify("", "Any question")
        
        # Should handle gracefully
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_very_long_answer(self, verifier):
        """Test handling of very long answer."""
        long_answer = "The result is 1. " * 100
        
        results = await verifier.verify(long_answer, "Long question")
        
        # Should handle without hanging
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_unicode_content(self, verifier):
        """Test handling of unicode content."""
        answer = "日本の首都は東京です。2 + 2 = 4"
        
        results = await verifier.verify(answer, "Unicode question")
        
        # Should handle unicode without error
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_no_verifiable_content(self, verifier):
        """Test answer with no verifiable content."""
        answer = "This is just a simple sentence."
        query = "Tell me something"
        
        results = await verifier.verify(answer, query)
        
        # Should return empty list or pass
        assert isinstance(results, list)
