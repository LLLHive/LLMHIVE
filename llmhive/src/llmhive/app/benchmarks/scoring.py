"""Scoring system for benchmark evaluation.

This module provides:
- Objective scoring: Deterministic checks (contains, regex, numeric)
- Rubric scoring: Qualitative LLM-based evaluation
- Composite scoring: Weighted combination of objective and rubric scores

The scoring system is designed to be fair, reproducible, and extensible.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ScoreType(Enum):
    """Type of scoring method used."""
    OBJECTIVE = "objective"
    RUBRIC = "rubric"
    COMPOSITE = "composite"


@dataclass
class ObjectiveScore:
    """Result of objective (deterministic) scoring."""
    score: float  # 0.0 to 1.0
    passed: bool
    checks: Dict[str, bool] = field(default_factory=dict)
    details: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "passed": self.passed,
            "checks": self.checks,
            "details": self.details,
        }


@dataclass
class RubricDimension:
    """A single dimension of rubric-based evaluation."""
    name: str
    score: int  # 1-5
    description: str
    rationale: str = ""


@dataclass
class RubricScore:
    """Result of rubric (qualitative) scoring."""
    dimensions: List[RubricDimension]
    average_score: float  # 0.0 to 5.0
    normalized_score: float  # 0.0 to 1.0
    judge_model: str = ""
    judge_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": [
                {
                    "name": d.name,
                    "score": d.score,
                    "description": d.description,
                }
                for d in self.dimensions
            ],
            "average_score": self.average_score,
            "normalized_score": self.normalized_score,
            "judge_model": self.judge_model,
            "judge_confidence": self.judge_confidence,
        }


@dataclass
class ScoringResult:
    """Complete scoring result for a benchmark case."""
    prompt_id: str
    system_name: str
    
    # Individual scores
    objective_score: Optional[ObjectiveScore] = None
    rubric_score: Optional[RubricScore] = None
    
    # Composite score
    composite_score: float = 0.0
    
    # Weights used
    objective_weight: float = 0.5
    rubric_weight: float = 0.5
    
    # Flags
    is_critical: bool = False
    critical_failed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "system_name": self.system_name,
            "objective_score": self.objective_score.to_dict() if self.objective_score else None,
            "rubric_score": self.rubric_score.to_dict() if self.rubric_score else None,
            "composite_score": self.composite_score,
            "objective_weight": self.objective_weight,
            "rubric_weight": self.rubric_weight,
            "is_critical": self.is_critical,
            "critical_failed": self.critical_failed,
        }


class ObjectiveScorer:
    """Scorer for deterministic/objective checks.
    
    Supports:
    - expected_contains: Substring match (case-insensitive)
    - expected_regex: Regular expression match
    - expected_numeric: Numeric value with tolerance
    - expected_not_contains: Anti-pattern check
    - expected_jsonschema: JSON schema validation
    """
    
    def score(
        self,
        answer: str,
        expected: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None,
    ) -> ObjectiveScore:
        """Score an answer against objective criteria.
        
        Args:
            answer: The answer text to evaluate.
            expected: Dictionary of expected values/patterns.
            requirements: Optional requirements (e.g., requires_no_clarification).
        
        Returns:
            ObjectiveScore with pass/fail and details.
        """
        checks = {}
        details = {}
        
        answer_lower = answer.lower()
        requirements = requirements or {}
        
        # Check expected_contains
        expected_contains = expected.get("expected_contains")
        if expected_contains:
            contains_passed = expected_contains.lower() in answer_lower
            checks["contains"] = contains_passed
            if not contains_passed:
                details["contains"] = f"Missing: '{expected_contains}'"
        
        # Check expected_regex
        expected_regex = expected.get("expected_regex")
        if expected_regex:
            try:
                regex_passed = bool(re.search(expected_regex, answer, re.IGNORECASE))
                checks["regex"] = regex_passed
                if not regex_passed:
                    details["regex"] = f"Pattern not found: '{expected_regex}'"
            except re.error as e:
                checks["regex"] = False
                details["regex"] = f"Invalid regex: {e}"
        
        # Check expected_not_contains
        expected_not_contains = expected.get("expected_not_contains")
        if expected_not_contains:
            not_contains_passed = expected_not_contains.lower() not in answer_lower
            checks["not_contains"] = not_contains_passed
            if not not_contains_passed:
                details["not_contains"] = f"Forbidden content found: '{expected_not_contains}'"
        
        # Check expected_numeric
        expected_numeric = expected.get("expected_numeric")
        if expected_numeric:
            numeric_result = self._check_numeric(answer, expected_numeric)
            checks["numeric"] = numeric_result[0]
            if not numeric_result[0]:
                details["numeric"] = numeric_result[1]
        
        # Check expected_jsonschema
        expected_jsonschema = expected.get("expected_jsonschema")
        if expected_jsonschema:
            schema_result = self._check_jsonschema(answer, expected_jsonschema)
            checks["jsonschema"] = schema_result[0]
            if not schema_result[0]:
                details["jsonschema"] = schema_result[1]
        
        # Check no_unnecessary_clarification requirement
        if requirements.get("requires_no_clarification"):
            clarification_phrases = [
                "could you clarify",
                "what do you mean",
                "please specify",
                "more details",
                "which one",
                "can you provide more",
                "could you please",
                "i need more information",
                "please elaborate",
            ]
            asked_clarification = any(
                phrase in answer_lower
                for phrase in clarification_phrases
            )
            checks["no_clarification"] = not asked_clarification
            if asked_clarification:
                details["no_clarification"] = "Unnecessary clarification was requested"
        
        # Check requires_clarification (should ask)
        if requirements.get("requires_clarification"):
            clarification_indicators = [
                "clarify", "specify", "which", "what do you", "could you",
                "please provide", "more information", "context",
            ]
            asked_clarification = any(
                indicator in answer_lower
                for indicator in clarification_indicators
            )
            checks["asked_clarification"] = asked_clarification
            if not asked_clarification:
                details["asked_clarification"] = "Should have asked for clarification"
        
        # Calculate overall score
        if not checks:
            # No checks defined - pass by default
            return ObjectiveScore(score=1.0, passed=True, checks={}, details={})
        
        passed_count = sum(1 for v in checks.values() if v)
        total_checks = len(checks)
        score = passed_count / total_checks if total_checks > 0 else 0.0
        passed = all(checks.values())
        
        return ObjectiveScore(
            score=score,
            passed=passed,
            checks=checks,
            details=details,
        )
    
    def _check_numeric(
        self,
        answer: str,
        numeric_config: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Check if answer contains expected numeric value.
        
        Args:
            answer: The answer text.
            numeric_config: Dict with value, tolerance, and optional extract_pattern.
        
        Returns:
            Tuple of (passed, error_message).
        """
        expected_value = numeric_config.get("value")
        tolerance = numeric_config.get("tolerance", 0)
        extract_pattern = numeric_config.get("extract_pattern")
        
        if expected_value is None:
            return False, "No expected value specified"
        
        # Try to extract numeric value from answer
        extracted_value = None
        
        if extract_pattern:
            # Use custom extraction pattern
            match = re.search(extract_pattern, answer)
            if match:
                try:
                    # Remove commas and parse
                    raw_value = match.group(1).replace(",", "")
                    extracted_value = float(raw_value)
                except (ValueError, IndexError):
                    pass
        
        if extracted_value is None:
            # Fallback: find any number in the answer
            numbers = re.findall(r"-?[\d,]+\.?\d*", answer)
            for num_str in numbers:
                try:
                    val = float(num_str.replace(",", ""))
                    # Check if this number is close to expected
                    if abs(val - expected_value) <= tolerance:
                        extracted_value = val
                        break
                except ValueError:
                    continue
        
        if extracted_value is None:
            return False, f"Could not extract numeric value (expected: {expected_value})"
        
        # Check if within tolerance
        if abs(extracted_value - expected_value) <= tolerance:
            return True, ""
        else:
            return False, f"Value {extracted_value} not within tolerance of {expected_value} (±{tolerance})"
    
    def _check_jsonschema(
        self,
        answer: str,
        schema: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Check if answer contains valid JSON matching schema.
        
        Args:
            answer: The answer text (should contain JSON).
            schema: JSON Schema to validate against.
        
        Returns:
            Tuple of (passed, error_message).
        """
        try:
            # Try to find JSON in the answer
            json_match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", answer)
            if not json_match:
                return False, "No JSON found in answer"
            
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            
            # Try to validate with jsonschema if available
            try:
                import jsonschema
                jsonschema.validate(parsed, schema)
                return True, ""
            except ImportError:
                # jsonschema not installed - just check parsing worked
                return True, ""
            except jsonschema.ValidationError as e:
                return False, f"JSON schema validation failed: {e.message}"
                
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"


class RubricScorer:
    """Scorer for qualitative rubric-based evaluation.
    
    Uses an LLM judge to evaluate answers on multiple dimensions:
    - reasoning_depth: Quality of reasoning process
    - accuracy_likelihood: Likelihood of factual accuracy
    - clarity: Organization and clarity of response
    - hallucination_risk: Risk of fabricated information (inverse)
    - completeness: How fully the query was addressed
    """
    
    DEFAULT_DIMENSIONS = [
        ("reasoning_depth", "How thoroughly does the response explore the problem?"),
        ("accuracy_likelihood", "How likely is the response to be factually accurate?"),
        ("clarity", "How clear and well-organized is the response?"),
        ("hallucination_risk", "Risk of containing made-up information (5=no risk)"),
        ("completeness", "Does the response fully address the query?"),
    ]
    
    def __init__(self, judge_runner=None):
        """Initialize the rubric scorer.
        
        Args:
            judge_runner: Optional runner to use as judge.
                         If None, rubric scoring will be skipped.
        """
        self.judge_runner = judge_runner
        self._dimensions = self.DEFAULT_DIMENSIONS
    
    async def score(
        self,
        prompt: str,
        answer: str,
        case_notes: str = "",
    ) -> Optional[RubricScore]:
        """Score an answer using rubric-based evaluation.
        
        Args:
            prompt: The original prompt.
            answer: The answer to evaluate.
            case_notes: Optional notes about what makes a good answer.
        
        Returns:
            RubricScore or None if judge is unavailable.
        """
        if self.judge_runner is None or not self.judge_runner.is_available():
            logger.debug("Rubric scoring skipped - no judge available")
            return None
        
        # Build judge prompt
        judge_prompt = self._build_judge_prompt(prompt, answer, case_notes)
        
        try:
            # Create a simple case for the judge
            from .runner_base import BenchmarkCase, RunConfig
            
            judge_case = BenchmarkCase(
                id="judge-evaluation",
                category="judge",
                prompt=judge_prompt,
            )
            
            # Run with deterministic settings
            judge_config = RunConfig(temperature=0.0, max_tokens=1024)
            result = await self.judge_runner.run_case(judge_case, judge_config)
            
            if result.status.value != "success":
                logger.warning(f"Judge failed: {result.error_message}")
                return None
            
            # Parse judge response
            return self._parse_judge_response(result.answer_text)
            
        except Exception as e:
            logger.warning(f"Rubric scoring failed: {e}")
            return None
    
    def _build_judge_prompt(
        self,
        prompt: str,
        answer: str,
        case_notes: str,
    ) -> str:
        """Build the prompt for the judge model."""
        dimensions_text = "\n".join(
            f"- {name}: {desc}"
            for name, desc in self._dimensions
        )
        
        return f"""You are evaluating an AI assistant's response. Rate each dimension from 1-5.

ORIGINAL QUESTION:
{prompt}

ASSISTANT'S ANSWER:
{answer}

{f"EVALUATION NOTES: {case_notes}" if case_notes else ""}

Rate the response on these dimensions (1=poor, 5=excellent):
{dimensions_text}

Respond with ONLY a JSON object in this exact format:
{{
    "reasoning_depth": <1-5>,
    "accuracy_likelihood": <1-5>,
    "clarity": <1-5>,
    "hallucination_risk": <1-5>,
    "completeness": <1-5>,
    "confidence": <0.0-1.0>
}}

Do NOT include any explanation, just the JSON."""
    
    def _parse_judge_response(self, response: str) -> Optional[RubricScore]:
        """Parse the judge's response into a RubricScore."""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                logger.warning("No JSON found in judge response")
                return None
            
            data = json.loads(json_match.group(0))
            
            dimensions = []
            total_score = 0
            
            for name, desc in self._dimensions:
                score = int(data.get(name, 3))
                score = max(1, min(5, score))  # Clamp to 1-5
                total_score += score
                
                dimensions.append(RubricDimension(
                    name=name,
                    score=score,
                    description=desc,
                ))
            
            average_score = total_score / len(self._dimensions) if self._dimensions else 0
            
            return RubricScore(
                dimensions=dimensions,
                average_score=average_score,
                normalized_score=average_score / 5.0,
                judge_model=self.judge_runner.model_id if self.judge_runner else "unknown",
                judge_confidence=float(data.get("confidence", 0.5)),
            )
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Failed to parse judge response: {e}")
            return None


class CompositeScorer:
    """Combines objective and rubric scores into a final composite score.
    
    The composite score is a weighted average of:
    - Objective score (deterministic checks)
    - Rubric score (qualitative evaluation)
    
    Weights are defined per benchmark case.
    """
    
    def __init__(
        self,
        objective_scorer: Optional[ObjectiveScorer] = None,
        rubric_scorer: Optional[RubricScorer] = None,
    ):
        """Initialize the composite scorer.
        
        Args:
            objective_scorer: Scorer for objective checks.
            rubric_scorer: Scorer for rubric evaluation.
        """
        self.objective_scorer = objective_scorer or ObjectiveScorer()
        self.rubric_scorer = rubric_scorer
    
    async def score(
        self,
        prompt_id: str,
        system_name: str,
        prompt: str,
        answer: str,
        expected: Dict[str, Any],
        requirements: Optional[Dict[str, Any]] = None,
        scoring_config: Optional[Dict[str, Any]] = None,
        case_notes: str = "",
    ) -> ScoringResult:
        """Generate a complete scoring result.
        
        Args:
            prompt_id: ID of the benchmark case.
            system_name: Name of the system being evaluated.
            prompt: The original prompt.
            answer: The answer to evaluate.
            expected: Expected values/patterns.
            requirements: Case requirements.
            scoring_config: Scoring weights and flags.
            case_notes: Notes for rubric evaluation.
        
        Returns:
            Complete ScoringResult.
        """
        requirements = requirements or {}
        scoring_config = scoring_config or {}
        
        objective_weight = scoring_config.get("objective_weight", 0.5)
        rubric_weight = scoring_config.get("rubric_weight", 0.5)
        is_critical = scoring_config.get("critical", False)
        
        # Normalize weights
        total_weight = objective_weight + rubric_weight
        if total_weight > 0:
            objective_weight /= total_weight
            rubric_weight /= total_weight
        
        # Objective scoring (always run)
        objective_score = self.objective_scorer.score(answer, expected, requirements)
        
        # Rubric scoring (if scorer available and has weight)
        rubric_score = None
        if rubric_weight > 0 and self.rubric_scorer:
            rubric_score = await self.rubric_scorer.score(prompt, answer, case_notes)
        
        # Calculate composite score
        composite = 0.0
        
        if objective_weight > 0:
            composite += objective_weight * objective_score.score
        
        if rubric_weight > 0 and rubric_score:
            composite += rubric_weight * rubric_score.normalized_score
        elif rubric_weight > 0:
            # No rubric score available - use only objective
            # Normalize to account for missing rubric
            if objective_weight > 0:
                composite = objective_score.score
        
        # Determine critical failure
        critical_failed = is_critical and not objective_score.passed
        
        return ScoringResult(
            prompt_id=prompt_id,
            system_name=system_name,
            objective_score=objective_score,
            rubric_score=rubric_score,
            composite_score=composite,
            objective_weight=objective_weight,
            rubric_weight=rubric_weight,
            is_critical=is_critical,
            critical_failed=critical_failed,
        )


def calculate_aggregate_scores(
    results: List[ScoringResult],
) -> Dict[str, Any]:
    """Calculate aggregate statistics across multiple scoring results.
    
    Args:
        results: List of ScoringResult objects.
    
    Returns:
        Dictionary with aggregate statistics.
    """
    if not results:
        return {"total": 0}
    
    # Group by system
    by_system: Dict[str, List[ScoringResult]] = {}
    for r in results:
        if r.system_name not in by_system:
            by_system[r.system_name] = []
        by_system[r.system_name].append(r)
    
    # Calculate per-system stats
    system_stats = {}
    for system_name, system_results in by_system.items():
        scores = [r.composite_score for r in system_results]
        objective_scores = [
            r.objective_score.score for r in system_results
            if r.objective_score
        ]
        
        critical_failures = [r for r in system_results if r.critical_failed]
        
        system_stats[system_name] = {
            "total_cases": len(system_results),
            "composite_mean": sum(scores) / len(scores) if scores else 0,
            "composite_min": min(scores) if scores else 0,
            "composite_max": max(scores) if scores else 0,
            "objective_mean": sum(objective_scores) / len(objective_scores) if objective_scores else 0,
            "passed_count": sum(1 for r in system_results if r.objective_score and r.objective_score.passed),
            "failed_count": sum(1 for r in system_results if r.objective_score and not r.objective_score.passed),
            "critical_failures": len(critical_failures),
            "critical_failure_ids": [r.prompt_id for r in critical_failures],
        }
    
    return {
        "total_cases": len(results),
        "systems": system_stats,
    }

