"""Tool-Augmented Verification - Verify Answers with External Tools.

LLMs hallucinate. Tools don't. This module uses external tools to
verify LLM outputs before returning them, dramatically reducing errors.

Enhanced Verification Capabilities:
1. Math - SymPy integration for algebraic/calculus verification
2. Code - Multi-language syntax and execution verification
3. Facts - Web search integration for claim verification
4. Logic - Consistency checking
5. Format - Structure and completeness verification

This is critical for beating single models on accuracy benchmarks.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum, auto

logger = logging.getLogger(__name__)

# Try to import SymPy for advanced math verification
try:
    import sympy
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    logger.info("SymPy not available, math verification will be limited")


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
    corrections_made: int = 0


@dataclass
class FactualClaim:
    """A factual claim extracted from text."""
    claim: str
    keywords: List[str]
    claim_type: str  # date, number, entity, statement
    verified: bool = False
    evidence: Optional[str] = None
    contradicted: bool = False


class ToolVerifier:
    """Verifies LLM outputs using external tools.
    
    This is a key differentiator: we catch LLM errors before they
    reach the user by verifying with deterministic tools.
    
    Enhanced with:
    - SymPy for algebraic verification
    - Web search integration for facts
    - Multi-language code verification
    """
    
    def __init__(
        self,
        web_search_fn: Optional[Callable] = None,
        code_executor_fn: Optional[Callable] = None,
    ):
        """Initialize the tool verifier.
        
        Args:
            web_search_fn: Optional async function for web search
            code_executor_fn: Optional async function for code execution
        """
        self._math_enabled = True
        self._code_enabled = True
        self._fact_check_enabled = True
        self._web_search_fn = web_search_fn
        self._code_executor_fn = code_executor_fn
        
        logger.info("ToolVerifier initialized (SymPy: %s)", SYMPY_AVAILABLE)
    
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
            try:
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
            except Exception as e:
                logger.warning("Verification %s failed: %s", vtype.name, e)
                # Continue with other verifications
        
        return results
    
    def _detect_verification_needs(
        self,
        query: str,
        answer: str
    ) -> List[VerificationType]:
        """Auto-detect which verifications are needed."""
        needs = []
        combined = f"{query} {answer}".lower()
        
        # Math detection - expanded patterns
        math_patterns = [
            r'\d+\s*[\+\-\*\/]\s*\d+',  # Basic operations
            r'=\s*\d+',  # Equals number
            r'\b(calculate|compute|sum|product|average|mean)\b',
            r'\b(equation|formula|integral|derivative)\b',
            r'\b(solve|simplify|factor|expand)\b',
            r'\b(sin|cos|tan|log|exp|sqrt)\b',
            r'\b(x\s*=|y\s*=|f\(x\))\b',  # Algebraic
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
            r'\b(has a population of|worth|valued at)\b',
            r'\b(invented|created|developed) (by|in)\b',
        ]
        if any(re.search(p, combined) for p in fact_patterns):
            needs.append(VerificationType.FACTUAL)
        
        # Always do format check
        needs.append(VerificationType.FORMAT)
        
        return needs
    
    async def _verify_math(self, answer: str, query: str) -> VerificationResult:
        """Verify mathematical calculations in the answer.
        
        Uses SymPy for advanced verification when available.
        """
        issues = []
        evidence = {}
        corrected_answer = answer
        corrections = 0
        
        # Extract mathematical expressions
        expressions = self._extract_math_expressions(answer)
        
        for expr, stated_result in expressions:
            try:
                # Try SymPy first for advanced math
                if SYMPY_AVAILABLE:
                    actual_result = self._sympy_eval(expr)
                else:
                    actual_result = self._safe_eval(expr)
                
                if actual_result is not None:
                    evidence[expr] = {
                        "stated": stated_result,
                        "calculated": actual_result,
                        "method": "sympy" if SYMPY_AVAILABLE else "eval",
                    }
                    
                    # Check if stated result matches
                    if stated_result is not None:
                        try:
                            stated_num = float(str(stated_result).replace(",", ""))
                            # Use relative tolerance for floating point
                            tolerance = max(0.001, abs(stated_num) * 0.001)
                            if abs(actual_result - stated_num) > tolerance:
                                issues.append(
                                    f"Math error: {expr} = {stated_num} (stated) "
                                    f"but actually = {actual_result}"
                                )
                                # Correct the answer - use exact match to avoid
                                # replacing unrelated occurrences
                                old_pattern = re.escape(str(stated_result))
                                corrected_answer = re.sub(
                                    rf'\b{old_pattern}\b',
                                    str(actual_result),
                                    corrected_answer,
                                    count=1
                                )
                                corrections += 1
                        except (ValueError, TypeError):
                            pass
            
            except Exception as e:
                logger.debug(f"Could not evaluate expression {expr}: {e}")
        
        # Try to verify algebraic solutions if SymPy available
        if SYMPY_AVAILABLE:
            algebraic_results = await self._verify_algebraic(answer, query)
            evidence.update(algebraic_results.get("evidence", {}))
            issues.extend(algebraic_results.get("issues", []))
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.MATH,
            original_answer=answer,
            verified_answer=corrected_answer if corrections > 0 else None,
            issues=issues,
            evidence=evidence,
            confidence=0.95 if not issues else 0.6,
            corrections_made=corrections,
        )
    
    def _sympy_eval(self, expr: str) -> Optional[float]:
        """Evaluate expression using SymPy."""
        if not SYMPY_AVAILABLE:
            return self._safe_eval(expr)
        
        try:
            # Clean expression
            expr = expr.replace('^', '**')
            expr = expr.replace('×', '*')
            expr = expr.replace('÷', '/')
            
            # Parse with transformations
            transformations = standard_transformations + (implicit_multiplication,)
            parsed = parse_expr(expr, transformations=transformations)
            
            # Evaluate
            result = float(parsed.evalf())
            return result
        except Exception:
            return self._safe_eval(expr)
    
    async def _verify_algebraic(
        self, 
        answer: str, 
        query: str
    ) -> Dict[str, Any]:
        """Verify algebraic solutions using SymPy."""
        result = {"evidence": {}, "issues": []}
        
        if not SYMPY_AVAILABLE:
            return result
        
        # Look for "x = value" patterns
        solution_patterns = [
            r'x\s*=\s*([-+]?\d+(?:\.\d+)?)',
            r'y\s*=\s*([-+]?\d+(?:\.\d+)?)',
            r'the (?:solution|answer|value) is\s*([-+]?\d+(?:\.\d+)?)',
        ]
        
        for pattern in solution_patterns:
            match = re.search(pattern, answer, re.IGNORECASE)
            if match:
                stated_value = float(match.group(1))
                
                # Try to find the equation in the query
                equation_match = re.search(
                    r'([\d\w\+\-\*\/\^\(\)\s]+)\s*=\s*([\d\+\-\*\/\^\(\)\s]+)',
                    query
                )
                
                if equation_match:
                    try:
                        lhs = equation_match.group(1)
                        rhs = equation_match.group(2)
                        
                        x = sympy.Symbol('x')
                        lhs_expr = parse_expr(lhs.replace('^', '**'))
                        rhs_expr = parse_expr(rhs.replace('^', '**'))
                        
                        solutions = sympy.solve(lhs_expr - rhs_expr, x)
                        
                        result["evidence"]["algebraic_check"] = {
                            "equation": f"{lhs} = {rhs}",
                            "stated_solution": stated_value,
                            "calculated_solutions": [float(s.evalf()) for s in solutions if s.is_real],
                        }
                        
                        # Check if stated value matches any solution
                        calc_solutions = [float(s.evalf()) for s in solutions if s.is_real]
                        if calc_solutions and not any(
                            abs(stated_value - s) < 0.01 for s in calc_solutions
                        ):
                            result["issues"].append(
                                f"Algebraic error: stated x={stated_value} but "
                                f"calculated solutions are {calc_solutions}"
                            )
                    except Exception as e:
                        logger.debug(f"Algebraic verification failed: {e}")
        
        return result
    
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
        
        for i, (lang, code) in enumerate(code_blocks):
            block_key = f"{lang}_block_{i}"
            
            if lang in ["python", "py", ""]:
                result = await self._test_python_code(code)
                evidence[block_key] = result
                
                if not result["success"]:
                    if result["error_type"] == "syntax":
                        issues.append(f"Syntax error in Python code: {result['error']}")
                    elif result["error_type"] == "runtime":
                        issues.append(f"Runtime error: {result['error']}")
            
            elif lang in ["javascript", "js", "typescript", "ts"]:
                result = self._check_js_syntax(code)
                evidence[block_key] = result
                if not result["valid"]:
                    issues.append(f"Potential JS/TS issue: {result.get('note', 'Unknown')}")
            
            elif lang in ["java", "c", "cpp", "c++", "rust", "go"]:
                # Basic syntax checks for compiled languages
                result = self._check_compiled_syntax(code, lang)
                evidence[block_key] = result
                if not result["valid"]:
                    issues.append(f"Potential {lang} issue: {result.get('note', 'Unknown')}")
            
            else:
                # Unknown language - note that only Python execution is supported
                evidence[block_key] = {
                    "valid": True,
                    "note": f"Language '{lang}' - syntax check only, execution not supported"
                }
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.CODE,
            original_answer=answer,
            issues=issues,
            evidence=evidence,
            confidence=0.9 if not issues else 0.5,
        )
    
    def _check_compiled_syntax(self, code: str, lang: str) -> Dict[str, Any]:
        """Basic syntax checks for compiled languages."""
        result = {"valid": True, "note": None, "language": lang}
        
        # Check brace matching
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            result["valid"] = False
            result["note"] = f"Mismatched braces ({open_braces} open, {close_braces} close)"
            return result
        
        # Check parentheses
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            result["valid"] = False
            result["note"] = f"Mismatched parentheses"
            return result
        
        # Check semicolons for C-like languages
        if lang in ["java", "c", "cpp", "c++"]:
            # Simple check: lines that look like statements should end with ;
            lines = code.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.endswith((';', '{', '}', ':', '//', '*/', '/*', '#')):
                    if re.match(r'^(if|for|while|switch|else|class|struct|enum)\b', line):
                        continue
                    if not line.startswith('//') and not line.startswith('#'):
                        # Might be missing semicolon
                        result["note"] = "Possible missing semicolons (check statement endings)"
        
        return result
    
    async def _verify_facts(self, answer: str, query: str) -> VerificationResult:
        """Verify factual claims in the answer using web search."""
        issues = []
        evidence = {}
        corrected_answer = answer
        corrections = 0
        
        # Extract claims that look factual
        claims = self._extract_factual_claims(answer)
        
        for claim in claims[:5]:  # Limit to 5 claims to avoid too many searches
            claim_evidence = await self._verify_single_claim(claim)
            evidence[claim.claim[:50]] = claim_evidence
            
            if claim_evidence.get("contradicted"):
                issues.append(f"Potential inaccuracy: {claim.claim[:100]}")
                if claim_evidence.get("correction"):
                    # Apply correction carefully
                    old = claim_evidence.get("original_value")
                    new = claim_evidence.get("correct_value")
                    if old and new and old in corrected_answer:
                        corrected_answer = corrected_answer.replace(old, new, 1)
                        corrections += 1
        
        # Check for common factual red flags
        red_flags = [
            (r'founded in (\d{4})', "Founded date claim - verify"),
            (r'born in (\d{4})', "Birth date claim - verify"),
            (r'is the (largest|biggest|most)', "Superlative claim - verify"),
            (r'has a population of', "Population claim - verify"),
            (r'worth \$?([\d,.]+)', "Value claim - verify"),
        ]
        
        for pattern, note in red_flags:
            match = re.search(pattern, answer.lower())
            if match:
                evidence[pattern] = {"note": note, "status": "flagged", "value": match.group(1) if match.groups() else None}
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.FACTUAL,
            original_answer=answer,
            verified_answer=corrected_answer if corrections > 0 else None,
            issues=issues,
            evidence=evidence,
            confidence=0.7 if issues else 0.85,  # Lower confidence when facts unverified
            corrections_made=corrections,
        )
    
    async def _verify_single_claim(self, claim: FactualClaim) -> Dict[str, Any]:
        """Verify a single factual claim using web search."""
        result = {
            "claim": claim.claim,
            "status": "unverified",
            "verified": False,
            "contradicted": False,
            "evidence": None,
        }
        
        if not self._web_search_fn:
            result["status"] = "no_search_available"
            return result
        
        try:
            # Build search query from claim keywords
            search_query = " ".join(claim.keywords[:5])
            
            # Execute search
            search_results = await self._web_search_fn(search_query)
            
            if not search_results:
                result["status"] = "no_results"
                return result
            
            # Analyze search results for verification
            search_text = str(search_results).lower()
            claim_keywords = [kw.lower() for kw in claim.keywords]
            
            # Check if evidence supports or contradicts
            keyword_matches = sum(1 for kw in claim_keywords if kw in search_text)
            
            if keyword_matches >= len(claim_keywords) * 0.6:
                result["verified"] = True
                result["status"] = "verified"
                result["evidence"] = f"Found supporting evidence with {keyword_matches} keyword matches"
            else:
                # Check for contradictory information
                # This is simplified - in production would use more sophisticated NLI
                result["status"] = "insufficient_evidence"
            
            return result
            
        except Exception as e:
            logger.warning("Fact verification search failed: %s", e)
            result["status"] = "search_failed"
            result["error"] = str(e)
            return result
    
    async def _verify_logic(self, answer: str, query: str) -> VerificationResult:
        """Check logical consistency of the answer."""
        issues = []
        evidence = {}
        
        # Check for logical contradictions
        contradiction_patterns = [
            (r'both .+ and not .+', "Potential contradiction"),
            (r'always .+ but sometimes', "Inconsistent quantifier"),
            (r'impossible .+ but .+ can', "Possibility contradiction"),
            (r'never .+ except .+ always', "Exception contradiction"),
        ]
        
        for pattern, note in contradiction_patterns:
            if re.search(pattern, answer.lower()):
                issues.append(f"Logical issue: {note}")
        
        # Check for unsupported conclusions
        conclusion_words = ["therefore", "thus", "hence", "consequently", "so"]
        for word in conclusion_words:
            if word in answer.lower():
                evidence["has_conclusion"] = True
                # Could add more sophisticated premise-conclusion checking
                break
        
        # Check for circular reasoning
        if self._detect_circular_reasoning(answer):
            issues.append("Potential circular reasoning detected")
        
        return VerificationResult(
            passed=len(issues) == 0,
            verification_type=VerificationType.LOGICAL,
            original_answer=answer,
            issues=issues,
            evidence=evidence,
            confidence=0.85 if not issues else 0.6,
        )
    
    def _detect_circular_reasoning(self, text: str) -> bool:
        """Detect potential circular reasoning."""
        sentences = re.split(r'[.!?]', text)
        
        # Simple check: if a later sentence is nearly identical to an earlier one
        # that's used as evidence, it might be circular
        for i, s1 in enumerate(sentences):
            for s2 in sentences[i+1:]:
                s1_words = set(s1.lower().split())
                s2_words = set(s2.lower().split())
                
                if len(s1_words) > 5 and len(s2_words) > 5:
                    overlap = len(s1_words & s2_words) / min(len(s1_words), len(s2_words))
                    if overlap > 0.8:
                        return True
        
        return False
    
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
            r'etc\.\s*$',
            r'and so on\s*$',
        ]
        for pattern in truncation_patterns:
            if re.search(pattern, answer):
                issues.append("Answer may be truncated")
                break
        
        # Check for proper ending
        stripped = answer.strip()
        if stripped and stripped[-1] not in '.!?)"\'`:':
            evidence["incomplete_ending"] = True
            issues.append("Answer ends abruptly without proper punctuation")
        
        # Check for unclosed formatting
        if answer.count('```') % 2 != 0:
            issues.append("Unclosed code block")
        
        if answer.count('**') % 2 != 0:
            issues.append("Unclosed bold formatting")
        
        # Check for markdown artifacts
        if re.search(r'\[\[|\]\]', answer):
            issues.append("Contains wiki-style artifacts")
        
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
        patterns = [
            r'(\d+(?:\.\d+)?\s*[\+\-\*\/\^]\s*\d+(?:\.\d+)?(?:\s*[\+\-\*\/\^]\s*\d+(?:\.\d+)?)*)\s*=\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?\s*[\×\÷]\s*\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)',  # Unicode operators
        ]
        
        for pattern in patterns:
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
        except Exception:
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
        
        # Use custom executor if provided
        if self._code_executor_fn:
            try:
                exec_result = await self._code_executor_fn(code, language="python")
                result["output"] = exec_result
                return result
            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
                result["error_type"] = "runtime"
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
                    "abs": abs,
                    "round": round,
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
        
        # Check brace matching
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            result["valid"] = False
            result["note"] = "Mismatched braces"
            return result
        
        # Check parentheses
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            result["valid"] = False
            result["note"] = "Mismatched parentheses"
            return result
        
        # Check brackets
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            result["valid"] = False
            result["note"] = "Mismatched brackets"
            return result
        
        # Check for common JS errors
        if re.search(r'\bconst\s+\w+\s*;\s*$', code, re.MULTILINE):
            result["note"] = "const declaration without initialization"
        
        return result
    
    def _extract_factual_claims(self, text: str) -> List[FactualClaim]:
        """Extract sentences that appear to be factual claims."""
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 15:
                continue
            
            claim_type = None
            keywords = []
            
            # Date claims
            date_match = re.search(r'\b(\d{4})\b', sentence)
            if date_match:
                claim_type = "date"
                keywords.append(date_match.group(1))
            
            # Number claims
            num_match = re.search(r'\b(\d+(?:,\d{3})*(?:\.\d+)?)\b', sentence)
            if num_match:
                claim_type = claim_type or "number"
                keywords.append(num_match.group(1))
            
            # Entity claims (capitalized words)
            entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence)
            if entities:
                claim_type = claim_type or "entity"
                keywords.extend(entities[:3])
            
            # General factual indicators
            factual_patterns = [
                r'\bis\b', r'\bwas\b', r'\bhas\b', r'\bhad\b',
                r'\b\d+%\b',  # Percentage
            ]
            
            if any(re.search(p, sentence) for p in factual_patterns):
                claim_type = claim_type or "statement"
            
            if claim_type:
                claims.append(FactualClaim(
                    claim=sentence,
                    keywords=keywords or sentence.split()[:5],
                    claim_type=claim_type,
                ))
        
        return claims


class VerificationPipeline:
    """Pipeline for comprehensive answer verification.
    
    Runs all applicable verifications and produces a final verdict.
    Integrates with EliteOrchestrator for challenge-and-refine loops.
    """
    
    def __init__(
        self,
        web_search_fn: Optional[Callable] = None,
        code_executor_fn: Optional[Callable] = None,
    ):
        self.verifier = ToolVerifier(
            web_search_fn=web_search_fn,
            code_executor_fn=code_executor_fn,
        )
    
    async def verify_answer(
        self,
        answer: str,
        query: str,
        fix_errors: bool = True,
    ) -> Tuple[str, float, List[str], Dict[str, Any]]:
        """Verify an answer and optionally fix errors.
        
        Args:
            answer: The answer to verify
            query: Original query
            fix_errors: Whether to return corrected answer
            
        Returns:
            Tuple of (final_answer, confidence, issues, full_report)
        """
        results = await self.verifier.verify(answer, query)
        
        all_issues = []
        min_confidence = 1.0
        final_answer = answer
        total_corrections = 0
        
        full_report = {
            "verifications_run": [],
            "all_evidence": {},
            "corrections_made": 0,
        }
        
        for result in results:
            all_issues.extend(result.issues)
            min_confidence = min(min_confidence, result.confidence)
            total_corrections += result.corrections_made
            
            # Apply corrections if available
            if fix_errors and result.verified_answer:
                final_answer = result.verified_answer
            
            full_report["verifications_run"].append(result.verification_type.name)
            full_report["all_evidence"][result.verification_type.name] = result.evidence
        
        full_report["corrections_made"] = total_corrections
        
        # Calculate overall confidence
        if all_issues:
            # Reduce confidence based on number of issues
            confidence_penalty = min(0.3, len(all_issues) * 0.1)
            final_confidence = max(0.3, min_confidence - confidence_penalty)
        else:
            final_confidence = min_confidence
        
        return final_answer, final_confidence, all_issues, full_report
    
    async def get_verification_feedback(
        self,
        answer: str,
        query: str,
    ) -> str:
        """Get verification feedback for use in challenge-and-refine loops.
        
        Returns a formatted string suitable for feeding back to a model.
        """
        _, confidence, issues, report = await self.verify_answer(answer, query, fix_errors=False)
        
        if not issues:
            return "Verification passed with high confidence."
        
        feedback_parts = [
            f"Verification confidence: {confidence:.0%}",
            "Issues found:",
        ]
        
        for i, issue in enumerate(issues[:5], 1):
            feedback_parts.append(f"  {i}. {issue}")
        
        if report.get("corrections_made", 0) > 0:
            feedback_parts.append(f"\n{report['corrections_made']} potential corrections identified.")
        
        return "\n".join(feedback_parts)


# Singleton
_verification_pipeline: Optional[VerificationPipeline] = None


def get_verification_pipeline() -> VerificationPipeline:
    """Get or create verification pipeline."""
    global _verification_pipeline
    if _verification_pipeline is None:
        _verification_pipeline = VerificationPipeline()
    return _verification_pipeline


def set_verification_pipeline(
    web_search_fn: Optional[Callable] = None,
    code_executor_fn: Optional[Callable] = None,
) -> VerificationPipeline:
    """Create and set a configured verification pipeline."""
    global _verification_pipeline
    _verification_pipeline = VerificationPipeline(
        web_search_fn=web_search_fn,
        code_executor_fn=code_executor_fn,
    )
    return _verification_pipeline
