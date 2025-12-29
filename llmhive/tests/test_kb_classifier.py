"""
Unit tests for the LLMHive KB Query Classifier.

Tests classification across different query types.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from llmhive.kb.query_classifier import (
    QueryClassifier,
    ClassificationResult,
    ReasoningType,
    RiskLevel,
    Domain,
    get_query_classifier,
    reset_classifier_instance,
)
from llmhive.kb.pipeline_selector import (
    PipelineName,
    select_pipeline,
)


class TestQueryClassifier:
    """Test the QueryClassifier."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset classifier before each test."""
        reset_classifier_instance()
    
    def test_math_classification(self):
        """Test mathematical query classification."""
        classifier = get_query_classifier()
        
        queries = [
            "Prove that sqrt(2) is irrational",
            "Calculate the integral of x^2",
            "Solve for x: 2x + 3 = 7",
        ]
        
        for query in queries:
            result = classifier.classify(query)
            assert result.domain == Domain.MATH, f"Query '{query}' should be MATH domain"
    
    def test_coding_classification(self):
        """Test coding query classification."""
        classifier = get_query_classifier()
        
        queries = [
            "Write a Python function to sort a list",
            "Debug this JavaScript code",
            "Fix this Java binary search algorithm",
        ]
        
        for query in queries:
            result = classifier.classify(query)
            assert result.domain == Domain.CODING, f"Query '{query}' should be CODING domain"
    
    def test_high_risk_medical(self):
        """Test high-risk medical query classification."""
        classifier = get_query_classifier()
        
        queries = [
            "What medication should I take for severe headache?",
            "Is this a symptom of diabetes?",
        ]
        
        for query in queries:
            result = classifier.classify(query)
            assert result.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH), \
                f"Query '{query}' should be medium or high risk"
    
    def test_citation_detection(self):
        """Test citation request detection."""
        classifier = get_query_classifier()
        
        # Should request citations
        query_with_cite = "According to scientific research, what causes climate change? Please cite sources."
        result = classifier.classify(query_with_cite)
        assert result.citations_requested, "Should detect citation request"
        
        # Should not request citations
        query_no_cite = "What is 2 + 2?"
        result = classifier.classify(query_no_cite)
        assert not result.citations_requested, "Should not detect citation request"
    
    def test_empty_query(self):
        """Test empty query handling."""
        classifier = get_query_classifier()
        
        result = classifier.classify("")
        assert result.reasoning_type == ReasoningType.GENERAL
        assert result.confidence == 0.5
        
        result = classifier.classify("   ")
        assert result.reasoning_type == ReasoningType.GENERAL


class TestPipelineSelector:
    """Test the pipeline selector."""
    
    def test_math_pipeline(self):
        """Test math queries get MATH_REASONING pipeline."""
        selection = select_pipeline("Prove that sqrt(2) is irrational")
        assert selection.pipeline_name == PipelineName.MATH_REASONING
    
    def test_coding_pipeline_with_sandbox(self):
        """Test coding queries with sandbox get CODING_AGENT pipeline."""
        selection = select_pipeline(
            "Write a Python function to sort a list",
            tools_available=["code_sandbox"]
        )
        assert selection.pipeline_name == PipelineName.CODING_AGENT
    
    def test_coding_pipeline_without_sandbox(self):
        """Test coding queries without sandbox get SIMPLE_DIRECT pipeline."""
        selection = select_pipeline(
            "Write a Python function to sort a list",
            tools_available=[]
        )
        assert selection.pipeline_name == PipelineName.SIMPLE_DIRECT
    
    def test_rag_pipeline_with_search(self):
        """Test factual queries with search get RAG pipeline."""
        selection = select_pipeline(
            "What is the capital of France?",
            tools_available=["web_search"]
        )
        assert selection.pipeline_name == PipelineName.RAG_CITATION_COVE
    
    def test_cost_optimized_routing(self):
        """Test low cost budget triggers cost-optimized routing."""
        selection = select_pipeline(
            "Tell me about AI",
            cost_budget="low"
        )
        assert selection.pipeline_name == PipelineName.COST_OPTIMIZED_ROUTING
    
    def test_tool_use_pipeline(self):
        """Test tool use queries get TOOL_USE_REACT pipeline."""
        selection = select_pipeline(
            "Search for the latest news about AI",
            tools_available=["web_search"]
        )
        assert selection.pipeline_name == PipelineName.TOOL_USE_REACT


def test_classifier_singleton():
    """Test classifier singleton pattern."""
    reset_classifier_instance()
    c1 = get_query_classifier()
    c2 = get_query_classifier()
    assert c1 is c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
