"""Enhanced PromptOps Layer - Advanced preprocessing for LLMHive Orchestrator.

This module implements the patent-specified PromptOps preprocessing layer with
advanced NLP analysis:
1. LLM-based task classification (not just keywords)
2. Advanced ambiguity detection and auto-clarification
3. Context-aware query refinement
4. HRM-aware task segmentation with auto-enablement
5. Tool hints integration with Tool Broker
6. Safety filtering with guardrails

The PromptOps layer ensures every query is well-formed before heavy orchestration.
"""
from __future__ import annotations

import logging
import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

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


class AmbiguityType(str, Enum):
    """Types of ambiguity detected in queries."""
    PRONOUN_REFERENCE = "pronoun_reference"
    VAGUE_COMPARATIVE = "vague_comparative"
    TEMPORAL_AMBIGUITY = "temporal_ambiguity"
    SCOPE_AMBIGUITY = "scope_ambiguity"
    TECHNICAL_AMBIGUITY = "technical_ambiguity"
    MISSING_CONTEXT = "missing_context"


class ClarificationAction(str, Enum):
    """Actions to take for clarification."""
    AUTO_CLARIFY = "auto_clarify"       # Automatically rephrase/clarify
    ASK_USER = "ask_user"               # Ask user for clarification
    PROCEED_WITH_ASSUMPTION = "proceed_with_assumption"  # Make best assumption


# ==============================================================================
# Data Classes
# ==============================================================================

@dataclass(slots=True)
class AmbiguityDetail:
    """Detailed ambiguity information."""
    ambiguity_type: AmbiguityType
    term: str
    description: str
    suggested_clarification: Optional[str] = None
    confidence: float = 0.8


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
    ambiguities: List[str]  # Legacy simple format
    ambiguity_details: List[AmbiguityDetail] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    key_entities: List[str] = field(default_factory=list)
    requires_tools: bool = False
    tool_hints: List[str] = field(default_factory=list)
    requires_hrm: bool = False  # Auto-set based on complexity
    clarification_action: ClarificationAction = ClarificationAction.PROCEED_WITH_ASSUMPTION
    clarification_questions: List[str] = field(default_factory=list)
    confidence_score: float = 0.9


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
    requires_hrm: bool = False
    requires_tools: bool = False
    tool_requests: List[str] = field(default_factory=list)
    safety_blocked: bool = False  # If true, refuse to process
    safety_sanitized: bool = False  # If true, query was sanitized


@dataclass(slots=True)
class LintResult:
    """Result of linting a query."""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    safety_flags: List[str]
    modified_query: Optional[str]
    blocked: bool = False  # Critical safety issue


# ==============================================================================
# LLM-Based Classification Prompts
# ==============================================================================

TASK_CLASSIFICATION_PROMPT = """Analyze this query and classify it:

Query: "{query}"

Respond in JSON format with these fields:
{{
    "task_type": one of ["code_generation", "math_problem", "factual_question", "research_analysis", "creative_writing", "explanation", "comparison", "planning", "debugging", "summarization", "general"],
    "complexity": one of ["simple", "moderate", "complex", "research"],
    "domain": the relevant domain/field,
    "requires_tools": boolean (true if needs web search, calculator, code execution),
    "tool_hints": list of tools that might help ["web_search", "calculator", "code_execution"],
    "ambiguities": list of unclear/ambiguous parts,
    "confidence": 0.0 to 1.0
}}

Respond ONLY with the JSON, no other text."""

AMBIGUITY_DETECTION_PROMPT = """Analyze this query for ambiguities:

Query: "{query}"

Identify any:
1. Unclear pronoun references (e.g., "it", "this")
2. Vague comparatives without reference (e.g., "better" without saying than what)
3. Temporal ambiguity (e.g., "recently" without timeframe)
4. Scope ambiguity (e.g., unclear what exactly is being asked)
5. Missing context (e.g., needs prior information)

Respond in JSON format:
{{
    "has_ambiguity": boolean,
    "ambiguities": [
        {{
            "type": "pronoun_reference|vague_comparative|temporal|scope|missing_context",
            "term": the ambiguous term/phrase,
            "description": why it's ambiguous,
            "suggested_clarification": how to clarify or rephrase
        }}
    ],
    "clarified_query": the query with ambiguities resolved (best guess),
    "needs_user_input": boolean (true if clarification requires user input),
    "clarification_questions": list of questions to ask user
}}

Respond ONLY with the JSON."""


# ==============================================================================
# PromptOps Layer Implementation
# ==============================================================================

class PromptOps:
    """Enhanced PromptOps layer with LLM-based analysis.
    
    Implements the full PromptOps pipeline with advanced capabilities:
    1. LLM-based task classification (falls back to keyword-based)
    2. Advanced ambiguity detection with auto-clarification
    3. HRM auto-enablement for complex queries
    4. Tool hints integration
    5. Safety filtering with blocking/sanitization
    """
    
    # Keywords for task type detection (fallback)
    TASK_KEYWORDS = {
        TaskType.CODE_GENERATION: [
            "code", "implement", "function", "class", "write a program",
            "create a script", "develop", "build", "write code", "programming"
        ],
        TaskType.MATH_PROBLEM: [
            "calculate", "solve", "compute", "equation", "formula",
            "mathematical", "algebra", "geometry", "statistics", "integral",
            "derivative", "prove", "theorem"
        ],
        TaskType.DEBUGGING: [
            "debug", "fix", "error", "bug", "issue", "not working",
            "problem with", "fails", "exception", "traceback"
        ],
        TaskType.RESEARCH_ANALYSIS: [
            "research", "analyze", "comprehensive", "detailed analysis",
            "in-depth", "evaluate", "compare and contrast", "investigate",
            "study", "examine thoroughly"
        ],
        TaskType.CREATIVE_WRITING: [
            "write a story", "creative", "poem", "essay", "narrative",
            "imaginative", "fiction", "compose", "write creatively"
        ],
        TaskType.EXPLANATION: [
            "explain", "what is", "how does", "why does", "describe",
            "define", "clarify", "teach me", "help me understand"
        ],
        TaskType.COMPARISON: [
            "compare", "contrast", "difference between", "versus",
            "pros and cons", "advantages and disadvantages", "vs"
        ],
        TaskType.PLANNING: [
            "plan", "strategy", "roadmap", "schedule", "organize",
            "outline", "steps to", "how to", "create a plan"
        ],
        TaskType.SUMMARIZATION: [
            "summarize", "summary", "brief overview", "key points",
            "tldr", "condense", "main points"
        ],
        TaskType.FACTUAL_QUESTION: [
            "who is", "when did", "what year", "where is", "how many",
            "fact", "true that", "is it true", "historical"
        ],
    }
    
    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "simple": ["quick", "simple", "just", "only", "brief", "short", "basic"],
        "complex": [
            "comprehensive", "detailed", "in-depth", "thorough",
            "extensive", "complete", "all aspects", "step by step",
            "multi-step", "complex"
        ],
        "research": [
            "research", "investigate", "multiple sources", "evidence-based",
            "academic", "scholarly", "systematic", "literature review"
        ]
    }
    
    # Enhanced ambiguity patterns
    AMBIGUITY_PATTERNS = {
        AmbiguityType.PRONOUN_REFERENCE: [
            r'\bit\b', r'\bthis\b', r'\bthat\b', r'\bthese\b', r'\bthose\b',
            r'\bhe\b', r'\bshe\b', r'\bthey\b', r'\bthe one\b'
        ],
        AmbiguityType.VAGUE_COMPARATIVE: [
            r'\bbetter\b(?!\s+than)', r'\bworse\b(?!\s+than)',
            r'\bmore\b(?!\s+than)', r'\bless\b(?!\s+than)',
            r'\bfaster\b(?!\s+than)', r'\bsmarter\b(?!\s+than)'
        ],
        AmbiguityType.TEMPORAL_AMBIGUITY: [
            r'\brecently\b', r'\bsoon\b', r'\blater\b', r'\bearlier\b',
            r'\btoday\b(?!\s+\d)', r'\bnow\b'
        ],
        AmbiguityType.SCOPE_AMBIGUITY: [
            r'\bsome\b', r'\bfew\b', r'\bmany\b', r'\bseveral\b',
            r'\bmost\b', r'\ball\b'
        ],
    }
    
    # Safety keywords - tiered by severity
    SAFETY_KEYWORDS_BLOCK = [
        "hack into", "exploit vulnerability", "create malware", "bypass security",
        "illegal access", "create weapon", "harm people", "ddos attack",
        "steal credentials", "phishing attack"
    ]
    
    SAFETY_KEYWORDS_WARN = [
        "hack", "exploit", "bypass", "illegal", "weapon",
        "harmful", "dangerous", "sensitive", "security hole"
    ]
    
    def __init__(
        self,
        providers: Optional[Dict[str, Any]] = None,
        enable_llm_classification: bool = True,
        enable_auto_clarification: bool = True,
        enable_safety_checks: bool = True,
        enable_hrm_auto: bool = True,
        default_domain: str = "general",
    ) -> None:
        """
        Initialize enhanced PromptOps layer.
        
        Args:
            providers: LLM providers for advanced analysis
            enable_llm_classification: Use LLM for task classification
            enable_auto_clarification: Auto-clarify ambiguous queries
            enable_safety_checks: Run safety filters
            enable_hrm_auto: Auto-enable HRM for complex queries
            default_domain: Default domain when not detected
        """
        self.providers = providers or {}
        self.enable_llm_classification = enable_llm_classification
        self.enable_auto_clarification = enable_auto_clarification
        self.enable_safety = enable_safety_checks
        self.enable_hrm_auto = enable_hrm_auto
        self.default_domain = default_domain
        
        # Callbacks for dialogue manager integration
        self.clarification_callback: Optional[Callable[[List[str]], str]] = None
    
    def set_clarification_callback(
        self, 
        callback: Callable[[List[str]], str]
    ) -> None:
        """Set callback for user clarification (Dialogue Manager integration)."""
        self.clarification_callback = callback
    
    async def process(
        self,
        query: str,
        *,
        context: Optional[str] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        domain_hint: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> PromptSpecification:
        """
        Run the complete enhanced PromptOps pipeline.
        
        Args:
            query: Raw user query
            context: Optional conversation context
            user_preferences: User-specified preferences
            domain_hint: Hint for domain detection
            history: Conversation history for context
            
        Returns:
            PromptSpecification with optimized prompt
        """
        preprocessing_notes: List[str] = []
        
        # Step 1: Normalize and Analyze (LLM or keyword-based)
        preprocessing_notes.append("Step 1: Advanced query analysis")
        if self.enable_llm_classification and self.providers:
            analysis = await self._llm_analyze_query(query, domain_hint, history)
        else:
            analysis = self._analyze_query(query, domain_hint)
        
        # Step 2: Enhanced Ambiguity Detection and Resolution
        preprocessing_notes.append("Step 2: Ambiguity detection")
        if self.enable_auto_clarification:
            analysis, refined_query = await self._resolve_ambiguities(
                query, analysis, context, history
            )
            if refined_query != query:
                preprocessing_notes.append(f"Query auto-clarified: {len(analysis.ambiguity_details)} ambiguities resolved")
        else:
            refined_query = query
        
        # Step 3: Lint and Safety Check
        preprocessing_notes.append("Step 3: Linting and safety checks")
        lint_result = self._lint_query(refined_query, analysis)
        
        if lint_result.blocked:
            # Critical safety issue - block processing
            return PromptSpecification(
                original_query=query,
                refined_query="",
                analysis=analysis,
                segments=[],
                safety_flags=lint_result.safety_flags,
                style_guidelines=[],
                context_additions=[],
                confidence=0.0,
                preprocessing_notes=["BLOCKED: Safety policy violation"],
                requires_hrm=False,
                requires_tools=False,
                safety_blocked=True,
            )
        
        if lint_result.modified_query:
            refined_query = lint_result.modified_query
            preprocessing_notes.append(f"Query sanitized: {len(lint_result.issues)} issues fixed")
        
        # Step 4: Auto-enable HRM for complex queries
        requires_hrm = False
        if self.enable_hrm_auto:
            requires_hrm = analysis.complexity in [
                QueryComplexity.COMPLEX, 
                QueryComplexity.RESEARCH
            ]
            if requires_hrm:
                preprocessing_notes.append("HRM auto-enabled for complex query")
        
        # Step 5: Segment Task (HRM-Aware)
        preprocessing_notes.append("Step 4: HRM-aware task segmentation")
        segments = self._segment_task(refined_query, analysis)
        
        # Step 6: Context Additions
        context_additions = self._generate_context_additions(
            analysis, context, user_preferences, history
        )
        
        # Step 7: Style Guidelines
        style_guidelines = self._determine_style_guidelines(
            analysis, user_preferences
        )
        
        # Step 8: Tool hints integration
        tool_requests = []
        if analysis.requires_tools:
            tool_requests = analysis.tool_hints
            preprocessing_notes.append(f"Tools required: {', '.join(tool_requests)}")
        
        # Step 9: Finalize Specification
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
            requires_hrm=requires_hrm,
            requires_tools=analysis.requires_tools,
            tool_requests=tool_requests,
            safety_sanitized=lint_result.modified_query is not None,
        )
    
    async def _llm_analyze_query(
        self,
        query: str,
        domain_hint: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> QueryAnalysis:
        """Use LLM for advanced query classification."""
        try:
            # Get a provider (prefer GPT-4o for analysis)
            provider = self.providers.get("openai") or next(iter(self.providers.values()), None)
            if not provider:
                return self._analyze_query(query, domain_hint)
            
            prompt = TASK_CLASSIFICATION_PROMPT.format(query=query)
            
            # Use fast model for classification
            result = await provider.complete(prompt, model="gpt-4o-mini")
            content = getattr(result, 'content', '') or getattr(result, 'text', '')
            
            # Parse JSON response
            # Clean up potential markdown code blocks
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            
            data = json.loads(content.strip())
            
            # Map to enums
            task_type = TaskType(data.get("task_type", "general"))
            complexity = QueryComplexity(data.get("complexity", "moderate"))
            
            return QueryAnalysis(
                original_query=query,
                task_type=task_type,
                complexity=complexity,
                domain=data.get("domain", domain_hint or self.default_domain),
                constraints=self._extract_constraints(query),
                success_criteria=self._extract_success_criteria(query, task_type),
                output_format=self._detect_output_format(query.lower()),
                ambiguities=data.get("ambiguities", []),
                requires_tools=data.get("requires_tools", False),
                tool_hints=data.get("tool_hints", []),
                requires_hrm=complexity in [QueryComplexity.COMPLEX, QueryComplexity.RESEARCH],
                confidence_score=data.get("confidence", 0.9),
            )
        except Exception as e:
            logger.warning("LLM classification failed, using fallback: %s", e)
            return self._analyze_query(query, domain_hint)
    
    async def _resolve_ambiguities(
        self,
        query: str,
        analysis: QueryAnalysis,
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> Tuple[QueryAnalysis, str]:
        """Detect and resolve ambiguities in the query."""
        # Enhanced pattern-based detection
        ambiguity_details: List[AmbiguityDetail] = []
        
        for amb_type, patterns in self.AMBIGUITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query.lower())
                for match in matches:
                    term = match.group()
                    ambiguity_details.append(AmbiguityDetail(
                        ambiguity_type=amb_type,
                        term=term,
                        description=f"Ambiguous {amb_type.value}: '{term}'",
                        suggested_clarification=self._get_clarification_suggestion(
                            amb_type, term, query, context, history
                        ),
                    ))
        
        # Try LLM-based clarification if we have providers
        refined_query = query
        if ambiguity_details and self.providers:
            try:
                refined_query = await self._auto_clarify_with_llm(
                    query, ambiguity_details, context, history
                )
            except Exception as e:
                logger.debug("LLM clarification failed: %s", e)
        elif ambiguity_details:
            # Apply rule-based clarifications
            refined_query = self._apply_rule_based_clarification(
                query, ambiguity_details, context, history
            )
        
        # Determine action
        action = ClarificationAction.PROCEED_WITH_ASSUMPTION
        questions = []
        
        if len(ambiguity_details) >= 3:  # Many ambiguities
            action = ClarificationAction.ASK_USER
            questions = self._generate_clarification_questions(ambiguity_details)
        elif ambiguity_details and refined_query != query:
            action = ClarificationAction.AUTO_CLARIFY
        
        # Update analysis
        analysis.ambiguity_details = ambiguity_details
        analysis.clarification_action = action
        analysis.clarification_questions = questions
        
        return analysis, refined_query
    
    async def _auto_clarify_with_llm(
        self,
        query: str,
        ambiguities: List[AmbiguityDetail],
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> str:
        """Use LLM to auto-clarify ambiguous query."""
        provider = self.providers.get("openai") or next(iter(self.providers.values()), None)
        if not provider:
            return query
        
        # Build context from history
        history_context = ""
        if history:
            recent = history[-3:] if len(history) > 3 else history
            history_context = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')[:200]}"
                for msg in recent
            ])
        
        prompt = f"""Given this query with ambiguities, rewrite it to be clear and unambiguous:

Original Query: {query}

Detected Ambiguities:
{json.dumps([{"term": a.term, "type": a.ambiguity_type.value} for a in ambiguities], indent=2)}

{f"Recent conversation context:{chr(10)}{history_context}" if history_context else ""}

Rewrite the query to be clear and specific, making reasonable assumptions.
Output ONLY the clarified query, nothing else."""

        result = await provider.complete(prompt, model="gpt-4o-mini")
        content = getattr(result, 'content', '') or getattr(result, 'text', '')
        return content.strip() or query
    
    def _get_clarification_suggestion(
        self,
        amb_type: AmbiguityType,
        term: str,
        query: str,
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> Optional[str]:
        """Get a clarification suggestion for an ambiguous term."""
        if amb_type == AmbiguityType.PRONOUN_REFERENCE:
            # Try to find referent from history
            if history:
                for msg in reversed(history[-5:]):
                    content = msg.get("content", "")
                    # Look for nouns that might be the referent
                    nouns = re.findall(r'\b[A-Z][a-z]+\b', content)
                    if nouns:
                        return f"Consider specifying what '{term}' refers to (possibly '{nouns[0]}')"
            return f"Specify what '{term}' refers to"
        
        elif amb_type == AmbiguityType.VAGUE_COMPARATIVE:
            return f"Add a comparison baseline (e.g., 'than X')"
        
        elif amb_type == AmbiguityType.TEMPORAL_AMBIGUITY:
            return f"Specify the time frame (e.g., 'in the last week')"
        
        elif amb_type == AmbiguityType.SCOPE_AMBIGUITY:
            return f"Clarify the scope or quantity"
        
        return None
    
    def _apply_rule_based_clarification(
        self,
        query: str,
        ambiguities: List[AmbiguityDetail],
        context: Optional[str],
        history: Optional[List[Dict[str, str]]],
    ) -> str:
        """Apply rule-based clarifications without LLM."""
        refined = query
        
        for amb in ambiguities:
            if amb.ambiguity_type == AmbiguityType.TEMPORAL_AMBIGUITY:
                # Replace vague temporal terms with concrete ones
                if amb.term == "today":
                    pass  # Keep as is, usually clear enough
                elif amb.term == "recently":
                    refined = refined.replace("recently", "in the past few days")
                elif amb.term == "soon":
                    refined = refined.replace("soon", "in the near future")
        
        return refined
    
    def _generate_clarification_questions(
        self,
        ambiguities: List[AmbiguityDetail],
    ) -> List[str]:
        """Generate questions to ask user for clarification."""
        questions = []
        
        for amb in ambiguities[:3]:  # Limit to 3 questions
            if amb.ambiguity_type == AmbiguityType.PRONOUN_REFERENCE:
                questions.append(f"What does '{amb.term}' refer to in your query?")
            elif amb.ambiguity_type == AmbiguityType.VAGUE_COMPARATIVE:
                questions.append(f"When you say '{amb.term}', compared to what?")
            elif amb.ambiguity_type == AmbiguityType.TEMPORAL_AMBIGUITY:
                questions.append(f"What time frame do you mean by '{amb.term}'?")
            elif amb.ambiguity_type == AmbiguityType.SCOPE_AMBIGUITY:
                questions.append(f"Can you be more specific about the scope?")
        
        return questions
    
    def _analyze_query(
        self,
        query: str,
        domain_hint: Optional[str] = None,
    ) -> QueryAnalysis:
        """Analyze the query using keyword-based classification (fallback)."""
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
        
        # Detect ambiguities (simple)
        ambiguities = self._detect_ambiguities_simple(query_lower)
        
        # Detect missing information
        missing_info = self._detect_missing_info(query, task_type)
        
        # Extract key entities
        key_entities = self._extract_key_entities(query)
        
        # Detect tool requirements
        requires_tools, tool_hints = self._detect_tool_requirements(query_lower, task_type)
        
        # Auto-enable HRM for complex queries
        requires_hrm = complexity in [QueryComplexity.COMPLEX, QueryComplexity.RESEARCH]
        
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
            requires_hrm=requires_hrm,
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
        if simple_score >= 2 or len(query_lower.split()) < 8:
            return QueryComplexity.SIMPLE
        
        # Word count factor
        word_count = len(query_lower.split())
        if word_count > 50:
            return QueryComplexity.COMPLEX
        elif word_count > 25:
            return QueryComplexity.MODERATE
        
        return QueryComplexity.MODERATE
    
    def _detect_domain(self, query_lower: str) -> str:
        """Detect the domain of the query."""
        domain_keywords = {
            "coding": ["code", "program", "function", "api", "software", "debug", "script"],
            "medical": ["health", "medical", "disease", "symptom", "treatment", "doctor", "patient"],
            "legal": ["law", "legal", "contract", "court", "rights", "attorney", "statute"],
            "finance": ["money", "investment", "stock", "financial", "budget", "tax", "trading"],
            "marketing": ["marketing", "brand", "advertising", "campaign", "customer", "sales"],
            "research": ["research", "study", "analysis", "academic", "paper", "thesis"],
            "education": ["learn", "teach", "study", "course", "student", "education"],
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
        if "code" in query.lower() and "python" in query.lower():
            constraints.append("Use Python")
        
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
        elif task_type == TaskType.DEBUGGING:
            criteria.extend([
                "Identify the root cause",
                "Provide working fix",
                "Explain why the fix works",
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
    
    def _detect_ambiguities_simple(self, query_lower: str) -> List[str]:
        """Detect potentially ambiguous terms (simple version)."""
        ambiguities = []
        
        ambiguous_terms = [
            "it", "this", "that", "the thing", "stuff", "things",
            "best", "good", "better", "improve", "optimize"
        ]
        
        for term in ambiguous_terms:
            if term in query_lower.split():
                ambiguities.append(f"Term '{term}' may be ambiguous")
        
        # Check for unspecified references
        if re.search(r"\bit\b|\bthis\b|\bthat\b", query_lower):
            ambiguities.append("Contains unspecified pronoun references")
        
        return ambiguities
    
    def _detect_missing_info(
        self,
        query: str,
        task_type: TaskType,
    ) -> List[str]:
        """Detect potentially missing information."""
        missing = []
        
        if task_type == TaskType.CODE_GENERATION:
            if not any(lang in query.lower() for lang in 
                      ["python", "javascript", "java", "c++", "rust", "go", "typescript"]):
                missing.append("Programming language not specified")
        
        if task_type == TaskType.COMPARISON:
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
        
        return list(set(entities))[:10]
    
    def _detect_tool_requirements(
        self,
        query_lower: str,
        task_type: TaskType,
    ) -> Tuple[bool, List[str]]:
        """Detect if tools are needed and which ones."""
        tool_hints = []
        
        # Web search indicators - expanded
        search_indicators = [
            "latest", "current", "2024", "2025", "today", "news",
            "who is", "when did", "what year", "how much does",
            "stock price", "weather", "score", "result"
        ]
        if any(term in query_lower for term in search_indicators):
            tool_hints.append("web_search")
        
        # Also trigger for factual questions
        if task_type == TaskType.FACTUAL_QUESTION:
            if "web_search" not in tool_hints:
                tool_hints.append("web_search")
        
        # Calculator/code execution
        if task_type == TaskType.MATH_PROBLEM:
            tool_hints.append("calculator")
        
        if task_type == TaskType.CODE_GENERATION:
            tool_hints.append("code_execution")
        
        if task_type == TaskType.DEBUGGING:
            tool_hints.append("code_execution")
        
        # Database lookup
        if any(term in query_lower for term in ["database", "lookup", "find in", "query"]):
            tool_hints.append("database")
        
        # Image generation
        if any(term in query_lower for term in 
               ["image of", "picture of", "diagram of", "generate image", "draw"]):
            tool_hints.append("image_generation")
        
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
        blocked = False
        
        # Check for very short queries
        if len(query.split()) < 3:
            issues.append("Query is very short, may be unclear")
            suggestions.append("Consider providing more context")
        
        # Check for missing question mark on questions
        question_words = ["what", "how", "why", "when", "where", "who", "which"]
        if any(query.lower().startswith(w) for w in question_words):
            if not query.endswith("?"):
                suggestions.append("Consider adding question mark")
        
        # Safety checks - blocking level
        if self.enable_safety:
            query_lower = query.lower()
            
            for keyword in self.SAFETY_KEYWORDS_BLOCK:
                if keyword in query_lower:
                    safety_flags.append(f"BLOCKED: Contains prohibited term: {keyword}")
                    blocked = True
                    break
            
            if not blocked:
                for keyword in self.SAFETY_KEYWORDS_WARN:
                    if keyword in query_lower:
                        safety_flags.append(f"Contains sensitive term: {keyword}")
                        # Sanitize by adding disclaimer
                        modified = f"[Note: This query contains sensitive content and should be handled carefully] {query}"
        
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
            blocked=blocked,
        )
    
    def _segment_task(
        self,
        query: str,
        analysis: QueryAnalysis,
    ) -> List[TaskSegment]:
        """Segment task into HRM-aware components."""
        segments = []
        
        # Planner segment (for complex tasks)
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
            TaskType.DEBUGGING: {
                "description": "Identify and fix code issues",
                "capabilities": {"debugging", "code_analysis", "testing"},
                "models": ["deepseek-chat", "gpt-4o", "claude-sonnet-4"],
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
        history: Optional[List[Dict[str, str]]],
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
        
        # Add recent history summary
        if history and len(history) > 2:
            additions.append("Conversation continues from previous context")
        
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
        
        # User preferences
        if user_preferences:
            tone = user_preferences.get("tone")
            if tone:
                guidelines.append(f"Use {tone} tone")
        
        return guidelines
    
    def _calculate_confidence(
        self,
        analysis: QueryAnalysis,
        lint_result: LintResult,
    ) -> float:
        """Calculate confidence in the prompt specification."""
        confidence = 1.0
        
        # Reduce for ambiguities
        confidence -= len(analysis.ambiguity_details) * 0.05
        confidence -= len(analysis.ambiguities) * 0.05
        
        # Reduce for missing info
        confidence -= len(analysis.missing_info) * 0.1
        
        # Reduce for lint issues
        confidence -= len(lint_result.issues) * 0.05
        
        # Reduce for safety flags
        confidence -= len(lint_result.safety_flags) * 0.1
        
        # Use analysis confidence if available
        if analysis.confidence_score < 1.0:
            confidence = min(confidence, analysis.confidence_score)
        
        return max(0.0, min(1.0, confidence))


# ==============================================================================
# Convenience Functions
# ==============================================================================

async def preprocess_query(
    query: str,
    *,
    providers: Optional[Dict[str, Any]] = None,
    context: Optional[str] = None,
    enable_llm: bool = True,
) -> PromptSpecification:
    """Convenience function to preprocess a query."""
    ops = PromptOps(
        providers=providers,
        enable_llm_classification=enable_llm,
    )
    return await ops.process(query, context=context)


def analyze_query(query: str) -> QueryAnalysis:
    """Quick analysis of a query without full preprocessing."""
    ops = PromptOps()
    return ops._analyze_query(query, None)


def get_task_type(query: str) -> TaskType:
    """Get the task type for a query."""
    ops = PromptOps()
    return ops._detect_task_type(query.lower())


def get_complexity(query: str) -> QueryComplexity:
    """Get the complexity level for a query."""
    ops = PromptOps()
    return ops._detect_complexity(query.lower())
