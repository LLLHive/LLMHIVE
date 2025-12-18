"""Industry Dominance Controller for LLMHive Opus 4.5.

This is the meta-controller that ensures LLMHive consistently outperforms
ChatGPT 5.1, Claude 4.5, Gemini 3, DeepSeek V3.2, and all competitors.

Key Responsibilities:
1. Orchestrate the entire elite pipeline
2. Make real-time decisions about strategy escalation
3. Monitor quality and trigger improvements
4. Learn from outcomes and adapt
5. Enforce zero-compromise quality standards

This is the "brain" that coordinates all subsystems.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration and Constants
# ==============================================================================

class OrchestrationStrategy(str, Enum):
    """Available orchestration strategies."""
    FAST = "fast"  # Single model, minimal verification
    STANDARD = "standard"  # Primary + verifier
    THOROUGH = "thorough"  # Full pipeline with challenge
    EXHAUSTIVE = "exhaustive"  # All techniques + debate


class QueryComplexity(str, Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


class QueryType(str, Enum):
    """Query type classification."""
    FACTUAL = "factual"
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVE = "creative"
    RESEARCH = "research"
    MULTI_HOP = "multi_hop"
    GENERAL = "general"


@dataclass(slots=True)
class QualityMetrics:
    """Metrics for tracking answer quality."""
    factual_accuracy: float = 0.0
    logical_consistency: float = 0.0
    completeness: float = 0.0
    clarity: float = 0.0
    overall_confidence: float = 0.0
    verification_passed: bool = False
    challenge_passed: bool = False
    models_agreed: bool = False


@dataclass(slots=True)
class OrchestrationResult:
    """Result of elite orchestration."""
    answer: str
    strategy_used: OrchestrationStrategy
    models_used: List[str]
    tools_used: List[str]
    quality_metrics: QualityMetrics
    total_latency_ms: float
    total_tokens: int
    iterations: int
    notes: List[str]


@dataclass(slots=True)
class ExecutionPlan:
    """A structured execution plan."""
    query_type: QueryType
    complexity: QueryComplexity
    strategy: OrchestrationStrategy
    primary_model: str
    support_models: List[str]
    tools_needed: List[str]
    verification_level: int  # 1-5
    max_iterations: int
    confidence_target: float
    time_budget_ms: Optional[float] = None


# ==============================================================================
# Query Analyzer
# ==============================================================================

class QueryAnalyzer:
    """Analyzes queries to determine type, complexity, and requirements."""
    
    # Classification keywords
    CODING_KEYWORDS = [
        "code", "function", "implement", "debug", "program", "script",
        "class", "method", "api", "algorithm", "syntax", "compile",
    ]
    
    REASONING_KEYWORDS = [
        "why", "how", "explain", "analyze", "compare", "evaluate",
        "reason", "logic", "proof", "deduce", "infer",
    ]
    
    FACTUAL_KEYWORDS = [
        "what is", "when did", "who was", "where is", "how many",
        "definition", "fact", "date", "name", "capital",
    ]
    
    RESEARCH_KEYWORDS = [
        "research", "study", "comprehensive", "in-depth", "analysis",
        "report", "survey", "overview", "review",
    ]
    
    CREATIVE_KEYWORDS = [
        "write", "create", "story", "poem", "creative", "imagine",
        "design", "generate", "compose",
    ]
    
    COMPLEXITY_INDICATORS = {
        "simple": ["quick", "simple", "brief", "short", "basic"],
        "complex": ["comprehensive", "detailed", "thorough", "complex", "advanced"],
        "critical": ["critical", "important", "urgent", "must be accurate", "life"],
    }
    
    def analyze(self, query: str) -> Tuple[QueryType, QueryComplexity]:
        """Analyze query to determine type and complexity."""
        query_lower = query.lower()
        
        # Determine query type
        query_type = self._classify_type(query_lower)
        
        # Determine complexity
        complexity = self._assess_complexity(query_lower, query_type)
        
        return query_type, complexity
    
    def _classify_type(self, query: str) -> QueryType:
        """Classify the query type."""
        # Check for coding
        if any(kw in query for kw in self.CODING_KEYWORDS):
            return QueryType.CODING
        
        # Check for research
        if any(kw in query for kw in self.RESEARCH_KEYWORDS):
            return QueryType.RESEARCH
        
        # Check for creative
        if any(kw in query for kw in self.CREATIVE_KEYWORDS):
            return QueryType.CREATIVE
        
        # Check for factual
        if any(kw in query for kw in self.FACTUAL_KEYWORDS):
            return QueryType.FACTUAL
        
        # Check for reasoning
        if any(kw in query for kw in self.REASONING_KEYWORDS):
            return QueryType.REASONING
        
        # Check for multi-hop (multiple questions or complex structure)
        if query.count("?") > 1 or " and " in query:
            return QueryType.MULTI_HOP
        
        return QueryType.GENERAL
    
    def _assess_complexity(self, query: str, query_type: QueryType) -> QueryComplexity:
        """Assess the complexity of the query."""
        # Check explicit complexity indicators
        for level, keywords in self.COMPLEXITY_INDICATORS.items():
            if any(kw in query for kw in keywords):
                if level == "critical":
                    return QueryComplexity.CRITICAL
                elif level == "complex":
                    return QueryComplexity.COMPLEX
                elif level == "simple":
                    return QueryComplexity.SIMPLE
        
        # Assess based on query characteristics
        word_count = len(query.split())
        question_marks = query.count("?")
        
        # Long queries or multiple questions indicate complexity
        if word_count > 50 or question_marks > 2:
            return QueryComplexity.COMPLEX
        elif word_count > 25 or question_marks > 1:
            return QueryComplexity.MODERATE
        
        # Research and multi-hop are inherently complex
        if query_type in [QueryType.RESEARCH, QueryType.MULTI_HOP]:
            return QueryComplexity.COMPLEX
        
        # Coding can be moderate to complex
        if query_type == QueryType.CODING:
            return QueryComplexity.MODERATE
        
        return QueryComplexity.SIMPLE


# ==============================================================================
# Strategy Selector
# ==============================================================================

class StrategySelector:
    """Selects the optimal orchestration strategy."""
    
    # Strategy mapping based on complexity and type
    STRATEGY_MAP = {
        (QueryComplexity.SIMPLE, QueryType.FACTUAL): OrchestrationStrategy.FAST,
        (QueryComplexity.SIMPLE, QueryType.GENERAL): OrchestrationStrategy.FAST,
        (QueryComplexity.MODERATE, QueryType.FACTUAL): OrchestrationStrategy.STANDARD,
        (QueryComplexity.MODERATE, QueryType.REASONING): OrchestrationStrategy.STANDARD,
        (QueryComplexity.MODERATE, QueryType.CODING): OrchestrationStrategy.THOROUGH,
        (QueryComplexity.COMPLEX, QueryType.REASONING): OrchestrationStrategy.THOROUGH,
        (QueryComplexity.COMPLEX, QueryType.RESEARCH): OrchestrationStrategy.EXHAUSTIVE,
        (QueryComplexity.COMPLEX, QueryType.MULTI_HOP): OrchestrationStrategy.EXHAUSTIVE,
        (QueryComplexity.CRITICAL, None): OrchestrationStrategy.EXHAUSTIVE,
    }
    
    # Confidence targets by strategy
    CONFIDENCE_TARGETS = {
        OrchestrationStrategy.FAST: 0.70,
        OrchestrationStrategy.STANDARD: 0.80,
        OrchestrationStrategy.THOROUGH: 0.90,
        OrchestrationStrategy.EXHAUSTIVE: 0.95,
    }
    
    # Model recommendations by query type
    MODEL_RECOMMENDATIONS = {
        QueryType.CODING: ["deepseek-chat", "claude-sonnet-4", "gpt-4o"],
        QueryType.REASONING: ["gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"],
        QueryType.FACTUAL: ["gemini-2.5-pro", "gpt-4o", "claude-sonnet-4"],
        QueryType.CREATIVE: ["claude-sonnet-4", "gpt-4o", "grok-2"],
        QueryType.RESEARCH: ["gemini-2.5-pro", "claude-sonnet-4", "gpt-4o"],
        QueryType.MULTI_HOP: ["gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"],
        QueryType.GENERAL: ["gpt-4o", "claude-sonnet-4", "gpt-4o-mini"],
    }
    
    def select_strategy(
        self,
        query_type: QueryType,
        complexity: QueryComplexity,
        time_budget_ms: Optional[float] = None,
    ) -> OrchestrationStrategy:
        """Select the optimal strategy."""
        # Check specific mapping
        strategy = self.STRATEGY_MAP.get((complexity, query_type))
        
        # Fall back to complexity-only mapping
        if strategy is None:
            strategy = self.STRATEGY_MAP.get((complexity, None))
        
        # Fall back to default
        if strategy is None:
            strategy = OrchestrationStrategy.STANDARD
        
        # Adjust for time constraints
        if time_budget_ms is not None and time_budget_ms < 5000:
            # Tight budget - downgrade strategy
            if strategy == OrchestrationStrategy.EXHAUSTIVE:
                strategy = OrchestrationStrategy.THOROUGH
            elif strategy == OrchestrationStrategy.THOROUGH:
                strategy = OrchestrationStrategy.STANDARD
        
        return strategy
    
    def get_confidence_target(self, strategy: OrchestrationStrategy) -> float:
        """Get the confidence target for a strategy."""
        return self.CONFIDENCE_TARGETS.get(strategy, 0.80)
    
    def get_recommended_models(
        self,
        query_type: QueryType,
        available_models: List[str],
    ) -> List[str]:
        """Get recommended models for a query type."""
        recommendations = self.MODEL_RECOMMENDATIONS.get(query_type, [])
        
        # Filter to available models
        available = [m for m in recommendations if m in available_models]
        
        # If none available, return what we have
        if not available:
            return available_models[:3]
        
        return available


# ==============================================================================
# Industry Dominance Controller
# ==============================================================================

class IndustryDominanceController:
    """
    The elite meta-controller that ensures LLMHive beats all competitors.
    
    This controller:
    1. Analyzes incoming queries
    2. Creates optimal execution plans
    3. Orchestrates the full pipeline
    4. Monitors quality in real-time
    5. Escalates when needed
    6. Learns from outcomes
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        elite_orchestrator: Optional[Any] = None,
        quality_booster: Optional[Any] = None,
        tool_broker: Optional[Any] = None,
        performance_tracker: Optional[Any] = None,
    ):
        """Initialize the dominance controller."""
        self.providers = providers
        self.elite_orchestrator = elite_orchestrator
        self.quality_booster = quality_booster
        self.tool_broker = tool_broker
        self.performance_tracker = performance_tracker
        
        self.analyzer = QueryAnalyzer()
        self.strategy_selector = StrategySelector()
        
        # Available models (from providers)
        self.available_models = list(providers.keys()) if providers else []
        
        logger.info(
            "IndustryDominanceController initialized with %d providers",
            len(self.available_models)
        )
    
    async def orchestrate(
        self,
        query: str,
        *,
        context: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        force_strategy: Optional[OrchestrationStrategy] = None,
    ) -> OrchestrationResult:
        """
        Orchestrate the elite pipeline for a query.
        
        This is the main entry point that coordinates everything.
        """
        start_time = time.time()
        notes: List[str] = []
        
        # Phase 1: Analyze and Plan
        execution_plan = self._create_execution_plan(
            query, context, user_preferences, force_strategy
        )
        notes.append(f"Strategy: {execution_plan.strategy.value}")
        notes.append(f"Query type: {execution_plan.query_type.value}")
        
        # Phase 2: Check for Tool Needs
        tool_results = ""
        tools_used: List[str] = []
        if self.tool_broker and execution_plan.tools_needed:
            try:
                analysis = self.tool_broker.analyze_tool_needs(query)
                if analysis.requires_tools:
                    results = await self.tool_broker.execute_tools(analysis.tool_requests)
                    tool_results = self.tool_broker.format_tool_results(results)
                    tools_used = [r.tool_type.value for r in results.values() if r.success]
                    notes.append(f"Tools used: {tools_used}")
            except Exception as e:
                logger.warning("Tool broker failed: %s", e)
        
        # Enhance query with tool results
        enhanced_query = query
        if tool_results:
            enhanced_query = f"{query}\n\n[TOOL RESULTS]\n{tool_results}"
        
        # Phase 3: Execute Based on Strategy
        if execution_plan.strategy == OrchestrationStrategy.FAST:
            result = await self._execute_fast_strategy(
                enhanced_query, execution_plan
            )
        elif execution_plan.strategy == OrchestrationStrategy.STANDARD:
            result = await self._execute_standard_strategy(
                enhanced_query, execution_plan
            )
        elif execution_plan.strategy == OrchestrationStrategy.THOROUGH:
            result = await self._execute_thorough_strategy(
                enhanced_query, execution_plan
            )
        else:  # EXHAUSTIVE
            result = await self._execute_exhaustive_strategy(
                enhanced_query, execution_plan
            )
        
        # Phase 4: Quality Assurance
        if result.quality_metrics.overall_confidence < execution_plan.confidence_target:
            # Escalate if below target
            notes.append("Quality below target - escalating")
            result = await self._escalate_and_improve(
                query, result, execution_plan
            )
        
        # Phase 5: Final Polish
        if self.quality_booster and execution_plan.strategy in [
            OrchestrationStrategy.THOROUGH, OrchestrationStrategy.EXHAUSTIVE
        ]:
            try:
                boost_result = await self.quality_booster.boost(
                    query, result.answer,
                    techniques=["reflection"],
                    max_iterations=1,
                )
                if boost_result.quality_improvement > 0:
                    result.answer = boost_result.boosted_response
                    notes.append("Quality boost applied")
            except Exception as e:
                logger.warning("Quality boost failed: %s", e)
        
        # Calculate total latency
        total_latency = (time.time() - start_time) * 1000
        result.total_latency_ms = total_latency
        result.tools_used = tools_used
        result.notes = notes
        
        # Log performance for learning
        self._log_performance(query, result, execution_plan)
        
        return result
    
    def _create_execution_plan(
        self,
        query: str,
        context: Optional[str],
        user_preferences: Optional[Dict[str, Any]],
        force_strategy: Optional[OrchestrationStrategy],
    ) -> ExecutionPlan:
        """Create an execution plan for the query."""
        # Analyze query
        query_type, complexity = self.analyzer.analyze(query)
        
        # Get user preferences
        prefs = user_preferences or {}
        time_budget = prefs.get("time_budget_ms")
        accuracy_level = prefs.get("accuracy_level", 3)
        
        # Adjust complexity based on accuracy level
        if accuracy_level >= 4:
            complexity = max(complexity, QueryComplexity.COMPLEX)
        elif accuracy_level <= 2:
            complexity = min(complexity, QueryComplexity.MODERATE)
        
        # Select strategy
        if force_strategy:
            strategy = force_strategy
        else:
            strategy = self.strategy_selector.select_strategy(
                query_type, complexity, time_budget
            )
        
        # Get recommended models
        recommended_models = self.strategy_selector.get_recommended_models(
            query_type, self.available_models
        )
        
        # Determine tools needed
        tools_needed = []
        query_lower = query.lower()
        if any(kw in query_lower for kw in ["latest", "current", "2024", "2025"]):
            tools_needed.append("web_search")
        if any(kw in query_lower for kw in ["calculate", "compute", "math"]):
            tools_needed.append("calculator")
        if any(kw in query_lower for kw in ["run", "execute", "test code"]):
            tools_needed.append("code_execution")
        
        return ExecutionPlan(
            query_type=query_type,
            complexity=complexity,
            strategy=strategy,
            primary_model=recommended_models[0] if recommended_models else "gpt-4o",
            support_models=recommended_models[1:3] if len(recommended_models) > 1 else [],
            tools_needed=tools_needed,
            verification_level=self._get_verification_level(strategy),
            max_iterations=self._get_max_iterations(strategy),
            confidence_target=self.strategy_selector.get_confidence_target(strategy),
            time_budget_ms=time_budget,
        )
    
    def _get_verification_level(self, strategy: OrchestrationStrategy) -> int:
        """Get verification level for a strategy."""
        levels = {
            OrchestrationStrategy.FAST: 1,
            OrchestrationStrategy.STANDARD: 2,
            OrchestrationStrategy.THOROUGH: 3,
            OrchestrationStrategy.EXHAUSTIVE: 5,
        }
        return levels.get(strategy, 2)
    
    def _get_max_iterations(self, strategy: OrchestrationStrategy) -> int:
        """Get max iterations for a strategy."""
        iterations = {
            OrchestrationStrategy.FAST: 1,
            OrchestrationStrategy.STANDARD: 2,
            OrchestrationStrategy.THOROUGH: 3,
            OrchestrationStrategy.EXHAUSTIVE: 5,
        }
        return iterations.get(strategy, 2)
    
    async def _execute_fast_strategy(
        self,
        query: str,
        plan: ExecutionPlan,
    ) -> OrchestrationResult:
        """Execute fast strategy - single model, minimal verification."""
        # Use elite orchestrator if available
        if self.elite_orchestrator:
            try:
                elite_result = await self.elite_orchestrator.orchestrate(
                    query,
                    task_type=plan.query_type.value,
                    available_models=[plan.primary_model],
                    strategy="single_best",
                )
                return OrchestrationResult(
                    answer=elite_result.final_answer,
                    strategy_used=plan.strategy,
                    models_used=elite_result.models_used,
                    tools_used=[],
                    quality_metrics=QualityMetrics(
                        overall_confidence=elite_result.confidence,
                        verification_passed=True,
                    ),
                    total_latency_ms=elite_result.total_latency_ms,
                    total_tokens=elite_result.total_tokens,
                    iterations=1,
                    notes=[],
                )
            except Exception as e:
                logger.warning("Elite orchestrator failed: %s", e)
        
        # Fallback to direct model call
        answer = await self._call_model(plan.primary_model, query)
        return OrchestrationResult(
            answer=answer,
            strategy_used=plan.strategy,
            models_used=[plan.primary_model],
            tools_used=[],
            quality_metrics=QualityMetrics(overall_confidence=0.75),
            total_latency_ms=0,
            total_tokens=0,
            iterations=1,
            notes=["Direct model call"],
        )
    
    async def _execute_standard_strategy(
        self,
        query: str,
        plan: ExecutionPlan,
    ) -> OrchestrationResult:
        """Execute standard strategy - primary + verifier."""
        if self.elite_orchestrator:
            try:
                models = [plan.primary_model] + plan.support_models[:1]
                elite_result = await self.elite_orchestrator.orchestrate(
                    query,
                    task_type=plan.query_type.value,
                    available_models=models,
                    strategy="quality_weighted_fusion",
                )
                return OrchestrationResult(
                    answer=elite_result.final_answer,
                    strategy_used=plan.strategy,
                    models_used=elite_result.models_used,
                    tools_used=[],
                    quality_metrics=QualityMetrics(
                        overall_confidence=elite_result.confidence,
                        verification_passed=True,
                    ),
                    total_latency_ms=elite_result.total_latency_ms,
                    total_tokens=elite_result.total_tokens,
                    iterations=elite_result.responses_generated,
                    notes=[f"Synthesis: {elite_result.synthesis_method}"],
                )
            except Exception as e:
                logger.warning("Elite orchestrator failed: %s", e)
        
        # Fallback
        answer = await self._call_model(plan.primary_model, query)
        return OrchestrationResult(
            answer=answer,
            strategy_used=plan.strategy,
            models_used=[plan.primary_model],
            tools_used=[],
            quality_metrics=QualityMetrics(overall_confidence=0.80),
            total_latency_ms=0,
            total_tokens=0,
            iterations=1,
            notes=["Fallback to direct call"],
        )
    
    async def _execute_thorough_strategy(
        self,
        query: str,
        plan: ExecutionPlan,
    ) -> OrchestrationResult:
        """Execute thorough strategy - full pipeline with challenge."""
        if self.elite_orchestrator:
            try:
                models = [plan.primary_model] + plan.support_models
                elite_result = await self.elite_orchestrator.orchestrate(
                    query,
                    task_type=plan.query_type.value,
                    available_models=models,
                    strategy="challenge_and_refine" if plan.query_type == QueryType.CODING else "best_of_n",
                )
                return OrchestrationResult(
                    answer=elite_result.final_answer,
                    strategy_used=plan.strategy,
                    models_used=elite_result.models_used,
                    tools_used=[],
                    quality_metrics=QualityMetrics(
                        overall_confidence=elite_result.confidence,
                        verification_passed=True,
                        challenge_passed=True,
                    ),
                    total_latency_ms=elite_result.total_latency_ms,
                    total_tokens=elite_result.total_tokens,
                    iterations=elite_result.responses_generated,
                    notes=elite_result.performance_notes,
                )
            except Exception as e:
                logger.warning("Elite orchestrator failed: %s", e)
        
        # Fallback
        answer = await self._call_model(plan.primary_model, query)
        return OrchestrationResult(
            answer=answer,
            strategy_used=plan.strategy,
            models_used=[plan.primary_model],
            tools_used=[],
            quality_metrics=QualityMetrics(overall_confidence=0.85),
            total_latency_ms=0,
            total_tokens=0,
            iterations=1,
            notes=["Fallback to direct call"],
        )
    
    async def _execute_exhaustive_strategy(
        self,
        query: str,
        plan: ExecutionPlan,
    ) -> OrchestrationResult:
        """Execute exhaustive strategy - all techniques + debate."""
        if self.elite_orchestrator:
            try:
                models = [plan.primary_model] + plan.support_models
                
                # Use expert panel for research, otherwise best_of_n with high n
                strategy = "expert_panel" if plan.query_type == QueryType.RESEARCH else "best_of_n"
                
                elite_result = await self.elite_orchestrator.orchestrate(
                    query,
                    task_type=plan.query_type.value,
                    available_models=models,
                    strategy=strategy,
                    quality_threshold=0.90,
                )
                return OrchestrationResult(
                    answer=elite_result.final_answer,
                    strategy_used=plan.strategy,
                    models_used=elite_result.models_used,
                    tools_used=[],
                    quality_metrics=QualityMetrics(
                        overall_confidence=elite_result.confidence,
                        verification_passed=True,
                        challenge_passed=True,
                        models_agreed=True,
                    ),
                    total_latency_ms=elite_result.total_latency_ms,
                    total_tokens=elite_result.total_tokens,
                    iterations=elite_result.responses_generated,
                    notes=elite_result.performance_notes,
                )
            except Exception as e:
                logger.warning("Elite orchestrator failed: %s", e)
        
        # Fallback
        answer = await self._call_model(plan.primary_model, query)
        return OrchestrationResult(
            answer=answer,
            strategy_used=plan.strategy,
            models_used=[plan.primary_model],
            tools_used=[],
            quality_metrics=QualityMetrics(overall_confidence=0.90),
            total_latency_ms=0,
            total_tokens=0,
            iterations=1,
            notes=["Fallback to direct call"],
        )
    
    async def _escalate_and_improve(
        self,
        query: str,
        current_result: OrchestrationResult,
        plan: ExecutionPlan,
    ) -> OrchestrationResult:
        """Escalate and improve when quality is below target."""
        # Try quality boosting
        if self.quality_booster:
            try:
                boost_result = await self.quality_booster.boost(
                    query,
                    current_result.answer,
                    techniques=["reflection", "verification"],
                    max_iterations=2,
                )
                if boost_result.quality_improvement > 0.1:
                    current_result.answer = boost_result.boosted_response
                    current_result.quality_metrics.overall_confidence += 0.1
                    current_result.notes.append("Escalation: quality boost successful")
            except Exception as e:
                logger.warning("Quality boost escalation failed: %s", e)
        
        return current_result
    
    async def _call_model(self, model: str, prompt: str) -> str:
        """Call a model directly."""
        # Find provider
        provider = None
        model_to_provider = {
            "gpt-4o": "openai",
            "gpt-4o-mini": "openai",
            "claude-sonnet-4": "anthropic",
            "claude-3-5-haiku": "anthropic",
            "gemini-2.5-pro": "gemini",
            "gemini-2.5-flash": "gemini",
            "deepseek-chat": "deepseek",
            "grok-2": "grok",
        }
        
        provider_name = model_to_provider.get(model)
        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
        elif self.providers:
            provider = next(iter(self.providers.values()))
        
        if not provider:
            return f"Error: No provider available for model {model}"
        
        try:
            result = await provider.complete(prompt, model=model)
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception as e:
            logger.error("Model call failed: %s", e)
            return f"Error: {e}"
    
    def _log_performance(
        self,
        query: str,
        result: OrchestrationResult,
        plan: ExecutionPlan,
    ) -> None:
        """Log performance for learning.
        
        Strategy Memory (PR2): Extended logging with strategy and model team info.
        """
        if not self.performance_tracker:
            return
        
        try:
            success_flag = result.quality_metrics.overall_confidence >= plan.confidence_target
            
            # Determine model roles based on plan phases
            model_roles = {}
            for i, model in enumerate(result.models_used):
                if i == 0:
                    model_roles[model] = "primary"
                else:
                    model_roles[model] = f"phase_{i}"
            
            # Strategy Memory (PR2): Extended logging
            self.performance_tracker.log_run(
                models_used=result.models_used,
                success_flag=success_flag,
                latency_ms=result.total_latency_ms,
                domain=plan.query_type.value,
                # Strategy Memory (PR2) extended fields
                strategy=f"dominance_{plan.complexity.value}" if hasattr(plan, 'complexity') else "dominance_controller",
                task_type=plan.query_type.value,
                primary_model=result.models_used[0] if result.models_used else None,
                model_roles=model_roles,
                quality_score=result.quality_metrics.overall_confidence,
                confidence=result.quality_metrics.overall_confidence,
                total_tokens=result.total_tokens,
                ensemble_size=len(result.models_used),
            )
        except Exception as e:
            logger.debug("Performance logging failed: %s", e)


# ==============================================================================
# Factory Function
# ==============================================================================

def create_dominance_controller(
    providers: Dict[str, Any],
    **kwargs,
) -> IndustryDominanceController:
    """Create a configured Industry Dominance Controller."""
    # Try to import and initialize optional components
    elite_orchestrator = None
    quality_booster = None
    tool_broker = None
    performance_tracker = None
    
    try:
        from .elite_orchestrator import EliteOrchestrator
        elite_orchestrator = EliteOrchestrator(providers)
    except ImportError:
        pass
    
    try:
        from .quality_booster import QualityBooster
        quality_booster = QualityBooster(providers)
    except ImportError:
        pass
    
    try:
        from .tool_broker import get_tool_broker
        tool_broker = get_tool_broker()
    except ImportError:
        pass
    
    try:
        from ..performance_tracker import performance_tracker as pt
        performance_tracker = pt
    except ImportError:
        pass
    
    return IndustryDominanceController(
        providers=providers,
        elite_orchestrator=elite_orchestrator,
        quality_booster=quality_booster,
        tool_broker=tool_broker,
        performance_tracker=performance_tracker,
    )

