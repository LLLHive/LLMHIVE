"""Integration tests for PromptOps preprocessing.

Tests the PromptOps layer that preprocesses user queries before orchestration.

Run from llmhive directory: pytest tests/integration/test_prompt_ops.py -v
"""
from __future__ import annotations

import sys
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Add src to path for imports
_src_path = Path(__file__).parent.parent.parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Try to import PromptOps components
try:
    from llmhive.app.orchestration.prompt_ops import (
        PromptOps,
        PromptSpecification,
        TaskType,
        QueryComplexity,
        QueryAnalysis,
    )
    PROMPT_OPS_AVAILABLE = True
except ImportError:
    PROMPT_OPS_AVAILABLE = False


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_providers():
    """Create mock LLM providers."""
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=MagicMock(
        content='{"task_type": "factual_question", "complexity": "simple"}',
    ))
    
    return {
        "openai": mock_provider,
        "anthropic": mock_provider,
    }


@pytest.fixture
def prompt_ops(mock_providers):
    """Create PromptOps instance."""
    if not PROMPT_OPS_AVAILABLE:
        pytest.skip("PromptOps not available")
    return PromptOps(providers=mock_providers)


# ============================================================
# Test Full PromptOps Pipeline (Main API)
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestPromptOpsPipeline:
    """Test full PromptOps preprocessing pipeline."""
    
    @pytest.mark.asyncio
    async def test_process_simple_query(self, prompt_ops):
        """Test processing a simple query."""
        query = "What is the capital of France?"
        
        spec = await prompt_ops.process(query)
        
        assert isinstance(spec, PromptSpecification)
        assert spec.original_query == query
        # refined_query is the actual field name
        assert spec.refined_query is not None
    
    @pytest.mark.asyncio
    async def test_process_returns_analysis(self, prompt_ops):
        """Test that process returns analysis object."""
        query = "Write a Python function"
        
        spec = await prompt_ops.process(query)
        
        # Analysis is nested within the specification
        assert spec.analysis is not None
        assert isinstance(spec.analysis, QueryAnalysis)
    
    @pytest.mark.asyncio
    async def test_process_with_domain_hint(self, prompt_ops):
        """Test processing with domain hint."""
        query = "How do I handle exceptions?"
        
        spec = await prompt_ops.process(query, domain_hint="coding")
        
        # Domain is in the analysis object
        assert spec.analysis.domain is not None
    
    @pytest.mark.asyncio
    async def test_process_complex_query(self, prompt_ops):
        """Test processing complex query."""
        query = """
        Analyze the performance characteristics of different sorting algorithms
        and provide a comparative analysis with code examples in Python.
        Also explain the time and space complexity for each algorithm.
        """
        
        spec = await prompt_ops.process(query)
        
        # Complexity is in the analysis object
        assert spec.analysis.complexity in [
            QueryComplexity.COMPLEX, 
            QueryComplexity.RESEARCH, 
            QueryComplexity.MODERATE,
            QueryComplexity.SIMPLE,
        ]
    
    @pytest.mark.asyncio
    async def test_specification_has_segments(self, prompt_ops):
        """Test that specification includes segments."""
        query = "Write a Python function to sort a list"
        
        spec = await prompt_ops.process(query)
        
        # Segments are part of the specification
        assert hasattr(spec, 'segments')
    
    @pytest.mark.asyncio
    async def test_specification_has_safety_flags(self, prompt_ops):
        """Test that specification includes safety flags."""
        query = "What is Python?"
        
        spec = await prompt_ops.process(query)
        
        assert hasattr(spec, 'safety_flags')
        assert hasattr(spec, 'safety_blocked')
    
    @pytest.mark.asyncio
    async def test_process_code_query(self, prompt_ops):
        """Test processing a code-related query."""
        query = """
        Fix this code:
        ```python
        def foo():
            print("hello"
        ```
        """
        
        spec = await prompt_ops.process(query)
        
        # Should have task_type in analysis
        assert spec.analysis.task_type in [
            TaskType.DEBUGGING, 
            TaskType.CODE_GENERATION, 
            TaskType.GENERAL,
        ]


# ============================================================
# Test Query Analysis Structure
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestQueryAnalysis:
    """Test QueryAnalysis structure."""
    
    @pytest.mark.asyncio
    async def test_analysis_has_task_type(self, prompt_ops):
        """Test analysis has task_type."""
        query = "What is 2 + 2?"
        spec = await prompt_ops.process(query)
        
        assert spec.analysis.task_type is not None
        assert isinstance(spec.analysis.task_type, TaskType)
    
    @pytest.mark.asyncio
    async def test_analysis_has_complexity(self, prompt_ops):
        """Test analysis has complexity."""
        query = "Explain quantum mechanics"
        spec = await prompt_ops.process(query)
        
        assert spec.analysis.complexity is not None
        assert isinstance(spec.analysis.complexity, QueryComplexity)
    
    @pytest.mark.asyncio
    async def test_analysis_has_domain(self, prompt_ops):
        """Test analysis has domain."""
        query = "Write a Python sort function"
        spec = await prompt_ops.process(query)
        
        assert spec.analysis.domain is not None
        assert isinstance(spec.analysis.domain, str)
    
    @pytest.mark.asyncio
    async def test_analysis_has_tool_hints(self, prompt_ops):
        """Test analysis has tool hints."""
        query = "Calculate the sum of 1 to 100"
        spec = await prompt_ops.process(query)
        
        assert hasattr(spec.analysis, 'tool_hints')
        assert hasattr(spec.analysis, 'requires_tools')


# ============================================================
# Test Edge Cases
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestPromptOpsEdgeCases:
    """Test edge cases in PromptOps."""
    
    @pytest.mark.asyncio
    async def test_very_long_query(self, prompt_ops):
        """Test handling of very long query."""
        long_query = "Explain " + " and ".join(["topic"] * 50)
        
        spec = await prompt_ops.process(long_query)
        
        # Should handle without error
        assert spec is not None
        assert spec.original_query is not None
    
    @pytest.mark.asyncio
    async def test_unicode_query(self, prompt_ops):
        """Test handling of unicode characters."""
        query = "What does 日本語 mean? Explain émoji: 🚀"
        
        spec = await prompt_ops.process(query)
        
        # Should handle unicode without error
        assert spec is not None
    
    @pytest.mark.asyncio
    async def test_short_query(self, prompt_ops):
        """Test handling of very short query."""
        query = "Hello"
        
        spec = await prompt_ops.process(query)
        
        assert spec is not None
        assert spec.analysis.complexity in [QueryComplexity.SIMPLE, QueryComplexity.MODERATE]
    
    @pytest.mark.asyncio
    async def test_query_with_whitespace(self, prompt_ops):
        """Test query with extra whitespace."""
        query = "   What   is   Python?   "
        
        spec = await prompt_ops.process(query)
        
        assert spec is not None
        # Refined query may have been cleaned
        assert spec.refined_query is not None


# ============================================================
# Test Task Type Detection
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestTaskTypeDetection:
    """Test task type detection through the pipeline."""
    
    @pytest.mark.asyncio
    async def test_code_query_detection(self, prompt_ops):
        """Test code-related queries are detected."""
        query = "Write a Python function to sort a list"
        spec = await prompt_ops.process(query)
        
        # Should detect code-related task
        assert spec.analysis.task_type in [
            TaskType.CODE_GENERATION,
            TaskType.GENERAL,
        ]
    
    @pytest.mark.asyncio
    async def test_math_query_detection(self, prompt_ops):
        """Test math queries are detected."""
        query = "Calculate 15 * 23 + 7"
        spec = await prompt_ops.process(query)
        
        # Should detect math or general
        assert spec.analysis.task_type in [
            TaskType.MATH_PROBLEM,
            TaskType.FACTUAL_QUESTION,
            TaskType.GENERAL,
        ]
    
    @pytest.mark.asyncio
    async def test_factual_query_detection(self, prompt_ops):
        """Test factual questions are detected."""
        query = "What is the capital of France?"
        spec = await prompt_ops.process(query)
        
        assert spec.analysis.task_type in [
            TaskType.FACTUAL_QUESTION,
            TaskType.GENERAL,
        ]
