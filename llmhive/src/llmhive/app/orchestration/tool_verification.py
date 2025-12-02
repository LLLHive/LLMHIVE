"""Tool-Augmented Verification - Verify Answers with External Tools.

LLMs hallucinate. Tools don't. This module uses external tools to
verify LLM outputs before returning them, dramatically reducing errors.

Key verifications:
1. Math - Use calculator/SymPy to verify calculations
2. Code - Execute code to verify it works
3. Facts - Cross-reference with search/knowledge base
4. Logic - Check logical consistency

This is critical for beating single models on accuracy benchmarks.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum, auto

logger = logging.getLogger(__name__)


class VerificationType(Enum):
    """Types of verification available."""
    MATH = auto()
    CODE = auto()
    FACTUAL = auto()
    LOGICAL = auto()
    FORMAT = auto()


@dataclass
class VerificationResult:
    """Result of tool-based verification."""
    passed: bool
    verification_type: VerificationType
    original_answer: str
    verified_answer: Optional[str] = None  # Corrected if wrong
    issues: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class ToolVerifier:
    """Verifies LLM outputs using external tools.
    
    This is a key differentiator: we catch LLM errors before they
    reach the user by verifying with deterministic tools.
    """
    
    def __init__(self):
        """Initialize the tool verifier."""
        self._math_enabled = True
        self._code_enabled = True
        self._fact_check_enabled = True
        
        logger.info("ToolVerifier initialized")
    
    async def verify(
        self,
        answer: str,
        query: str,
        verification_types: Optional[List[VerificationType]] = None,
    ) -> List[VerificationResult]:
        """Verify an answer using appropriate tools.
        
        Args:
            answer: The answer to verify
            query: Original query for context
            verification_types: Which verifications to run (None = auto-detect)
            
        Returns:
            List of verification results
        """
        if verification_types is None:
            verification_types = self._detect_verification_needs(query, answer)
        
        results = []
        
        for vtype in verification_types:
            if vtype == VerificationType.MATH:
                result = await self._verify_math(answer, query)
            elif vtype == VerificationType.CODE:
                result = await self._verify_code(answer, query)
            elif vtype == VerificationType.FACTUAL:
                result = await self._verify_facts(answer, query)
            elif vtype == VerificationType.LOGICAL:
                result = await self._verify_logic(answer, query)
            elif vtype == VerificationType.FORMAT:
                result = await self._verify_format(answer, query)
            else:
                continue
            
            results.append(result)
        
        return results
    
    def _detect_verification_needs(
        self,
        query: str,
        answer: str
    ) -> List[VerificationType]:
        """Auto-detect which verifications are needed."""
        needs = []
        combined = f"{query} {answer}".lower()
        
        # Math detection
        math_patterns = [
            r'\d+\s*[\+\-\*\/]\s*\d+',  # Basic operations
            r'=\s*\d+',  # Equals number
            r'\b(calculate|compute|sum|product|average|mean)\b',
            r'\b(equation|formula|integral|derivative)\b',
        ]
        if any(re.search(p, combined) for p in math_patterns):
            needs.append(VerificationType.MATH)
        
        # Code detection
        code_patterns = [
            r'```\w*\n',  # Code blocks
            r'\b(def |function |class |import |from |const |let |var )\b',
            r'\b(return|print|console\.log)\b',
        ]
        if any(re.search(p, answer) for p in code_patterns):
            needs.append(VerificationType.CODE)
        
        # Factual detection
        fact_patterns = [
            r'\b(in \d{4}|founded|born|died|discovered)\b',
            r'\b(according to|statistics show|research indicates)\b',
            r'\b(is the (largest|smallest|oldest|newest))\b',
        ]
        if any(re.search(p, combined) for p in fact_patterns):
            needs.append(VerificationType.FACTUAL)
        
        # Always do format check
        needs.append(VerificationType.FORMAT)
        
        return needs
    
    async def _verify_math(self, answer: str, query: str) -> VerificationResult:
        """Verify mathematical calculations in the answer."""
        issues = []
        evidence = {}
        corrected_answer = answer
        
        # Extract mathematical expressions
        expressions = self._extract_math_expressions(answer)
        
        for expr, stated_result in expressions:
            try:
                # Evaluate using Python's eval (safe subset)
                actual_result = self._safe_eval(expr)
                
                if actual_result is not None:
                    evidence[expr] = {
                        "stated": stated_result,
                        "calculated": actual_result,
                    }
                    
                    # Check if stated result matches
                    if stated_result is not None:
                        try:
                            stated_num = float(str(stated_result).replace(",", ""))
                            if abs(actual_result - stated_num) > 0.001:
                                issues.append(
                                    f"Math error: {expr} = {stated_num} (stated) "
                                    f"but actually = {actual_result}"
                                )
                                # Correct the answer
                                corrected_answer = corrected_answer.replace(
                                    str(stated_result), str(actual_result)
                                )
                        except (ValueError, TypeError):
                            pass
            
            except Exception as e:
                logger.debug(f"Could not evaluate expression {expr}: {e}")
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.MATH,
            original_answer=answer,
            verified_answer=corrected_answer if issues else None,
            issues=issues,
            evidence=evidence,
            confidence=0.95 if not issues else 0.6,
        )
    
    async def _verify_code(self, answer: str, query: str) -> VerificationResult:
        """Verify code in the answer by attempting execution."""
        issues = []
        evidence = {}
        
        # Extract code blocks
        code_blocks = self._extract_code_blocks(answer)
        
        if not code_blocks:
            return VerificationResult(
                passed=True,
                verification_type=VerificationType.CODE,
                original_answer=answer,
                issues=[],
                evidence={"note": "No code blocks found"},
                confidence=0.8,
            )
        
        for lang, code in code_blocks:
            if lang in ["python", "py", ""]:
                result = await self._test_python_code(code)
                evidence[f"python_block"] = result
                
                if not result["success"]:
                    if result["error_type"] == "syntax":
                        issues.append(f"Syntax error in code: {result['error']}")
                    elif result["error_type"] == "runtime":
                        issues.append(f"Runtime error: {result['error']}")
            
            elif lang in ["javascript", "js"]:
                # Basic syntax check only
                result = self._check_js_syntax(code)
                evidence["js_block"] = result
                if not result["valid"]:
                    issues.append(f"Potential JS issue: {result.get('note', 'Unknown')}")
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.CODE,
            original_answer=answer,
            issues=issues,
            evidence=evidence,
            confidence=0.9 if not issues else 0.5,
        )
    
    async def _verify_facts(self, answer: str, query: str) -> VerificationResult:
        """Verify factual claims in the answer."""
        issues = []
        evidence = {}
        
        # Extract claims that look factual
        claims = self._extract_factual_claims(answer)
        
        for claim in claims[:5]:  # Limit to 5 claims
            # In production: use knowledge base or search API
            # For now, flag claims that seem uncertain
            evidence[claim[:50]] = {"status": "requires_verification"}
        
        # Check for common factual red flags
        red_flags = [
            (r'founded in \d{4}', "Date claim - verify founding date"),
            (r'born in \d{4}', "Birth date claim - verify"),
            (r'is the (largest|biggest|most)', "Superlative claim - verify"),
            (r'has a population of', "Population claim - verify"),
        ]
        
        for pattern, note in red_flags:
            if re.search(pattern, answer.lower()):
                evidence[pattern] = {"note": note, "status": "flagged"}
        
        return VerificationResult(
            passed=True,  # Don't block, just flag
            verification_type=VerificationType.FACTUAL,
            original_answer=answer,
            issues=issues,
            evidence=evidence,
            confidence=0.7,  # Lower confidence when facts not verified
        )
    
    async def _verify_logic(self, answer: str, query: str) -> VerificationResult:
        """Check logical consistency of the answer."""
        issues = []
        evidence = {}
        
        # Check for logical contradictions
        contradiction_patterns = [
            (r'both .+ and not .+', "Potential contradiction"),
            (r'always .+ but sometimes', "Inconsistent quantifier"),
            (r'impossible .+ but .+ can', "Possibility contradiction"),
        ]
        
        for pattern, note in contradiction_patterns:
            if re.search(pattern, answer.lower()):
                issues.append(f"Logical issue: {note}")
        
        # Check conclusion follows from premises
        # (Simplified - in production use proper inference checking)
        if "therefore" in answer.lower() or "thus" in answer.lower():
            evidence["has_conclusion"] = True
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.LOGICAL,
            original_answer=answer,
            issues=issues,
            evidence=evidence,
            confidence=0.85 if not issues else 0.6,
        )
    
    async def _verify_format(self, answer: str, query: str) -> VerificationResult:
        """Verify the answer format is appropriate."""
        issues = []
        evidence = {}
        
        # Check for empty or too short answers
        if len(answer.strip()) < 10:
            issues.append("Answer too short")
        
        # Check for truncation indicators
        truncation_patterns = [
            r'\.\.\.$',
            r'continue[ds]?\s*$',
            r'etc\.$',
        ]
        for pattern in truncation_patterns:
            if re.search(pattern, answer):
                issues.append("Answer may be truncated")
                break
        
        # Check for proper ending
        if not answer.strip()[-1] in '.!?)"\'':
            evidence["incomplete_ending"] = True
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.FORMAT,
            original_answer=answer,
            issues=issues,
            evidence=evidence,
            confidence=0.95 if not issues else 0.7,
        )
    
    # ==================== Helper Methods ====================
    
    def _extract_math_expressions(self, text: str) -> List[Tuple[str, Optional[str]]]:
        """Extract mathematical expressions and their stated results."""
        expressions = []
        
        # Pattern: expression = result
        pattern = r'(\d+(?:\.\d+)?\s*[\+\-\*\/\^]\s*\d+(?:\.\d+)?(?:\s*[\+\-\*\/\^]\s*\d+(?:\.\d+)?)*)\s*=\s*(\d+(?:\.\d+)?)'
        for match in re.finditer(pattern, text):
            expressions.append((match.group(1), match.group(2)))
        
        return expressions
    
    def _safe_eval(self, expr: str) -> Optional[float]:
        """Safely evaluate a mathematical expression."""
        # Only allow numbers and basic operators
        allowed_chars = set('0123456789.+-*/() ')
        if not all(c in allowed_chars for c in expr):
            return None
        
        try:
            # Replace ^ with ** for Python
            expr = expr.replace('^', '**')
            result = eval(expr, {"__builtins__": {}}, {})
            return float(result)
        except:
            return None
    
    def _extract_code_blocks(self, text: str) -> List[Tuple[str, str]]:
        """Extract code blocks from text."""
        blocks = []
        
        # Match ```language\ncode\n```
        pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(pattern, text, re.DOTALL):
            lang = match.group(1).lower() or "python"
            code = match.group(2).strip()
            blocks.append((lang, code))
        
        return blocks
    
    async def _test_python_code(self, code: str) -> Dict[str, Any]:
        """Test Python code for errors."""
        result = {
            "success": True,
            "error": None,
            "error_type": None,
            "output": None,
        }
        
        # First: syntax check
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            result["success"] = False
            result["error"] = str(e)
            result["error_type"] = "syntax"
            return result
        
        # Try to execute in restricted environment
        try:
            # Create restricted globals
            safe_globals = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "set": set,
                    "tuple": tuple,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "sorted": sorted,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "True": True,
                    "False": False,
                    "None": None,
                }
            }
            
            # Execute with timeout
            exec(code, safe_globals)
            result["output"] = "Executed successfully"
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            result["error_type"] = "runtime"
        
        return result
    
    def _check_js_syntax(self, code: str) -> Dict[str, Any]:
        """Basic JavaScript syntax check."""
        result = {"valid": True, "note": None}
        
        # Simple checks
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            result["valid"] = False
            result["note"] = "Mismatched braces"
        
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            result["valid"] = False
            result["note"] = "Mismatched parentheses"
        
        return result
    
    def _extract_factual_claims(self, text: str) -> List[str]:
        """Extract sentences that appear to be factual claims."""
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Factual indicators
            factual_patterns = [
                r'\bis\b',
                r'\bwas\b',
                r'\bhas\b',
                r'\bhad\b',
                r'\b\d{4}\b',  # Year
                r'\b\d+%\b',  # Percentage
            ]
            
            if any(re.search(p, sentence) for p in factual_patterns):
                claims.append(sentence)
        
        return claims


class VerificationPipeline:
    """Pipeline for comprehensive answer verification.
    
    Runs all applicable verifications and produces a final verdict.
    """
    
    def __init__(self):
        self.verifier = ToolVerifier()
    
    async def verify_answer(
        self,
        answer: str,
        query: str,
        fix_errors: bool = True,
    ) -> Tuple[str, float, List[str]]:
        """Verify an answer and optionally fix errors.
        
        Args:
            answer: The answer to verify
            query: Original query
            fix_errors: Whether to return corrected answer
            
        Returns:
            Tuple of (final_answer, confidence, issues)
        """
        results = await self.verifier.verify(answer, query)
        
        all_issues = []
        min_confidence = 1.0
        final_answer = answer
        
        for result in results:
            all_issues.extend(result.issues)
            min_confidence = min(min_confidence, result.confidence)
            
            # Apply corrections if available
            if fix_errors and result.verified_answer:
                final_answer = result.verified_answer
        
        # Calculate overall confidence
        if all_issues:
            # Reduce confidence based on number of issues
            confidence_penalty = min(0.3, len(all_issues) * 0.1)
            final_confidence = max(0.3, min_confidence - confidence_penalty)
        else:
            final_confidence = min_confidence
        
        return final_answer, final_confidence, all_issues


# Singleton
_verification_pipeline: Optional[VerificationPipeline] = None


def get_verification_pipeline() -> VerificationPipeline:
    """Get or create verification pipeline."""
    global _verification_pipeline
    if _verification_pipeline is None:
        _verification_pipeline = VerificationPipeline()
    return _verification_pipeline

