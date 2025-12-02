"""Smart Ensemble - Intelligent Model Selection and Combination.

This module optimizes which models to use for each query and how to
combine their outputs for maximum accuracy.

Key strategies:
1. Task-specific model routing (use best model for each task type)
2. Confidence-weighted combination (trust models that know they're right)
3. Skill-based selection (match model strengths to query needs)
4. Dynamic adaptation (learn from outcomes)

The goal: Never use the wrong model for a task.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum, auto
from collections import defaultdict
import random

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """Categories of tasks for model routing."""
    CODING = "coding"
    MATH = "math"
    REASONING = "reasoning"
    CREATIVE = "creative"
    FACTUAL = "factual"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    CONVERSATION = "conversation"
    INSTRUCTION = "instruction"
    MULTILINGUAL = "multilingual"


@dataclass
class ModelProfile:
    """Profile of a model's capabilities."""
    model_id: str
    name: str
    provider: str
    
    # Capability scores (0-1)
    skills: Dict[TaskCategory, float] = field(default_factory=dict)
    
    # Performance metrics
    avg_latency_ms: float = 1000
    cost_per_1k_tokens: float = 0.01
    success_rate: float = 0.9
    
    # Metadata
    context_length: int = 8192
    supports_function_calling: bool = False
    supports_vision: bool = False
    
    def score_for_task(self, task: TaskCategory) -> float:
        """Get model's score for a task type."""
        return self.skills.get(task, 0.5)


@dataclass
class EnsembleResult:
    """Result from ensemble selection/combination."""
    final_answer: str
    confidence: float
    models_used: List[str]
    contributions: Dict[str, float]  # Model -> contribution weight
    method: str
    reasoning: str = ""


class SmartEnsemble:
    """Intelligent model selection and output combination.
    
    This is what makes multi-model orchestration beat single models:
    - Pick the RIGHT model for each sub-task
    - Combine outputs optimally based on confidence
    - Learn which models excel at what
    """
    
    def __init__(self, model_caller: Callable):
        """Initialize smart ensemble.
        
        Args:
            model_caller: Async function(model_id, prompt) -> response
        """
        self.model_caller = model_caller
        self._profiles: Dict[str, ModelProfile] = {}
        self._performance_history: Dict[str, List[bool]] = defaultdict(list)
        
        # Initialize default profiles
        self._init_default_profiles()
        
        logger.info("SmartEnsemble initialized")
    
    def _init_default_profiles(self) -> None:
        """Initialize default model profiles based on known strengths."""
        # GPT-4o - Strong all-around, especially reasoning
        self._profiles["gpt-4o"] = ModelProfile(
            model_id="gpt-4o",
            name="GPT-4o",
            provider="openai",
            skills={
                TaskCategory.CODING: 0.95,
                TaskCategory.MATH: 0.90,
                TaskCategory.REASONING: 0.95,
                TaskCategory.CREATIVE: 0.90,
                TaskCategory.FACTUAL: 0.85,
                TaskCategory.ANALYSIS: 0.95,
                TaskCategory.SUMMARIZATION: 0.90,
                TaskCategory.CONVERSATION: 0.90,
                TaskCategory.INSTRUCTION: 0.95,
                TaskCategory.MULTILINGUAL: 0.85,
            },
            avg_latency_ms=1500,
            cost_per_1k_tokens=0.01,
            context_length=128000,
            supports_function_calling=True,
            supports_vision=True,
        )
        
        # Claude Sonnet 4 - Excellent for long-form, analysis
        self._profiles["claude-sonnet-4-20250514"] = ModelProfile(
            model_id="claude-sonnet-4-20250514",
            name="Claude Sonnet 4",
            provider="anthropic",
            skills={
                TaskCategory.CODING: 0.92,
                TaskCategory.MATH: 0.85,
                TaskCategory.REASONING: 0.92,
                TaskCategory.CREATIVE: 0.95,
                TaskCategory.FACTUAL: 0.88,
                TaskCategory.ANALYSIS: 0.95,
                TaskCategory.SUMMARIZATION: 0.95,
                TaskCategory.CONVERSATION: 0.95,
                TaskCategory.INSTRUCTION: 0.92,
                TaskCategory.MULTILINGUAL: 0.90,
            },
            avg_latency_ms=2000,
            cost_per_1k_tokens=0.015,
            context_length=200000,
            supports_function_calling=True,
        )
        
        # DeepSeek - Excellent for coding
        self._profiles["deepseek-chat"] = ModelProfile(
            model_id="deepseek-chat",
            name="DeepSeek V3",
            provider="deepseek",
            skills={
                TaskCategory.CODING: 0.98,
                TaskCategory.MATH: 0.95,
                TaskCategory.REASONING: 0.88,
                TaskCategory.CREATIVE: 0.70,
                TaskCategory.FACTUAL: 0.80,
                TaskCategory.ANALYSIS: 0.85,
                TaskCategory.SUMMARIZATION: 0.80,
                TaskCategory.CONVERSATION: 0.75,
                TaskCategory.INSTRUCTION: 0.85,
                TaskCategory.MULTILINGUAL: 0.70,
            },
            avg_latency_ms=800,
            cost_per_1k_tokens=0.001,
            context_length=64000,
        )
        
        # Gemini - Good multimodal, fast
        self._profiles["gemini-2.5-pro"] = ModelProfile(
            model_id="gemini-2.5-pro",
            name="Gemini 2.5 Pro",
            provider="google",
            skills={
                TaskCategory.CODING: 0.88,
                TaskCategory.MATH: 0.90,
                TaskCategory.REASONING: 0.88,
                TaskCategory.CREATIVE: 0.85,
                TaskCategory.FACTUAL: 0.90,
                TaskCategory.ANALYSIS: 0.88,
                TaskCategory.SUMMARIZATION: 0.90,
                TaskCategory.CONVERSATION: 0.88,
                TaskCategory.INSTRUCTION: 0.88,
                TaskCategory.MULTILINGUAL: 0.95,
            },
            avg_latency_ms=1000,
            cost_per_1k_tokens=0.005,
            context_length=2000000,
            supports_function_calling=True,
            supports_vision=True,
        )
        
        # Grok - Fast, good at current events
        self._profiles["grok-2"] = ModelProfile(
            model_id="grok-2",
            name="Grok 2",
            provider="xai",
            skills={
                TaskCategory.CODING: 0.85,
                TaskCategory.MATH: 0.82,
                TaskCategory.REASONING: 0.85,
                TaskCategory.CREATIVE: 0.88,
                TaskCategory.FACTUAL: 0.92,  # Good at current events
                TaskCategory.ANALYSIS: 0.85,
                TaskCategory.SUMMARIZATION: 0.85,
                TaskCategory.CONVERSATION: 0.90,
                TaskCategory.INSTRUCTION: 0.85,
                TaskCategory.MULTILINGUAL: 0.75,
            },
            avg_latency_ms=800,
            cost_per_1k_tokens=0.005,
            context_length=32000,
        )
    
    def detect_task_category(self, query: str) -> TaskCategory:
        """Detect the primary task category of a query."""
        query_lower = query.lower()
        
        # Coding detection
        code_keywords = ["code", "function", "implement", "debug", "program", "script", 
                        "python", "javascript", "api", "error", "bug", "class"]
        if any(kw in query_lower for kw in code_keywords):
            return TaskCategory.CODING
        
        # Math detection
        math_keywords = ["calculate", "solve", "equation", "math", "sum", "product",
                        "integral", "derivative", "algebra", "="]
        if any(kw in query_lower for kw in math_keywords):
            return TaskCategory.MATH
        
        # Reasoning detection
        reasoning_keywords = ["why", "explain", "reasoning", "logic", "because",
                            "if then", "conclude", "deduce", "infer"]
        if any(kw in query_lower for kw in reasoning_keywords):
            return TaskCategory.REASONING
        
        # Creative detection
        creative_keywords = ["write", "story", "poem", "creative", "imagine",
                           "fiction", "narrative", "compose"]
        if any(kw in query_lower for kw in creative_keywords):
            return TaskCategory.CREATIVE
        
        # Factual detection
        factual_keywords = ["what is", "who is", "when did", "where is", "fact",
                          "define", "name", "list", "how many"]
        if any(kw in query_lower for kw in factual_keywords):
            return TaskCategory.FACTUAL
        
        # Analysis detection
        analysis_keywords = ["analyze", "compare", "evaluate", "assess", "review",
                           "examine", "critique", "pros cons"]
        if any(kw in query_lower for kw in analysis_keywords):
            return TaskCategory.ANALYSIS
        
        # Summarization detection
        summary_keywords = ["summarize", "summary", "brief", "tldr", "main points",
                          "key takeaways", "overview"]
        if any(kw in query_lower for kw in summary_keywords):
            return TaskCategory.SUMMARIZATION
        
        return TaskCategory.CONVERSATION  # Default
    
    def select_best_model(
        self,
        query: str,
        available_models: List[str],
        task_category: Optional[TaskCategory] = None,
        optimize_for: str = "quality"  # "quality", "speed", "cost"
    ) -> str:
        """Select the single best model for a query.
        
        Args:
            query: The query to process
            available_models: Models that are available
            task_category: Optional pre-detected category
            optimize_for: What to optimize ("quality", "speed", "cost")
            
        Returns:
            Best model ID
        """
        if not task_category:
            task_category = self.detect_task_category(query)
        
        # Score each available model
        scores = []
        for model_id in available_models:
            profile = self._profiles.get(model_id)
            if not profile:
                scores.append((model_id, 0.5))
                continue
            
            # Base score from task skill
            base_score = profile.score_for_task(task_category)
            
            # Adjust for optimization target
            if optimize_for == "speed":
                # Penalize slow models
                latency_factor = 1 - (profile.avg_latency_ms / 5000)
                score = base_score * 0.7 + latency_factor * 0.3
            elif optimize_for == "cost":
                # Penalize expensive models
                cost_factor = 1 - (profile.cost_per_1k_tokens / 0.03)
                score = base_score * 0.6 + cost_factor * 0.4
            else:  # quality
                score = base_score
            
            # Adjust for historical performance
            history = self._performance_history.get(model_id, [])
            if len(history) >= 5:
                recent_success = sum(history[-10:]) / len(history[-10:])
                score = score * 0.8 + recent_success * 0.2
            
            scores.append((model_id, score))
        
        # Select best
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0]
    
    def select_ensemble(
        self,
        query: str,
        available_models: List[str],
        max_models: int = 3,
        task_category: Optional[TaskCategory] = None,
    ) -> List[str]:
        """Select an optimal ensemble of models for a query.
        
        Selects models that complement each other's strengths.
        """
        if not task_category:
            task_category = self.detect_task_category(query)
        
        # Score all models
        model_scores = []
        for model_id in available_models:
            profile = self._profiles.get(model_id)
            if profile:
                score = profile.score_for_task(task_category)
                model_scores.append((model_id, score, profile))
            else:
                model_scores.append((model_id, 0.5, None))
        
        # Sort by score
        model_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select diverse ensemble
        selected = []
        selected_providers = set()
        
        for model_id, score, profile in model_scores:
            if len(selected) >= max_models:
                break
            
            # Prefer diversity in providers
            provider = profile.provider if profile else "unknown"
            if provider in selected_providers and len(selected) < max_models - 1:
                # Skip if we already have this provider (unless we need to fill)
                continue
            
            selected.append(model_id)
            selected_providers.add(provider)
        
        return selected
    
    async def weighted_combine(
        self,
        responses: Dict[str, str],
        query: str,
        task_category: Optional[TaskCategory] = None,
    ) -> EnsembleResult:
        """Combine multiple model responses with intelligent weighting.
        
        Args:
            responses: Dict of model_id -> response
            query: Original query
            task_category: Task category
            
        Returns:
            EnsembleResult with combined answer
        """
        if not task_category:
            task_category = self.detect_task_category(query)
        
        if len(responses) == 1:
            model_id, response = list(responses.items())[0]
            return EnsembleResult(
                final_answer=response,
                confidence=0.8,
                models_used=[model_id],
                contributions={model_id: 1.0},
                method="single_model",
            )
        
        # Calculate weights for each response
        weights = {}
        for model_id, response in responses.items():
            profile = self._profiles.get(model_id)
            
            # Base weight from model skill
            if profile:
                skill_weight = profile.score_for_task(task_category)
            else:
                skill_weight = 0.5
            
            # Adjust for response quality indicators
            quality_weight = self._assess_response_quality(response)
            
            # Combine
            weights[model_id] = skill_weight * 0.6 + quality_weight * 0.4
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Select or combine based on agreement
        unique_answers = self._extract_unique_answers(responses)
        
        if len(unique_answers) == 1:
            # All agree - high confidence
            answer = list(responses.values())[0]
            confidence = 0.95
            method = "unanimous"
        elif self._answers_similar(list(responses.values())):
            # Similar answers - pick highest weighted
            best_model = max(weights.keys(), key=lambda x: weights[x])
            answer = responses[best_model]
            confidence = 0.85
            method = "weighted_selection"
        else:
            # Disagreement - synthesize
            answer = await self._synthesize_responses(
                query, responses, weights, task_category
            )
            confidence = 0.75
            method = "synthesis"
        
        return EnsembleResult(
            final_answer=answer,
            confidence=confidence,
            models_used=list(responses.keys()),
            contributions=weights,
            method=method,
        )
    
    def _assess_response_quality(self, response: str) -> float:
        """Assess quality of a response (heuristic)."""
        score = 0.5
        
        # Length (moderate is good)
        length = len(response)
        if 100 < length < 2000:
            score += 0.1
        elif length > 50:
            score += 0.05
        
        # Has structure (paragraphs, lists)
        if "\n" in response:
            score += 0.1
        if any(marker in response for marker in ["1.", "- ", "* ", "•"]):
            score += 0.1
        
        # Confidence language
        confident_markers = ["therefore", "thus", "in conclusion", "the answer is"]
        if any(m in response.lower() for m in confident_markers):
            score += 0.1
        
        # Uncertainty language (slight penalty)
        uncertain_markers = ["i'm not sure", "i think maybe", "possibly", "might be"]
        if any(m in response.lower() for m in uncertain_markers):
            score -= 0.1
        
        return max(0, min(1, score))
    
    def _extract_unique_answers(self, responses: Dict[str, str]) -> set:
        """Extract unique final answers from responses."""
        answers = set()
        for response in responses.values():
            # Extract just the final answer part
            answer = self._get_answer_part(response)
            answers.add(answer.lower().strip())
        return answers
    
    def _get_answer_part(self, response: str) -> str:
        """Extract the answer portion of a response."""
        markers = ["final answer:", "answer:", "therefore:", "thus:"]
        response_lower = response.lower()
        
        for marker in markers:
            if marker in response_lower:
                idx = response_lower.rfind(marker)
                return response[idx + len(marker):].split("\n")[0].strip()
        
        # Last line
        lines = [l.strip() for l in response.split("\n") if l.strip()]
        return lines[-1] if lines else response
    
    def _answers_similar(self, responses: List[str]) -> bool:
        """Check if responses give similar answers."""
        if len(responses) <= 1:
            return True
        
        answers = [self._get_answer_part(r).lower() for r in responses]
        
        # Check if answers share significant overlap
        first_words = set(answers[0].split()[:5])
        for ans in answers[1:]:
            other_words = set(ans.split()[:5])
            overlap = len(first_words & other_words)
            if overlap < 2:
                return False
        
        return True
    
    async def _synthesize_responses(
        self,
        query: str,
        responses: Dict[str, str],
        weights: Dict[str, float],
        task_category: TaskCategory,
    ) -> str:
        """Synthesize multiple disagreeing responses into one answer."""
        # Use highest-weighted model to synthesize
        synthesis_model = max(weights.keys(), key=lambda x: weights[x])
        
        responses_text = "\n\n".join([
            f"Expert {i+1} ({weights.get(model, 0):.0%} weight):\n{resp[:500]}"
            for i, (model, resp) in enumerate(responses.items())
        ])
        
        synthesis_prompt = f"""Multiple experts answered this question differently.

Question: {query}

Expert answers:
{responses_text}

Synthesize these into the best answer. Consider:
1. Which points are agreed upon?
2. Where there's disagreement, which reasoning is stronger?
3. What's the most accurate and complete answer?

Best answer:"""
        
        synthesized = await self.model_caller(synthesis_model, synthesis_prompt)
        return synthesized
    
    def record_outcome(
        self,
        model_id: str,
        success: bool,
        task_category: Optional[TaskCategory] = None
    ) -> None:
        """Record outcome for learning."""
        self._performance_history[model_id].append(success)
        
        # Keep last 100 results
        if len(self._performance_history[model_id]) > 100:
            self._performance_history[model_id] = self._performance_history[model_id][-100:]
    
    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all models."""
        stats = {}
        for model_id, profile in self._profiles.items():
            history = self._performance_history.get(model_id, [])
            recent_success = sum(history[-20:]) / len(history[-20:]) if history else 0.5
            
            stats[model_id] = {
                "name": profile.name,
                "provider": profile.provider,
                "top_skills": sorted(
                    profile.skills.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3],
                "recent_success_rate": recent_success,
                "total_uses": len(history),
            }
        return stats


# Global instance
_smart_ensemble: Optional[SmartEnsemble] = None


def get_smart_ensemble(model_caller: Optional[Callable] = None) -> SmartEnsemble:
    """Get or create smart ensemble."""
    global _smart_ensemble
    if _smart_ensemble is None:
        if model_caller is None:
            async def dummy(model, prompt):
                return f"Response from {model}"
            model_caller = dummy
        _smart_ensemble = SmartEnsemble(model_caller)
    return _smart_ensemble

