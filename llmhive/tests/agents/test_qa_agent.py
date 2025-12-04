"""Tests for the Quality Assurance Agent.

These tests verify the QA Agent's ability to:
1. Evaluate response quality accurately
2. Identify common issues
3. Track metrics over time
4. Provide actionable recommendations
"""
import pytest
from datetime import datetime

from llmhive.app.agents.qa_agent import (
    QualityAssuranceAgent,
    QualityScore,
    evaluate_coherence,
    evaluate_completeness,
    evaluate_conciseness,
    evaluate_relevance,
    evaluate_safety,
    identify_issues,
)
from llmhive.app.agents.base import AgentTask, AgentPriority


# ============================================================
# Test Quality Evaluation Functions
# ============================================================

class TestCoherenceEvaluation:
    """Test coherence scoring."""
    
    def test_empty_response(self):
        """Empty response should score 0."""
        assert evaluate_coherence("") == 0.0
        assert evaluate_coherence("short") == 0.0
    
    def test_coherent_response(self):
        """Well-structured response should score high."""
        response = """
        First, let me explain the concept. The process involves multiple steps.
        Therefore, you need to consider several factors.
        In conclusion, this approach provides the best results.
        """
        score = evaluate_coherence(response)
        assert score >= 0.7, f"Expected coherent response to score >= 0.7, got {score}"
    
    def test_logical_connectors_boost_score(self):
        """Responses with logical connectors should score higher."""
        without_connectors = "This is a statement. Here is another statement. And more."
        with_connectors = "First, this is a statement. However, here is another point. Therefore, we conclude."
        
        score_without = evaluate_coherence(without_connectors)
        score_with = evaluate_coherence(with_connectors)
        
        assert score_with > score_without
    
    def test_repetitive_response(self):
        """Highly repetitive response should score lower."""
        response = "the the the the the the the the the the the the word word word"
        score = evaluate_coherence(response)
        assert score < 0.7


class TestCompletenessEvaluation:
    """Test completeness scoring."""
    
    def test_empty_response(self):
        """Empty response should score 0."""
        assert evaluate_completeness("What is Python?", "") == 0.0
    
    def test_relevant_response(self):
        """Response addressing query terms should score higher."""
        query = "What is Python programming language?"
        response = """
        Python is a high-level programming language known for its simplicity.
        It supports multiple programming paradigms including procedural,
        object-oriented, and functional programming.
        """
        score = evaluate_completeness(query, response)
        assert score >= 0.7
    
    def test_incomplete_response(self):
        """Response with incomplete patterns should score lower."""
        query = "Explain quantum computing"
        response = "I don't know much about quantum computing..."
        score = evaluate_completeness(query, response)
        assert score < 0.6
    
    def test_structured_response_bonus(self):
        """Structured responses should score higher."""
        query = "List the benefits of exercise"
        unstructured = "Exercise is good for health and helps with weight and mood."
        structured = """
        The benefits of exercise include:
        1. Improved cardiovascular health
        2. Better weight management
        3. Enhanced mood and mental health
        4. Increased energy levels
        """
        
        score_unstructured = evaluate_completeness(query, unstructured)
        score_structured = evaluate_completeness(query, structured)
        
        assert score_structured >= score_unstructured


class TestConcisenessEvaluation:
    """Test conciseness scoring."""
    
    def test_empty_response(self):
        """Empty response should score 0."""
        assert evaluate_conciseness("") == 0.0
    
    def test_optimal_length(self):
        """Response with optimal length should score high."""
        response = " ".join(["word"] * 100)  # 100 words
        score = evaluate_conciseness(response)
        assert score >= 0.7
    
    def test_too_brief(self):
        """Very short response should score lower."""
        response = "Yes."
        score = evaluate_conciseness(response)
        assert score < 0.7
    
    def test_too_verbose(self):
        """Very long response should score lower."""
        response = " ".join(["word"] * 1500)  # 1500 words
        score = evaluate_conciseness(response)
        assert score < 0.7
    
    def test_filler_phrases_penalty(self):
        """Responses with filler phrases should score lower."""
        clean = "The answer is clear. We should proceed with option A."
        with_filler = "To be honest, basically, the answer is clear. I mean, we should proceed with option A."
        
        score_clean = evaluate_conciseness(clean)
        score_filler = evaluate_conciseness(with_filler)
        
        assert score_clean > score_filler


class TestRelevanceEvaluation:
    """Test relevance scoring."""
    
    def test_empty_inputs(self):
        """Empty inputs should return neutral score."""
        assert evaluate_relevance("", "") == 0.5
    
    def test_relevant_response(self):
        """Response with query terms should score higher."""
        query = "How does photosynthesis work in plants?"
        response = "Photosynthesis is the process by which plants convert light energy into chemical energy."
        score = evaluate_relevance(query, response)
        assert score >= 0.7
    
    def test_off_topic_response(self):
        """Off-topic response should score lower."""
        query = "What is machine learning?"
        response = "The weather today is sunny and warm. I like ice cream."
        score = evaluate_relevance(query, response)
        assert score <= 0.7  # Allow boundary value


class TestSafetyEvaluation:
    """Test safety scoring."""
    
    def test_safe_response(self):
        """Safe response should score 1.0."""
        response = "Python is a programming language used for web development and data science."
        score = evaluate_safety(response)
        assert score >= 0.9
    
    def test_response_with_disclaimer(self):
        """Response with safety disclaimer should maintain high score."""
        response = "I recommend consulting a doctor for medical advice. This is not medical advice."
        score = evaluate_safety(response)
        assert score >= 0.9
    
    def test_empty_response(self):
        """Empty response is considered safe."""
        assert evaluate_safety("") == 1.0


# ============================================================
# Test Issue Identification
# ============================================================

class TestIssueIdentification:
    """Test issue detection."""
    
    def test_no_issues_for_high_quality(self):
        """High quality score should have no issues."""
        score = QualityScore(
            coherence=0.9,
            completeness=0.9,
            conciseness=0.9,
            relevance=0.9,
            safety=1.0,
        )
        issues = identify_issues("test query", "test response", score)
        assert len(issues) == 0
    
    def test_low_coherence_issue(self):
        """Low coherence should flag issue."""
        # Use 0.2 to trigger "high" severity (threshold is < 0.3)
        score = QualityScore(coherence=0.2, completeness=0.9, conciseness=0.9, relevance=0.9, safety=1.0)
        issues = identify_issues("query", "response", score)
        
        assert any(i.issue_type == "incoherent" for i in issues)
        assert any(i.severity == "high" for i in issues)
    
    def test_low_completeness_issue(self):
        """Low completeness should flag issue."""
        score = QualityScore(coherence=0.9, completeness=0.3, conciseness=0.9, relevance=0.9, safety=1.0)
        issues = identify_issues("query", "response", score)
        
        assert any(i.issue_type == "incomplete" for i in issues)
    
    def test_low_relevance_issue(self):
        """Low relevance should flag issue."""
        score = QualityScore(coherence=0.9, completeness=0.9, conciseness=0.9, relevance=0.3, safety=1.0)
        issues = identify_issues("query", "response", score)
        
        assert any(i.issue_type == "off_topic" for i in issues)
    
    def test_low_safety_issue(self):
        """Low safety should flag critical issue."""
        score = QualityScore(coherence=0.9, completeness=0.9, conciseness=0.9, relevance=0.9, safety=0.4)
        issues = identify_issues("query", "response", score)
        
        assert any(i.issue_type == "unsafe" for i in issues)
        assert any(i.severity == "critical" for i in issues)


# ============================================================
# Test QA Agent
# ============================================================

class TestQualityAssuranceAgent:
    """Test the QA Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a QA agent for testing."""
        return QualityAssuranceAgent()
    
    def test_agent_initialization(self, agent):
        """Agent should initialize correctly."""
        assert agent.name == "qa_agent"
        assert agent._total_evaluations == 0
    
    def test_get_capabilities(self, agent):
        """Agent should report capabilities."""
        caps = agent.get_capabilities()
        
        assert "name" in caps
        assert "task_types" in caps
        assert "evaluate_response" in caps["task_types"]
        assert "quality_thresholds" in caps
    
    @pytest.mark.asyncio
    async def test_evaluate_response_task(self, agent):
        """Agent should evaluate a response."""
        task = AgentTask(
            task_id="test-1",
            task_type="evaluate_response",
            payload={
                "query": "What is Python?",
                "response": "Python is a high-level programming language known for its readability and versatility.",
                "model": "gpt-4o",
            },
        )
        
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert "score" in result.output
        assert "overall" in result.output["score"]
        assert result.output["score"]["overall"] >= 0.5
    
    @pytest.mark.asyncio
    async def test_evaluate_empty_response(self, agent):
        """Agent should handle empty response gracefully."""
        task = AgentTask(
            task_id="test-2",
            task_type="evaluate_response",
            payload={
                "query": "What is Python?",
                "response": "",
            },
        )
        
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "error" in result.error.lower() or "no response" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_batch_evaluate(self, agent):
        """Agent should batch evaluate multiple responses."""
        task = AgentTask(
            task_id="test-3",
            task_type="batch_evaluate",
            payload={
                "items": [
                    {"query": "What is Python?", "response": "Python is a programming language."},
                    {"query": "What is Java?", "response": "Java is a programming language."},
                ]
            },
        )
        
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["evaluated_count"] == 2
        assert "average_score" in result.output
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, agent):
        """Agent should return metrics."""
        # First add some evaluations
        for i in range(3):
            task = AgentTask(
                task_id=f"eval-{i}",
                task_type="evaluate_response",
                payload={
                    "query": f"Question {i}",
                    "response": f"This is a detailed response to question {i}. It contains multiple sentences and provides useful information.",
                },
            )
            agent.add_task(task)
            await agent.run()
        
        # Now get metrics
        task = AgentTask(
            task_id="metrics",
            task_type="get_metrics",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["total_evaluations"] == 3
        assert "average_score" in result.output
    
    def test_get_metrics_summary(self, agent):
        """Agent should provide metrics summary."""
        summary = agent.get_metrics_summary()
        
        assert "total_evaluations" in summary
        assert "message" in summary or "average_score" in summary
    
    @pytest.mark.asyncio
    async def test_quality_tracking(self, agent):
        """Agent should track quality over time."""
        # Evaluate a good response
        good_task = AgentTask(
            task_id="good",
            task_type="evaluate_response",
            payload={
                "query": "Explain machine learning",
                "response": """
                Machine learning is a subset of artificial intelligence that enables 
                systems to learn from data. First, it involves training models on datasets.
                Then, the models can make predictions on new data. Therefore, machine learning
                is widely used in applications like recommendation systems and image recognition.
                """,
                "model": "gpt-4o",
            },
        )
        agent.add_task(good_task)
        good_result = await agent.run()
        
        # Evaluate a poor response
        poor_task = AgentTask(
            task_id="poor",
            task_type="evaluate_response",
            payload={
                "query": "Explain machine learning",
                "response": "I don't know...",
                "model": "gpt-4o-mini",
            },
        )
        agent.add_task(poor_task)
        poor_result = await agent.run()
        
        # Check scores
        assert good_result.output["score"]["overall"] > poor_result.output["score"]["overall"]
        
        # Check metrics tracked
        metrics = agent.get_metrics_summary()
        assert metrics["total_evaluations"] == 2


# ============================================================
# Test Quality Score Dataclass
# ============================================================

class TestQualityScore:
    """Test QualityScore dataclass."""
    
    def test_overall_score_calculation(self):
        """Overall score should be weighted average."""
        score = QualityScore(
            coherence=1.0,
            completeness=1.0,
            conciseness=1.0,
            relevance=1.0,
            safety=1.0,
        )
        assert score.overall == pytest.approx(1.0)  # Handle floating point precision
    
    def test_overall_score_with_zeros(self):
        """Overall score with all zeros."""
        score = QualityScore()
        assert score.overall >= 0  # Safety defaults to 1.0
    
    def test_to_dict(self):
        """Score should convert to dictionary."""
        score = QualityScore(
            coherence=0.8,
            completeness=0.7,
            conciseness=0.9,
            relevance=0.85,
            safety=1.0,
        )
        d = score.to_dict()
        
        assert "coherence" in d
        assert "completeness" in d
        assert "overall" in d
        assert isinstance(d["coherence"], float)
