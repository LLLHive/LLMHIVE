"""PromptOps Layer - Always-on preprocessing for LLMHive Orchestrator.

This module implements the patent-specified PromptOps preprocessing layer:
1. Normalize and Analyze the Query
2. Apply Linting and Safety Checks
3. Segment the Task (HRM-Aware)
4. Micro-Optimize Prompt Variants (if needed)
5. Finalize the Prompt Specification

The PromptOps layer ensures every query is well-formed before heavy orchestration.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# Enums and Types
# ==============================================================================

class TaskType(str, Enum):
    """Types of tasks that can be identified from queries."""
    CODE_GENERATION = "code_generation"
    MATH_PROBLEM = "math_problem"
    FACTUAL_QUESTION = "factual_question"
    RESEARCH_ANALYSIS = "research_analysis"
    CREATIVE_WRITING = "creative_writing"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    PLANNING = "planning"
    DEBUGGING = "debugging"
    SUMMARIZATION = "summarization"
    GENERAL = "general"


class QueryComplexity(str, Enum):
    """Complexity levels for queries."""
    SIMPLE = "simple"          # Direct answer, minimal reasoning
    MODERATE = "moderate"      # Some reasoning, single model sufficient
    COMPLEX = "complex"        # Multi-step reasoning, may need tools
    RESEARCH = "research"      # Extensive research, multiple sources


class SegmentType(str, Enum):
    """Segment types for HRM-aware task decomposition."""
    PLANNER = "planner"        # High-level strategy
    SOLVER = "solver"          # Specific sub-task execution
    VERIFIER = "verifier"      # Validation and fact-checking
    REFINER = "refiner"        # Final polishing


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class QueryAnalysis:
    """Result of analyzing a query."""
    original_query: str
    task_type: TaskType
    complexity: QueryComplexity
    domain: str
    constraints: List[str]
    success_criteria: List[str]
    output_format: Optional[str]
    ambiguities: List[str]
    missing_info: List[str]
    key_entities: List[str]
    requires_tools: bool
    tool_hints: List[str]


@dataclass(slots=True)
class TaskSegment:
    """A segment of the decomposed task."""
    segment_type: SegmentType
    description: str
    required_capabilities: Set[str]
    input_requirements: List[str]
    output_expectations: List[str]
    acceptance_criteria: List[str]
    candidate_models: List[str]
    parallelizable: bool = False
    priority: int = 1


@dataclass(slots=True)
class PromptSpecification:
    """Final optimized prompt specification."""
    original_query: str
    refined_query: str
    analysis: QueryAnalysis
    segments: List[TaskSegment]
    safety_flags: List[str]
    style_guidelines: List[str]
    context_additions: List[str]
    confidence: float
    preprocessing_notes: List[str]


@dataclass(slots=True)
class LintResult:
    """Result of linting a query."""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    safety_flags: List[str]
    modified_query: Optional[str]


# ==============================================================================
# PromptOps Layer Implementation
# ==============================================================================

class PromptOps:
    """Always-on preprocessing layer for query optimization.
    
    Implements the full PromptOps pipeline:
    1. Query normalization and analysis
    2. Linting and safety checks
    3. HRM-aware task segmentation
    4. Prompt variant optimization
    5. Specification finalization
    """
    
    # Keywords for task type detection
    TASK_KEYWORDS = {
        TaskType.CODE_GENERATION: [
            "code", "implement", "function", "class", "write a program",
            "create a script", "develop", "build"
        ],
        TaskType.MATH_PROBLEM: [
            "calculate", "solve", "compute", "equation", "formula",
            "mathematical", "algebra", "geometry", "statistics"
        ],
        TaskType.DEBUGGING: [
            "debug", "fix", "error", "bug", "issue", "not working",
            "problem with", "fails", "exception"
        ],
        TaskType.RESEARCH_ANALYSIS: [
            "research", "analyze", "comprehensive", "detailed analysis",
            "in-depth", "evaluate", "compare and contrast", "investigate"
        ],
        TaskType.CREATIVE_WRITING: [
            "write a story", "creative", "poem", "essay", "narrative",
            "imaginative", "fiction"
        ],
        TaskType.EXPLANATION: [
            "explain", "what is", "how does", "why does", "describe",
            "define", "clarify"
        ],
        TaskType.COMPARISON: [
            "compare", "contrast", "difference between", "versus",
            "pros and cons", "advantages and disadvantages"
        ],
        TaskType.PLANNING: [
            "plan", "strategy", "roadmap", "schedule", "organize",
            "outline", "steps to"
        ],
        TaskType.SUMMARIZATION: [
            "summarize", "summary", "brief overview", "key points",
            "tldr", "condense"
        ],
    }
    
    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "simple": ["quick", "simple", "just", "only", "brief", "short"],
        "complex": [
            "comprehensive", "detailed", "in-depth", "thorough",
            "extensive", "complete", "all aspects"
        ],
        "research": [
            "research", "investigate", "multiple sources", "evidence-based",
            "academic", "scholarly"
        ]
    }
    
    # Ambiguity markers
    AMBIGUOUS_TERMS = [
        "it", "this", "that", "the thing", "stuff", "things",
        "best", "good", "better", "improve", "optimize", "today",
        "recent", "new", "old", "some", "many", "few"
    ]
    
    # Safety keywords
    SAFETY_KEYWORDS = [
        "hack", "exploit", "bypass", "illegal", "weapon",
        "harmful", "dangerous", "sensitive"
    ]
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        enable_variant_optimization: bool = True,
        enable_safety_checks: bool = True,
        default_domain: str = "general",
    ) -> None:
        """
        Initialize PromptOps layer.
        
        Args:
            providers: LLM providers for advanced optimization
            enable_variant_optimization: Whether to generate prompt variants
            enable_safety_checks: Whether to run safety filters
            default_domain: Default domain when not detected
        """
        self.providers = providers or {}
        self.enable_variants = enable_variant_optimization
        self.enable_safety = enable_safety_checks
        self.default_domain = default_domain
    
    async def process(
        self,
        query: str,
        *,
        context: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        domain_hint: Optional[str] = None,
    ) -> PromptSpecification:
        """
        Run the complete PromptOps pipeline.
        
        Args:
            query: Raw user query
            context: Optional conversation context
            user_preferences: User-specified preferences
            domain_hint: Hint for domain detection
            
        Returns:
            PromptSpecification with optimized prompt
        """
        preprocessing_notes: List[str] = []
        
        # Step 1: Normalize and Analyze
        preprocessing_notes.append("Step 1: Query analysis")
        analysis = self._analyze_query(query, domain_hint)
        
        # Step 2: Lint and Safety Check
        preprocessing_notes.append("Step 2: Linting and safety checks")
        lint_result = self._lint_query(query, analysis)
        
        refined_query = lint_result.modified_query or query
        if lint_result.modified_query:
            preprocessing_notes.append(f"Query refined: {len(lint_result.issues)} issues fixed")
        
        # Step 3: Segment Task (HRM-Aware)
        preprocessing_notes.append("Step 3: HRM-aware task segmentation")
        segments = self._segment_task(refined_query, analysis)
        
        # Step 4: Context Additions
        context_additions = self._generate_context_additions(
            analysis, context, user_preferences
        )
        
        # Step 5: Style Guidelines
        style_guidelines = self._determine_style_guidelines(
            analysis, user_preferences
        )
        
        # Step 6: Finalize Specification
        preprocessing_notes.append("Step 5: Specification finalized")
        
        # Calculate confidence
        confidence = self._calculate_confidence(analysis, lint_result)
        
        return PromptSpecification(
            original_query=query,
            refined_query=refined_query,
            analysis=analysis,
            segments=segments,
            safety_flags=lint_result.safety_flags,
            style_guidelines=style_guidelines,
            context_additions=context_additions,
            confidence=confidence,
            preprocessing_notes=preprocessing_notes,
        )
    
    def _analyze_query(
        self,
        query: str,
        domain_hint: Optional[str] = None,
    ) -> QueryAnalysis:
        """Analyze the query to extract task type, complexity, etc."""
        query_lower = query.lower()
        
        # Detect task type
        task_type = self._detect_task_type(query_lower)
        
        # Detect complexity
        complexity = self._detect_complexity(query_lower)
        
        # Detect domain
        domain = domain_hint or self._detect_domain(query_lower)
        
        # Extract constraints
        constraints = self._extract_constraints(query)
        
        # Extract success criteria
        success_criteria = self._extract_success_criteria(query, task_type)
        
        # Detect output format
        output_format = self._detect_output_format(query_lower)
        
        # Detect ambiguities
        ambiguities = self._detect_ambiguities(query_lower)
        
        # Detect missing information
        missing_info = self._detect_missing_info(query, task_type)
        
        # Extract key entities
        key_entities = self._extract_key_entities(query)
        
        # Detect tool requirements
        requires_tools, tool_hints = self._detect_tool_requirements(query_lower, task_type)
        
        return QueryAnalysis(
            original_query=query,
            task_type=task_type,
            complexity=complexity,
            domain=domain,
            constraints=constraints,
            success_criteria=success_criteria,
            output_format=output_format,
            ambiguities=ambiguities,
            missing_info=missing_info,
            key_entities=key_entities,
            requires_tools=requires_tools,
            tool_hints=tool_hints,
        )
    
    def _detect_task_type(self, query_lower: str) -> TaskType:
        """Detect the type of task from query."""
        best_match = TaskType.GENERAL
        best_score = 0
        
        for task_type, keywords in self.TASK_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > best_score:
                best_score = score
                best_match = task_type
        
        return best_match
    
    def _detect_complexity(self, query_lower: str) -> QueryComplexity:
        """Detect query complexity."""
        # Check for research indicators
        research_score = sum(
            1 for term in self.COMPLEXITY_INDICATORS["research"]
            if term in query_lower
        )
        if research_score >= 2:
            return QueryComplexity.RESEARCH
        
        # Check for complex indicators
        complex_score = sum(
            1 for term in self.COMPLEXITY_INDICATORS["complex"]
            if term in query_lower
        )
        if complex_score >= 2:
            return QueryComplexity.COMPLEX
        
        # Check for simple indicators
        simple_score = sum(
            1 for term in self.COMPLEXITY_INDICATORS["simple"]
            if term in query_lower
        )
        if simple_score >= 2 or len(query_lower.split()) < 10:
            return QueryComplexity.SIMPLE
        
        return QueryComplexity.MODERATE
    
    def _detect_domain(self, query_lower: str) -> str:
        """Detect the domain of the query."""
        domain_keywords = {
            "coding": ["code", "program", "function", "api", "software", "debug"],
            "medical": ["health", "medical", "disease", "symptom", "treatment", "doctor"],
            "legal": ["law", "legal", "contract", "court", "rights", "attorney"],
            "finance": ["money", "investment", "stock", "financial", "budget", "tax"],
            "marketing": ["marketing", "brand", "advertising", "campaign", "customer"],
            "research": ["research", "study", "analysis", "academic", "paper"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in query_lower for kw in keywords):
                return domain
        
        return self.default_domain
    
    def _extract_constraints(self, query: str) -> List[str]:
        """Extract explicit constraints from query."""
        constraints = []
        
        # Length constraints
        length_patterns = [
            (r"(\d+)\s*words?", "Maximum {} words"),
            (r"(\d+)\s*sentences?", "Maximum {} sentences"),
            (r"(\d+)\s*paragraphs?", "Maximum {} paragraphs"),
            (r"brief|short|concise", "Keep response concise"),
            (r"detailed|comprehensive|thorough", "Provide detailed response"),
        ]
        
        for pattern, template in length_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if match.groups():
                    constraints.append(template.format(match.group(1)))
                else:
                    constraints.append(template)
        
        # Format constraints
        if "bullet" in query.lower() or "list" in query.lower():
            constraints.append("Use bullet point format")
        if "step by step" in query.lower():
            constraints.append("Provide step-by-step explanation")
        if "example" in query.lower():
            constraints.append("Include examples")
        
        return constraints
    
    def _extract_success_criteria(
        self,
        query: str,
        task_type: TaskType,
    ) -> List[str]:
        """Extract success criteria based on task type."""
        criteria = []
        
        # Task-specific criteria
        if task_type == TaskType.CODE_GENERATION:
            criteria.extend([
                "Code should be functional and runnable",
                "Include necessary imports and dependencies",
                "Follow coding best practices",
            ])
        elif task_type == TaskType.MATH_PROBLEM:
            criteria.extend([
                "Show calculation steps",
                "Verify the final answer",
                "Use correct mathematical notation",
            ])
        elif task_type == TaskType.FACTUAL_QUESTION:
            criteria.extend([
                "Provide accurate, verifiable information",
                "Cite sources when possible",
                "Acknowledge uncertainty if present",
            ])
        elif task_type == TaskType.RESEARCH_ANALYSIS:
            criteria.extend([
                "Cover multiple perspectives",
                "Support claims with evidence",
                "Provide balanced analysis",
            ])
        else:
            criteria.extend([
                "Address all parts of the question",
                "Provide clear and organized response",
            ])
        
        return criteria
    
    def _detect_output_format(self, query_lower: str) -> Optional[str]:
        """Detect expected output format."""
        format_indicators = {
            "json": ["json", "json format", "in json"],
            "markdown": ["markdown", "md format"],
            "code": ["code", "script", "function", "program"],
            "list": ["list", "bullet", "numbered"],
            "table": ["table", "tabular"],
            "essay": ["essay", "paragraph form"],
        }
        
        for fmt, indicators in format_indicators.items():
            if any(ind in query_lower for ind in indicators):
                return fmt
        
        return None
    
    def _detect_ambiguities(self, query_lower: str) -> List[str]:
        """Detect potentially ambiguous terms."""
        ambiguities = []
        
        for term in self.AMBIGUOUS_TERMS:
            if term in query_lower.split():
                ambiguities.append(f"Term '{term}' may be ambiguous")
        
        # Check for unspecified references
        if re.search(r"\bit\b|\bthis\b|\bthat\b", query_lower):
            ambiguities.append("Contains unspecified pronoun references")
        
        # Check for vague comparatives
        if re.search(r"\bbetter\b|\bworse\b|\bmore\b|\bless\b", query_lower):
            if not re.search(r"\bthan\b", query_lower):
                ambiguities.append("Contains comparative without reference point")
        
        return ambiguities
    
    def _detect_missing_info(
        self,
        query: str,
        task_type: TaskType,
    ) -> List[str]:
        """Detect potentially missing information."""
        missing = []
        
        if task_type == TaskType.CODE_GENERATION:
            if not any(lang in query.lower() for lang in ["python", "javascript", "java", "c++", "rust", "go"]):
                missing.append("Programming language not specified")
        
        if task_type == TaskType.COMPARISON:
            # Check if comparison subjects are clear
            if query.lower().count(" and ") == 0 and " vs " not in query.lower():
                missing.append("Comparison subjects may not be clear")
        
        return missing
    
    def _extract_key_entities(self, query: str) -> List[str]:
        """Extract key entities from query."""
        entities = []
        
        # Extract capitalized terms (potential proper nouns)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(proper_nouns)
        
        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)
        
        # Extract technical terms (camelCase, snake_case)
        technical = re.findall(r'\b[a-z]+(?:[A-Z][a-z]+)+\b|\b[a-z]+(?:_[a-z]+)+\b', query)
        entities.extend(technical)
        
        return list(set(entities))[:10]  # Limit to 10 entities
    
    def _detect_tool_requirements(
        self,
        query_lower: str,
        task_type: TaskType,
    ) -> Tuple[bool, List[str]]:
        """Detect if tools are needed and which ones."""
        tool_hints = []
        
        # Web search indicators
        if any(term in query_lower for term in ["latest", "current", "2024", "2025", "today"]):
            tool_hints.append("web_search")
        
        # Calculator/code execution
        if task_type == TaskType.MATH_PROBLEM:
            tool_hints.append("calculator")
        
        if task_type == TaskType.CODE_GENERATION:
            tool_hints.append("code_execution")
        
        # Database lookup
        if any(term in query_lower for term in ["database", "lookup", "find in"]):
            tool_hints.append("database")
        
        requires_tools = len(tool_hints) > 0
        return requires_tools, tool_hints
    
    def _lint_query(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> LintResult:
        """Lint the query for issues and apply safety checks."""
        issues = []
        suggestions = []
        safety_flags = []
        modified = query
        
        # Check for very short queries
        if len(query.split()) < 3:
            issues.append("Query is very short, may be unclear")
            suggestions.append("Consider providing more context")
        
        # Check for missing question mark on questions
        question_words = ["what", "how", "why", "when", "where", "who", "which"]
        if any(query.lower().startswith(w) for w in question_words):
            if not query.endswith("?"):
                suggestions.append("Consider adding question mark")
        
        # Check for ambiguities
        if analysis.ambiguities:
            issues.extend(analysis.ambiguities)
        
        # Safety checks
        if self.enable_safety:
            for keyword in self.SAFETY_KEYWORDS:
                if keyword in query.lower():
                    safety_flags.append(f"Contains sensitive term: {keyword}")
        
        # Apply fixes to modified query
        modified = modified.strip()
        
        # Remove excessive whitespace
        modified = re.sub(r'\s+', ' ', modified)
        
        is_valid = len(issues) == 0 or len(issues) <= 2  # Allow minor issues
        
        return LintResult(
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions,
            safety_flags=safety_flags,
            modified_query=modified if modified != query else None,
        )
    
    def _segment_task(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> List[TaskSegment]:
        """Segment task into HRM-aware components."""
        segments = []
        
        # Planner segment (always present for complex tasks)
        if analysis.complexity in [QueryComplexity.COMPLEX, QueryComplexity.RESEARCH]:
            segments.append(TaskSegment(
                segment_type=SegmentType.PLANNER,
                description="Analyze request and create execution plan",
                required_capabilities={"planning", "analysis", "coordination"},
                input_requirements=["User query", "Domain context"],
                output_expectations=["Structured plan", "Sub-task breakdown"],
                acceptance_criteria=[
                    "Plan covers all aspects of query",
                    "Sub-tasks are specific and actionable",
                ],
                candidate_models=["gpt-4o", "claude-sonnet-4"],
                parallelizable=False,
                priority=1,
            ))
        
        # Solver segment(s) based on task type
        solver_segment = self._create_solver_segment(analysis)
        segments.append(solver_segment)
        
        # Research segment if needed
        if analysis.requires_tools or analysis.complexity == QueryComplexity.RESEARCH:
            segments.append(TaskSegment(
                segment_type=SegmentType.SOLVER,
                description="Gather information and evidence",
                required_capabilities={"research", "retrieval", "synthesis"},
                input_requirements=["Research queries", "Tool access"],
                output_expectations=["Relevant facts", "Sources", "Evidence"],
                acceptance_criteria=[
                    "Information is relevant to query",
                    "Sources are credible",
                ],
                candidate_models=["gemini-2.5-flash", "gpt-4o-mini"],
                parallelizable=True,
                priority=2,
            ))
        
        # Verifier segment
        segments.append(TaskSegment(
            segment_type=SegmentType.VERIFIER,
            description="Validate response accuracy and completeness",
            required_capabilities={"verification", "fact_checking", "quality_assessment"},
            input_requirements=["Generated response", "Original query", "Evidence"],
            output_expectations=["Verification report", "Issue list", "Confidence score"],
            acceptance_criteria=[
                "All factual claims verified",
                "Response addresses query completely",
                "No contradictions detected",
            ],
            candidate_models=["gpt-4o", "claude-sonnet-4"],
            parallelizable=False,
            priority=3,
        ))
        
        # Refiner segment
        segments.append(TaskSegment(
            segment_type=SegmentType.REFINER,
            description="Polish and format final response",
            required_capabilities={"editing", "formatting", "coherence"},
            input_requirements=["Verified response", "Format requirements", "Style guidelines"],
            output_expectations=["Polished final answer", "Proper formatting"],
            acceptance_criteria=[
                "Response is clear and well-organized",
                "Follows requested format",
                "Maintains accuracy of verified content",
            ],
            candidate_models=["gpt-4o", "claude-sonnet-4"],
            parallelizable=False,
            priority=4,
        ))
        
        return segments
    
    def _create_solver_segment(self, analysis: QueryAnalysis) -> TaskSegment:
        """Create solver segment based on task type."""
        task_configs = {
            TaskType.CODE_GENERATION: {
                "description": "Generate functional code solution",
                "capabilities": {"coding", "debugging", "documentation"},
                "models": ["gpt-4o", "claude-sonnet-4", "deepseek-chat"],
            },
            TaskType.MATH_PROBLEM: {
                "description": "Solve mathematical problem with steps",
                "capabilities": {"mathematics", "reasoning", "calculation"},
                "models": ["gpt-4o", "deepseek-chat"],
            },
            TaskType.RESEARCH_ANALYSIS: {
                "description": "Analyze and synthesize research findings",
                "capabilities": {"analysis", "synthesis", "critical_thinking"},
                "models": ["claude-sonnet-4", "gpt-4o", "gemini-2.5-pro"],
            },
            TaskType.EXPLANATION: {
                "description": "Provide clear explanation",
                "capabilities": {"explanation", "teaching", "simplification"},
                "models": ["gpt-4o", "claude-sonnet-4"],
            },
        }
        
        config = task_configs.get(analysis.task_type, {
            "description": "Generate comprehensive response",
            "capabilities": {"reasoning", "generation"},
            "models": ["gpt-4o", "claude-sonnet-4"],
        })
        
        return TaskSegment(
            segment_type=SegmentType.SOLVER,
            description=config["description"],
            required_capabilities=config["capabilities"],
            input_requirements=["Refined query", "Context", "Constraints"],
            output_expectations=["Primary response content"],
            acceptance_criteria=analysis.success_criteria,
            candidate_models=config["models"],
            parallelizable=False,
            priority=2,
        )
    
    def _generate_context_additions(
        self,
        analysis: QueryAnalysis,
        context: Optional[str],
        user_preferences: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Generate context additions to enhance the prompt."""
        additions = []
        
        # Add domain context
        if analysis.domain != "general":
            additions.append(f"Domain context: {analysis.domain}")
        
        # Add constraint reminders
        if analysis.constraints:
            additions.append(f"Constraints: {', '.join(analysis.constraints)}")
        
        # Add format requirement
        if analysis.output_format:
            additions.append(f"Output format: {analysis.output_format}")
        
        return additions
    
    def _determine_style_guidelines(
        self,
        analysis: QueryAnalysis,
        user_preferences: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Determine style guidelines for the response."""
        guidelines = []
        
        # Complexity-based guidelines
        if analysis.complexity == QueryComplexity.SIMPLE:
            guidelines.append("Keep response concise and direct")
        elif analysis.complexity == QueryComplexity.RESEARCH:
            guidelines.append("Provide comprehensive coverage with citations")
        
        # Task-based guidelines
        if analysis.task_type == TaskType.CODE_GENERATION:
            guidelines.extend([
                "Include code comments",
                "Provide usage examples",
            ])
        elif analysis.task_type == TaskType.EXPLANATION:
            guidelines.extend([
                "Use clear, accessible language",
                "Include examples where helpful",
            ])
        
        return guidelines
    
    def _calculate_confidence(
        self,
        analysis: QueryAnalysis,
        lint_result: LintResult,
    ) -> float:
        """Calculate confidence in the prompt specification."""
        confidence = 1.0
        
        # Reduce for ambiguities
        confidence -= len(analysis.ambiguities) * 0.1
        
        # Reduce for missing info
        confidence -= len(analysis.missing_info) * 0.1
        
        # Reduce for lint issues
        confidence -= len(lint_result.issues) * 0.05
        
        # Reduce for safety flags
        confidence -= len(lint_result.safety_flags) * 0.1
        
        return max(0.0, min(1.0, confidence))


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def preprocess_query(
    query: str,
    *,
    providers: Optional[Dict[str, Any]] = None,
    context: Optional[str] = None,
) -> PromptSpecification:
    """Convenience function to preprocess a query."""
    ops = PromptOps(providers=providers)
    return await ops.process(query, context=context)


def analyze_query(query: str) -> QueryAnalysis:
    """Quick analysis of a query without full preprocessing."""
    ops = PromptOps()
    return ops._analyze_query(query, None)

