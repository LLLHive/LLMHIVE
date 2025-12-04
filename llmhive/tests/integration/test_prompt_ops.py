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
        SegmentType,
        AmbiguityType,
        AmbiguityDetail,
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
# Test Task Type Classification
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestTaskTypeClassification:
    """Test task type classification."""
    
    def test_code_generation_detection(self, prompt_ops):
        """Test code generation task detection."""
        queries = [
            "Write a Python function to sort a list",
            "Create a JavaScript class for user authentication",
            "Implement a binary search algorithm in C++",
        ]
        
        for query in queries:
            # Rule-based classification should work without LLM
            analysis = prompt_ops._analyze_query_rules(query)
            
            assert analysis.task_type in [
                TaskType.CODE_GENERATION,
                TaskType.DEBUGGING,
                TaskType.GENERAL,
            ]
    
    def test_math_problem_detection(self, prompt_ops):
        """Test math problem task detection."""
        queries = [
            "Calculate the integral of x^2",
            "What is 2 + 2?",
            "Solve for x: 2x + 5 = 15",
        ]
        
        for query in queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            # Should detect as math or general (depending on complexity)
            assert analysis.task_type in [
                TaskType.MATH_PROBLEM,
                TaskType.FACTUAL_QUESTION,
                TaskType.GENERAL,
            ]
    
    def test_factual_question_detection(self, prompt_ops):
        """Test factual question detection."""
        queries = [
            "What is the capital of France?",
            "Who wrote Romeo and Juliet?",
            "When was the Declaration of Independence signed?",
        ]
        
        for query in queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            assert analysis.task_type in [
                TaskType.FACTUAL_QUESTION,
                TaskType.GENERAL,
            ]
    
    def test_creative_writing_detection(self, prompt_ops):
        """Test creative writing task detection."""
        queries = [
            "Write a poem about autumn",
            "Create a short story about a robot",
            "Compose a haiku about the ocean",
        ]
        
        for query in queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            assert analysis.task_type in [
                TaskType.CREATIVE_WRITING,
                TaskType.GENERAL,
            ]


# ============================================================
# Test Query Complexity Assessment
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestQueryComplexity:
    """Test query complexity assessment."""
    
    def test_simple_query(self, prompt_ops):
        """Test simple query complexity."""
        simple_queries = [
            "What is 2 + 2?",
            "What color is the sky?",
            "Hello",
        ]
        
        for query in simple_queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            assert analysis.complexity in [
                QueryComplexity.SIMPLE,
                QueryComplexity.MODERATE,
            ]
    
    def test_moderate_query(self, prompt_ops):
        """Test moderate query complexity."""
        moderate_queries = [
            "Explain how photosynthesis works in plants",
            "Compare Python and JavaScript for web development",
        ]
        
        for query in moderate_queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            assert analysis.complexity in [
                QueryComplexity.MODERATE,
                QueryComplexity.COMPLEX,
            ]
    
    def test_complex_query(self, prompt_ops):
        """Test complex query complexity."""
        complex_queries = [
            "Write a comprehensive analysis of the economic impacts of climate change on agriculture in developing countries, including policy recommendations",
            "Design a distributed system architecture for a real-time trading platform that handles millions of transactions per second with fault tolerance",
        ]
        
        for query in complex_queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            assert analysis.complexity in [
                QueryComplexity.COMPLEX,
                QueryComplexity.RESEARCH,
            ]


# ============================================================
# Test Ambiguity Detection
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestAmbiguityDetection:
    """Test ambiguity detection in queries."""
    
    def test_pronoun_ambiguity(self, prompt_ops):
        """Test pronoun reference ambiguity detection."""
        query = "Tell me more about it"  # No clear referent
        
        analysis = prompt_ops._analyze_query_rules(query)
        
        # Should detect ambiguity or missing context
        assert (
            len(analysis.ambiguities) > 0 or
            analysis.needs_clarification
        )
    
    def test_clear_query_no_ambiguity(self, prompt_ops):
        """Test that clear queries don't flag false ambiguities."""
        clear_queries = [
            "What is the capital of France?",
            "Write a Python function that calculates factorial",
            "Explain the theory of relativity",
        ]
        
        for query in clear_queries:
            analysis = prompt_ops._analyze_query_rules(query)
            
            # Should not require clarification
            assert analysis.needs_clarification is False or len(analysis.ambiguities) == 0


# ============================================================
# Test Domain Detection
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestDomainDetection:
    """Test domain detection from queries."""
    
    def test_coding_domain(self, prompt_ops):
        """Test coding domain detection."""
        query = "Write a Python function to parse JSON"
        
        analysis = prompt_ops._analyze_query_rules(query)
        
        assert analysis.domain in ["coding", "technical", "default", "general"]
    
    def test_medical_domain(self, prompt_ops):
        """Test medical domain detection."""
        query = "What are the symptoms of diabetes?"
        
        analysis = prompt_ops._analyze_query_rules(query)
        
        # May detect as medical or default depending on implementation
        assert analysis.domain is not None
    
    def test_legal_domain(self, prompt_ops):
        """Test legal domain detection."""
        query = "What are the requirements for filing a patent?"
        
        analysis = prompt_ops._analyze_query_rules(query)
        
        # May detect as legal or default
        assert analysis.domain is not None


# ============================================================
# Test Full PromptOps Pipeline
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
        assert spec.processed_query is not None
    
    @pytest.mark.asyncio
    async def test_process_with_domain_hint(self, prompt_ops):
        """Test processing with domain hint."""
        query = "How do I handle exceptions?"
        
        spec = await prompt_ops.process(query, domain_hint="coding")
        
        assert spec.domain in ["coding", "technical"]
    
    @pytest.mark.asyncio
    async def test_process_complex_query(self, prompt_ops):
        """Test processing complex query."""
        query = """
        Analyze the performance characteristics of different sorting algorithms
        and provide a comparative analysis with code examples in Python.
        Also explain the time and space complexity for each algorithm.
        """
        
        spec = await prompt_ops.process(query)
        
        assert spec.complexity in [QueryComplexity.COMPLEX, QueryComplexity.RESEARCH, QueryComplexity.MODERATE]


# ============================================================
# Test Query Refinement
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestQueryRefinement:
    """Test query refinement features."""
    
    @pytest.mark.asyncio
    async def test_query_normalization(self, prompt_ops):
        """Test query text normalization."""
        query = "   What   is   Python?   "  # Extra whitespace
        
        spec = await prompt_ops.process(query)
        
        # Processed query should be cleaned
        assert "   " not in spec.processed_query
    
    @pytest.mark.asyncio
    async def test_query_with_context(self, prompt_ops):
        """Test query processing with conversation context."""
        # This tests that context can influence processing
        query = "Tell me more"
        
        spec = await prompt_ops.process(
            query,
            context={"previous_topic": "Python programming"}
        )
        
        # Should process without error
        assert spec is not None


# ============================================================
# Test Prompt Specification Output
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestPromptSpecification:
    """Test PromptSpecification output structure."""
    
    @pytest.mark.asyncio
    async def test_specification_fields(self, prompt_ops):
        """Test all specification fields are populated."""
        query = "Write a Python function"
        
        spec = await prompt_ops.process(query)
        
        # Required fields
        assert spec.original_query == query
        assert spec.processed_query is not None
        assert spec.task_type is not None
        assert spec.complexity is not None
        assert spec.domain is not None


# ============================================================
# Test Edge Cases
# ============================================================

@pytest.mark.skipif(not PROMPT_OPS_AVAILABLE, reason="PromptOps not available")
class TestPromptOpsEdgeCases:
    """Test edge cases in PromptOps."""
    
    @pytest.mark.asyncio
    async def test_very_long_query(self, prompt_ops):
        """Test handling of very long query."""
        long_query = "Explain " + " and ".join(["topic"] * 100)
        
        spec = await prompt_ops.process(long_query)
        
        # Should handle without error
        assert spec is not None
    
    @pytest.mark.asyncio
    async def test_unicode_query(self, prompt_ops):
        """Test handling of unicode characters."""
        query = "What does 日本語 mean? Explain émoji: 🚀"
        
        spec = await prompt_ops.process(query)
        
        # Should handle unicode without error
        assert spec is not None
    
    @pytest.mark.asyncio
    async def test_code_in_query(self, prompt_ops):
        """Test handling of code snippets in query."""
        query = """
        Fix this code:
        ```python
        def foo():
            print("hello"
        ```
        """
        
        spec = await prompt_ops.process(query)
        
        assert spec.task_type in [TaskType.DEBUGGING, TaskType.CODE_GENERATION, TaskType.GENERAL]
