"""Quality Booster Module for LLMHive.

This module implements techniques to boost response quality beyond individual
model capabilities through:

1. CHAIN-OF-THOUGHT ENFORCEMENT - Force step-by-step reasoning
2. SELF-CONSISTENCY - Generate multiple reasoning paths, vote on answer
3. REFLECTION - Make model critique and improve its own answer
4. DECOMPOSITION - Break complex questions into simpler parts
5. SCAFFOLDING - Provide structured templates for complex tasks
6. VERIFICATION LOOPS - Iteratively verify and correct

These techniques are proven to improve accuracy on complex tasks.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Quality Enhancement Prompts
# ==============================================================================

CHAIN_OF_THOUGHT_PREFIX = """Let's approach this step-by-step:

1. First, I'll understand what's being asked
2. Then, I'll break down the problem
3. Next, I'll work through each part systematically
4. Finally, I'll synthesize the answer

"""

SELF_REFLECTION_PROMPT = """Review your response critically:

Your response: {response}

Now ask yourself:
1. Is this answer complete?
2. Are there any errors or inaccuracies?
3. Could anything be explained more clearly?
4. Is there important information I missed?

If you find any issues, provide an improved response. 
If the response is already good, respond with "APPROVED: [your confidence level 1-10]"
"""

VERIFICATION_PROMPT = """Verify this answer:

Question: {question}
Answer: {answer}

Check:
1. Factual accuracy - Are all facts correct?
2. Logical consistency - Does the reasoning hold?
3. Completeness - Is anything important missing?
4. Relevance - Does it address the actual question?

If there are issues, describe them and provide corrections.
If the answer is correct, respond with "VERIFIED" followed by confidence (1-10).
"""

DECOMPOSITION_PROMPT = """Break this complex question into simpler sub-questions:

Question: {question}

Generate 2-4 simpler sub-questions that together would answer the original.
Format each as:
Q1: [sub-question]
Q2: [sub-question]
...
"""

SYNTHESIS_PROMPT = """Synthesize these sub-answers into a complete response:

Original question: {question}

Sub-answers:
{sub_answers}

Provide a comprehensive, coherent answer that integrates all the sub-answers.
"""


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class QualityResult:
    """Result of quality boosting."""
    original_response: str
    boosted_response: str
    quality_improvement: float  # Estimated improvement (0-1)
    techniques_applied: List[str]
    iterations: int
    verification_passed: bool
    confidence: float
    notes: List[str]


@dataclass(slots=True)
class ConsistencyVote:
    """A vote in self-consistency."""
    answer: str
    confidence: float
    reasoning_path: str


# ==============================================================================
# Quality Booster Implementation
# ==============================================================================

class QualityBooster:
    """Boosts response quality through various techniques.
    
    Techniques:
    1. Chain-of-Thought: Force step-by-step reasoning
    2. Self-Consistency: Multiple reasoning paths, majority vote
    3. Reflection: Self-critique and improvement
    4. Decomposition: Break complex into simple
    5. Verification Loop: Iterative checking
    """
    
    def __init__(
        self,
        providers: Dict[str, Any],
        default_model: str = "gpt-4o",
    ) -> None:
        """Initialize quality booster.
        
        Args:
            providers: LLM providers
            default_model: Default model for boosting operations
        """
        self.providers = providers
        self.default_model = default_model
    
    async def boost(
        self,
        prompt: str,
        response: str,
        *,
        techniques: Optional[List[str]] = None,
        model: Optional[str] = None,
        max_iterations: int = 2,
    ) -> QualityResult:
        """
        Apply quality boosting techniques to improve a response.
        
        Args:
            prompt: Original prompt
            response: Initial response to boost
            techniques: Techniques to apply (default: auto-select)
            model: Model to use for boosting
            max_iterations: Max improvement iterations
            
        Returns:
            QualityResult with improved response
        """
        model = model or self.default_model
        techniques = techniques or self._auto_select_techniques(prompt, response)
        
        current = response
        applied: List[str] = []
        notes: List[str] = []
        iterations = 0
        
        for technique in techniques:
            if iterations >= max_iterations:
                break
            
            try:
                if technique == "reflection":
                    improved, improved_flag = await self._apply_reflection(
                        prompt, current, model
                    )
                    if improved_flag:
                        current = improved
                        applied.append("reflection")
                        iterations += 1
                
                elif technique == "verification":
                    verified, passed, conf = await self._apply_verification(
                        prompt, current, model
                    )
                    if not passed:
                        current = verified
                        applied.append("verification_correction")
                        iterations += 1
                    notes.append(f"Verification: {'passed' if passed else 'corrected'}")
                
                elif technique == "chain_of_thought":
                    improved = await self._apply_cot(prompt, model)
                    if improved:
                        current = improved
                        applied.append("chain_of_thought")
                        iterations += 1
                
            except Exception as e:
                logger.warning("Technique %s failed: %s", technique, e)
                notes.append(f"Technique {technique} failed")
        
        # Final verification
        _, verified, confidence = await self._apply_verification(prompt, current, model)
        
        # Estimate quality improvement
        improvement = self._estimate_improvement(response, current, applied)
        
        return QualityResult(
            original_response=response,
            boosted_response=current,
            quality_improvement=improvement,
            techniques_applied=applied,
            iterations=iterations,
            verification_passed=verified,
            confidence=confidence,
            notes=notes,
        )
    
    async def generate_with_cot(
        self,
        prompt: str,
        model: Optional[str] = None,
    ) -> str:
        """Generate response with enforced chain-of-thought."""
        model = model or self.default_model
        
        cot_prompt = f"{CHAIN_OF_THOUGHT_PREFIX}\nQuestion: {prompt}"
        
        response = await self._call_model(model, cot_prompt)
        return response
    
    async def generate_with_self_consistency(
        self,
        prompt: str,
        n_paths: int = 3,
        model: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Generate with self-consistency (multiple reasoning paths).
        
        Returns the most consistent answer and confidence.
        """
        model = model or self.default_model
        
        # Generate multiple reasoning paths
        tasks = []
        for i in range(n_paths):
            varied_prompt = f"""Think through this problem carefully. Path {i+1}:

{prompt}

Show your reasoning step by step, then give your final answer.
Mark your final answer clearly with "FINAL ANSWER:"
"""
            tasks.append(self._call_model(model, varied_prompt))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract answers
        votes: List[ConsistencyVote] = []
        for resp in responses:
            if isinstance(resp, str):
                answer = self._extract_final_answer(resp)
                votes.append(ConsistencyVote(
                    answer=answer,
                    confidence=0.8,
                    reasoning_path=resp,
                ))
        
        if not votes:
            return "", 0.0
        
        # Find most common answer (majority vote)
        answer_counts: Dict[str, int] = {}
        for vote in votes:
            key = self._normalize_answer(vote.answer)
            answer_counts[key] = answer_counts.get(key, 0) + 1
        
        best_answer = max(answer_counts.keys(), key=lambda k: answer_counts[k])
        confidence = answer_counts[best_answer] / len(votes)
        
        # Return the full response with the winning answer
        for vote in votes:
            if self._normalize_answer(vote.answer) == best_answer:
                return vote.reasoning_path, confidence
        
        return votes[0].reasoning_path, confidence
    
    async def generate_with_decomposition(
        self,
        prompt: str,
        model: Optional[str] = None,
    ) -> str:
        """Generate by decomposing complex question into simpler parts."""
        model = model or self.default_model
        
        # Decompose (use replace for question which may contain curly braces)
        decomp_prompt = DECOMPOSITION_PROMPT.replace("{question}", prompt)
        decomp_response = await self._call_model(model, decomp_prompt)
        
        # Extract sub-questions
        sub_questions = self._extract_sub_questions(decomp_response)
        
        if len(sub_questions) <= 1:
            # Not decomposable, return direct answer
            return await self._call_model(model, prompt)
        
        # Answer each sub-question
        sub_answers = []
        for i, sq in enumerate(sub_questions, 1):
            answer = await self._call_model(model, sq)
            sub_answers.append(f"Q{i}: {sq}\nA{i}: {answer}")
        
        # Synthesize (use replace for question and sub_answers which may contain curly braces)
        synth_prompt = SYNTHESIS_PROMPT.replace("{question}", prompt).replace("{sub_answers}", "\n\n".join(sub_answers))
        
        final = await self._call_model(model, synth_prompt)
        return final
    
    async def _apply_reflection(
        self,
        prompt: str,
        response: str,
        model: str,
    ) -> Tuple[str, bool]:
        """Apply self-reflection to improve response."""
        # Use replace for response which may contain curly braces
        reflect_prompt = SELF_REFLECTION_PROMPT.replace("{response}", response)
        
        reflection = await self._call_model(model, reflect_prompt)
        
        # Check if approved
        if "APPROVED" in reflection.upper():
            return response, False  # No improvement needed
        
        return reflection, True
    
    async def _apply_verification(
        self,
        prompt: str,
        response: str,
        model: str,
    ) -> Tuple[str, bool, float]:
        """Apply verification and correction."""
        # Use replace for question and answer which may contain curly braces
        verify_prompt = VERIFICATION_PROMPT.replace("{question}", prompt).replace("{answer}", response)
        
        verification = await self._call_model(model, verify_prompt)
        
        # Check if verified
        if "VERIFIED" in verification.upper():
            # Extract confidence
            conf_match = re.search(r'(\d+)', verification)
            confidence = float(conf_match.group(1)) / 10 if conf_match else 0.8
            return response, True, confidence
        
        # Extract corrected version
        return verification, False, 0.6
    
    async def _apply_cot(
        self,
        prompt: str,
        model: str,
    ) -> str:
        """Apply chain-of-thought prompting."""
        return await self.generate_with_cot(prompt, model)
    
    def _auto_select_techniques(
        self,
        prompt: str,
        response: str,
    ) -> List[str]:
        """Auto-select appropriate boosting techniques."""
        techniques = []
        prompt_lower = prompt.lower()
        
        # Always use reflection for quality
        techniques.append("reflection")
        
        # Complex reasoning benefits from verification
        if any(word in prompt_lower for word in [
            "analyze", "compare", "evaluate", "explain why", "prove"
        ]):
            techniques.append("verification")
        
        # Math/logic benefits from CoT
        if any(word in prompt_lower for word in [
            "calculate", "solve", "math", "equation", "logic"
        ]):
            techniques.append("chain_of_thought")
        
        return techniques
    
    def _extract_final_answer(self, response: str) -> str:
        """Extract final answer from response."""
        # Look for explicit marker
        if "FINAL ANSWER:" in response.upper():
            parts = response.upper().split("FINAL ANSWER:", 1)
            if len(parts) > 1:
                return parts[1].strip()[:200]
        
        # Last sentence/line as fallback
        lines = [l.strip() for l in response.split('\n') if l.strip()]
        return lines[-1][:200] if lines else response[:200]
    
    def _normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison."""
        # Remove punctuation, lowercase, strip
        normalized = re.sub(r'[^\w\s]', '', answer.lower())
        normalized = ' '.join(normalized.split())
        return normalized[:100]  # First 100 chars
    
    def _extract_sub_questions(self, decomp: str) -> List[str]:
        """Extract sub-questions from decomposition response."""
        questions = []
        
        for line in decomp.split('\n'):
            line = line.strip()
            # Match Q1:, Q2:, etc.
            if re.match(r'^Q\d+:', line, re.IGNORECASE):
                question = re.sub(r'^Q\d+:\s*', '', line, flags=re.IGNORECASE)
                if question:
                    questions.append(question)
        
        return questions
    
    def _estimate_improvement(
        self,
        original: str,
        improved: str,
        techniques: List[str],
    ) -> float:
        """Estimate quality improvement."""
        if original == improved:
            return 0.0
        
        improvement = 0.0
        
        # Length increase (up to a point) often means more detail
        len_ratio = len(improved) / max(len(original), 1)
        if 1.0 < len_ratio < 2.0:
            improvement += 0.1
        
        # Structure improvement
        orig_structure = original.count('\n') + original.count('1.')
        new_structure = improved.count('\n') + improved.count('1.')
        if new_structure > orig_structure:
            improvement += 0.1
        
        # Technique bonuses
        improvement += len(techniques) * 0.1
        
        return min(0.5, improvement)
    
    async def _call_model(self, model: str, prompt: str) -> str:
        """Call a model and return response text."""
        # Find provider
        provider = None
        for prov_name, prov in self.providers.items():
            if prov_name in model.lower() or model.lower().startswith(prov_name[:3]):
                provider = prov
                break
        
        if not provider:
            # Use first available
            provider = next(iter(self.providers.values()))
        
        try:
            result = await provider.complete(prompt, model=model)
            return getattr(result, 'content', '') or getattr(result, 'text', '')
        except Exception as e:
            logger.error("Model call failed: %s", e)
            return ""


# ==============================================================================
# Specialized Quality Techniques
# ==============================================================================

class FactualQualityBooster:
    """Specialized booster for factual accuracy."""
    
    def __init__(self, providers: Dict[str, Any]) -> None:
        self.providers = providers
        self.booster = QualityBooster(providers)
    
    async def boost_factual(
        self,
        prompt: str,
        response: str,
        model: str = "gpt-4o",
    ) -> QualityResult:
        """Boost factual accuracy specifically."""
        # First, identify factual claims
        claims_prompt = f"""Identify all factual claims in this response:

Response: {response}

List each factual claim on a new line with "CLAIM:" prefix.
Only include verifiable facts, not opinions or general statements.
"""
        
        claims_response = await self.booster._call_model(model, claims_prompt)
        
        # Extract claims
        claims = [
            line.replace("CLAIM:", "").strip()
            for line in claims_response.split('\n')
            if line.strip().startswith("CLAIM:")
        ]
        
        if not claims:
            # No factual claims, return original
            return QualityResult(
                original_response=response,
                boosted_response=response,
                quality_improvement=0.0,
                techniques_applied=["factual_analysis"],
                iterations=0,
                verification_passed=True,
                confidence=0.8,
                notes=["No factual claims to verify"],
            )
        
        # Verify each claim
        verify_prompt = f"""Verify these factual claims. For each, indicate if it's:
- CORRECT: The claim is accurate
- INCORRECT: The claim is wrong (provide correct info)
- UNCERTAIN: Cannot verify

Claims to verify:
{chr(10).join(f"- {c}" for c in claims[:10])}

Format: [CORRECT/INCORRECT/UNCERTAIN] - [claim] - [correction if incorrect]
"""
        
        verification = await self.booster._call_model(model, verify_prompt)
        
        # Check if corrections needed
        if "INCORRECT" in verification:
            # Apply corrections
            correction_prompt = f"""Update this response to fix the factual errors identified:

Original response: {response}

Verification results:
{verification}

Provide the corrected response, fixing only the incorrect facts.
"""
            corrected = await self.booster._call_model(model, correction_prompt)
            
            return QualityResult(
                original_response=response,
                boosted_response=corrected,
                quality_improvement=0.3,
                techniques_applied=["factual_verification", "factual_correction"],
                iterations=1,
                verification_passed=False,
                confidence=0.85,
                notes=[f"Verified {len(claims)} claims, corrections applied"],
            )
        
        return QualityResult(
            original_response=response,
            boosted_response=response,
            quality_improvement=0.1,
            techniques_applied=["factual_verification"],
            iterations=1,
            verification_passed=True,
            confidence=0.9,
            notes=[f"Verified {len(claims)} claims, all correct"],
        )


class CodeQualityBooster:
    """Specialized booster for code quality."""
    
    def __init__(self, providers: Dict[str, Any]) -> None:
        self.providers = providers
        self.booster = QualityBooster(providers)
    
    async def boost_code(
        self,
        prompt: str,
        response: str,
        model: str = "gpt-4o",
    ) -> QualityResult:
        """Boost code quality specifically."""
        # Review code
        review_prompt = f"""Review this code for quality:

{response}

Check for:
1. Bugs or errors
2. Security issues
3. Performance problems
4. Missing error handling
5. Code style issues

If issues found, provide the corrected code.
If code is good, respond with "CODE_APPROVED" and confidence (1-10).
"""
        
        review = await self.booster._call_model(model, review_prompt)
        
        if "CODE_APPROVED" in review.upper():
            return QualityResult(
                original_response=response,
                boosted_response=response,
                quality_improvement=0.0,
                techniques_applied=["code_review"],
                iterations=1,
                verification_passed=True,
                confidence=0.9,
                notes=["Code review passed"],
            )
        
        # Extract improved code
        return QualityResult(
            original_response=response,
            boosted_response=review,
            quality_improvement=0.25,
            techniques_applied=["code_review", "code_fix"],
            iterations=1,
            verification_passed=False,
            confidence=0.85,
            notes=["Code issues found and fixed"],
        )


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def boost_response(
    prompt: str,
    response: str,
    providers: Dict[str, Any],
    model: str = "gpt-4o",
) -> QualityResult:
    """Convenience function to boost a response."""
    booster = QualityBooster(providers)
    return await booster.boost(prompt, response, model=model)


async def generate_high_quality(
    prompt: str,
    providers: Dict[str, Any],
    model: str = "gpt-4o",
    technique: str = "reflection",
) -> str:
    """Generate a high-quality response using boosting techniques."""
    booster = QualityBooster(providers, default_model=model)
    
    if technique == "cot":
        return await booster.generate_with_cot(prompt, model)
    elif technique == "consistency":
        response, _ = await booster.generate_with_self_consistency(prompt, model=model)
        return response
    elif technique == "decomposition":
        return await booster.generate_with_decomposition(prompt, model)
    else:
        # Generate then reflect
        initial = await booster._call_model(model, prompt)
        result = await booster.boost(prompt, initial, techniques=["reflection"])
        return result.boosted_response

