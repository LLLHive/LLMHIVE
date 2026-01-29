"""Prompt Diffusion and Multi-Agent Prompt Refinement for LLMHive.

This module implements an iterative refinement process where multiple agents
with different roles and perspectives collaboratively improve prompts through
multiple rounds of refinement. Each agent specializes in a different aspect:

- Clarifier: Identifies ambiguities and adds clarifications
- Expander: Adds context, examples, and constraints
- Critic: Identifies weaknesses and suggests improvements
- Synthesizer: Combines insights into a cohesive refined prompt
- Specialist: Applies domain-specific knowledge

The "diffusion" process creates a gradient of improvements, where each
iteration builds upon the previous, gradually converging to an optimal prompt.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Refiner Roles
# ==============================================================================

class RefinerRole(str, Enum):
    """Roles for prompt refinement agents."""
    CLARIFIER = "clarifier"      # Identifies and resolves ambiguities
    EXPANDER = "expander"        # Adds context, examples, constraints
    CRITIC = "critic"            # Finds weaknesses and gaps
    SYNTHESIZER = "synthesizer"  # Combines perspectives
    SPECIALIST = "specialist"    # Domain-specific refinement
    SIMPLIFIER = "simplifier"    # Reduces complexity while maintaining intent
    CONSISTENCY = "consistency"  # Checks conflicts and preserves facts
    OBJECTIVE_GUARD = "objective_guard"  # Ensures goal/intent is preserved


# Role-specific prompts for refinement
ROLE_PROMPTS: Dict[RefinerRole, str] = {
    RefinerRole.CLARIFIER: """You are a Clarification Specialist. Your job is to:
1. Identify any ambiguous words, phrases, or requirements in the prompt
2. Resolve ambiguities by adding specific definitions or examples
3. Ensure the intent is crystal clear to any AI model
4. Add clarifying questions if the user's intent is unclear

Focus on: Ambiguity detection, term definition, intent clarification.""",

    RefinerRole.EXPANDER: """You are a Context Expansion Specialist. Your job is to:
1. Add relevant context that would help answer the prompt
2. Include helpful examples or edge cases to consider
3. Add constraints or requirements that are implied but not stated
4. Expand abbreviations and technical terms

Focus on: Context enrichment, example provision, constraint addition.""",

    RefinerRole.CRITIC: """You are a Prompt Quality Critic. Your job is to:
1. Identify weaknesses in the current prompt formulation
2. Find gaps in information or unclear instructions
3. Detect potential misinterpretations
4. Suggest structural improvements

Focus on: Weakness identification, gap analysis, structure improvement.""",

    RefinerRole.SYNTHESIZER: """You are a Prompt Synthesis Specialist. Your job is to:
1. Combine multiple perspectives into one cohesive prompt
2. Resolve conflicting suggestions intelligently
3. Create a balanced prompt that is clear yet comprehensive
4. Maintain the original intent while incorporating improvements

Focus on: Integration, coherence, balance.""",

    RefinerRole.SPECIALIST: """You are a Domain Specialist. Your job is to:
1. Add domain-specific terminology and concepts
2. Include best practices from the relevant field
3. Reference important frameworks or methodologies
4. Ensure technical accuracy

Focus on: Domain expertise, technical accuracy, best practices.""",

    RefinerRole.SIMPLIFIER: """You are a Simplification Specialist. Your job is to:
1. Reduce unnecessary complexity while keeping intent clear
2. Remove redundant phrases and verbose language
3. Make the prompt more direct and actionable
4. Ensure the prompt is concise yet complete

Focus on: Simplicity, directness, efficiency.""",

    RefinerRole.CONSISTENCY: """You are a Consistency Checker. Your job is to:
1. Detect and resolve contradictions or conflicts in the prompt
2. Ensure all constraints, entities, and numbers align with prior context/user details
3. Preserve the original facts and constraints while improving clarity

Focus on: Conflict detection, fidelity to user-provided facts, alignment with prior context.""",

    RefinerRole.OBJECTIVE_GUARD: """You are an Objective Guard. Your job is to:
1. Ensure the prompt stays true to the user's stated goal/objective
2. Re-emphasize the desired output and success criteria
3. Prevent scope drift—do not change the intent or omit key asks

Focus on: Goal alignment, intent preservation, outcome clarity.""",
}


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class PromptVersion:
    """Represents a version of a prompt during the diffusion process."""
    version: int
    prompt: str
    author: str  # Model/agent that created this version
    role: Optional[RefinerRole] = None  # Role of the refiner
    parent_version: Optional[int] = None
    score: float = 0.0
    improvements: List[str] = field(default_factory=list)
    reasoning: str = ""  # Explanation of changes
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RefinementStep:
    """A single refinement step in the diffusion process."""
    role: RefinerRole
    model: str
    input_prompt: str
    output_prompt: str
    score: float
    reasoning: str
    duration_ms: float = 0.0


@dataclass(slots=True)
class DiffusionResult:
    """Result of the prompt diffusion process."""
    original_prompt: str
    final_prompt: str
    versions: List[PromptVersion]
    refinement_steps: List[RefinementStep]
    convergence_score: float
    rounds_completed: int
    best_version: PromptVersion
    total_duration_ms: float = 0.0
    ambiguities_resolved: List[str] = field(default_factory=list)
    clarifications_added: List[str] = field(default_factory=list)
    
    def get_refinement_summary(self) -> Dict[str, Any]:
        """Get a summary of the refinement process for UI display."""
        return {
            "original_prompt": self.original_prompt,
            "final_prompt": self.final_prompt,
            "rounds_completed": self.rounds_completed,
            "convergence_score": self.convergence_score,
            "improvements": [
                imp for v in self.versions for imp in v.improvements
            ],
            "refiners_used": [
                {"role": step.role.value, "model": step.model}
                for step in self.refinement_steps
            ],
            "ambiguities_resolved": self.ambiguities_resolved,
            "clarifications_added": self.clarifications_added,
        }


@dataclass(slots=True)
class AmbiguityAnalysis:
    """Analysis of ambiguities in a prompt."""
    ambiguities: List[str]
    suggested_clarifications: List[str]
    clarity_score: float  # 0-1, where 1 is perfectly clear
    needs_user_input: bool


# ==============================================================================
# Multi-Agent Prompt Diffusion
# ==============================================================================

class PromptDiffusion:
    """Multi-agent prompt diffusion and refinement system.
    
    Orchestrates multiple refiner agents with different roles to collaboratively
    improve prompts through iterative refinement rounds.
    
    Features:
    - Multiple specialized refiner roles
    - Iterative refinement with convergence detection
    - Ambiguity analysis and resolution
    - Quality scoring and improvement tracking
    - Transparency through version history
    """
    
    DEFAULT_ROLES = [
        RefinerRole.CLARIFIER,
        RefinerRole.EXPANDER,
        RefinerRole.CRITIC,
        RefinerRole.SPECIALIST,
        RefinerRole.SIMPLIFIER,
        RefinerRole.CONSISTENCY,
        RefinerRole.OBJECTIVE_GUARD,
        RefinerRole.SYNTHESIZER,
    ]
    
    def __init__(
        self,
        providers: Dict[str, Any],
        max_rounds: int = 6,
        convergence_threshold: float = 0.9,
        min_improvement_threshold: float = 0.02,
        enable_parallel_refinement: bool = True,
        knowledge_base: Optional[Any] = None,
    ) -> None:
        """
        Initialize the prompt diffusion system.
        
        Args:
            providers: Dict of LLM providers by name
            max_rounds: Maximum refinement rounds (default: 3)
            convergence_threshold: Score threshold for convergence (default: 0.85)
            min_improvement_threshold: Minimum improvement to continue (default: 0.05)
            enable_parallel_refinement: Run refiners in parallel (default: True)
        """
        self.providers = providers
        self.max_rounds = max_rounds
        self.convergence_threshold = convergence_threshold
        self.min_improvement_threshold = min_improvement_threshold
        self.enable_parallel = enable_parallel_refinement
        self.knowledge_base = knowledge_base
    
    async def diffuse(
        self,
        initial_prompt: str,
        models: List[str],
        *,
        roles: Optional[List[RefinerRole]] = None,
        context: Optional[str] = None,
        subject: Optional[str] = None,
        domain: Optional[str] = None,
        analyze_ambiguity: bool = True,
        clarity_target: float = 0.93,
        max_rounds: Optional[int] = None,
    ) -> DiffusionResult:
        """
        Run the multi-agent prompt diffusion process.
        
        Args:
            initial_prompt: The starting prompt to refine
            models: List of models to use for refinement
            roles: Specific refiner roles to use (default: CLARIFIER, EXPANDER, SYNTHESIZER)
            context: Optional additional context
            subject: Optional subject description
            domain: Optional domain for specialist refinement
            analyze_ambiguity: Whether to analyze and resolve ambiguities
            
        Returns:
            DiffusionResult with final prompt and refinement history
        """
        import time
        start_time = time.time()
        
        if not models:
            raise ValueError("At least one model is required for prompt diffusion")
        
        roles = roles or self.DEFAULT_ROLES
        max_rounds = max_rounds or self.max_rounds
        versions: List[PromptVersion] = []
        refinement_steps: List[RefinementStep] = []
        current_prompt = initial_prompt
        
        # Ambiguity analysis
        ambiguities_resolved: List[str] = []
        clarifications_added: List[str] = []
        clarity_score: Optional[float] = None
        
        if analyze_ambiguity:
            ambiguity_analysis = await self._analyze_ambiguity(
                initial_prompt, models[0]
            )
            clarity_score = ambiguity_analysis.clarity_score
            if ambiguity_analysis.ambiguities:
                logger.info(
                    "Found %d ambiguities in prompt",
                    len(ambiguity_analysis.ambiguities)
                )
        
        # Create initial version
        initial_version = PromptVersion(
            version=0,
            prompt=initial_prompt,
            author="user",
            score=0.5,  # Baseline
        )
        versions.append(initial_version)
        
        # Run refinement rounds
        previous_best_score = 0.5
        
        stalled_rounds = 0
        for round_num in range(1, max_rounds + 1):
            logger.info("Prompt diffusion round %d/%d", round_num, max_rounds)
            
            round_versions: List[PromptVersion] = []
            round_steps: List[RefinementStep] = []
            
            # Apply each role's refinement
            if self.enable_parallel:
                # Run all roles in parallel
                tasks = []
                for i, role in enumerate(roles):
                    model = models[i % len(models)]
                    tasks.append(self._apply_role_refinement(
                        current_prompt,
                        role,
                        model,
                        round_num=round_num,
                        context=context,
                        domain=domain,
                    ))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning("Refinement failed: %s", result)
                        continue
                    version, step = result
                    round_versions.append(version)
                    round_steps.append(step)
            else:
                # Sequential refinement (each builds on previous)
                intermediate_prompt = current_prompt
                for i, role in enumerate(roles):
                    model = models[i % len(models)]
                    try:
                        version, step = await self._apply_role_refinement(
                            intermediate_prompt,
                            role,
                            model,
                            round_num=round_num,
                            context=context,
                            domain=domain,
                        )
                        round_versions.append(version)
                        round_steps.append(step)
                        intermediate_prompt = version.prompt
                    except Exception as e:
                        logger.warning("Role %s failed: %s", role.value, e)
            
            if not round_versions:
                logger.warning("No successful refinements in round %d", round_num)
                break
            
            refinement_steps.extend(round_steps)
            
            # Synthesize if we have multiple versions
            if len(round_versions) > 1:
                synthesis_version = await self._synthesize_versions(
                    round_versions,
                    models[0],
                    round_num,
                )
                round_versions.append(synthesis_version)
            
            # Select best version from this round
            best_version = max(round_versions, key=lambda v: v.score)
            best_version.version = len(versions)
            best_version.parent_version = len(versions) - 1
            versions.append(best_version)
            
            # Track improvements
            if best_version.role == RefinerRole.CLARIFIER:
                clarifications_added.extend(best_version.improvements)
            
            # Check convergence
            improvement = best_version.score - previous_best_score
            convergence_score = self._calculate_convergence(versions, clarity_hint=clarity_score if analyze_ambiguity else None)
            
            logger.info(
                "Round %d: Score %.3f, Improvement %.3f, Convergence %.3f",
                round_num, best_version.score, improvement, convergence_score
            )
            
            # Stop if converged or no improvement
            if convergence_score >= max(self.convergence_threshold, clarity_target):
                logger.info("Prompt diffusion converged at round %d (convergence=%.3f)", round_num, convergence_score)
                break
            
            if improvement < self.min_improvement_threshold and round_num > 1:
                stalled_rounds += 1
                logger.info("Minimal improvement (%.3f); stalled rounds=%d", improvement, stalled_rounds)
                if stalled_rounds >= 2:
                    logger.info("Stopping due to consecutive stalled rounds")
                    break
            else:
                stalled_rounds = 0
            
            previous_best_score = best_version.score
            current_prompt = best_version.prompt
        
        # Final best version
        final_best = max(versions, key=lambda v: v.score)
        final_convergence = self._calculate_convergence(versions, clarity_hint=clarity_score)
        total_duration = (time.time() - start_time) * 1000
        
        return DiffusionResult(
            original_prompt=initial_prompt,
            final_prompt=final_best.prompt,
            versions=versions,
            refinement_steps=refinement_steps,
            convergence_score=final_convergence,
            rounds_completed=len(versions) - 1,
            best_version=final_best,
            total_duration_ms=total_duration,
            ambiguities_resolved=ambiguities_resolved,
            clarifications_added=clarifications_added,
        )
    
    async def quick_refine(
        self,
        prompt: str,
        model: str,
        *,
        focus: Optional[RefinerRole] = None,
    ) -> Tuple[str, float]:
        """
        Quick single-pass refinement for simple prompts.
        
        Args:
            prompt: Prompt to refine
            model: Model to use
            focus: Optional specific focus (default: SYNTHESIZER)
            
        Returns:
            Tuple of (refined_prompt, quality_score)
        """
        role = focus or RefinerRole.SYNTHESIZER
        version, _ = await self._apply_role_refinement(
            prompt, role, model, round_num=1
        )
        return version.prompt, version.score
    
    async def _apply_role_refinement(
        self,
        prompt: str,
        role: RefinerRole,
        model: str,
        *,
        round_num: int = 1,
        context: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Tuple[PromptVersion, RefinementStep]:
        """Apply a specific role's refinement to a prompt."""
        import time
        start_time = time.time()
        
        provider = self._select_provider(model)
        
        # Opportunistic knowledge retrieval for context-hungry roles
        enriched_context = context
        if self.knowledge_base and role in {RefinerRole.EXPANDER, RefinerRole.SPECIALIST}:
            try:
                kb_results = self._fetch_knowledge(prompt, top_k=3)
                if kb_results:
                    snippets = "\n".join(f"- {r}" for r in kb_results)
                    kb_block = f"Relevant background from knowledge base:\n{snippets}"
                    enriched_context = f"{context}\n{kb_block}" if context else kb_block
            except Exception as e:
                logger.debug("Knowledge fetch skipped: %s", e)
        
        # Build refinement prompt
        refinement_prompt = self._build_role_prompt(
            prompt, role, round_num, enriched_context, domain
        )
        
        # Get refinement
        result = await provider.complete(refinement_prompt, model=model)
        refined_prompt = self._extract_refined_prompt(result.content)
        
        # Score the refinement
        score = await self._score_refinement(prompt, refined_prompt, model)
        
        # Extract improvements
        improvements = self._extract_improvements(prompt, refined_prompt)
        reasoning = self._extract_reasoning(result.content)
        
        duration = (time.time() - start_time) * 1000
        
        version = PromptVersion(
            version=0,  # Will be set by caller
            prompt=refined_prompt,
            author=model,
            role=role,
            score=score,
            improvements=improvements,
            reasoning=reasoning,
        )
        
        step = RefinementStep(
            role=role,
            model=model,
            input_prompt=prompt,
            output_prompt=refined_prompt,
            score=score,
            reasoning=reasoning,
            duration_ms=duration,
        )
        
        return version, step
    
    def _build_role_prompt(
        self,
        prompt: str,
        role: RefinerRole,
        round_num: int,
        context: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> str:
        """Build the refinement prompt for a specific role."""
        role_instruction = ROLE_PROMPTS.get(role, ROLE_PROMPTS[RefinerRole.SYNTHESIZER])
        
        lines = [
            role_instruction,
            "",
            "=" * 50,
            f"CURRENT PROMPT (Round {round_num}):",
            "=" * 50,
            f'"{prompt}"',
            "",
        ]
        
        if context:
            lines.extend([
                "ADDITIONAL CONTEXT:",
                context,
                "",
            ])
        
        if domain:
            lines.extend([
                f"DOMAIN: {domain}",
                "",
            ])
        
        lines.extend([
            "=" * 50,
            "YOUR TASK:",
            "=" * 50,
            "",
            "1. Analyze the prompt based on your role's focus",
            "2. Identify specific improvements you can make",
            "3. Create an improved version of the prompt",
            "",
            "OUTPUT FORMAT:",
            "First, briefly explain your reasoning (1-2 sentences).",
            "Then output the refined prompt on a new line starting with 'REFINED PROMPT:'",
            "",
            "Example:",
            "Reasoning: Added clarification about scope and added example case.",
            "REFINED PROMPT: [Your improved prompt here]",
        ])
        
        return "\n".join(lines)
    
    def _extract_refined_prompt(self, content: str) -> str:
        """Extract the refined prompt from model output."""
        import re
        
        content = content.strip()
        
        # Look for explicit marker
        if "REFINED PROMPT:" in content.upper():
            parts = content.upper().split("REFINED PROMPT:", 1)
            if len(parts) > 1:
                # Get everything after the marker
                refined = content[content.upper().find("REFINED PROMPT:") + 15:]
                return refined.strip().strip('"\'')
        
        # Look for prompt in quotes
        quote_match = re.search(r'"([^"]{20,})"', content)
        if quote_match:
            return quote_match.group(1)
        
        # If content is short enough, use as-is
        if len(content) < 2000:
            # Remove common prefixes
            for prefix in ["Here's the refined prompt:", "Refined:", "Improved prompt:"]:
                if content.lower().startswith(prefix.lower()):
                    content = content[len(prefix):].strip()
                    break
            return content.strip().strip('"\'')
        
        # Last resort: first substantial line
        lines = [l.strip() for l in content.split('\n') if len(l.strip()) > 20]
        return lines[0] if lines else content[:500]
    
    def _extract_reasoning(self, content: str) -> str:
        """Extract reasoning from model output."""
        if "REFINED PROMPT:" in content.upper():
            parts = content.split("REFINED PROMPT:", 1)
            reasoning = parts[0].strip()
            
            # Clean up
            for prefix in ["Reasoning:", "Analysis:", "Explanation:"]:
                if reasoning.lower().startswith(prefix.lower()):
                    reasoning = reasoning[len(prefix):].strip()
            
            return reasoning[:500]  # Limit length
        
        return ""
    
    async def _synthesize_versions(
        self,
        versions: List[PromptVersion],
        model: str,
        round_num: int,
    ) -> PromptVersion:
        """Synthesize multiple refined versions into one."""
        provider = self._select_provider(model)
        
        # Build synthesis prompt
        synthesis_prompt = [
            "You are synthesizing multiple refined versions of a prompt into one optimal version.",
            "",
            "The following versions were created by different refinement agents:",
        ]
        
        for i, v in enumerate(versions, 1):
            role_name = v.role.value if v.role else "unknown"
            synthesis_prompt.append(f"\nVersion {i} ({role_name}):")
            synthesis_prompt.append(f'"{v.prompt}"')
            if v.improvements:
                synthesis_prompt.append(f"Improvements: {', '.join(v.improvements)}")
        
        synthesis_prompt.extend([
            "",
            "Create a single synthesized prompt that:",
            "1. Combines the best aspects of all versions",
            "2. Resolves any conflicts between versions",
            "3. Is clear, comprehensive, and actionable",
            "4. Maintains the original intent",
            "",
            "Output ONLY the synthesized prompt, no explanation needed.",
        ])
        
        result = await provider.complete("\n".join(synthesis_prompt), model=model)
        synthesized = self._extract_refined_prompt(result.content)
        
        # Score synthesis
        # Use average of input versions as reference
        avg_score = sum(v.score for v in versions) / len(versions)
        # Synthesis should be at least as good as average
        synthesis_score = min(1.0, avg_score + 0.1)
        
        return PromptVersion(
            version=0,
            prompt=synthesized,
            author=model,
            role=RefinerRole.SYNTHESIZER,
            score=synthesis_score,
            improvements=["Combined multiple perspectives"],
        )
    
    async def _analyze_ambiguity(
        self,
        prompt: str,
        model: str,
    ) -> AmbiguityAnalysis:
        """Analyze a prompt for ambiguities."""
        provider = self._select_provider(model)
        
        analysis_prompt = f"""Analyze this prompt for ambiguities and unclear elements.

Prompt: "{prompt}"

Identify:
1. Ambiguous words or phrases
2. Missing context that would be helpful
3. Unclear requirements or constraints

Output format:
AMBIGUITIES:
- [List each ambiguity on a new line, or "None" if clear]

SUGGESTED_CLARIFICATIONS:
- [List suggested clarifications]

CLARITY_SCORE: [0.0-1.0]
NEEDS_USER_INPUT: [YES/NO]"""
        
        try:
            result = await provider.complete(analysis_prompt, model=model)
            return self._parse_ambiguity_analysis(result.content)
        except Exception as e:
            logger.warning("Ambiguity analysis failed: %s", e)
            return AmbiguityAnalysis(
                ambiguities=[],
                suggested_clarifications=[],
                clarity_score=0.7,
                needs_user_input=False,
            )
    
    def _parse_ambiguity_analysis(self, content: str) -> AmbiguityAnalysis:
        """Parse ambiguity analysis from model output."""
        import re
        
        ambiguities = []
        clarifications = []
        clarity_score = 0.7
        needs_user_input = False
        
        # Extract ambiguities
        if "AMBIGUITIES:" in content.upper():
            section = content.upper().split("AMBIGUITIES:", 1)[1]
            if "SUGGESTED_CLARIFICATIONS:" in section:
                section = section.split("SUGGESTED_CLARIFICATIONS:")[0]
            
            for line in section.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line and line.lower() != "none" and len(line) > 3:
                    ambiguities.append(line)
        
        # Extract clarifications
        if "SUGGESTED_CLARIFICATIONS:" in content.upper():
            section = content.upper().split("SUGGESTED_CLARIFICATIONS:", 1)[1]
            if "CLARITY_SCORE:" in section:
                section = section.split("CLARITY_SCORE:")[0]
            
            for line in section.split("\n"):
                line = line.strip().lstrip("-").strip()
                if line and len(line) > 3:
                    clarifications.append(line)
        
        # Extract clarity score
        score_match = re.search(r"CLARITY_SCORE:\s*([\d.]+)", content, re.IGNORECASE)
        if score_match:
            try:
                clarity_score = float(score_match.group(1))
                clarity_score = min(1.0, max(0.0, clarity_score))
            except ValueError:
                pass
        
        # Check if user input needed
        needs_user_input = "YES" in content.upper() and "NEEDS_USER_INPUT" in content.upper()
        
        return AmbiguityAnalysis(
            ambiguities=ambiguities[:5],  # Limit
            suggested_clarifications=clarifications[:5],
            clarity_score=clarity_score,
            needs_user_input=needs_user_input,
        )
    
    async def _score_refinement(
        self,
        original: str,
        refined: str,
        model: str,
    ) -> float:
        """Score a refined prompt against the original."""
        provider = self._select_provider(model)
        
        scoring_prompt = f"""Rate this prompt refinement on a scale of 0.0 to 1.0.

Original: "{original[:500]}"
Refined: "{refined[:500]}"

Scoring criteria (0-1 total):
- Clarity (0.0-0.25): Is the refined prompt clearer?
- Specificity (0.0-0.2): Is it more specific and actionable?
- Completeness (0.0-0.2): Does it cover all necessary aspects?
- Intent preservation (0.0-0.25): Does it maintain the original intent?
- Consistency (0.0-0.1): No conflicts or contradictions introduced?

Respond with ONLY a decimal number between 0.0 and 1.0."""
        
        try:
            result = await provider.complete(scoring_prompt, model=model)
            import re
            match = re.search(r"(\d+\.?\d*)", result.content.strip())
            if match:
                score = float(match.group(1))
                return min(1.0, max(0.0, score))
        except Exception as e:
            logger.warning("Scoring failed: %s", e)
        
        # Heuristic fallback with intent/consistency checks
        intent_score = self._intent_preservation_score(original, refined)
        len_improvement = len(refined) / max(len(original), 1)
        structural_bonus = 0.05 if '?' in refined and '?' not in original else 0.0
        base = 0.55 + structural_bonus
        if 0.7 < len_improvement < 1.8:
            base += 0.05
        return min(1.0, max(0.0, base * intent_score))
    
    def _calculate_convergence(self, versions: List[PromptVersion], clarity_hint: Optional[float] = None) -> float:
        """Calculate convergence score based on version history and optional clarity."""
        if len(versions) < 2:
            return 0.0
        
        last = versions[-1]
        prev = versions[-2]
        
        # Length similarity
        len_sim = 1.0 - abs(len(last.prompt) - len(prev.prompt)) / max(
            len(last.prompt), len(prev.prompt), 1
        )
        
        # Word overlap (Jaccard similarity)
        last_words = set(last.prompt.lower().split())
        prev_words = set(prev.prompt.lower().split())
        if last_words or prev_words:
            jaccard = len(last_words & prev_words) / len(last_words | prev_words)
        else:
            jaccard = 0.0
        
        # Score trend
        score_improvement = max(0.0, last.score - prev.score)
        
        # Clarity bonus if provided
        clarity = clarity_hint if clarity_hint is not None else 0.0
        
        # Weighted convergence
        convergence = (
            len_sim * 0.15
            + jaccard * 0.35
            + last.score * 0.35
            + clarity * 0.15
        )
        
        return min(1.0, convergence)
    
    def _extract_improvements(self, original: str, refined: str) -> List[str]:
        """Extract improvements made in refinement."""
        improvements = []
        
        orig_len = len(original)
        ref_len = len(refined)
        
        if ref_len > orig_len * 1.2:
            improvements.append("Added detail and context")
        elif ref_len < orig_len * 0.8:
            improvements.append("Made more concise")
        
        # Check for structural improvements
        if '?' in refined and '?' not in original:
            improvements.append("Added clarifying questions")
        
        if refined.count('.') > original.count('.'):
            improvements.append("Improved structure")
        
        # Check for example addition
        if any(marker in refined.lower() for marker in ['example', 'e.g.', 'for instance']):
            if not any(marker in original.lower() for marker in ['example', 'e.g.', 'for instance']):
                improvements.append("Added examples")
        
        # Consistency/intent checks
        if self._intent_preservation_score(original, refined) < 0.85:
            improvements.append("Intent risk detected; recommend Objective Guard review")
        else:
            improvements.append("Preserved stated intent")
        
        return improvements

    def _intent_preservation_score(self, original: str, refined: str) -> float:
        """Heuristic intent preservation based on key token retention."""
        # Preserve quoted phrases and numbers
        import re
        phrases = re.findall(r'"(.*?)"|\'(.*?)\'', original)
        flat_phrases = [p for pair in phrases for p in pair if p]
        numbers = re.findall(r'\d+(?:\.\d+)?', original)
        
        score = 1.0
        for phrase in flat_phrases:
            if phrase and phrase.lower() not in refined.lower():
                score -= 0.05
        for num in numbers:
            if num not in refined:
                score -= 0.05
        
        return max(0.0, min(1.0, score))

    def _fetch_knowledge(self, prompt: str, top_k: int = 3) -> List[str]:
        """Fetch relevant snippets from knowledge base if available."""
        if not self.knowledge_base or not hasattr(self.knowledge_base, "search"):
            return []
        try:
            results = self.knowledge_base.search(prompt, top_k=top_k)
            snippets = []
            for r in results or []:
                content = r.get("content") or r.get("text") or str(r)
                if content:
                    snippets.append(content[:300])
            return snippets
        except Exception as e:
            logger.debug("Knowledge search failed: %s", e)
            return []
        
        return improvements
    
    def _select_provider(self, model: str) -> Any:
        """Select provider for a model."""
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
        
        # Fallback - prefer openrouter, then first non-stub provider (NEVER stub)
        if "openrouter" in self.providers:
            return self.providers["openrouter"]
        
        return next((p for n, p in self.providers.items() if n != "stub"), next(iter(self.providers.values())))


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def refine_prompt(
    prompt: str,
    providers: Dict[str, Any],
    models: List[str],
    *,
    max_rounds: int = 2,
    roles: Optional[List[RefinerRole]] = None,
) -> DiffusionResult:
    """Convenience function to refine a prompt."""
    diffusion = PromptDiffusion(
        providers=providers,
        max_rounds=max_rounds,
    )
    return await diffusion.diffuse(prompt, models, roles=roles)


async def quick_clarify(
    prompt: str,
    provider: Any,
    model: str,
) -> str:
    """Quick clarification pass on a prompt."""
    diffusion = PromptDiffusion(providers={"default": provider})
    refined, _ = await diffusion.quick_refine(prompt, model, focus=RefinerRole.CLARIFIER)
    return refined
