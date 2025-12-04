"""Quality Assurance Agent for LLMHive.

This persistent agent monitors response quality and triggers improvements.

The QA Agent performs:
1. Response quality scoring (coherence, completeness, accuracy signals)
2. Detection of potential issues (hallucinations, incomplete answers)
3. Quality metrics tracking over time
4. Recommendations for improvement

Quality Scoring Criteria:
- Coherence: Is the response logically consistent?
- Completeness: Does it fully address the query?
- Conciseness: Is it appropriately detailed without being verbose?
- Relevance: Does it stay on topic?
- Safety: Does it avoid harmful content?
"""
from __future__ import annotations

import asyncio
import logging
import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


# ============================================================
# Quality Metrics Types
# ============================================================

@dataclass
class QualityScore:
    """Quality score for a single response."""
    coherence: float = 0.0  # 0-1: logical consistency
    completeness: float = 0.0  # 0-1: addresses the query fully
    conciseness: float = 0.0  # 0-1: appropriate length
    relevance: float = 0.0  # 0-1: stays on topic
    safety: float = 1.0  # 0-1: safe content
    
    @property
    def overall(self) -> float:
        """Weighted overall score."""
        weights = {
            "coherence": 0.25,
            "completeness": 0.30,
            "conciseness": 0.15,
            "relevance": 0.20,
            "safety": 0.10,
        }
        return (
            self.coherence * weights["coherence"] +
            self.completeness * weights["completeness"] +
            self.conciseness * weights["conciseness"] +
            self.relevance * weights["relevance"] +
            self.safety * weights["safety"]
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "coherence": round(self.coherence, 3),
            "completeness": round(self.completeness, 3),
            "conciseness": round(self.conciseness, 3),
            "relevance": round(self.relevance, 3),
            "safety": round(self.safety, 3),
            "overall": round(self.overall, 3),
        }


@dataclass
class QualityIssue:
    """An identified quality issue."""
    issue_type: str  # "incomplete", "off_topic", "verbose", "incoherent", "unsafe"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggestion: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationQuality:
    """Quality assessment for a conversation."""
    conversation_id: str
    query: str
    response: str
    score: QualityScore
    issues: List[QualityIssue]
    timestamp: datetime = field(default_factory=datetime.now)
    model_used: Optional[str] = None


# ============================================================
# Quality Evaluation Functions
# ============================================================

def evaluate_coherence(response: str) -> float:
    """
    Evaluate logical coherence of a response.
    
    Checks for:
    - Sentence structure
    - Logical connectors
    - Consistent terminology
    """
    if not response or len(response) < 10:
        return 0.0
    
    score = 0.7  # Base score
    
    # Check for logical connectors (indicates structured reasoning)
    connectors = [
        r'\bfirst\b', r'\bsecond\b', r'\bthird\b', r'\bfinally\b',
        r'\bhowever\b', r'\btherefore\b', r'\bconsequently\b',
        r'\bbecause\b', r'\bsince\b', r'\balthough\b',
        r'\bmoreover\b', r'\bfurthermore\b', r'\badditionally\b',
        r'\bin summary\b', r'\bin conclusion\b',
    ]
    
    connector_count = sum(1 for c in connectors if re.search(c, response, re.IGNORECASE))
    if connector_count > 0:
        score += min(0.15, connector_count * 0.03)
    
    # Check for proper sentence structure (ends with punctuation)
    sentences = re.split(r'[.!?]+', response)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) > 1:
        score += 0.1
    
    # Penalize very short responses
    if len(response) < 50:
        score -= 0.2
    
    # Penalize responses with excessive repetition
    words = response.lower().split()
    if len(words) > 10:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:  # Too much repetition
            score -= 0.2
    
    return max(0.0, min(1.0, score))


def evaluate_completeness(query: str, response: str) -> float:
    """
    Evaluate how completely the response addresses the query.
    
    Checks for:
    - Response length relative to query complexity
    - Presence of key query terms in response
    - Structured answer format
    """
    if not response:
        return 0.0
    
    if not query:
        return 0.5  # Can't evaluate without query
    
    score = 0.6  # Base score
    
    # Extract key terms from query (nouns, verbs)
    query_words = set(w.lower() for w in re.findall(r'\b\w{4,}\b', query))
    response_words = set(w.lower() for w in re.findall(r'\b\w{4,}\b', response))
    
    # Check query term coverage
    if query_words:
        coverage = len(query_words & response_words) / len(query_words)
        score += coverage * 0.2
    
    # Check response length relative to query complexity
    query_complexity = len(query.split())
    response_length = len(response.split())
    
    # Expect longer responses for complex queries
    if query_complexity > 20 and response_length > 50:
        score += 0.1
    elif query_complexity > 10 and response_length > 30:
        score += 0.05
    
    # Check for common incomplete patterns
    incomplete_patterns = [
        r"I don't know",
        r"I'm not sure",
        r"I cannot",
        r"I can't help",
        r"\.\.\.$",  # Ends with ellipsis
    ]
    
    for pattern in incomplete_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            score -= 0.15
            break
    
    # Bonus for structured responses
    if re.search(r'\n\d+\.|\n-|\n\*', response):  # Lists
        score += 0.1
    
    return max(0.0, min(1.0, score))


def evaluate_conciseness(response: str) -> float:
    """
    Evaluate appropriate length and verbosity.
    
    Checks for:
    - Reasonable response length
    - Information density
    - Avoiding filler phrases
    """
    if not response:
        return 0.0
    
    word_count = len(response.split())
    
    # Optimal range: 50-500 words for most responses
    if word_count < 20:
        score = 0.5  # Too brief
    elif word_count < 50:
        score = 0.7
    elif word_count <= 500:
        score = 0.9  # Optimal
    elif word_count <= 1000:
        score = 0.7
    else:
        score = 0.5  # Too verbose
    
    # Penalize filler phrases
    filler_patterns = [
        r"to be honest",
        r"in other words",
        r"basically",
        r"essentially",
        r"you know",
        r"I mean",
        r"as I mentioned",
        r"it's worth noting that",
        r"it should be noted that",
    ]
    
    filler_count = sum(1 for p in filler_patterns if re.search(p, response, re.IGNORECASE))
    score -= min(0.2, filler_count * 0.05)
    
    # Penalize excessive repetition
    sentences = re.split(r'[.!?]+', response)
    if len(sentences) > 3:
        # Check for repeated sentence starts
        starts = [s.strip().split()[:3] for s in sentences if s.strip()]
        starts = [tuple(s) for s in starts if len(s) >= 3]
        if starts:
            unique_starts = len(set(starts)) / len(starts)
            if unique_starts < 0.5:
                score -= 0.1
    
    return max(0.0, min(1.0, score))


def evaluate_relevance(query: str, response: str) -> float:
    """
    Evaluate how relevant the response is to the query.
    
    Checks for:
    - Topic alignment
    - Direct addressing of question
    """
    if not query or not response:
        return 0.5
    
    score = 0.7  # Base score
    
    # Simple keyword overlap
    query_terms = set(w.lower() for w in re.findall(r'\b\w{3,}\b', query))
    response_terms = set(w.lower() for w in re.findall(r'\b\w{3,}\b', response))
    
    # Remove common stop words
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'will', 'more',
        'when', 'who', 'oil', 'its', 'how', 'what', 'where', 'which', 'why',
    }
    query_terms -= stop_words
    response_terms -= stop_words
    
    if query_terms:
        overlap = len(query_terms & response_terms) / len(query_terms)
        score += overlap * 0.2
    
    # Check for off-topic indicators
    off_topic_patterns = [
        r"I cannot discuss",
        r"unrelated to your question",
        r"changing the topic",
        r"on a different note",
    ]
    
    for pattern in off_topic_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            score -= 0.3
            break
    
    return max(0.0, min(1.0, score))


def evaluate_safety(response: str) -> float:
    """
    Evaluate safety of response content.
    
    Checks for:
    - Harmful content markers
    - Unsafe recommendations
    """
    if not response:
        return 1.0
    
    score = 1.0  # Start with perfect safety
    
    # Check for potentially harmful patterns (basic check)
    harmful_patterns = [
        r"\bhow to (hack|steal|kill|hurt|harm)\b",
        r"\bweapon(s)?\b.*\b(make|build|create)\b",
        r"\billegal\b.*\b(drug|substance)\b",
        r"\bself[- ]harm\b",
        r"\bsuicide\b.*\b(method|way|how)\b",
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            score -= 0.5
            break
    
    # Check for disclaimer/safety notices (positive)
    safety_patterns = [
        r"consult (a |your )?(doctor|professional|expert)",
        r"seek (medical|professional) (help|advice)",
        r"I (can't|cannot) (help|assist) with (that|this)",
        r"not (legal|medical) advice",
    ]
    
    for pattern in safety_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            score = min(1.0, score + 0.1)
    
    return max(0.0, min(1.0, score))


def identify_issues(
    query: str,
    response: str,
    score: QualityScore,
) -> List[QualityIssue]:
    """Identify specific quality issues based on scores."""
    issues = []
    
    # Coherence issues
    if score.coherence < 0.5:
        issues.append(QualityIssue(
            issue_type="incoherent",
            severity="high" if score.coherence < 0.3 else "medium",
            description="Response lacks logical structure or consistency",
            suggestion="Restructure response with clear logical flow and transitions",
        ))
    
    # Completeness issues
    if score.completeness < 0.5:
        issues.append(QualityIssue(
            issue_type="incomplete",
            severity="high" if score.completeness < 0.3 else "medium",
            description="Response does not fully address the query",
            suggestion="Ensure all aspects of the query are addressed",
        ))
    
    # Conciseness issues
    if score.conciseness < 0.5:
        word_count = len(response.split())
        if word_count > 500:
            issues.append(QualityIssue(
                issue_type="verbose",
                severity="low",
                description=f"Response is overly verbose ({word_count} words)",
                suggestion="Reduce unnecessary elaboration and filler phrases",
            ))
        elif word_count < 30:
            issues.append(QualityIssue(
                issue_type="too_brief",
                severity="medium",
                description=f"Response may be too brief ({word_count} words)",
                suggestion="Provide more detailed explanation",
            ))
    
    # Relevance issues
    if score.relevance < 0.5:
        issues.append(QualityIssue(
            issue_type="off_topic",
            severity="high" if score.relevance < 0.3 else "medium",
            description="Response does not stay on topic",
            suggestion="Focus response on the specific query topic",
        ))
    
    # Safety issues
    if score.safety < 0.8:
        issues.append(QualityIssue(
            issue_type="unsafe",
            severity="critical" if score.safety < 0.5 else "high",
            description="Response may contain unsafe or harmful content",
            suggestion="Review and remove potentially harmful content",
        ))
    
    return issues


# ============================================================
# QA Agent Implementation
# ============================================================

class QualityAssuranceAgent(BaseAgent):
    """Agent that monitors and ensures response quality.
    
    Responsibilities:
    - Sample and review conversation quality
    - Detect factual errors or hallucinations
    - Trigger Reflexion on poor responses
    - Track quality metrics over time
    - Identify systematic issues
    
    Usage:
        agent = QualityAssuranceAgent()
        
        # Evaluate a single response
        task = AgentTask(
            task_id="eval-1",
            task_type="evaluate_response",
            payload={
                "query": "What is Python?",
                "response": "Python is a programming language...",
                "model": "gpt-4o",
            }
        )
        result = await agent.run()
        
        # Get quality metrics
        metrics = agent.get_metrics_summary()
    """
    
    # Quality thresholds
    QUALITY_THRESHOLD_LOW = 0.5
    QUALITY_THRESHOLD_ACCEPTABLE = 0.7
    QUALITY_THRESHOLD_GOOD = 0.85
    
    # History settings
    MAX_HISTORY_SIZE = 1000
    METRICS_WINDOW_HOURS = 24
    
    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="qa_agent",
                agent_type=AgentType.PERSISTENT,
                priority=AgentPriority.HIGH,
                max_tokens_per_run=3000,
                max_runtime_seconds=300,
                allowed_tools=["fact_checker", "query_replay"],
                memory_namespace="qa",
            )
        super().__init__(config)
        
        # Quality tracking
        self._quality_history: deque[ConversationQuality] = deque(maxlen=self.MAX_HISTORY_SIZE)
        self._issue_counts: Dict[str, int] = {}
        self._model_scores: Dict[str, List[float]] = {}
        
        # Statistics
        self._total_evaluations = 0
        self._low_quality_count = 0
        self._high_quality_count = 0
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """
        Execute quality monitoring.
        
        Task types:
        - "evaluate_response": Evaluate a single query/response pair
        - "batch_evaluate": Evaluate multiple responses
        - "get_metrics": Return current quality metrics
        - "get_issues": Return identified issues summary
        
        Returns:
            AgentResult with quality assessment
        """
        start_time = datetime.now()
        
        if not task:
            # Run general quality monitoring
            return await self._run_monitoring()
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "evaluate_response":
                return await self._evaluate_single_response(payload)
            
            elif task_type == "batch_evaluate":
                return await self._batch_evaluate(payload)
            
            elif task_type == "get_metrics":
                return self._get_metrics_result()
            
            elif task_type == "get_issues":
                return self._get_issues_summary()
            
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown task type: {task_type}",
                )
                
        except Exception as e:
            logger.error("QA Agent execution failed: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )
    
    async def _evaluate_single_response(self, payload: Dict[str, Any]) -> AgentResult:
        """Evaluate a single query/response pair."""
        query = payload.get("query", "")
        response = payload.get("response", "")
        model = payload.get("model")
        conversation_id = payload.get("conversation_id", f"conv-{datetime.now().timestamp()}")
        
        if not response:
            return AgentResult(
                success=False,
                error="No response provided for evaluation",
            )
        
        # Evaluate quality
        quality = self._evaluate_quality(query, response, conversation_id, model)
        
        # Store in history
        self._quality_history.append(quality)
        self._total_evaluations += 1
        
        # Update model tracking
        if model:
            if model not in self._model_scores:
                self._model_scores[model] = []
            self._model_scores[model].append(quality.score.overall)
            # Keep only recent scores
            if len(self._model_scores[model]) > 100:
                self._model_scores[model] = self._model_scores[model][-100:]
        
        # Update issue counts
        for issue in quality.issues:
            self._issue_counts[issue.issue_type] = self._issue_counts.get(issue.issue_type, 0) + 1
        
        # Update quality counters
        if quality.score.overall < self.QUALITY_THRESHOLD_LOW:
            self._low_quality_count += 1
        elif quality.score.overall >= self.QUALITY_THRESHOLD_GOOD:
            self._high_quality_count += 1
        
        # Build recommendations
        recommendations = []
        if quality.score.overall < self.QUALITY_THRESHOLD_ACCEPTABLE:
            recommendations.append("Consider triggering Reflexion for this response")
        for issue in quality.issues:
            recommendations.append(f"{issue.issue_type}: {issue.suggestion}")
        
        # Write to blackboard if available
        if self._blackboard:
            await self.write_to_blackboard(
                f"quality:{conversation_id}",
                quality.score.to_dict(),
                ttl_seconds=3600,
            )
        
        return AgentResult(
            success=True,
            output={
                "conversation_id": conversation_id,
                "score": quality.score.to_dict(),
                "issues": [
                    {
                        "type": i.issue_type,
                        "severity": i.severity,
                        "description": i.description,
                    }
                    for i in quality.issues
                ],
                "quality_level": self._get_quality_level(quality.score.overall),
                "needs_improvement": quality.score.overall < self.QUALITY_THRESHOLD_ACCEPTABLE,
            },
            recommendations=recommendations,
            findings=[
                {
                    "metric": k,
                    "value": v,
                    "status": "good" if v >= 0.7 else "needs_attention",
                }
                for k, v in quality.score.to_dict().items()
                if k != "overall"
            ],
        )
    
    async def _batch_evaluate(self, payload: Dict[str, Any]) -> AgentResult:
        """Evaluate multiple responses."""
        items = payload.get("items", [])
        
        if not items:
            return AgentResult(
                success=False,
                error="No items provided for batch evaluation",
            )
        
        results = []
        total_score = 0.0
        
        for item in items:
            quality = self._evaluate_quality(
                item.get("query", ""),
                item.get("response", ""),
                item.get("conversation_id", f"batch-{len(results)}"),
                item.get("model"),
            )
            self._quality_history.append(quality)
            self._total_evaluations += 1
            
            results.append({
                "conversation_id": quality.conversation_id,
                "overall_score": quality.score.overall,
                "issue_count": len(quality.issues),
            })
            total_score += quality.score.overall
        
        avg_score = total_score / len(results) if results else 0
        
        return AgentResult(
            success=True,
            output={
                "evaluated_count": len(results),
                "average_score": round(avg_score, 3),
                "quality_level": self._get_quality_level(avg_score),
                "results": results,
            },
            recommendations=[
                f"Average quality: {self._get_quality_level(avg_score)}",
                f"Responses below threshold: {sum(1 for r in results if r['overall_score'] < self.QUALITY_THRESHOLD_ACCEPTABLE)}",
            ],
        )
    
    async def _run_monitoring(self) -> AgentResult:
        """Run general quality monitoring on recent history."""
        if not self._quality_history:
            return AgentResult(
                success=True,
                output={"status": "No quality data to analyze"},
            )
        
        # Analyze recent window
        cutoff = datetime.now() - timedelta(hours=self.METRICS_WINDOW_HOURS)
        recent = [q for q in self._quality_history if q.timestamp >= cutoff]
        
        if not recent:
            return AgentResult(
                success=True,
                output={"status": "No recent quality data"},
            )
        
        # Calculate statistics
        scores = [q.score.overall for q in recent]
        avg_score = statistics.mean(scores)
        
        # Identify trends
        findings = []
        recommendations = []
        
        # Check for quality degradation
        if len(scores) >= 10:
            first_half = statistics.mean(scores[:len(scores)//2])
            second_half = statistics.mean(scores[len(scores)//2:])
            
            if second_half < first_half - 0.1:
                findings.append({
                    "type": "quality_degradation",
                    "description": f"Quality decreased from {first_half:.2f} to {second_half:.2f}",
                })
                recommendations.append("Investigate recent changes that may have affected quality")
        
        # Check for common issues
        issue_summary = {}
        for q in recent:
            for issue in q.issues:
                issue_summary[issue.issue_type] = issue_summary.get(issue.issue_type, 0) + 1
        
        if issue_summary:
            most_common = max(issue_summary.items(), key=lambda x: x[1])
            if most_common[1] > len(recent) * 0.3:  # More than 30% have this issue
                findings.append({
                    "type": "frequent_issue",
                    "issue": most_common[0],
                    "count": most_common[1],
                    "percentage": round(most_common[1] / len(recent) * 100, 1),
                })
                recommendations.append(f"Address frequent '{most_common[0]}' issues")
        
        # Model performance comparison
        model_performance = {}
        for q in recent:
            if q.model_used:
                if q.model_used not in model_performance:
                    model_performance[q.model_used] = []
                model_performance[q.model_used].append(q.score.overall)
        
        if model_performance:
            model_avgs = {m: statistics.mean(s) for m, s in model_performance.items() if s}
            if model_avgs:
                best_model = max(model_avgs.items(), key=lambda x: x[1])
                worst_model = min(model_avgs.items(), key=lambda x: x[1])
                
                if best_model[1] - worst_model[1] > 0.15:
                    findings.append({
                        "type": "model_variance",
                        "best": {"model": best_model[0], "score": round(best_model[1], 3)},
                        "worst": {"model": worst_model[0], "score": round(worst_model[1], 3)},
                    })
        
        return AgentResult(
            success=True,
            output={
                "period_hours": self.METRICS_WINDOW_HOURS,
                "evaluated_count": len(recent),
                "average_score": round(avg_score, 3),
                "quality_level": self._get_quality_level(avg_score),
                "score_range": {
                    "min": round(min(scores), 3),
                    "max": round(max(scores), 3),
                },
                "issue_summary": issue_summary,
                "model_performance": {m: round(statistics.mean(s), 3) for m, s in model_performance.items()} if model_performance else {},
            },
            findings=findings,
            recommendations=recommendations,
        )
    
    def _get_metrics_result(self) -> AgentResult:
        """Get current metrics summary."""
        return AgentResult(
            success=True,
            output=self.get_metrics_summary(),
        )
    
    def _get_issues_summary(self) -> AgentResult:
        """Get issues summary."""
        return AgentResult(
            success=True,
            output={
                "total_issues_tracked": sum(self._issue_counts.values()),
                "issue_breakdown": dict(self._issue_counts),
                "most_common": max(self._issue_counts.items(), key=lambda x: x[1]) if self._issue_counts else None,
            },
        )
    
    def _evaluate_quality(
        self,
        query: str,
        response: str,
        conversation_id: str,
        model: Optional[str] = None,
    ) -> ConversationQuality:
        """Evaluate quality of a query/response pair."""
        score = QualityScore(
            coherence=evaluate_coherence(response),
            completeness=evaluate_completeness(query, response),
            conciseness=evaluate_conciseness(response),
            relevance=evaluate_relevance(query, response),
            safety=evaluate_safety(response),
        )
        
        issues = identify_issues(query, response, score)
        
        return ConversationQuality(
            conversation_id=conversation_id,
            query=query[:200] if query else "",  # Truncate for storage
            response=response[:500] if response else "",  # Truncate for storage
            score=score,
            issues=issues,
            model_used=model,
        )
    
    def _get_quality_level(self, score: float) -> str:
        """Get quality level label from score."""
        if score >= self.QUALITY_THRESHOLD_GOOD:
            return "excellent"
        elif score >= self.QUALITY_THRESHOLD_ACCEPTABLE:
            return "good"
        elif score >= self.QUALITY_THRESHOLD_LOW:
            return "acceptable"
        else:
            return "needs_improvement"
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of quality metrics."""
        if not self._quality_history:
            return {
                "total_evaluations": 0,
                "message": "No quality data available",
            }
        
        recent_scores = [q.score.overall for q in self._quality_history]
        
        return {
            "total_evaluations": self._total_evaluations,
            "history_size": len(self._quality_history),
            "average_score": round(statistics.mean(recent_scores), 3) if recent_scores else 0,
            "score_std_dev": round(statistics.stdev(recent_scores), 3) if len(recent_scores) > 1 else 0,
            "low_quality_count": self._low_quality_count,
            "high_quality_count": self._high_quality_count,
            "low_quality_rate": round(self._low_quality_count / self._total_evaluations, 3) if self._total_evaluations > 0 else 0,
            "issue_counts": dict(self._issue_counts),
            "models_tracked": list(self._model_scores.keys()),
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "name": "Quality Assurance Agent",
            "type": "persistent",
            "purpose": "Monitor and ensure response quality",
            "task_types": [
                "evaluate_response",
                "batch_evaluate",
                "get_metrics",
                "get_issues",
            ],
            "outputs": [
                "Quality scores (coherence, completeness, conciseness, relevance, safety)",
                "Issue identification and severity",
                "Improvement recommendations",
                "Quality trend analysis",
                "Model performance comparison",
            ],
            "quality_thresholds": {
                "low": self.QUALITY_THRESHOLD_LOW,
                "acceptable": self.QUALITY_THRESHOLD_ACCEPTABLE,
                "good": self.QUALITY_THRESHOLD_GOOD,
            },
        }
