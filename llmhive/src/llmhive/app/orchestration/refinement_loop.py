"""Loop-Back Refinement Controller for LLMHive Orchestrator.

This module implements an iterative self-correction mechanism where the system
can refine answers multiple times until:
1. The answer passes all verification checks
2. A maximum number of iterations is reached
3. No further improvement is detected (convergence)

The refinement loop integrates with:
- Fact checking for verification
- Prompt diffusion for prompt refinement
- Memory for context enhancement
- Multiple models for diverse perspectives

This implements the closed-loop self-correction mechanism for enhanced reliability.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class RefinementStrategy(str, Enum):
    """Strategy for refining the answer."""
    PROMPT_ENHANCE = "prompt_enhance"     # Enhance prompt with failed claims info
    MODEL_SWITCH = "model_switch"         # Try a different model
    DECOMPOSE = "decompose"               # Break query into sub-questions
    MEMORY_AUGMENT = "memory_augment"     # Add more memory context
    WEB_SEARCH = "web_search"             # Search for specific facts
    DIRECT_CORRECT = "direct_correct"     # Direct LLM correction


class LoopStatus(str, Enum):
    """Status of the refinement loop."""
    IN_PROGRESS = "in_progress"
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations"
    NO_IMPROVEMENT = "no_improvement"
    PASSED = "passed"
    FAILED = "failed"


class IssueType(str, Enum):
    """Type of issue found during verification."""
    FACTUAL_ERROR = "factual_error"
    INCOMPLETE = "incomplete"
    CONTRADICTORY = "contradictory"
    UNSUPPORTED = "unsupported"
    OUTDATED = "outdated"


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class VerificationIssue:
    """A single verification issue to address."""
    issue_type: IssueType
    description: str
    claim: str
    evidence: str = ""
    correction_hint: Optional[str] = None
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass(slots=True)
class RefinementIteration:
    """Record of a single refinement iteration."""
    iteration: int
    input_answer: str
    output_answer: str
    verification_score: float
    issues_found: int
    issues_resolved: int
    strategy_used: RefinementStrategy
    model_used: str
    prompt_used: str
    duration_ms: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass(slots=True)
class RefinementResult:
    """Final result of the refinement loop."""
    original_answer: str
    final_answer: str
    iterations: List[RefinementIteration]
    final_status: LoopStatus
    final_verification_score: float
    total_issues_found: int
    issues_resolved: int
    total_duration_ms: float = 0.0
    strategies_used: List[RefinementStrategy] = field(default_factory=list)
    convergence_history: List[float] = field(default_factory=list)
    transparency_notes: List[str] = field(default_factory=list)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary for UI/logging."""
        return {
            "iterations_completed": len(self.iterations),
            "final_status": self.final_status.value,
            "final_score": self.final_verification_score,
            "issues_found": self.total_issues_found,
            "issues_resolved": self.issues_resolved,
            "strategies_used": [s.value for s in self.strategies_used],
            "improvement": (
                self.final_verification_score - 
                (self.iterations[0].verification_score if self.iterations else 0)
            ),
        }


@dataclass(slots=True)
class RefinementConfig:
    """Configuration for the refinement loop."""
    max_iterations: int = 3
    convergence_threshold: float = 0.90
    min_improvement_threshold: float = 0.05
    stagnation_tolerance: int = 1  # How many iterations without improvement to allow
    enable_prompt_refinement: bool = True
    enable_model_switching: bool = True
    enable_decomposition: bool = True
    priority_strategies: List[RefinementStrategy] = field(default_factory=lambda: [
        RefinementStrategy.PROMPT_ENHANCE,
        RefinementStrategy.WEB_SEARCH,
        RefinementStrategy.DIRECT_CORRECT,
    ])


# ==============================================================================
# Refinement Loop Controller
# ==============================================================================

class RefinementLoopController:
    """Controls the iterative refinement loop for answer improvement.
    
    This controller manages the cycle of:
    1. Verify answer
    2. Identify issues
    3. Select refinement strategy
    4. Apply refinement
    5. Re-verify
    
    Until convergence or maximum iterations.
    """
    
    def __init__(
        self,
        fact_checker: Optional[Any] = None,
        prompt_diffusion: Optional[Any] = None,
        providers: Optional[Dict[str, Any]] = None,
        memory_manager: Optional[Any] = None,
        web_client: Optional[Any] = None,
        config: Optional[RefinementConfig] = None,
    ) -> None:
        """
        Initialize the refinement loop controller.
        
        Args:
            fact_checker: FactChecker instance for verification
            prompt_diffusion: PromptDiffusion for prompt refinement
            providers: Dict of LLM providers
            memory_manager: Memory manager for context
            web_client: Web research client for fact lookup
            config: Refinement configuration
        """
        self.fact_checker = fact_checker
        self.prompt_diffusion = prompt_diffusion
        self.providers = providers or {}
        self.memory_manager = memory_manager
        self.web_client = web_client
        self.config = config or RefinementConfig()
    
    async def run_refinement_loop(
        self,
        answer: str,
        prompt: str,
        *,
        model: str = "default",
        context: Optional[str] = None,
        available_models: Optional[List[str]] = None,
        web_documents: Optional[List[Any]] = None,
    ) -> RefinementResult:
        """
        Run the iterative refinement loop on an answer.
        
        Args:
            answer: Initial answer to refine
            prompt: Original user prompt
            model: Model that generated the answer
            context: Additional context
            available_models: List of models available for switching
            web_documents: Pre-fetched web documents for verification
            
        Returns:
            RefinementResult with final answer and iteration history
        """
        import time
        start_time = time.time()
        
        iterations: List[RefinementIteration] = []
        current_answer = answer
        current_model = model
        convergence_history: List[float] = []
        strategies_used: Set[RefinementStrategy] = set()
        total_issues_found = 0
        issues_resolved = 0
        transparency_notes: List[str] = []
        stagnation_count = 0
        previous_score = 0.0
        
        transparency_notes.append(f"Starting refinement loop with max {self.config.max_iterations} iterations")
        
        for iteration in range(1, self.config.max_iterations + 1):
            iter_start = time.time()
            logger.info("Refinement iteration %d/%d", iteration, self.config.max_iterations)
            
            # Step 1: Verify current answer
            verification_result = await self._verify_answer(
                current_answer, prompt, web_documents
            )
            
            current_score = verification_result.get("score", 0.0)
            issues = verification_result.get("issues", [])
            convergence_history.append(current_score)
            
            logger.info(
                "Iteration %d: score=%.2f, issues=%d",
                iteration, current_score, len(issues)
            )
            
            # Step 2: Check for convergence/termination
            if current_score >= self.config.convergence_threshold:
                transparency_notes.append(
                    f"Iteration {iteration}: Passed verification (score: {current_score:.2f})"
                )
                
                iter_result = RefinementIteration(
                    iteration=iteration,
                    input_answer=current_answer,
                    output_answer=current_answer,
                    verification_score=current_score,
                    issues_found=len(issues),
                    issues_resolved=0,
                    strategy_used=RefinementStrategy.DIRECT_CORRECT,
                    model_used=current_model,
                    prompt_used=prompt,
                    duration_ms=(time.time() - iter_start) * 1000,
                    notes=["Passed verification"],
                )
                iterations.append(iter_result)
                
                return RefinementResult(
                    original_answer=answer,
                    final_answer=current_answer,
                    iterations=iterations,
                    final_status=LoopStatus.PASSED,
                    final_verification_score=current_score,
                    total_issues_found=total_issues_found + len(issues),
                    issues_resolved=issues_resolved,
                    total_duration_ms=(time.time() - start_time) * 1000,
                    strategies_used=list(strategies_used),
                    convergence_history=convergence_history,
                    transparency_notes=transparency_notes,
                )
            
            # Check for stagnation
            improvement = current_score - previous_score
            if iteration > 1 and improvement < self.config.min_improvement_threshold:
                stagnation_count += 1
                if stagnation_count > self.config.stagnation_tolerance:
                    transparency_notes.append(
                        f"Iteration {iteration}: Stopping due to no improvement"
                    )
                    
                    return RefinementResult(
                        original_answer=answer,
                        final_answer=current_answer,
                        iterations=iterations,
                        final_status=LoopStatus.NO_IMPROVEMENT,
                        final_verification_score=current_score,
                        total_issues_found=total_issues_found + len(issues),
                        issues_resolved=issues_resolved,
                        total_duration_ms=(time.time() - start_time) * 1000,
                        strategies_used=list(strategies_used),
                        convergence_history=convergence_history,
                        transparency_notes=transparency_notes,
                    )
            else:
                stagnation_count = 0
            
            previous_score = current_score
            total_issues_found += len(issues)
            
            # Step 3: Select refinement strategy
            strategy = self._select_strategy(
                issues, iteration, list(strategies_used), available_models
            )
            strategies_used.add(strategy)
            
            transparency_notes.append(
                f"Iteration {iteration}: Found {len(issues)} issues, using {strategy.value} strategy"
            )
            
            # Step 4: Apply refinement
            refined_answer, refined_prompt, new_model = await self._apply_refinement(
                current_answer,
                prompt,
                issues,
                strategy,
                current_model,
                available_models,
                context,
            )
            
            # Count resolved issues
            new_verification = await self._verify_answer(
                refined_answer, prompt, web_documents
            )
            new_issues = new_verification.get("issues", [])
            resolved = len(issues) - len(new_issues)
            issues_resolved += max(0, resolved)
            
            # Record iteration
            iter_result = RefinementIteration(
                iteration=iteration,
                input_answer=current_answer,
                output_answer=refined_answer,
                verification_score=current_score,
                issues_found=len(issues),
                issues_resolved=max(0, resolved),
                strategy_used=strategy,
                model_used=new_model,
                prompt_used=refined_prompt,
                duration_ms=(time.time() - iter_start) * 1000,
                notes=[f"Applied {strategy.value}", f"Resolved {max(0, resolved)} issues"],
            )
            iterations.append(iter_result)
            
            current_answer = refined_answer
            current_model = new_model
        
        # Max iterations reached
        final_verification = await self._verify_answer(
            current_answer, prompt, web_documents
        )
        final_score = final_verification.get("score", 0.0)
        
        transparency_notes.append(
            f"Completed {self.config.max_iterations} iterations (final score: {final_score:.2f})"
        )
        
        return RefinementResult(
            original_answer=answer,
            final_answer=current_answer,
            iterations=iterations,
            final_status=LoopStatus.MAX_ITERATIONS,
            final_verification_score=final_score,
            total_issues_found=total_issues_found,
            issues_resolved=issues_resolved,
            total_duration_ms=(time.time() - start_time) * 1000,
            strategies_used=list(strategies_used),
            convergence_history=convergence_history,
            transparency_notes=transparency_notes,
        )
    
    async def _verify_answer(
        self,
        answer: str,
        prompt: str,
        web_documents: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Verify an answer and return structured result."""
        issues: List[VerificationIssue] = []
        score = 0.8  # Default if no fact checker
        
        if self.fact_checker:
            try:
                report = await self.fact_checker.verify(
                    answer, prompt=prompt, web_documents=web_documents
                )
                
                score = report.verification_score
                
                # Convert failed claims to issues
                for item in report.items:
                    if not item.verified:
                        issue = VerificationIssue(
                            issue_type=IssueType.FACTUAL_ERROR,
                            description=f"Unverified claim: {item.text[:100]}",
                            claim=item.text,
                            evidence=item.evidence,
                            correction_hint=item.correction,
                            priority=1 if item.confidence < 0.3 else 2,
                        )
                        issues.append(issue)
                
            except Exception as e:
                logger.warning("Verification failed: %s", e)
        
        return {
            "score": score,
            "issues": issues,
            "passed": score >= self.config.convergence_threshold,
        }
    
    def _select_strategy(
        self,
        issues: List[VerificationIssue],
        iteration: int,
        used_strategies: List[RefinementStrategy],
        available_models: Optional[List[str]],
    ) -> RefinementStrategy:
        """Select the best refinement strategy for current issues."""
        # Priority strategies from config
        for strategy in self.config.priority_strategies:
            if strategy not in used_strategies:
                # Check if strategy is applicable
                if strategy == RefinementStrategy.MODEL_SWITCH:
                    if not self.config.enable_model_switching or not available_models:
                        continue
                if strategy == RefinementStrategy.PROMPT_ENHANCE:
                    if not self.config.enable_prompt_refinement:
                        continue
                if strategy == RefinementStrategy.DECOMPOSE:
                    if not self.config.enable_decomposition:
                        continue
                return strategy
        
        # Fallback based on issue types
        factual_errors = sum(1 for i in issues if i.issue_type == IssueType.FACTUAL_ERROR)
        
        if factual_errors > len(issues) // 2:
            return RefinementStrategy.WEB_SEARCH
        elif iteration > 1:
            return RefinementStrategy.DIRECT_CORRECT
        else:
            return RefinementStrategy.PROMPT_ENHANCE
    
    async def _apply_refinement(
        self,
        answer: str,
        prompt: str,
        issues: List[VerificationIssue],
        strategy: RefinementStrategy,
        current_model: str,
        available_models: Optional[List[str]],
        context: Optional[str],
    ) -> Tuple[str, str, str]:
        """
        Apply the selected refinement strategy.
        
        Returns:
            Tuple of (refined_answer, used_prompt, used_model)
        """
        refined_prompt = prompt
        used_model = current_model
        
        if strategy == RefinementStrategy.PROMPT_ENHANCE:
            # Enhance prompt with issue information
            refined_prompt = self._enhance_prompt_with_issues(prompt, issues)
            refined_answer = await self._regenerate_answer(
                refined_prompt, used_model, context
            )
            
        elif strategy == RefinementStrategy.MODEL_SWITCH:
            # Switch to a different model
            if available_models:
                for model in available_models:
                    if model != current_model:
                        used_model = model
                        break
            refined_answer = await self._regenerate_answer(
                prompt, used_model, context
            )
            
        elif strategy == RefinementStrategy.WEB_SEARCH:
            # Search for correct facts and enhance answer
            refined_answer = await self._refine_with_search(answer, issues)
            
        elif strategy == RefinementStrategy.DIRECT_CORRECT:
            # Direct LLM correction
            refined_answer = await self._direct_correct(answer, issues, current_model)
            
        elif strategy == RefinementStrategy.MEMORY_AUGMENT:
            # Add memory context and regenerate
            memory_context = await self._get_memory_context(prompt, issues)
            if memory_context:
                refined_prompt = f"{prompt}\n\nRelevant context:\n{memory_context}"
            refined_answer = await self._regenerate_answer(
                refined_prompt, used_model, context
            )
            
        elif strategy == RefinementStrategy.DECOMPOSE:
            # Break into sub-questions and answer each
            refined_answer = await self._decompose_and_answer(
                prompt, issues, used_model, context
            )
            
        else:
            refined_answer = answer
        
        return refined_answer, refined_prompt, used_model
    
    def _enhance_prompt_with_issues(
        self,
        prompt: str,
        issues: List[VerificationIssue],
    ) -> str:
        """Enhance prompt with information about issues to avoid."""
        if not issues:
            return prompt
        
        issue_notes = []
        for issue in issues[:3]:  # Limit to top 3 issues
            if issue.correction_hint:
                issue_notes.append(
                    f"- Note: The claim '{issue.claim[:50]}...' may be incorrect. "
                    f"Consider: {issue.correction_hint}"
                )
            else:
                issue_notes.append(
                    f"- Verify: '{issue.claim[:50]}...' - {issue.description}"
                )
        
        enhanced = f"""{prompt}

IMPORTANT: Previous attempts had the following issues that need correction:
{chr(10).join(issue_notes)}

Please ensure your answer addresses these concerns and provides accurate information."""
        
        return enhanced
    
    async def _regenerate_answer(
        self,
        prompt: str,
        model: str,
        context: Optional[str],
    ) -> str:
        """Regenerate answer with enhanced prompt."""
        if not self.providers:
            return ""
        
        provider = self._select_provider(model)
        if not provider:
            return ""
        
        try:
            full_prompt = prompt
            if context:
                full_prompt = f"Context: {context}\n\n{prompt}"
            
            result = await provider.complete(full_prompt, model=model)
            return result.content.strip()
        except Exception as e:
            logger.warning("Failed to regenerate answer: %s", e)
            return ""
    
    async def _refine_with_search(
        self,
        answer: str,
        issues: List[VerificationIssue],
    ) -> str:
        """Refine answer by searching for correct facts."""
        if not self.web_client:
            return answer
        
        corrections: Dict[str, str] = {}
        
        for issue in issues[:3]:  # Process top 3 issues
            if issue.issue_type == IssueType.FACTUAL_ERROR:
                try:
                    # Search for correct information
                    query = f"{issue.claim} correct fact"
                    results = await self.web_client.search(query)
                    
                    if results:
                        snippet = getattr(results[0], 'snippet', '')
                        if snippet:
                            # Use snippet as correction hint
                            corrections[issue.claim] = f"[Corrected: Based on sources, {snippet[:200]}]"
                except Exception as e:
                    logger.debug("Search for correction failed: %s", e)
        
        # Apply corrections to answer
        refined = answer
        for wrong, correct in corrections.items():
            refined = refined.replace(wrong, correct)
        
        return refined
    
    async def _direct_correct(
        self,
        answer: str,
        issues: List[VerificationIssue],
        model: str,
    ) -> str:
        """Ask LLM to directly correct issues."""
        if not self.providers:
            return answer
        
        provider = self._select_provider(model)
        if not provider:
            return answer
        
        issue_list = "\n".join([
            f"- {i.claim[:100]}: {i.description}"
            for i in issues[:5]
        ])
        
        correction_prompt = f"""Please correct the following answer. These specific issues need to be fixed:

Issues found:
{issue_list}

Original answer:
{answer}

Please provide a corrected version that addresses all the issues above. Output ONLY the corrected answer."""
        
        try:
            result = await provider.complete(correction_prompt, model=model)
            return result.content.strip()
        except Exception as e:
            logger.warning("Direct correction failed: %s", e)
            return answer
    
    async def _get_memory_context(
        self,
        prompt: str,
        issues: List[VerificationIssue],
    ) -> str:
        """Get relevant memory context for issues."""
        if not self.memory_manager:
            return ""
        
        context_parts = []
        
        try:
            # Query memory for each issue
            for issue in issues[:3]:
                hits = self.memory_manager.query_memory(
                    query_text=issue.claim,
                    top_k=2,
                    filter_verified=True,
                )
                for hit in hits:
                    if hit.score >= 0.7:
                        context_parts.append(hit.text)
        except Exception as e:
            logger.debug("Memory query failed: %s", e)
        
        return "\n".join(context_parts[:3])
    
    async def _decompose_and_answer(
        self,
        prompt: str,
        issues: List[VerificationIssue],
        model: str,
        context: Optional[str],
    ) -> str:
        """Break prompt into sub-questions and answer each."""
        if not self.providers:
            return ""
        
        provider = self._select_provider(model)
        if not provider:
            return ""
        
        # Generate sub-questions
        decompose_prompt = f"""Break down this question into 2-3 specific sub-questions that can be answered separately:

Question: {prompt}

Output each sub-question on a new line, prefixed with "Q:"."""
        
        try:
            result = await provider.complete(decompose_prompt, model=model)
            
            # Extract sub-questions
            sub_questions = []
            for line in result.content.split('\n'):
                if line.strip().startswith('Q:'):
                    sub_questions.append(line.strip()[2:].strip())
            
            if not sub_questions:
                return ""
            
            # Answer each sub-question
            sub_answers = []
            for sq in sub_questions[:3]:
                answer_result = await provider.complete(sq, model=model)
                sub_answers.append(f"**{sq}**\n{answer_result.content.strip()}")
            
            return "\n\n".join(sub_answers)
            
        except Exception as e:
            logger.warning("Decomposition failed: %s", e)
            return ""
    
    def _select_provider(self, model: str) -> Optional[Any]:
        """Select provider for a model."""
        if not self.providers:
            return None
        
        model_lower = model.lower()
        
        provider_map = {
            "gpt": "openai",
            "claude": "anthropic",
            "grok": "grok",
            "gemini": "gemini",
            "deepseek": "deepseek",
        }
        
        for prefix, provider_name in provider_map.items():
            if model_lower.startswith(prefix) and provider_name in self.providers:
                return self.providers[provider_name]
        
        if "stub" in self.providers:
            return self.providers["stub"]
        
        if self.providers:
            return next(iter(self.providers.values()))
        
        return None


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def run_refinement_loop(
    answer: str,
    prompt: str,
    *,
    fact_checker: Optional[Any] = None,
    providers: Optional[Dict[str, Any]] = None,
    max_iterations: int = 3,
    convergence_threshold: float = 0.90,
    **kwargs,
) -> RefinementResult:
    """Convenience function to run refinement loop."""
    config = RefinementConfig(
        max_iterations=max_iterations,
        convergence_threshold=convergence_threshold,
    )
    
    controller = RefinementLoopController(
        fact_checker=fact_checker,
        providers=providers,
        config=config,
    )
    
    return await controller.run_refinement_loop(
        answer, prompt, **kwargs
    )


def create_refinement_controller(
    fact_checker: Optional[Any] = None,
    providers: Optional[Dict[str, Any]] = None,
    **config_kwargs,
) -> RefinementLoopController:
    """Create a configured refinement loop controller."""
    config = RefinementConfig(**config_kwargs)
    
    return RefinementLoopController(
        fact_checker=fact_checker,
        providers=providers,
        config=config,
    )

