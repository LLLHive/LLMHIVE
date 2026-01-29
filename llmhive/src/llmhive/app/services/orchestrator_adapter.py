"""Adapter service to bridge ChatRequest to internal orchestrator.

Enhanced with Elite Orchestration for maximum performance:
- PromptOps preprocessing (ALWAYS ON)
- Intelligent model-task matching
- Quality-weighted fusion
- Parallel execution
- Challenge and refine strategies
- Verification gate with retry
- Answer refinement (ALWAYS ON)
"""
from __future__ import annotations

import json
import logging
import re
import time
import os
from typing import Dict, Any, List, Optional, Tuple

from ..models.orchestration import (
    ChatRequest,
    ChatResponse,
    AgentTrace,
    ReasoningMode,
    ReasoningMethod,
    DomainPack,
    AgentMode,
)
from ..orchestrator import Orchestrator
# profiles_firestore requires google-cloud-firestore which may not be available
try:
    from ..profiles_firestore import get_profile
    PROFILES_AVAILABLE = True
except ImportError:
    get_profile = lambda x: None  # type: ignore
    PROFILES_AVAILABLE = False
from ..audit_log import log_audit_event
from .model_router import (
    get_models_for_reasoning_method,
    map_reasoning_mode_to_method,
    ReasoningMethod as RouterReasoningMethod,
    FALLBACK_GPT_5,
    FALLBACK_GPT_4O,
    FALLBACK_GPT_4O_MINI,
    FALLBACK_O3,
    FALLBACK_O1,
    FALLBACK_CLAUDE_OPUS_4,
    FALLBACK_CLAUDE_SONNET_4,
    FALLBACK_CLAUDE_3_5,
    FALLBACK_CLAUDE_3_HAIKU,
    FALLBACK_GEMINI_3_PRO,
    FALLBACK_GEMINI_2_5,
    FALLBACK_GEMINI_2_5_FLASH,
    FALLBACK_GROK_4,
    FALLBACK_GROK_BETA,
    FALLBACK_DEEPSEEK,
    FALLBACK_DEEPSEEK_R1,
    FALLBACK_LLAMA_4,
    FALLBACK_MISTRAL_LARGE,
    # Automatic model selection functions
    get_best_models_for_task,
    get_diverse_ensemble,
    MODEL_CAPABILITIES,
    # Category-specific routing (January 2026 improvements)
    get_long_context_model,
    get_multilingual_models,
    get_speed_optimized_models,
    get_math_specialist_models,
    get_rag_optimized_models,
    estimate_token_count,
    detect_language,
    is_multilingual_query,
    is_long_context_query,
    is_speed_critical,
)
from .reasoning_prompts import get_reasoning_prompt_template, get_category_prompt

# Import Clarification Manager for ambiguity detection
try:
    from ..orchestration.clarification_manager import (
        ClarificationManager,
        ClarificationStatus,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError:
    CLARIFICATION_AVAILABLE = False
    ClarificationManager = None

# Import ModelKnowledgeStore for Pinecone-backed intelligent model selection
try:
    from ..knowledge.model_knowledge_store import (
        ModelKnowledgeStore,
        get_model_knowledge_store,
    )
    MODEL_KNOWLEDGE_AVAILABLE = True
except ImportError:
    MODEL_KNOWLEDGE_AVAILABLE = False
    ModelKnowledgeStore = None
    get_model_knowledge_store = None

# Import comprehensive model intelligence for deep orchestration decisions
try:
    from ..knowledge.model_intelligence import (
        MODEL_PROFILES,
        REASONING_METHODS,
        REASONING_HACKS,
        TEAM_STRATEGIES,
        get_model_profile,
        get_best_models_for_task as get_intelligent_best_models,
        get_team_for_task,
        get_reasoning_hack,
        ModelTier,
    )
    MODEL_INTELLIGENCE_AVAILABLE = True
except ImportError:
    MODEL_INTELLIGENCE_AVAILABLE = False
    MODEL_PROFILES = {}
    REASONING_METHODS = {}
    REASONING_HACKS = {}
    TEAM_STRATEGIES = {}
    get_model_profile = lambda x: None
    get_intelligent_best_models = lambda *a, **k: []
    get_team_for_task = lambda x: None
    get_reasoning_hack = lambda *a: None
    ModelTier = None

# Import Elite Orchestrator and Quality Booster
try:
    from ..orchestration.elite_orchestrator import (
        EliteOrchestrator,
        EliteResult,
        get_best_model_for_task,
    )
    ELITE_AVAILABLE = True
except ImportError:
    ELITE_AVAILABLE = False
    EliteOrchestrator = None

# Import Elite Orchestration Module (Phase 18 - Top Position Strategy)
try:
    from ..orchestration.elite_orchestration import (
        elite_orchestrate,
        elite_math_solve,
        elite_reasoning_solve,
        elite_rag_query,
        detect_elite_category,
        EliteTier,
        EliteConfig,
        ELITE_MODELS,
    )
    ELITE_ORCHESTRATION_AVAILABLE = True
except ImportError:
    ELITE_ORCHESTRATION_AVAILABLE = False
    elite_orchestrate = None
    EliteTier = None

try:
    from ..orchestration.quality_booster import (
        QualityBooster,
        boost_response,
    )
    QUALITY_BOOSTER_AVAILABLE = True
except ImportError:
    QUALITY_BOOSTER_AVAILABLE = False
    QualityBooster = None

# Import Performance Tracker for learning from query outcomes
try:
    from ..performance_tracker import PerformanceTracker, performance_tracker
    PERFORMANCE_TRACKER_AVAILABLE = True
except ImportError:
    PERFORMANCE_TRACKER_AVAILABLE = False
    performance_tracker = None

# Import PromptOps for always-on preprocessing
try:
    from ..orchestration.prompt_ops import PromptOps, PromptSpecification
    PROMPTOPS_AVAILABLE = True
except ImportError:
    PROMPTOPS_AVAILABLE = False
    PromptOps = None
    PromptSpecification = None

# Import Answer Refiner for polishing
try:
    from ..orchestration.answer_refiner import (
        AnswerRefiner,
        RefinementConfig,
        OutputFormat,
        ToneStyle,
    )
    REFINER_AVAILABLE = True
except ImportError:
    REFINER_AVAILABLE = False
    AnswerRefiner = None

# Import Prompt Templates for verification
try:
    from ..orchestration.prompt_templates import build_verifier_prompt
    VERIFIER_PROMPT_AVAILABLE = True
except ImportError:
    VERIFIER_PROMPT_AVAILABLE = False

# Import Tool Verification for math, code, and factual verification
try:
    from ..orchestration.tool_verification import (
        get_verification_pipeline,
        VerificationPipeline,
        VerificationType,
    )
    TOOL_VERIFICATION_AVAILABLE = True
except ImportError:
    TOOL_VERIFICATION_AVAILABLE = False
    get_verification_pipeline = None

# Import Tool Broker for automatic tool detection and execution
try:
    from ..orchestration.tool_broker import (
        get_tool_broker,
        ToolBroker,
        ToolType,
        ToolAnalysis,
        check_and_execute_tools,
    )
    TOOL_BROKER_AVAILABLE = True
except ImportError:
    TOOL_BROKER_AVAILABLE = False
    get_tool_broker = None

# PR5: Import budget-aware routing
try:
    from ..orchestration.adaptive_router import (
        BudgetConstraints,
        get_adaptive_router,
    )
    BUDGET_ROUTING_AVAILABLE = True
except ImportError:
    BUDGET_ROUTING_AVAILABLE = False
    BudgetConstraints = None

# Import Pinecone Knowledge Base for RAG and learning
try:
    from ..knowledge.pinecone_kb import (
        get_knowledge_base,
        PineconeKnowledgeBase,
        RecordType,
    )
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    get_knowledge_base = None

# Import cascade router and reasoning detector for intelligent routing
try:
    from ..orchestration.cascade_router import CascadeRouter, QueryComplexity
    from ..orchestration.reasoning_detector import ReasoningDetector, ReasoningType
    CASCADE_ROUTING_AVAILABLE = True
except ImportError:
    CASCADE_ROUTING_AVAILABLE = False
    CascadeRouter = None  # type: ignore
    ReasoningDetector = None  # type: ignore
    QueryComplexity = None  # type: ignore
    ReasoningType = None  # type: ignore

logger = logging.getLogger(__name__)

# Configuration
MAX_CHALLENGE_LOOPS = 2  # Max retry attempts on verification failure
VERIFICATION_ENABLED = True  # Enable verification gate
REFINER_ALWAYS_ON = True  # Always run answer refinement

# Global orchestrator instance
_orchestrator = Orchestrator()

# Elite orchestrator instance (initialized on first use)
_elite_orchestrator: Optional[EliteOrchestrator] = None


def _clean_reasoning_output(text: str) -> str:
    """
    Clean reasoning output for user-facing display.
    
    This function:
    - Removes internal scaffold markers (=== SECTION ===)
    - Preserves step-by-step reasoning content
    - Formats the output nicely for users
    
    Used for reasoning tasks where we want to show work but not internal markers.
    """
    if not text:
        return text
    
    # Replace scaffold section markers with cleaner headings
    section_replacements = [
        (r'===\s*PROBLEM\s*===\s*', '**Problem:**\n'),
        (r'===\s*UNDERSTANDING\s*===\s*', '\n**Understanding:**\n'),
        (r'===\s*APPROACH\s*===\s*', '\n**Approach:**\n'),
        (r'===\s*STEP-BY-STEP\s*SOLUTION\s*===\s*', '\n**Solution:**\n'),
        (r'===\s*SOLUTION\s*===\s*', '\n**Solution:**\n'),
        (r'===\s*VERIFICATION\s*===\s*', '\n**Verification:**\n'),
        (r'===\s*FINAL\s*ANSWER\s*===\s*', '\n**Answer:**\n'),
        (r'===\s*SYNTHESIS\s*===\s*', '\n**Conclusion:**\n'),
        # Generic pattern for any remaining === SECTION === markers
        (r'===\s*([A-Z][A-Z\s]+)\s*===\s*', r'\n**\1:**\n'),
    ]
    
    result = text
    for pattern, replacement in section_replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    # Clean up any remaining triple equals
    result = re.sub(r'===+', '', result)
    
    # Clean up excessive whitespace
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()
    
    return result


def _strip_internal_scaffolding(text: str) -> str:
    """
    Strip internal orchestration scaffolding from the final response.
    
    This removes patterns that should never appear in user-facing output:
    - === PROBLEM === sections
    - IMPORTANT: Answer the user's... instructions
    - Internal reasoning scaffold markers
    - Reasoning hack templates (confidence_gated, self_debate, etc.)
    """
    if not text:
        return text
    
    # re is imported at module level
    
    # Pattern 0: Check for reasoning hack template leakage
    # These templates should NEVER appear in the output - they mean the LLM returned its prompt
    reasoning_hack_patterns = [
        r'^Solve this problem\.\s*You MUST express confidence',  # confidence_gated template
        r'^===\s*ATTEMPT\s*\d+\s*===',  # confidence_gated attempt markers
        r'^\[IF CONFIDENCE\s*<\s*\d+%,\s*CONTINUE:\]',  # template instructions
        r'^Let me think through this step by step',  # basic_cot template start
        r'^=== Step 1: Understand the Problem ===',  # structured_reasoning template
        r'^I\'ll analyze this from multiple perspectives',  # self_debate template
        # Multi-step task templates (accuracy_level 4)
        r'^.*?\*\*Problem:\*\*\s*IMPORTANT:',  # multi-step template start
        r'^Sure,?\s*let\'s address.*?step-by-step',  # common template response pattern
        r'^Complete this multi-part task',  # multi_step category prompt
        r'^Think through this problem carefully',  # reasoning category prompt
    ]
    for pattern in reasoning_hack_patterns:
        if re.match(pattern, text, re.IGNORECASE | re.MULTILINE):
            logger.warning("Detected reasoning hack template in response - extracting final answer")
            # Try to find actual answer content
            # Look for common answer patterns
            answer_patterns = [
                r'(?:Final\s*Answer|FINAL\s*ANSWER)[:\s]*(.+?)(?:$|\n===)',
                r'(?:The answer is|Therefore)[:\s]*(.+?)(?:\n\n|$)',
                r'(?:Solution|Result)[:\s]*(.+?)(?:\n\n|$)',
            ]
            for ap in answer_patterns:
                match = re.search(ap, text, re.IGNORECASE | re.DOTALL)
                if match:
                    extracted = match.group(1).strip()
                    # VALIDATION: Ensure extracted content is complete, not a fragment
                    # Fragments often start with lowercase or are too short
                    is_fragment = (
                        len(extracted) < 20 or
                        (extracted[0].islower() and not extracted.startswith('$')) or
                        extracted.startswith('is ') or
                        extracted.startswith('are ') or
                        extracted.startswith('was ') or
                        extracted.startswith('to ') or
                        not any(c.isalnum() for c in extracted[:10])
                    )
                    if not is_fragment:
                        return extracted
                    else:
                        logger.warning("Extracted fragment looks incomplete: %s", extracted[:50])
            # If no clear answer found, return the original text cleaned up
            logger.warning("Could not extract clean answer, returning cleaned original")
            # Try to return everything after the template markers
            clean_text = re.sub(r'^.*?(?:FINAL ANSWER|final answer)[:\s]*', '', text, flags=re.IGNORECASE | re.DOTALL)
            if clean_text and len(clean_text) > 20:
                return clean_text.strip()
            return text  # Return original if nothing better found
    
    # Pattern 1: Remove "=== PROBLEM ===" or similar scaffold headers with instructions
    scaffold_pattern = r'^===\s*(PROBLEM|UNDERSTANDING|APPROACH|SOLUTION)\s*===\s*(IMPORTANT:|CRITICAL:)?'
    if re.match(scaffold_pattern, text, re.IGNORECASE):
        # Try to find "=== FINAL ANSWER ===" or "=== SYNTHESIS ===" and extract from there
        final_patterns = [
            r'===\s*FINAL\s*ANSWER\s*===\s*(.+?)(?:===|$)',
            r'===\s*SYNTHESIS\s*===\s*(.+?)(?:===|$)',
            r'===\s*SOLUTION\s*===\s*(.+?)(?:===|$)',
            r'Final\s*Answer\s*:\s*(.+?)(?:\n===|$)',
        ]
        for pattern in final_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                # VALIDATION: Ensure extracted content is complete, not a fragment
                is_fragment = (
                    len(extracted) < 20 or
                    (extracted[0].islower() and not extracted.startswith('$')) or
                    extracted.startswith('is ') or
                    extracted.startswith('are ') or
                    extracted.startswith('was ') or
                    extracted.startswith('to ')
                )
                if not is_fragment:
                    logger.info("Stripped internal scaffold, extracted final answer")
                    return extracted
                else:
                    logger.warning("Pattern 1: Extracted fragment looks incomplete, continuing search")
        
        # If no clear final answer section, try to find content after system instructions
        # Look for the first line that doesn't look like an instruction
        lines = text.split('\n')
        content_start = 0
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            # Skip scaffold markers and system instructions
            if (line_lower.startswith('===') or
                line_lower.startswith('important:') or
                line_lower.startswith('critical:') or
                'do not ask' in line_lower or
                'never refuse' in line_lower or
                'answer the user' in line_lower):
                content_start = i + 1
                continue
            break
        
        if content_start > 0 and content_start < len(lines):
            cleaned = '\n'.join(lines[content_start:]).strip()
            if len(cleaned) > 20:
                logger.info("Stripped %d lines of internal scaffold", content_start)
                return cleaned
    
    # Pattern 2: Remove leading "IMPORTANT: Answer the user's..." instruction block
    instruction_pattern = r'^IMPORTANT:\s*Answer the user.*?(?:NEVER refuse[^.]*\.)\s*'
    text = re.sub(instruction_pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 2b: Remove leaked system prompt and reasoning instruction content
    system_prompt_patterns = [
        r'^IMPORTANT:\s*Answer the user.*?(?:specialty|scope)[.\s]*',
        r'^Do NOT ask clarifying questions.*?(?:specialty|scope)[.\s]*',
        r'^You are a helpful assistant.*?(?:scope|specialty)[.\s]*',
        r'^CRITICAL RULES:.*?(?:Just answer\.|scope\.)\s*',
        r'^1\.\s*NEVER ask clarifying questions.*?(?:Just answer\.|scope\.)\s*',
        r"^If the user specifies criteria.*?(?:alternative criteria\.)\s*",
        r"^Do not ask about alternative criteria\..*?\n+",
        r"^NEVER refuse to answer.*?(?:specialty\.)\s*",
        r"^For any question.*?(?:outside your scope\.)\s*",
        r"^You have expertise in.*?(?:knowledge base\.)\s*",
        # Multi-step template patterns (accuracy_level 4)
        r'\*\*Problem:\*\*\s*IMPORTANT:\s*This is a complex request.*?completely\.\s*',
        r'IMPORTANT:\s*This is a complex request.*?(?:completely|part)\.\s*',
        r'You MUST address EVERY part.*?(?:completely|\.)\s*',
        r'## The Request:\s*',
    ]
    for pattern in system_prompt_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Pattern 3: Remove "Stub response for:" patterns
    stub_pattern = r'^Stub response for:.*?\n+'
    text = re.sub(stub_pattern, '', text, flags=re.IGNORECASE)
    
    # Pattern 4: Remove trailing scaffold markers
    text = re.sub(r'\s*===\s*(END|COMPLETE|DONE)\s*===\s*$', '', text, flags=re.IGNORECASE)
    
    # FINAL VALIDATION: Check if result is a fragment and reject
    result = text.strip()
    fragment_indicators = [
        'is accurate to',
        'is correct',
        'is the answer',
        'are the results',
        'was calculated',
        'to the cent',
        'as shown above',
        'as calculated',
        'do not ask clarifying',
        'never refuse to answer',
        'helpful assistant',
        'critical rules',
        'if the user specifies',
        'important: answer the user',
        'solve this problem in two phases',
        'phase 1 - planning',
        'let\'s work this out',
        'clearly marked as',
        'provide a concise',
        'after reasoning',
        # Multi-step template fragments
        'this is a complex request',
        'you must address every part',
        'address each requirement',
        'complete this multi-part task',
        'think through this problem',
        '## the request:',
    ]
    result_lower = result.lower()
    
    # If result starts with a fragment indicator, it's incomplete
    if any(result_lower.startswith(frag) for frag in fragment_indicators):
        logger.warning("Final result is a fragment: %s", result[:50])
        # Return empty to trigger fallback
        return ""
    
    # Also check for responses that look like fragments (continue from previous text)
    # Increase threshold to 100 chars since fragments can be longer
    if len(result) < 100 and result_lower.startswith(('is ', 'are ', 'was ', 'were ', 'to ', 'based on ', 'according to ')):
        logger.warning("Fragment detected: %s", result)
        return ""
    
    # Try to extract Final Answer if present
    final_answer_match = re.search(r"(?:Final\s*Answer|FINAL\s*ANSWER|final answer)[:\s]*([^\n].*?)(?:\n\n|$)", result, re.IGNORECASE | re.DOTALL)
    if final_answer_match:
        extracted = final_answer_match.group(1).strip()
        # Make sure it's a real answer, not just scaffolding
        if len(extracted) > 10 and not any(extracted.lower().startswith(f) for f in ['provide ', 'clearly ', 'after ']):
            logger.info("Extracted Final Answer: %s", extracted[:100])
            return extracted
    
    return result
_quality_booster: Optional[QualityBooster] = None


def _get_elite_orchestrator() -> Optional[EliteOrchestrator]:
    """Get or create elite orchestrator instance."""
    global _elite_orchestrator
    if _elite_orchestrator is None and ELITE_AVAILABLE:
        _elite_orchestrator = EliteOrchestrator(
            providers=_orchestrator.providers,
            performance_tracker=getattr(_orchestrator, 'performance_tracker', None),
            enable_learning=True,
        )
        logger.info("Elite orchestrator initialized")
    return _elite_orchestrator


# ==============================================================================
# INTELLIGENT PINECONE-BACKED MODEL SELECTION
# ==============================================================================

# Actual OpenRouter model IDs (VERIFIED December 2025)
# These MUST match exactly what OpenRouter returns from /api/v1/models
OPENROUTER_GPT_5 = "openai/gpt-5"                        # ✓ Verified - EXPENSIVE
OPENROUTER_CLAUDE_OPUS_4 = "anthropic/claude-opus-4"    # ✓ Verified - EXPENSIVE
OPENROUTER_GEMINI_2_PRO = "google/gemini-2.5-pro"       # ✓ Verified (2.5, not 2.0)
OPENROUTER_CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4"  # ✓ Verified (no date suffix)
OPENROUTER_O3 = "openai/o3"                              # ✓ Verified - EXPENSIVE
OPENROUTER_O1 = "openai/o1-pro"                          # ✓ Verified - EXPENSIVE
OPENROUTER_LLAMA_4 = "meta-llama/llama-4-maverick"       # ✓ Verified (maverick variant)
OPENROUTER_MISTRAL_LARGE = "mistralai/mistral-large-2512"  # ✓ Verified
OPENROUTER_GPT_4O = "openai/gpt-4o"                      # ✓ Verified - COST-EFFECTIVE
OPENROUTER_DEEPSEEK = "deepseek/deepseek-v3.2"           # ✓ Verified - COST-EFFECTIVE
OPENROUTER_DEEPSEEK_R1 = "deepseek/deepseek-r1-0528"     # ✓ Verified - COST-EFFECTIVE
OPENROUTER_GROK_4 = "x-ai/grok-4"                        # ✓ Verified
OPENROUTER_GEMINI_2_5_FLASH = "google/gemini-2.5-flash"  # ✓ Verified - VERY CHEAP
OPENROUTER_GEMINI_3_PRO = "google/gemini-3-pro-preview"  # ✓ Verified (newest)

# Budget-aware flag - set to True to use cost-effective models only
BUDGET_MODE = os.getenv("BUDGET_MODE", "true").lower() == "true"

# Cost-effective models (use when credits are limited)
COST_EFFECTIVE_MODELS = [
    OPENROUTER_GPT_4O,           # ~$5/1M tokens - excellent quality
    OPENROUTER_DEEPSEEK,         # ~$0.14/1M tokens - great for coding
    OPENROUTER_DEEPSEEK_R1,      # ~$0.55/1M tokens - reasoning specialist
    OPENROUTER_GEMINI_2_5_FLASH, # ~$0.075/1M tokens - very fast
    OPENROUTER_GEMINI_2_PRO,     # ~$1.25/1M tokens - good for research
    OPENROUTER_CLAUDE_SONNET_4,  # ~$3/1M tokens - good balance
    OPENROUTER_LLAMA_4,          # ~$0.20/1M tokens - open source
    OPENROUTER_MISTRAL_LARGE,    # ~$2/1M tokens - good for coding
]

# Premium models (require more credits)
PREMIUM_MODELS = [
    OPENROUTER_GPT_5,            # ~$15/1M tokens
    OPENROUTER_CLAUDE_OPUS_4,    # ~$15/1M tokens
    OPENROUTER_O3,               # ~$20/1M tokens
    OPENROUTER_O1,               # ~$15/1M tokens
]

# Define model strengths for complementary selection (matching ACTUAL OpenRouter models)
MODEL_STRENGTHS = {
    # ===== TOP TIER (verified December 2025) =====
    OPENROUTER_GPT_5: {
        "strengths": ["reasoning", "coding", "analysis", "general", "factual"],
        "provider": "openai", "tier": "flagship", "rank": 1
    },
    OPENROUTER_CLAUDE_OPUS_4: {
        "strengths": ["reasoning", "creative", "analysis", "medical", "legal"],
        "provider": "anthropic", "tier": "flagship", "rank": 2
    },
    OPENROUTER_GEMINI_2_PRO: {
        "strengths": ["reasoning", "factual", "analysis", "multimodal", "research"],
        "provider": "google", "tier": "flagship", "rank": 3
    },
    OPENROUTER_GEMINI_3_PRO: {
        "strengths": ["reasoning", "factual", "analysis", "multimodal", "research", "medical"],
        "provider": "google", "tier": "flagship", "rank": 4
    },
    OPENROUTER_CLAUDE_SONNET_4: {
        "strengths": ["reasoning", "creative", "coding", "analysis"],
        "provider": "anthropic", "tier": "flagship", "rank": 5
    },
    
    # ===== REASONING SPECIALISTS =====
    OPENROUTER_O3: {
        "strengths": ["reasoning", "math", "coding", "logic", "analysis", "research"],
        "provider": "openai", "tier": "reasoning", "rank": 6
    },
    OPENROUTER_O1: {
        "strengths": ["reasoning", "math", "coding", "logic", "analysis"],
        "provider": "openai", "tier": "reasoning", "rank": 7
    },
    OPENROUTER_DEEPSEEK_R1: {
        "strengths": ["reasoning", "math", "coding", "logic"],
        "provider": "deepseek", "tier": "reasoning", "rank": 8
    },
    
    # ===== OTHER TOP MODELS =====
    OPENROUTER_LLAMA_4: {
        "strengths": ["reasoning", "coding", "general", "open-source"],
        "provider": "meta", "tier": "flagship", "rank": 9
    },
    OPENROUTER_MISTRAL_LARGE: {
        "strengths": ["reasoning", "coding", "multilingual", "analysis"],
        "provider": "mistral", "tier": "flagship", "rank": 10
    },
    
    # ===== STILL AVAILABLE (legacy/fallback) =====
    OPENROUTER_GPT_4O: {
        "strengths": ["reasoning", "coding", "analysis", "general"],
        "provider": "openai", "tier": "flagship", "rank": 11
    },
    OPENROUTER_DEEPSEEK: {
        "strengths": ["coding", "math", "reasoning"],
        "provider": "deepseek", "tier": "specialized", "rank": 12
    },
    OPENROUTER_GROK_4: {
        "strengths": ["factual", "realtime", "creative", "reasoning"],
        "provider": "xai", "tier": "flagship", "rank": 13
    },
    
    # ===== FAST MODELS =====
    OPENROUTER_GEMINI_2_5_FLASH: {
        "strengths": ["speed", "factual", "general"],
        "provider": "google", "tier": "fast", "rank": 20
    },
}

# Map domains to required strengths
DOMAIN_REQUIRED_STRENGTHS = {
    "health_medical": ["medical", "reasoning", "factual", "analysis"],
    "legal_analysis": ["reasoning", "analysis", "factual", "legal"],
    "financial_analysis": ["math", "analysis", "reasoning"],
    "science_research": ["analysis", "factual", "reasoning", "research"],
    "code_generation": ["coding", "reasoning"],
    "debugging": ["coding", "analysis"],
    "math_problem": ["math", "reasoning", "logic"],
    "creative_writing": ["creative", "reasoning"],
    "factual_question": ["factual", "reasoning"],
    "research_analysis": ["analysis", "reasoning", "factual", "research"],
    "general": ["reasoning", "general"],
}

# Domain-specific top models - COST-EFFECTIVE versions (for budget mode)
DOMAIN_TOP_MODELS_BUDGET = {
    "health_medical": [
        OPENROUTER_GPT_4O,          # Cost-effective, still excellent
        OPENROUTER_CLAUDE_SONNET_4, # Good for medical reasoning
        OPENROUTER_GEMINI_2_PRO,    # Strong for research
        OPENROUTER_DEEPSEEK,        # Very cheap, decent quality
    ],
    "legal_analysis": [
        OPENROUTER_CLAUDE_SONNET_4, # Good for legal reasoning
        OPENROUTER_GPT_4O,
        OPENROUTER_DEEPSEEK_R1,     # Reasoning model
    ],
    "financial_analysis": [
        OPENROUTER_DEEPSEEK_R1,     # Math + reasoning, cheap
        OPENROUTER_GPT_4O,
        OPENROUTER_DEEPSEEK,
    ],
    "science_research": [
        OPENROUTER_GEMINI_2_PRO,    # Strong for research
        OPENROUTER_GPT_4O,
        OPENROUTER_DEEPSEEK,
    ],
    "code_generation": [
        OPENROUTER_CLAUDE_SONNET_4, # Best for coding
        OPENROUTER_DEEPSEEK,        # Excellent for coding, very cheap
        OPENROUTER_GPT_4O,
    ],
    "debugging": [
        OPENROUTER_DEEPSEEK,        # Great for debugging
        OPENROUTER_CLAUDE_SONNET_4,
        OPENROUTER_GPT_4O,
    ],
    "math_problem": [
        OPENROUTER_DEEPSEEK_R1,     # Reasoning model, cheap
        OPENROUTER_GPT_4O,
        OPENROUTER_GEMINI_2_PRO,
    ],
    "creative_writing": [
        OPENROUTER_CLAUDE_SONNET_4, # Good for creative
        OPENROUTER_GPT_4O,
        OPENROUTER_GEMINI_2_PRO,
    ],
    "factual_question": [
        OPENROUTER_GPT_4O,
        OPENROUTER_GEMINI_2_5_FLASH, # Very fast and cheap
        OPENROUTER_DEEPSEEK,
    ],
    "general": [
        OPENROUTER_GPT_4O,
        OPENROUTER_CLAUDE_SONNET_4,
        OPENROUTER_DEEPSEEK,
    ],
}

# Domain-specific top models - PREMIUM versions (for when credits available)
DOMAIN_TOP_MODELS_PREMIUM = {
    "health_medical": [
        OPENROUTER_GPT_5,           # #1 overall
        OPENROUTER_CLAUDE_OPUS_4,   # #2 - excellent for medical reasoning
        OPENROUTER_GEMINI_3_PRO,    # #3 - newest Google model
        OPENROUTER_GEMINI_2_PRO,    # #4 - strong for factual/research
    ],
    "legal_analysis": [
        OPENROUTER_CLAUDE_OPUS_4,   # Best for legal reasoning
        OPENROUTER_GPT_5,
        OPENROUTER_O3,              # Strong reasoning model
    ],
    "financial_analysis": [
        OPENROUTER_O3,              # Math + reasoning specialist
        OPENROUTER_GPT_5,
        OPENROUTER_CLAUDE_OPUS_4,
        OPENROUTER_DEEPSEEK_R1,     # Good at math
    ],
    "science_research": [
        OPENROUTER_GEMINI_3_PRO,    # Newest, strong for research
        OPENROUTER_GEMINI_2_PRO,    # Strong for research
        OPENROUTER_CLAUDE_OPUS_4,
        OPENROUTER_GPT_5,
    ],
    "code_generation": [
        OPENROUTER_CLAUDE_SONNET_4, # Best for coding
        OPENROUTER_GPT_5,
        OPENROUTER_DEEPSEEK,        # Specialized for coding
        OPENROUTER_DEEPSEEK_R1,     # Reasoning + coding
    ],
    "debugging": [
        OPENROUTER_CLAUDE_SONNET_4,
        OPENROUTER_DEEPSEEK,
        OPENROUTER_GPT_5,
    ],
    "math_problem": [
        OPENROUTER_O3,              # Best reasoning specialist
        OPENROUTER_DEEPSEEK_R1,     # Reasoning model
        OPENROUTER_GPT_5,
        OPENROUTER_GEMINI_2_PRO,
    ],
    "creative_writing": [
        OPENROUTER_CLAUDE_OPUS_4,   # Best for creative
        OPENROUTER_CLAUDE_SONNET_4,
        OPENROUTER_GPT_5,
    ],
    "factual_question": [
        OPENROUTER_GPT_5,
        OPENROUTER_GEMINI_3_PRO,
        OPENROUTER_GROK_4,          # Real-time knowledge
    ],
    "general": [
        OPENROUTER_GPT_5,
        OPENROUTER_CLAUDE_OPUS_4,
        OPENROUTER_GEMINI_2_PRO,
    ],
}

# Select domain models based on budget mode
DOMAIN_TOP_MODELS = DOMAIN_TOP_MODELS_BUDGET if BUDGET_MODE else DOMAIN_TOP_MODELS_PREMIUM

# Models with tool/function calling support (VERIFIED against OpenRouter)
TOOL_CAPABLE_MODELS = {
    OPENROUTER_GPT_5,
    OPENROUTER_GPT_4O,
    OPENROUTER_O3,
    OPENROUTER_O1,
    OPENROUTER_CLAUDE_OPUS_4,
    OPENROUTER_CLAUDE_SONNET_4,
    OPENROUTER_GEMINI_3_PRO,
    OPENROUTER_GEMINI_2_PRO,
    OPENROUTER_GEMINI_2_5_FLASH,
    OPENROUTER_LLAMA_4,
    OPENROUTER_MISTRAL_LARGE,
    OPENROUTER_GROK_4,
    OPENROUTER_DEEPSEEK,
}


async def get_intelligent_models(
    task_type: str,
    num_models: int = 3,
    require_tools: bool = False,
    available_models: Optional[List[str]] = None,
    accuracy_priority: bool = True,
) -> List[str]:
    """
    Intelligent model selection using COMPREHENSIVE MODEL INTELLIGENCE:
    1. Deep model profiles (strengths, weaknesses, costs, latency)
    2. Team composition strategies
    3. Domain-specific top models (from OpenRouter rankings)
    4. Pinecone category rankings
    5. Complementary model strengths (provider diversity)
    6. Tool support filtering
    
    Args:
        task_type: The detected task type (from PromptOps)
        num_models: Number of models to select
        require_tools: If True, only select models with tool support
        available_models: Limit selection to these models
        accuracy_priority: If True, prioritize accuracy over speed
        
    Returns:
        List of model IDs optimized for the task
    """
    selected = []
    used_providers = set()
    
    # ===========================================================================
    # STEP 0: Use comprehensive MODEL_INTELLIGENCE if available
    # ===========================================================================
    if MODEL_INTELLIGENCE_AVAILABLE and MODEL_PROFILES:
        # Try to get a team strategy first
        team_strategy = get_team_for_task(task_type)
        if team_strategy and accuracy_priority:
            logger.info(
                "Using team strategy '%s' for %s: %s",
                team_strategy.name, task_type, team_strategy.models
            )
            for model_id in team_strategy.models:
                if len(selected) >= num_models:
                    break
                if require_tools:
                    profile = get_model_profile(model_id)
                    if profile and not profile.supports_tools:
                        continue
                if available_models is not None and model_id not in available_models:
                    continue
                
                profile = get_model_profile(model_id)
                if profile:
                    provider = profile.provider.lower()
                    if provider not in used_providers or len(selected) < 2:
                        selected.append(model_id)
                        used_providers.add(provider)
            
            if selected:
                logger.info(
                    "Team strategy selected for %s: %s (roles: %s)",
                    task_type, selected, 
                    {m: team_strategy.roles.get(m, "member") for m in selected}
                )
                return selected[:num_models]
        
        # Fall back to intelligent best models from profiles
        if not selected:
            max_tier = ModelTier.FLAGSHIP if accuracy_priority else ModelTier.BALANCED
            profile_selected = get_intelligent_best_models(
                task_type,
                num_models=num_models,
                max_cost_tier=max_tier,
                require_tools=require_tools,
            )
            if profile_selected:
                for model_id in profile_selected:
                    if available_models is not None and model_id not in available_models:
                        continue
                    profile = get_model_profile(model_id)
                    if profile:
                        provider = profile.provider.lower()
                        if provider not in used_providers or len(selected) < 2:
                            selected.append(model_id)
                            used_providers.add(provider)
                
                if selected:
                    logger.info(
                        "MODEL_PROFILES selected for %s: %s",
                        task_type, selected
                    )
                    return selected[:num_models]
    
    # ===========================================================================
    # STEP 1: Use domain-specific top models (fallback from OpenRouter rankings)
    # ===========================================================================
    domain_top = DOMAIN_TOP_MODELS.get(task_type, DOMAIN_TOP_MODELS.get("general", []))
    for model_id in domain_top:
        if len(selected) >= num_models:
            break
        if require_tools and model_id not in TOOL_CAPABLE_MODELS:
            continue
        if available_models is not None and model_id not in available_models:
            continue
        
        model_info = MODEL_STRENGTHS.get(model_id, {})
        provider = model_info.get("provider", "unknown")
        
        # Ensure provider diversity
        if provider not in used_providers or len(selected) < 2:
            selected.append(model_id)
            used_providers.add(provider)
    
    if selected:
        logger.info(
            "Domain-specific models for %s: %s (from OpenRouter rankings)",
            task_type, selected
        )
    
    # Step 1: Supplement with Pinecone category rankings if needed
    if len(selected) < num_models and MODEL_KNOWLEDGE_AVAILABLE and get_model_knowledge_store is not None:
        try:
            store = get_model_knowledge_store()
            # Get category-specific rankings
            rankings = await store.get_best_models_for_task(
                task_description=task_type,
                category=task_type,
                top_k=num_models * 2,  # Get extra for filtering
                require_tools=require_tools,
            )
            
            if rankings:
                for record in rankings:
                    model_id = record.model_id
                    if model_id and model_id not in selected and len(selected) < num_models:
                        # Check if available
                        if available_models is None or model_id in available_models:
                            # Ensure provider diversity
                            model_info = MODEL_STRENGTHS.get(model_id, {})
                            provider = model_info.get("provider", "unknown")
                            
                            if provider not in used_providers or len(used_providers) >= 3:
                                selected.append(model_id)
                                used_providers.add(provider)
                
                if len(selected) > len(domain_top):
                    logger.info(
                        "Pinecone added %d more models for %s",
                        len(selected) - len(domain_top), task_type
                    )
        except Exception as e:
            logger.warning("Pinecone model selection failed, using fallback: %s", e)
    
    # Step 2: Add complementary models based on required strengths
    required_strengths = DOMAIN_REQUIRED_STRENGTHS.get(task_type, ["reasoning", "general"])
    
    # Score remaining models by strength match + diversity
    candidates = []
    for model_id, info in MODEL_STRENGTHS.items():
        if model_id in selected:
            continue
        if available_models is not None and model_id not in available_models:
            continue
        if require_tools and model_id not in TOOL_CAPABLE_MODELS:
            continue
            
        # Calculate strength match score
        model_strengths = set(info.get("strengths", []))
        match_score = len(model_strengths & set(required_strengths))
        
        # Bonus for provider diversity
        provider = info.get("provider", "unknown")
        diversity_bonus = 2 if provider not in used_providers else 0
        
        # Tier bonus (flagship > specialized > fast for accuracy)
        tier = info.get("tier", "fast")
        if accuracy_priority:
            tier_bonus = {"flagship": 3, "specialized": 2, "fast": 0}.get(tier, 0)
        else:
            tier_bonus = {"flagship": 1, "specialized": 1, "fast": 3}.get(tier, 0)
        
        total_score = match_score + diversity_bonus + tier_bonus
        candidates.append((model_id, total_score, provider))
    
    # Sort by score and add to selection
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    for model_id, score, provider in candidates:
        if len(selected) >= num_models:
            break
        selected.append(model_id)
        used_providers.add(provider)
    
    # Step 3: Fallback to OpenRouter top-ranked models (VERIFIED December 2025)
    if len(selected) < num_models:
        # Use actual OpenRouter ranking order (verified against /api/v1/models)
        fallback_order = [
            OPENROUTER_GPT_5,           # #1
            OPENROUTER_CLAUDE_OPUS_4,   # #2
            OPENROUTER_GEMINI_3_PRO,    # #3 newest
            OPENROUTER_GEMINI_2_PRO,    # #4
            OPENROUTER_CLAUDE_SONNET_4, # #5
            OPENROUTER_O3,              # #6 reasoning
            OPENROUTER_LLAMA_4,         # #7
            OPENROUTER_MISTRAL_LARGE,   # #8
            OPENROUTER_GROK_4,          # #9
            OPENROUTER_GPT_4O,          # fallback
        ]
        for model_id in fallback_order:
            if model_id not in selected and len(selected) < num_models:
                if available_models is None or model_id in available_models:
                    if not require_tools or model_id in TOOL_CAPABLE_MODELS:
                        selected.append(model_id)
    
    logger.info(
        "Intelligent model selection for '%s': %d models, require_tools=%s -> %s",
        task_type, num_models, require_tools, selected
    )
    
    return selected[:num_models]


def get_intelligent_models_sync(
    task_type: str,
    num_models: int = 3,
    require_tools: bool = False,
    available_models: Optional[List[str]] = None,
    accuracy_priority: bool = True,
) -> List[str]:
    """
    Synchronous wrapper for intelligent model selection.
    Uses local knowledge when Pinecone is not available.
    """
    import asyncio
    
    # Try async version first
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context - use sync fallback
            return _get_intelligent_models_local(
                task_type, num_models, require_tools, available_models, accuracy_priority
            )
        else:
            return loop.run_until_complete(
                get_intelligent_models(
                    task_type, num_models, require_tools, available_models, accuracy_priority
                )
            )
    except RuntimeError:
        # No event loop - use sync fallback
        return _get_intelligent_models_local(
            task_type, num_models, require_tools, available_models, accuracy_priority
        )


def _get_intelligent_models_local(
    task_type: str,
    num_models: int = 3,
    require_tools: bool = False,
    available_models: Optional[List[str]] = None,
    accuracy_priority: bool = True,
) -> List[str]:
    """
    Local (non-Pinecone) intelligent model selection.
    Uses DOMAIN_TOP_MODELS first, then MODEL_STRENGTHS for supplementary selection.
    """
    selected = []
    used_providers = set()
    
    # Step 0: Use domain-specific top models FIRST (from OpenRouter rankings)
    domain_top = DOMAIN_TOP_MODELS.get(task_type, DOMAIN_TOP_MODELS.get("general", []))
    for model_id in domain_top:
        if len(selected) >= num_models:
            break
        if require_tools and model_id not in TOOL_CAPABLE_MODELS:
            continue
        if available_models is not None and model_id not in available_models:
            continue
        
        model_info = MODEL_STRENGTHS.get(model_id, {})
        provider = model_info.get("provider", "unknown")
        
        if provider not in used_providers or len(selected) < 2:
            selected.append(model_id)
            used_providers.add(provider)
    
    # If we need more, score remaining models by strength match
    if len(selected) < num_models:
        required_strengths = DOMAIN_REQUIRED_STRENGTHS.get(task_type, ["reasoning", "general"])
        
        candidates = []
        for model_id, info in MODEL_STRENGTHS.items():
            if model_id in selected:
                continue
            if available_models is not None and model_id not in available_models:
                continue
            if require_tools and model_id not in TOOL_CAPABLE_MODELS:
                continue
            
            model_strengths = set(info.get("strengths", []))
            match_score = len(model_strengths & set(required_strengths))
            
            provider = info.get("provider", "unknown")
            diversity_bonus = 2 if provider not in used_providers else 0
            
            # Use rank if available (lower is better)
            rank = info.get("rank", 99)
            rank_bonus = max(0, 10 - rank)  # Higher bonus for lower rank
            
            tier = info.get("tier", "fast")
            if accuracy_priority:
                tier_bonus = {"flagship": 3, "reasoning": 4, "specialized": 2, "fast": 0}.get(tier, 0)
            else:
                tier_bonus = {"flagship": 1, "reasoning": 1, "specialized": 1, "fast": 3}.get(tier, 0)
            
            total_score = match_score + diversity_bonus + tier_bonus + rank_bonus
            candidates.append((model_id, total_score, provider))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        for model_id, score, provider in candidates:
            if len(selected) >= num_models:
                break
            selected.append(model_id)
            used_providers.add(provider)
    
    # Fallback - use actual OpenRouter top-ranked models
    if len(selected) < num_models:
        fallback_order = [
            OPENROUTER_GPT_5,
            OPENROUTER_CLAUDE_OPUS_4,
            OPENROUTER_GEMINI_2_PRO,
            OPENROUTER_CLAUDE_SONNET_4,
            OPENROUTER_O1,
        ]
        for model_id in fallback_order:
            if model_id not in selected and len(selected) < num_models:
                if available_models is None or model_id in available_models:
                    selected.append(model_id)
    
    return selected[:num_models]


def _get_quality_booster() -> Optional[QualityBooster]:
    """Get or create quality booster instance."""
    global _quality_booster
    if _quality_booster is None and QUALITY_BOOSTER_AVAILABLE:
        _quality_booster = QualityBooster(
            providers=_orchestrator.providers,
            default_model="gpt-4o",
        )
        logger.info("Quality booster initialized")
    return _quality_booster


# Knowledge base instance
_knowledge_base: Optional[PineconeKnowledgeBase] = None

# Cascade router and reasoning detector instances
_cascade_router: Optional["CascadeRouter"] = None
_reasoning_detector: Optional["ReasoningDetector"] = None


def _get_cascade_router() -> Optional["CascadeRouter"]:
    """Get or create cascade router for cost-optimized model selection."""
    global _cascade_router
    if _cascade_router is None and CASCADE_ROUTING_AVAILABLE:
        _cascade_router = CascadeRouter()
        logger.info("Cascade router initialized for cost-optimized routing")
    return _cascade_router


def _get_reasoning_detector() -> Optional["ReasoningDetector"]:
    """Get or create reasoning detector for complex query detection."""
    global _reasoning_detector
    if _reasoning_detector is None and CASCADE_ROUTING_AVAILABLE:
        _reasoning_detector = ReasoningDetector()
        logger.info("Reasoning detector initialized")
    return _reasoning_detector


def _get_knowledge_base() -> Optional[PineconeKnowledgeBase]:
    """Get or create knowledge base instance for RAG and learning."""
    global _knowledge_base
    if _knowledge_base is None and KNOWLEDGE_BASE_AVAILABLE:
        _knowledge_base = get_knowledge_base()
        logger.info("Knowledge base initialized")
    return _knowledge_base


async def _augment_with_rag(
    prompt: str,
    domain: str = "default",
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> str:
    """Augment prompt with relevant context from knowledge base."""
    kb = _get_knowledge_base()
    if not kb:
        return prompt
    
    try:
        verification_result = None
        refined_text = None
        selected_strategy = "standard"
        augmented = await kb.augment_prompt(
            query=prompt,
            domain=domain,
            user_id=user_id,
            project_id=project_id,
            org_id=org_id,
            max_context_length=1500,
        )
        if augmented != prompt:
            logger.info("Prompt augmented with RAG context")
        return augmented
    except Exception as e:
        logger.warning(f"RAG augmentation failed: {e}")
        return prompt


async def _store_answer_for_learning(
    query: str,
    answer: str,
    models_used: List[str],
    quality_score: float,
    domain: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    org_id: Optional[str] = None,
    is_partial: bool = False,
    record_type: Optional[RecordType] = None,
) -> None:
    """Store answer in knowledge base for future learning."""
    kb = _get_knowledge_base()
    if not kb:
        return
    
    try:
        record_type = record_type or (RecordType.PARTIAL_ANSWER if is_partial else RecordType.FINAL_ANSWER)
        await kb.store_answer(
            query=query,
            answer=answer,
            models_used=models_used,
            record_type=record_type,
            quality_score=quality_score,
            domain=domain,
            user_id=user_id,
            project_id=project_id,
            org_id=org_id,
        )
        logger.debug(f"Stored {'partial' if is_partial else 'final'} answer for learning")
    except Exception as e:
        logger.warning(f"Failed to store answer: {e}")


async def _learn_orchestration_pattern(
    query_type: str,
    strategy_used: str,
    models_used: List[str],
    success: bool,
    latency_ms: int,
    quality_score: float,
    user_id: Optional[str] = None,
) -> None:
    """Learn from orchestration pattern for future optimization."""
    kb = _get_knowledge_base()
    if not kb:
        return
    
    try:
        await kb.store_orchestration_pattern(
            query_type=query_type,
            strategy_used=strategy_used,
            models_used=models_used,
            success=success,
            latency_ms=latency_ms,
            quality_score=quality_score,
            user_id=user_id,
        )
        logger.debug(f"Learned orchestration pattern: {strategy_used} for {query_type}")
    except Exception as e:
        logger.warning(f"Failed to learn pattern: {e}")


def _detect_task_type(prompt: str) -> str:
    """Detect task type from prompt for optimal routing.
    
    Categories map to model capabilities and rankings for intelligent selection.
    """
    prompt_lower = prompt.lower()
    
    # ===========================================================================
    # PRIORITY 1: Multi-step Tasks (need decomposition and HRM)
    # ===========================================================================
    # Detect numbered requirements, complex designs, multi-part requests
    multi_step_indicators = [
        # Numbered requirements
        r'\b(1\)|1\.|first).*(2\)|2\.|second)',
        r'include:?\s*\d+\)',
        # Complex design tasks
        r'\b(design|create|build)\s+.*(complete|full|entire|comprehensive)',
        r'\b(rest\s+api|api\s+design|system\s+design)\b',
        # Multi-requirement tasks
        r'\b(want|need|require)\s+.*(and|,).*(and|,)',
        # Explicit multi-part
        r'\b(list|provide|include)\s*:.*\d+\)',
    ]
    for pattern in multi_step_indicators:
        if re.search(pattern, prompt_lower):
            return "multi_step"
    
    # ===========================================================================
    # PRIORITY 2: Reasoning/Logic Tasks (need chain-of-thought)
    # ===========================================================================
    # Detect logic puzzles, syllogisms, word problems with unknowns
    reasoning_indicators = [
        # Logic puzzles and word problems
        r'\b(how many|how much)\b.*(if|when|given)',
        r'\b(chickens?|rabbits?|cows?|sheep|animals?)\b.*\b(heads?|legs?|total)\b',
        r'\b(heads?|legs?)\b.*\b(count|total|number)\b',
        # Syllogisms and formal logic
        r'\b(all|some|no|none)\s+\w+\s+(are|is)\b.*\b(can we conclude|therefore|implies)\b',
        r'\b(if all|if some|if no)\b.*\b(then|therefore|conclude)\b',
        r'\bcan we (conclude|infer|deduce)\b',
        # Deductive reasoning
        r'\b(valid|invalid|logical|fallacy)\b.*\b(argument|reasoning|conclusion)\b',
        # Multi-step word problems
        r'\b(age|years? old)\b.*\b(older|younger|twice|half)\b',
        r'\b(distance|speed|time)\b.*\b(traveled|moving|mph|km/h)\b',
        # Probability and statistics reasoning
        r'\b(probability|odds|chance|likely)\b.*\b(if|given|when)\b',
    ]
    for pattern in reasoning_indicators:
        if re.search(pattern, prompt_lower):
            return "reasoning"
    
    # ===========================================================================
    # PRIORITY 3: Math Problems (need calculator)
    # ===========================================================================
    # Code/Programming - DeepSeek, Claude Sonnet 4, GPT-4o excel
    if any(kw in prompt_lower for kw in ["code", "function", "implement", "debug", "program", "script", "api", "backend", "frontend"]):
        return "code_generation"
    
    # Math/Quantitative - o1, GPT-4o, Gemini Pro excel
    # Enhanced patterns for financial calculations
    elif any(kw in prompt_lower for kw in [
        "calculate", "solve", "math", "equation", "integral", "derivative", "proof",
        "compound interest", "simple interest", "invested at", "annual interest",
        "compounded", "principal", "rate of return", "profit margin",
        "% of", "percent of", "percentage of"
    ]):
        return "math_problem"
    
    # Health/Medical/Wellness - Claude Opus 4, GPT-5, Med-PaLM 3 excel (requires accuracy)
    elif any(kw in prompt_lower for kw in [
        "treatment", "symptom", "diagnosis", "medical", "health", "disease", "medication",
        "drug", "therapy", "clinical", "patient", "headache", "pain", "condition",
        "doctor", "hospital", "illness", "chronic", "acute", "prognosis",
        # Wellness & Fitness (added)
        "exercise", "workout", "fitness", "nutrition", "diet", "weight loss", "muscle",
        "cardio", "strength", "sleep", "stress", "mental health", "wellbeing", "wellness",
        "benefits of", "healthy", "vitamin", "supplement", "lifestyle"
    ]):
        return "health_medical"
    
    # Science/Academic - Claude Opus 4, o1, Gemini Pro excel
    elif any(kw in prompt_lower for kw in [
        "scientific", "research", "study", "hypothesis", "experiment", "theory",
        "peer-reviewed", "journal", "academic", "physics", "chemistry", "biology"
    ]):
        return "science_research"
    
    # Legal - Claude models, GPT-4o excel (requires precision)
    elif any(kw in prompt_lower for kw in [
        "legal", "law", "contract", "liability", "court", "attorney", "lawsuit",
        "regulation", "compliance", "statute", "precedent", "jurisdiction"
    ]):
        return "legal_analysis"
    
    # Finance/Business - o1, Gemini Pro, GPT-4o excel
    elif any(kw in prompt_lower for kw in [
        "financial", "investment", "stock", "market", "portfolio", "valuation",
        "revenue", "profit", "budget", "accounting", "tax", "fiscal"
    ]):
        return "financial_analysis"
    
    # Creative Writing - Claude models excel
    elif any(kw in prompt_lower for kw in [
        "write", "story", "creative", "poem", "narrative", "fiction", "character"
    ]):
        return "creative_writing"
    
    # Research/Analysis - needs multi-model consensus
    elif any(kw in prompt_lower for kw in ["research", "analyze", "comprehensive", "in-depth", "latest", "developments"]):
        return "research_analysis"
    
    # Explanation - needs clarity
    elif any(kw in prompt_lower for kw in ["explain", "what is", "how does", "why"]):
        return "explanation"
    
    # Comparison - needs multi-perspective
    elif any(kw in prompt_lower for kw in ["compare", "versus", "difference", "pros and cons"]):
        return "comparison"
    
    elif any(kw in prompt_lower for kw in ["summarize", "summary", "tldr"]):
        return "summarization"
    elif any(kw in prompt_lower for kw in ["quick", "fast", "brief"]):
        return "fast_response"
    elif any(kw in prompt_lower for kw in ["detailed", "thorough", "complete"]):
        return "high_quality"
    else:
        return "general"


def _select_elite_strategy(
    accuracy_level: int,
    task_type: str,
    num_models: int,
    complexity: str = "moderate",
    criteria: Optional[dict] = None,
    prompt_spec: Optional[Any] = None,
) -> str:
    """Select the best elite orchestration strategy intelligently.
    
    Strategies (in order of quality vs. speed tradeoff):
    - single_best: Fastest - simple queries, single model (~100ms)
    - parallel_race: Fast - speed-critical, first-win (~150ms)
    - best_of_n: Medium - select best from multiple (~300ms)
    - quality_weighted_fusion: Balanced - combine perspectives (~400ms)
    - expert_panel: Thorough - multiple expert views (~600ms)
    - challenge_and_refine: Most thorough - verification loop (~800ms)
    
    Selection considers:
    - Task type (code/math need verification, research needs perspectives)
    - Complexity (simple → fast, complex → thorough)
    - Accuracy level (1-5, user preference)
    - User criteria (speed, accuracy, creativity weights)
    - PromptOps analysis (if available)
    """
    # Default criteria
    if not criteria:
        criteria = {"accuracy": 70, "speed": 50, "creativity": 50}
    
    speed_priority = criteria.get("speed", 50)
    accuracy_priority = criteria.get("accuracy", 70)
    creativity_priority = criteria.get("creativity", 50)
    
    # ========================================================================
    # PHASE 1: HARD RULES - ALL ACCURACY-CRITICAL DOMAINS GET EXPERT TREATMENT
    # ========================================================================
    
    # Code and math ALWAYS need verification (non-negotiable)
    if task_type in ["code_generation", "debugging", "math_problem"]:
        # Math problems benefit from self-consistency at high accuracy
        if task_type == "math_problem" and num_models >= 3 and accuracy_level >= 3:
            logger.info("Strategy: Math problem with 3+ models -> best_of_n (self-consistency for numerical accuracy)")
            return "best_of_n"  # Generate multiple solutions, vote on answer
        # Speed-optimize if user explicitly wants fast
        if speed_priority >= 80 and accuracy_level <= 2:
            logger.info("Strategy: Code/math with high speed priority -> best_of_n")
            return "best_of_n"  # Skip challenge loop but still compare
        logger.info("Strategy: Code/math task -> challenge_and_refine")
        return "challenge_and_refine"
    
    # ALL ACCURACY-CRITICAL DOMAINS: Health, Legal, Finance, Science
    # These require expert_panel (3+ models) or challenge_and_refine (fewer models)
    accuracy_critical_domains = [
        "health_medical",      # Lives at stake
        "legal_analysis",      # Legal liability
        "financial_analysis",  # Money at stake
        "science_research",    # Factual accuracy
    ]
    
    if task_type in accuracy_critical_domains:
        if num_models >= 3:
            logger.info("Strategy: %s task, 3+ models -> expert_panel (accuracy-critical)", task_type)
            return "expert_panel"  # Multiple perspectives for critical domains
        elif num_models >= 2:
            logger.info("Strategy: %s task, 2 models -> quality_weighted_fusion (accuracy-critical)", task_type)
            return "quality_weighted_fusion"
        logger.info("Strategy: %s task -> challenge_and_refine (accuracy-critical)", task_type)
        return "challenge_and_refine"
    
    # Factual questions with high accuracy need verification
    if task_type == "factual_question" and accuracy_priority >= 80:
        if num_models >= 3:
            logger.info("Strategy: Factual question, 3+ models, high accuracy -> expert_panel")
            return "expert_panel"
        logger.info("Strategy: Factual question with high accuracy -> challenge_and_refine")
        return "challenge_and_refine"
    
    # ========================================================================
    # PHASE 1.5: REASONING AND MULTI-STEP TASKS (Need special handling)
    # ========================================================================
    
    # Reasoning tasks benefit from self-consistency (sample N, vote on answer)
    if task_type == "reasoning":
        if num_models >= 3 and accuracy_level >= 3:
            logger.info("Strategy: Reasoning task with 3+ models -> best_of_n (self-consistency voting)")
            return "best_of_n"  # Generate multiple reasoning paths, vote on best
        logger.info("Strategy: Reasoning task -> challenge_and_refine (forces verification)")
        return "challenge_and_refine"  # Always verify reasoning
    
    # Multi-step tasks need decomposition and synthesis
    if task_type == "multi_step":
        if num_models >= 3:
            logger.info("Strategy: Multi-step task, 3+ models -> expert_panel (decomposition)")
            return "expert_panel"  # Different models for different sub-tasks
        logger.info("Strategy: Multi-step task -> challenge_and_refine (iterative refinement)")
        return "challenge_and_refine"
    
    # ========================================================================
    # PHASE 2: FAST PATH (Speed-optimized)
    # ========================================================================
    
    # Simple complexity OR explicit fast preference OR low accuracy setting
    if complexity == "simple" or speed_priority >= 85 or accuracy_level <= 1:
        if num_models == 1:
            logger.info("Strategy: Fast mode, 1 model -> single_best")
            return "single_best"
        else:
            logger.info("Strategy: Fast mode, multiple models -> parallel_race")
            return "parallel_race"
    
    # ========================================================================
    # PHASE 3: BALANCED SELECTION (Based on task characteristics)
    # ========================================================================
    
    # Research and analysis tasks need multiple perspectives
    if task_type in ["research_analysis", "comparison", "explanation"]:
        if num_models >= 3 and accuracy_level >= 3:
            logger.info("Strategy: Research task, 3+ models -> expert_panel")
            return "expert_panel"
        elif num_models >= 2:
            logger.info("Strategy: Research task, 2+ models -> quality_weighted_fusion")
            return "quality_weighted_fusion"
    
    # Creative writing benefits from multiple perspectives and synthesis
    if task_type == "creative_writing":
        if creativity_priority >= 70 and num_models >= 2:
            logger.info("Strategy: Creative task, high creativity -> expert_panel")
            return "expert_panel"  # More diverse outputs
        logger.info("Strategy: Creative task -> quality_weighted_fusion")
        return "quality_weighted_fusion"
    
    # Planning tasks need structured approach
    if task_type == "planning":
        if accuracy_level >= 4:
            logger.info("Strategy: Planning task, high accuracy -> challenge_and_refine")
            return "challenge_and_refine"
        logger.info("Strategy: Planning task -> best_of_n")
        return "best_of_n"
    
    # ========================================================================
    # PHASE 4: ACCURACY-DRIVEN SELECTION
    # ========================================================================
    
    # Maximum accuracy requested
    if accuracy_level >= 5 or accuracy_priority >= 90:
        if num_models >= 2:
            logger.info("Strategy: Maximum accuracy -> challenge_and_refine")
            return "challenge_and_refine"
        logger.info("Strategy: Maximum accuracy, 1 model -> single_best (with verification)")
        return "single_best"  # Will use internal verification
    
    # High accuracy
    if accuracy_level >= 4 or accuracy_priority >= 75:
        if num_models >= 3:
            logger.info("Strategy: High accuracy, 3+ models -> expert_panel")
            return "expert_panel"
        elif num_models >= 2:
            logger.info("Strategy: High accuracy, 2+ models -> best_of_n")
            return "best_of_n"
    
    # Medium accuracy
    if accuracy_level >= 3:
        if num_models >= 2:
            logger.info("Strategy: Medium accuracy, 2+ models -> quality_weighted_fusion")
            return "quality_weighted_fusion"
    
    # ========================================================================
    # PHASE 5: COMPLEXITY-DRIVEN FALLBACK
    # ========================================================================
    
    # Complex or research complexity
    if complexity in ["complex", "research"]:
        if num_models >= 2:
            logger.info("Strategy: Complex task -> quality_weighted_fusion")
            return "quality_weighted_fusion"
    
    # Moderate complexity
    if complexity == "moderate" and num_models >= 2:
        logger.info("Strategy: Moderate complexity -> parallel_race")
        return "parallel_race"
    
    # ========================================================================
    # PHASE 6: DEFAULT
    # ========================================================================
    if num_models >= 2:
        logger.info("Strategy: Default multi-model -> quality_weighted_fusion")
        return "quality_weighted_fusion"
    
    logger.info("Strategy: Default single model -> single_best")
    return "single_best"


def _map_reasoning_mode(mode: ReasoningMode) -> int:
    """Map ReasoningMode enum to reasoning depth integer."""
    mapping = {
        ReasoningMode.fast: 1,
        ReasoningMode.standard: 2,
        ReasoningMode.deep: 3,
    }
    return mapping.get(mode, 2)


def _map_model_to_provider(model_id: str, available_providers: list) -> str:
    """Map a selected model ID to actual OpenRouter model ID.
    
    IMPORTANT: This function should preserve the exact model ID when it's
    already a valid OpenRouter model ID (e.g., "openai/gpt-5").
    
    Latest models (VERIFIED December 2025 from OpenRouter):
    - OpenAI: gpt-5, gpt-4o, o3, o1-pro
    - Anthropic: claude-opus-4, claude-sonnet-4
    - Google: gemini-3-pro-preview, gemini-2.5-pro, gemini-2.5-flash
    - xAI: grok-4
    - DeepSeek: deepseek-v3.2, deepseek-r1-0528
    """
    # If it's already a full OpenRouter model ID (contains "/"), return as-is
    if "/" in model_id:
        return model_id
    
    model_lower = model_id.lower()
    
    # OpenAI models
    if "gpt-5" in model_lower:
        return OPENROUTER_GPT_5  # openai/gpt-5
    elif "o3" in model_lower:
        return OPENROUTER_O3  # openai/o3
    elif "o1" in model_lower:
        return OPENROUTER_O1  # openai/o1-pro
    elif "gpt-4o-mini" in model_lower:
        return FALLBACK_GPT_4O_MINI
    elif "gpt-4" in model_lower:
        return OPENROUTER_GPT_4O  # openai/gpt-4o
    
    # Anthropic Claude models
    elif "claude" in model_lower:
        if "opus" in model_lower:
            return OPENROUTER_CLAUDE_OPUS_4  # anthropic/claude-opus-4
        elif "sonnet-4" in model_lower or "sonnet" in model_lower:
            return OPENROUTER_CLAUDE_SONNET_4  # anthropic/claude-sonnet-4
        elif "haiku" in model_lower:
            return FALLBACK_CLAUDE_3_HAIKU
        return OPENROUTER_CLAUDE_SONNET_4  # default to Sonnet 4
    
    # Google Gemini models
    elif "gemini" in model_lower:
        if "3" in model_lower and "pro" in model_lower:
            return OPENROUTER_GEMINI_3_PRO  # google/gemini-3-pro-preview
        elif "flash" in model_lower:
            return OPENROUTER_GEMINI_2_5_FLASH
        return OPENROUTER_GEMINI_2_PRO  # google/gemini-2.5-pro
    
    # xAI Grok models
    elif "grok" in model_lower:
        return OPENROUTER_GROK_4  # x-ai/grok-4
    
    # DeepSeek models
    elif "deepseek" in model_lower:
        if "r1" in model_lower:
            return OPENROUTER_DEEPSEEK_R1  # deepseek/deepseek-r1-0528
        return OPENROUTER_DEEPSEEK  # deepseek/deepseek-v3.2
    
    # Meta Llama models
    elif "llama" in model_lower:
        if "local" in available_providers:
            return "local"
        return OPENROUTER_LLAMA_4  # meta-llama/llama-4-maverick
    
    # Mistral models
    elif "mistral" in model_lower:
        return OPENROUTER_MISTRAL_LARGE  # mistralai/mistral-large-2512
    
    # Direct model name match
    elif model_id in available_providers:
        return model_id
    
    else:
        # Default to GPT-5 (best overall)
        return OPENROUTER_GPT_5


def _get_display_name(model_id: str) -> str:
    """Get a user-friendly display name for a model."""
    display_names = {
        # Latest models (December 2025)
        OPENROUTER_GPT_5: "GPT-5",
        OPENROUTER_CLAUDE_OPUS_4: "Claude Opus 4",
        OPENROUTER_CLAUDE_SONNET_4: "Claude Sonnet 4",
        OPENROUTER_GEMINI_3_PRO: "Gemini 3 Pro",
        OPENROUTER_GEMINI_2_PRO: "Gemini 2.5 Pro",
        OPENROUTER_O3: "o3",
        OPENROUTER_O1: "o1 Pro",
        OPENROUTER_GROK_4: "Grok-4",
        OPENROUTER_DEEPSEEK: "DeepSeek V3.2",
        OPENROUTER_DEEPSEEK_R1: "DeepSeek R1",
        OPENROUTER_LLAMA_4: "Llama 4 Maverick",
        OPENROUTER_MISTRAL_LARGE: "Mistral Large",
        OPENROUTER_GEMINI_2_5_FLASH: "Gemini 2.5 Flash",
        # Legacy fallbacks
        OPENROUTER_GPT_4O: "GPT-4o",
        FALLBACK_GPT_4O_MINI: "GPT-4o Mini",
        FALLBACK_CLAUDE_3_5: "Claude 3.5 Sonnet",
        FALLBACK_CLAUDE_3_HAIKU: "Claude 3.5 Haiku",
    }
    return display_names.get(model_id, model_id)


def _auto_select_reasoning_method(prompt: str, domain_pack: str) -> RouterReasoningMethod | None:
    """Heuristic selection of reasoning strategy when none provided."""
    plower = prompt.lower()
    math_signals = any(tok in plower for tok in ["solve", "equation", "integral", "derivative", "sum", "product"]) or any(ch in plower for ch in ["=", "+", "-", "*", "/"])
    code_signals = any(tok in plower for tok in ["code", "function", "class", "bug", "error", "stack trace", "compile", "python", "javascript", "typescript", "java", "c++"])
    factual_signals = any(plower.startswith(w) for w in ["who", "what", "when", "where", "which", "name", "list", "give me", "provide", "cite"])
    planning_signals = any(tok in plower for tok in ["plan", "roadmap", "strategy", "architecture", "design", "options", "tradeoff", "trade-off", "pros and cons", "compare"])
    ambiguous = len(prompt.split()) < 6
    try:
        if code_signals or math_signals:
            return RouterReasoningMethod.plan_and_solve
        if planning_signals:
            return RouterReasoningMethod.hierarchical_decomposition
        if factual_signals:
            return RouterReasoningMethod.self_consistency
        if ambiguous:
            return RouterReasoningMethod.tree_of_thought
        if domain_pack == "coding":
            return RouterReasoningMethod.plan_and_solve
        return RouterReasoningMethod.chain_of_thought
    except Exception:
        return None


async def run_orchestration(request: ChatRequest) -> ChatResponse:
    """
    Run orchestration with ChatRequest and return ChatResponse.
    
    This adapter builds an orchestration_config from the ChatRequest,
    uses user-selected models if provided, and calls the orchestrator.
    """
    start_time = time.perf_counter()
    
    try:
        # Profile defaults (format/tone/show_confidence)
        user_profile = None
        try:
            user_profile = get_profile(request.metadata.user_id if request.metadata else None)
        except Exception:
            user_profile = None

        # Determine reasoning method (explicit > auto > legacy mode)
        if request.reasoning_method:
            reasoning_method = RouterReasoningMethod(request.reasoning_method.value)
        else:
            # Heuristic auto-selection based on query/task
            reasoning_method = _auto_select_reasoning_method(
                request.prompt,
                domain_pack=request.domain_pack.value,
            )
            # Fallback to legacy mode mapping
            if reasoning_method is None:
                reasoning_method = map_reasoning_mode_to_method(request.reasoning_mode.value)
        
        logger.info(
            "Using reasoning method: %s (from mode: %s)",
            reasoning_method.value,
            request.reasoning_mode.value,
        )
        
        # Get available providers from orchestrator
        available_providers = list(_orchestrator.providers.keys())
        
        # Use user-selected models if provided, otherwise auto-select
        if request.models and len(request.models) > 0:
            logger.info("User selected models: %s", request.models)
            
            # Map user-selected model names to actual provider models
            actual_models = []
            user_model_names = []  # Track what the user selected for response
            
            for model_id in request.models:
                mapped_model = _map_model_to_provider(model_id, available_providers)
                if mapped_model not in actual_models:  # Avoid duplicates
                    actual_models.append(mapped_model)
                    user_model_names.append(model_id)
            
            logger.info(
                "Mapped user models to providers: %s -> %s",
                request.models,
                actual_models,
            )
        else:
            # Auto-select models with intelligent routing
            # Step 1: Check if query requires advanced reasoning
            needs_reasoning_model = False
            reasoning_type = None
            reasoning_detector = _get_reasoning_detector()
            if reasoning_detector:
                try:
                    reasoning_signals = reasoning_detector.detect_reasoning_signals(request.prompt)
                    needs_reasoning_model = reasoning_detector.needs_reasoning_model(reasoning_signals)
                    if needs_reasoning_model:
                        reasoning_type = reasoning_signals.primary_type
                        logger.info(
                            "Reasoning detection: needs_reasoning=%s, type=%s, confidence=%.2f",
                            needs_reasoning_model,
                            reasoning_type.value if reasoning_type else "none",
                            reasoning_signals.confidence,
                        )
                except Exception as e:
                    logger.debug("Reasoning detection failed: %s", e)
            
            # Step 2: Use cascade routing for cost optimization
            cascade_router = _get_cascade_router()
            if cascade_router:
                try:
                    cascade_result = cascade_router.route_query_cascade(request.prompt)
                    logger.info(
                        "Cascade routing: complexity=%s, tier=%s, recommended_models=%s",
                        cascade_result.complexity.value,
                        cascade_result.tier.value,
                        cascade_result.models[:3],
                    )
                except Exception as e:
                    logger.debug("Cascade routing failed: %s", e)
            
            # Step 3: Select models based on reasoning method (fallback)
            selected_models = get_models_for_reasoning_method(
                reasoning_method,
                available_models=available_providers,
            )
            
            # Step 4: If reasoning model needed, prioritize reasoning-capable models
            if needs_reasoning_model:
                # Prioritize o1, o3-mini, or other reasoning models
                reasoning_models = ["gpt-4o", "claude-sonnet-4-20250514"]  # Best reasoning
                for rm in reasoning_models:
                    if rm in available_providers and rm not in selected_models:
                        selected_models.insert(0, rm)
                logger.info("Prioritized reasoning models: %s", selected_models[:3])
            
            # =========================================================================
            # Step 5: CATEGORY-SPECIFIC ROUTING (January 2026 Improvements)
            # Optimize for: Long Context, Multilingual, Speed, Math, RAG
            # =========================================================================
            category_override = False
            
            # 5a: Long Context Routing (#10 -> #3)
            prompt_tokens = estimate_token_count(request.prompt)
            if is_long_context_query(request.prompt, threshold=30000):
                long_context_model = get_long_context_model(prompt_tokens, available_providers)
                if long_context_model:
                    selected_models = [long_context_model] + [m for m in selected_models if m != long_context_model]
                    category_override = True
                    logger.info("Long context routing: %d tokens -> %s", prompt_tokens, long_context_model)
            
            # 5b: Multilingual Routing (#6 -> #3)
            elif is_multilingual_query(request.prompt):
                detected_lang = detect_language(request.prompt)
                multilingual_models = get_multilingual_models(detected_lang, num_models=2)
                selected_models = multilingual_models + [m for m in selected_models if m not in multilingual_models]
                category_override = True
                logger.info("Multilingual routing: lang=%s -> %s", detected_lang, multilingual_models)
            
            # 5c: Speed-Critical Routing (#9 -> #3)
            elif is_speed_critical(metadata_dict if 'metadata_dict' in dir() else None):
                speed_models = get_speed_optimized_models(num_models=1)
                selected_models = speed_models
                category_override = True
                logger.info("Speed routing -> %s", speed_models)
            
            # 5d: Math Problem Routing - ELITE MODE for top position
            # Use PREMIUM models (o3, GPT-5.2, Claude Opus) for math
            elif _detect_task_type(request.prompt) == "math_problem":
                # Phase 18: Use elite models for math to achieve #1 ranking
                # Get accuracy_level from request (defined later in orchestration_config)
                early_accuracy_level = getattr(request.orchestration, 'accuracy_level', 3)
                if ELITE_ORCHESTRATION_AVAILABLE and early_accuracy_level >= 3:
                    # Use the actual top math models
                    selected_models = ELITE_MODELS.get("math", [])[:3]
                    logger.info("ELITE Math routing (Phase 18) -> %s", selected_models)
                else:
                    math_models = get_math_specialist_models(num_models=2)
                    selected_models = math_models + [m for m in selected_models if m not in math_models]
                    logger.info("Math routing -> %s", math_models)
                category_override = True
            
            # 5e: RAG Routing - ELITE MODE for top position
            # Use PREMIUM models (GPT-5.2, Claude Opus) for RAG
            elif getattr(request.orchestration, 'enable_rag', False) or "search" in request.prompt.lower() or "find information" in request.prompt.lower():
                # Phase 18: Use elite models for RAG to achieve #1 ranking
                early_accuracy_level = getattr(request.orchestration, 'accuracy_level', 3)
                if ELITE_ORCHESTRATION_AVAILABLE and early_accuracy_level >= 3:
                    selected_models = ELITE_MODELS.get("rag", [])[:2]
                    logger.info("ELITE RAG routing (Phase 18) -> %s", selected_models)
                else:
                    rag_models = get_rag_optimized_models(num_models=2)
                    selected_models = rag_models + [m for m in selected_models if m not in rag_models]
                    logger.info("RAG routing -> %s", rag_models)
                category_override = True
            
            # 5f: Reasoning Routing - ELITE MODE for top position
            elif _detect_task_type(request.prompt) in ("reasoning", "multi_step"):
                early_accuracy_level = getattr(request.orchestration, 'accuracy_level', 3)
                if ELITE_ORCHESTRATION_AVAILABLE and early_accuracy_level >= 3:
                    selected_models = ELITE_MODELS.get("reasoning", [])[:3]
                    logger.info("ELITE Reasoning routing (Phase 18) -> %s", selected_models)
                else:
                    selected_models = [FALLBACK_O3, FALLBACK_GPT_5] + selected_models
                category_override = True
            
            # Map to actual model names
            actual_models = []
            user_model_names = []
            for model_id in selected_models:
                mapped = _map_model_to_provider(model_id, available_providers)
                if mapped not in actual_models:
                    actual_models.append(mapped)
                    user_model_names.append(model_id)
        
        if not actual_models:
            actual_models = ["gpt-4o-mini"]
            user_model_names = ["GPT-4o Mini"]
        
        logger.info(
            "Final models for orchestration: %s (display: %s)",
            actual_models,
            user_model_names,
        )
        
        # Extract criteria settings from metadata if provided
        criteria_settings = None
        metadata_dict: Dict[str, Any] = {}  # Initialize metadata_dict
        
        if request.metadata:
            # Get dict representation of metadata
            if hasattr(request.metadata, 'model_dump'):
                metadata_dict = request.metadata.model_dump(exclude_none=True)
            elif hasattr(request.metadata, 'dict'):
                metadata_dict = request.metadata.dict(exclude_none=True)
            
            # Check for criteria object directly on metadata (new format)
            if hasattr(request.metadata, 'criteria') and request.metadata.criteria:
                criteria_obj = request.metadata.criteria
                if hasattr(criteria_obj, 'model_dump'):
                    criteria_settings = criteria_obj.model_dump()
                elif hasattr(criteria_obj, 'dict'):
                    criteria_settings = criteria_obj.dict()
                elif isinstance(criteria_obj, dict):
                    criteria_settings = criteria_obj
            # Fallback: check dict representation
            elif 'criteria' in metadata_dict:
                criteria_settings = metadata_dict['criteria']
        
        # =====================================================================
        # PR5: Extract budget constraints from request
        # =====================================================================
        max_cost_usd = getattr(request.orchestration, 'max_cost_usd', None)
        prefer_cheaper = getattr(request.orchestration, 'prefer_cheaper_models', False)
        budget_constraints = None
        
        if BUDGET_ROUTING_AVAILABLE and (max_cost_usd is not None or prefer_cheaper):
            budget_constraints = BudgetConstraints(
                max_cost_usd=max_cost_usd or 1.0,
                prefer_cheaper=prefer_cheaper,
                estimated_tokens=getattr(request.orchestration, 'max_tokens', 2000) or 2000,
            )
            logger.info(
                "PR5: Budget constraints active: max_cost=$%.2f, prefer_cheaper=%s",
                budget_constraints.max_cost_usd,
                budget_constraints.prefer_cheaper,
            )
        
        # Build orchestration_config dict
        orchestration_config: Dict[str, Any] = {
            "reasoning_depth": _map_reasoning_mode(request.reasoning_mode),
            "reasoning_method": reasoning_method.value,
            "domain_pack": request.domain_pack.value,
            "agent_mode": request.agent_mode.value,
            "use_prompt_optimization": request.tuning.prompt_optimization,
            "use_output_validation": request.tuning.output_validation,
            "use_answer_structure": request.tuning.answer_structure,
            "learn_from_chat": request.tuning.learn_from_chat,
            "metadata": metadata_dict,
            "history": request.history or [],
            # Orchestration Studio settings
            "accuracy_level": request.orchestration.accuracy_level,
            # engines_mode: "automatic" = backend selects best engines, "manual" = use explicit settings
            "engines_mode": getattr(request.orchestration, 'engines_mode', 'automatic'),
            "use_hrm": request.orchestration.enable_hrm,
            "use_prompt_diffusion": request.orchestration.enable_prompt_diffusion,
            "use_deep_consensus": request.orchestration.enable_deep_consensus,
            "use_adaptive_routing": request.orchestration.enable_adaptive_ensemble,
            # PR5: Budget constraints
            "max_cost_usd": max_cost_usd,
            "budget_constraints": budget_constraints,
        }
        
        # Add criteria settings if provided (for dynamic criteria equaliser)
        if criteria_settings:
            orchestration_config["criteria"] = criteria_settings
            logger.info(
                "Using criteria settings: accuracy=%d%%, speed=%d%%, creativity=%d%%",
                criteria_settings.get("accuracy", 70),
                criteria_settings.get("speed", 70),
                criteria_settings.get("creativity", 50),
            )
        
        # ========================================================================
        # STEP -1: SECURITY - Injection check on RAW user prompt (BEFORE enhancement)
        # ========================================================================
        # CRITICAL: Check injection on the ORIGINAL user prompt, not the enhanced one.
        # The enhanced prompt contains system instructions (e.g., "act as a planner")
        # which would falsely trigger injection detection.
        try:
            from ..orchestration.stage3_upgrades import create_injection_detector, STAGE3_AVAILABLE as _S3_AVAILABLE
            if _S3_AVAILABLE:
                _early_injection_detector = create_injection_detector(block_threshold="medium")
                injection_check = _early_injection_detector.check(request.prompt)
                if injection_check.should_block:
                    logger.warning(
                        "Prompt injection BLOCKED (early check): threat=%s",
                        injection_check.threat_level
                    )
                    return ChatResponse(
                        message=_early_injection_detector.get_safe_refusal(),
                        models_used=["security_filter"],
                        reasoning_mode=request.reasoning_mode,
                        reasoning_method=request.reasoning_method,
                        domain_pack=request.domain_pack,
                        agent_mode=request.agent_mode,
                        used_tuning=request.tuning,
                        metadata=request.metadata,
                        tokens_used="0",
                        latency_ms=int((time.perf_counter() - start_time) * 1000),
                        agent_traces=[],
                        extra={"blocked": True, "reason": "injection_detected"},
                    )
        except ImportError:
            pass  # Stage 3 not available, skip early injection check
        
        # ========================================================================
        # STEP 0: RAG AUGMENTATION (If enabled)
        # ========================================================================
        enable_rag = getattr(request.orchestration, 'enable_vector_rag', False)
        user_id = metadata_dict.get('user_id')
        project_id = metadata_dict.get('project_id')
        org_id = metadata_dict.get('org_id')
        
        # Fast reuse: return cached high-confidence answer if nearly identical
        if KNOWLEDGE_BASE_AVAILABLE and os.getenv("ENABLE_FAST_REUSE", "0").lower() in {"1", "true", "yes"}:
            kb = _get_knowledge_base()
            if kb:
                try:
                    cached = await kb.retrieve_context(
                        query=request.prompt,
                        top_k=1,
                        record_types=[RecordType.FINAL_ANSWER, RecordType.DOMAIN_KNOWLEDGE],
                        domain=request.domain_pack.value,
                        user_id=user_id,
                        project_id=project_id,
                        org_id=org_id,
                        min_quality_score=0.9,
                        rerank=True,
                    )
                    if cached and cached[0].score >= 0.92:
                        meta_models = cached[0].metadata.get("models_used", "")
                        cached_models = meta_models.split(",") if isinstance(meta_models, str) else []
                        logger.info(
                            "Fast reuse hit: returning cached answer (score=%.2f, record=%s)",
                            cached[0].score,
                            cached[0].id,
                        )
                        return ChatResponse(
                            message=cached[0].content,
                            models_used=cached_models or ["knowledge_base_cache"],
                            reasoning_mode=request.reasoning_mode,
                            reasoning_method=request.reasoning_method,
                            domain_pack=request.domain_pack,
                            agent_mode=request.agent_mode,
                            used_tuning=request.tuning,
                            metadata=request.metadata,
                            tokens_used="cached",
                            latency_ms=int((time.perf_counter() - start_time) * 1000),
                            agent_traces=[],
                            extra={"source": "knowledge_base_cache", "record_id": cached[0].id},
                        )
                except Exception as e:
                    logger.debug("Fast reuse check failed: %s", e)
        
        if enable_rag and KNOWLEDGE_BASE_AVAILABLE:
            try:
                augmented_prompt = await _augment_with_rag(
                    prompt=request.prompt,
                    domain=request.domain_pack.value,
                    user_id=user_id,
                    project_id=project_id,
                    org_id=org_id,
                )
                original_prompt = request.prompt
                # Note: We don't modify request.prompt directly, use augmented_prompt in the pipeline
            except Exception as e:
                logger.warning(f"RAG augmentation failed: {e}")
                augmented_prompt = request.prompt
                original_prompt = request.prompt
        else:
            augmented_prompt = request.prompt
            original_prompt = request.prompt
        
        # ========================================================================
        # STEP 1: PROMPTOPS PREPROCESSING (Always On)
        # ========================================================================
        base_prompt = augmented_prompt  # Use RAG-augmented prompt if available
        prompt_spec: Optional[PromptSpecification] = None
        detected_task_type = "general"
        detected_complexity = "moderate"
        is_strict_format = False
        requested_output_format: Optional[str] = None
        
        if PROMPTOPS_AVAILABLE:
            try:
                prompt_ops = PromptOps(providers=_orchestrator.providers)
                prompt_spec = await prompt_ops.process(
                    request.prompt,
                    domain_hint=request.domain_pack.value,
                )
                
                # Use PromptOps analysis
                base_prompt = prompt_spec.refined_query
                detected_task_type = prompt_spec.analysis.task_type.value
                detected_complexity = prompt_spec.analysis.complexity.value
                requested_output_format = prompt_spec.analysis.output_format
                
                logger.info(
                    "PromptOps: task=%s, complexity=%s, tools=%s, confidence=%.2f",
                    detected_task_type,
                    detected_complexity,
                    prompt_spec.analysis.tool_hints,
                    prompt_spec.confidence,
                )
                
                # Log any ambiguities or safety flags
                if prompt_spec.analysis.ambiguities:
                    logger.info("PromptOps detected ambiguities: %s", prompt_spec.analysis.ambiguities[:3])
                if prompt_spec.safety_flags:
                    logger.warning("PromptOps safety flags: %s", prompt_spec.safety_flags)
                    
            except Exception as e:
                logger.warning("PromptOps failed, using raw prompt: %s", e)
        
        # ========================================================================
        # STEP 1.1: AUTO-ENABLE HRM FOR COMPLEX QUERIES
        # ========================================================================
        # Auto-activate Hierarchical Role Management (HRM) when PromptOps determines
        # the query is complex or research-level (requires_hrm=True).
        # ========================================================================
        # STEP 1.21: AUTOMATIC ENGINE SELECTION
        # ========================================================================
        # When engines_mode="automatic", intelligently select engines based on:
        # - Query complexity (simple/moderate/complex/expert)
        # - Task type (coding, math, reasoning, etc.)
        # - Accuracy level setting
        #
        engines_mode = orchestration_config.get("engines_mode", "automatic")
        if engines_mode == "automatic":
            accuracy_lvl = orchestration_config.get("accuracy_level", 3)
            
            # Reset all manual engine settings - we'll enable what's needed
            orchestration_config["use_hrm"] = False
            orchestration_config["use_prompt_diffusion"] = False
            orchestration_config["use_deep_consensus"] = False
            orchestration_config["use_adaptive_routing"] = False
            
            # Determine which engines to enable based on complexity and task
            if detected_complexity in ("complex", "expert"):
                # Complex queries benefit from HRM (hierarchical decomposition)
                orchestration_config["use_hrm"] = True
                # High accuracy also gets deep consensus
                if accuracy_lvl >= 4:
                    orchestration_config["use_deep_consensus"] = True
                logger.info(
                    "Auto-engines (complex): HRM=%s, DeepConsensus=%s",
                    True, accuracy_lvl >= 4
                )
            elif detected_complexity == "moderate":
                # Moderate queries: use adaptive routing for model selection
                orchestration_config["use_adaptive_routing"] = True
                # Higher accuracy gets prompt diffusion for refinement
                if accuracy_lvl >= 3:
                    orchestration_config["use_prompt_diffusion"] = True
                logger.info(
                    "Auto-engines (moderate): AdaptiveRouting=%s, PromptDiffusion=%s",
                    True, accuracy_lvl >= 3
                )
            else:
                # Simple queries: minimal overhead, just adaptive routing if accuracy > 2
                if accuracy_lvl >= 3:
                    orchestration_config["use_adaptive_routing"] = True
                logger.info(
                    "Auto-engines (simple): AdaptiveRouting=%s",
                    accuracy_lvl >= 3
                )
            
            # Task-specific engine overrides
            if detected_task_type in ("coding", "code_generation", "debugging"):
                # Coding benefits from prompt diffusion (iterative refinement)
                orchestration_config["use_prompt_diffusion"] = True
            elif detected_task_type in ("reasoning", "math", "science_research"):
                # Reasoning/math benefits from deep consensus
                if accuracy_lvl >= 3:
                    orchestration_config["use_deep_consensus"] = True
            elif detected_task_type in ("creative_writing", "marketing"):
                # Creative tasks benefit from adaptive ensemble (diverse outputs)
                orchestration_config["use_adaptive_routing"] = True
            
            logger.info(
                "Automatic engine selection: HRM=%s, PromptDiffusion=%s, DeepConsensus=%s, AdaptiveEnsemble=%s",
                orchestration_config.get("use_hrm"),
                orchestration_config.get("use_prompt_diffusion"),
                orchestration_config.get("use_deep_consensus"),
                orchestration_config.get("use_adaptive_routing"),
            )
        else:
            logger.info("Manual engine mode: using explicit settings from request")
        
        # ========================================================================
        # STEP 1.22: AUTO-ENABLE HRM FOR COMPLEX QUERIES (Legacy + Override)
        # ========================================================================
        # This allows complex queries to be automatically decomposed into sub-steps
        # without requiring manual enable_hrm flag in the request.
        #
        # NOTE: When HRM is auto-enabled, the orchestrator will execute the hierarchical
        # plan INSTEAD of the standard multi-model ensemble strategies. This is intentional
        # for complex queries that benefit from step-by-step decomposition.
        #
        # Edge case: If a query is labeled complex but could be handled by a single model,
        # HRM may still decompose it. We trust PromptOps for now; monitor for over-triggering.
        if prompt_spec and hasattr(prompt_spec, 'requires_hrm') and prompt_spec.requires_hrm:
            if not orchestration_config.get("use_hrm", False):
                # Auto-enable HRM for complex/research queries
                orchestration_config["use_hrm"] = True
                logger.info(
                    "Auto-enabled HRM for complex query (complexity=%s, task=%s)",
                    detected_complexity,
                    detected_task_type,
                )
        
        # ========================================================================
        # STEP 1.25: CLARIFICATION CHECK (Optional - adds questions to extra)
        # ========================================================================
        clarification_questions = []
        
        # FIX 1.2: Skip clarification for clear factoid queries
        def _should_skip_clarification(query: str) -> bool:
            """Skip clarification for clear factual questions."""
            import re as re_local
            query_lower = query.lower().strip()
            
            # Always skip for well-formed questions with good length
            if query_lower.endswith('?') and len(query.split()) >= 5:
                return True
            
            # Factoid patterns that NEVER need clarification
            NEVER_CLARIFY_PATTERNS = [
                r'\b(who|what|when|where)\s+(discovered|invented|wrote|created|founded|is|are|was|were)\b',
                r'\b(capital|largest|smallest|highest|lowest|first|last)\b.*\b(of|in)\b',
                r'\b(chemical symbol|boiling point|speed of light|melting point)\b',
                r'\bwhat year\b',
                r'\bhow (tall|old|far|long|much|many)\b',
            ]
            for pattern in NEVER_CLARIFY_PATTERNS:
                if re_local.search(pattern, query_lower):
                    logger.debug("FIX 1.2: Skipping clarification for factoid query")
                    return True
            return False
        
        skip_clarification = _should_skip_clarification(request.prompt)
        
        if CLARIFICATION_AVAILABLE and prompt_spec and prompt_spec.analysis.ambiguities and not skip_clarification:
            try:
                clarification_mgr = ClarificationManager()
                # Check if prompt is ambiguous enough to warrant clarification
                needs_clarification = await clarification_mgr.analyze_query(request.prompt)
                
                if needs_clarification.status != ClarificationStatus.NOT_NEEDED:
                    # Generate clarifying questions
                    questions = await clarification_mgr.generate_questions(
                        request.prompt,
                        max_query_questions=3,
                        max_preference_questions=3,
                    )
                    
                    if questions:
                        clarification_questions = [
                            {
                                "id": q.id,
                                "question": q.question,
                                "category": q.category,
                                "options": q.options,
                                "required": q.required,
                            }
                            for q in questions
                        ]
                        logger.info(
                            "Clarification: Generated %d questions for ambiguous query",
                            len(clarification_questions)
                        )
            except Exception as e:
                logger.warning("Clarification check failed: %s", e)
        
        # ========================================================================
        # STEP 1.4: EXPLICIT HISTORY CONTEXT INJECTION (Multi-turn reliability)
        # ========================================================================
        if request.history:
            try:
                history_snippets = []
                for msg in request.history[-6:]:  # last 6 turns for context
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    content = content[:400]  # cap length per turn
                    prefix = "User" if role == "user" else "Assistant"
                    history_snippets.append(f"- {prefix}: {content}")
                
                if history_snippets:
                    history_block = "\n".join(history_snippets)
                    base_prompt = (
                        f"{base_prompt}\n\n"
                        "[CONTEXT FROM PREVIOUS MESSAGES]\n"
                        f"{history_block}\n"
                        "You MUST use this context and not contradict it. "
                        "Do not claim the preferences are missing; they are provided above. "
                        "Do not invent new preferences; rely ONLY on the context above."
                    )
            except Exception as e:
                logger.warning("Failed to inject history context: %s", e)
        
        # ========================================================================
        # STEP 1.45: OUTPUT FORMAT ENFORCEMENT (JSON-only)
        # ========================================================================
        if requested_output_format and requested_output_format.startswith("json"):
            if requested_output_format.endswith("_strict"):
                is_strict_format = True
            base_prompt = (
                f"{base_prompt}\n\n"
                "[OUTPUT FORMAT]\n"
                "Return ONLY a single JSON object with the required keys. "
                "Do not include any prose, explanations, or markdown fences. "
                "Output must be valid JSON."
            )
        
        # ========================================================================
        # STEP 1.5: TOOL BROKER - Automatic Tool Detection and Execution
        # ========================================================================
        tool_context = ""
        tool_results_info: Dict[str, Any] = {"used": False}
        
        # Check if live research is explicitly enabled (from frontend temporal detection)
        force_web_search = getattr(request.orchestration, 'enable_live_research', False)
        
        # ========================================================================
        # FIX 5.1: Pre-check for math queries BEFORE gating condition
        # This ensures calculator is invoked even when prompt_spec.requires_tools is False
        # ========================================================================
        force_calculator = False
        if TOOL_BROKER_AVAILABLE:
            try:
                from ..orchestration.tool_broker import should_use_calculator
                force_calculator = should_use_calculator(base_prompt)
                if force_calculator:
                    logger.info("FIX 5.1: Math query detected - forcing tool broker entry")
            except Exception as e:
                logger.debug("Could not check should_use_calculator: %s", e)
        
        if TOOL_BROKER_AVAILABLE and (prompt_spec is None or prompt_spec.analysis.requires_tools or force_web_search or force_calculator):
            try:
                broker = get_tool_broker()
                
                # ================================================================
                # FIX 1.1: Force calculator for math queries BEFORE standard analysis
                # ================================================================
                from ..orchestration.tool_broker import should_use_calculator, extract_math_expression, ToolType as TT, ToolPriority, ToolRequest
                if should_use_calculator(base_prompt):
                    logger.info("FIX 1.1: Forcing calculator for detected math query")
                    try:
                        # Extract the math expression from natural language
                        math_expr = extract_math_expression(base_prompt)
                        logger.info("FIX 1.1: Extracted math expression: %s", math_expr)
                        
                        # Create a calculator request with the extracted expression
                        calc_request = ToolRequest(
                            tool_type=TT.CALCULATOR,
                            query=math_expr,  # Use extracted expression, not full query
                            purpose="Mathematical calculation (forced)",
                            priority=ToolPriority.CRITICAL,
                        )
                        calc_results = await broker.execute_tools([calc_request], parallel=False)
                        calc_result = calc_results.get(TT.CALCULATOR)
                        
                        if calc_result and calc_result.success and calc_result.data:
                            calc_data = calc_result.data
                            result_value = calc_data.get('result', 'N/A')
                            expression = calc_data.get('expression', base_prompt)
                            calc_context = (
                                f"\n\n[CALCULATOR VERIFIED RESULT]\n"
                                f"Expression: {expression}\n"
                                f"Result: {result_value}\n"
                                f"[END CALCULATOR RESULT]\n\n"
                                f"IMPORTANT: Use the calculator result above as the authoritative answer. "
                                f"Do NOT recalculate - the result is verified.\n\n"
                            )
                            base_prompt = calc_context + base_prompt
                            tool_context = calc_context
                            tool_results_info = {
                                "used": True,
                                "tools": ["calculator"],
                                "success_count": 1,
                                "reasoning": "Math query - calculator forced",
                                "calculator_result": result_value,  # Store for validation
                                "calculator_expression": expression,
                            }
                            logger.info("Calculator result: %s = %s", expression, result_value)
                    except Exception as calc_e:
                        logger.warning("Forced calculator failed: %s", calc_e)
                
                tool_analysis = broker.analyze_tool_needs(base_prompt)
                
                # Force web search if enable_live_research is set
                if force_web_search and not tool_analysis.requires_tools:
                    logger.info("Forcing web search due to enable_live_research=True")
                    from ..orchestration.tool_broker import ToolRequest, ToolType as TT, ToolPriority
                    # Enhance query for recency and add recency params
                    import datetime
                    current_date = datetime.datetime.now().strftime("%B %Y")  # e.g., "December 2024"
                    enhanced_query = f"{base_prompt} {current_date} latest"
                    tool_analysis.tool_requests.append(ToolRequest(
                        tool_type=TT.WEB_SEARCH,
                        query=enhanced_query,
                        purpose="Real-time web search for current information",
                        priority=ToolPriority.HIGH,
                        metadata={"days": 30, "topic": "news"},  # Last 30 days, news topic
                    ))
                    tool_analysis.requires_tools = True
                
                # For any temporal query, ensure recency params are set
                if force_web_search:
                    for req in tool_analysis.tool_requests:
                        if req.tool_type.value == "web_search" and not req.metadata.get("days"):
                            req.metadata["days"] = 30
                            req.metadata["topic"] = "news"
                
                if tool_analysis.requires_tools:
                    logger.info(
                        "Tool Broker: Detected need for tools: %s",
                        [r.tool_type.value for r in tool_analysis.tool_requests],
                    )
                    
                    # Execute tools in parallel
                    tool_results = await broker.execute_tools(
                        tool_analysis.tool_requests,
                        parallel=True,
                    )
                    
                    # Format results for model context
                    tool_context = broker.format_tool_results(tool_results)
                    
                    # Track tool usage for response metadata
                    tool_results_info = {
                        "used": True,
                        "tools": [t.value for t in tool_results.keys()],
                        "success_count": sum(1 for r in tool_results.values() if r.success),
                        "reasoning": tool_analysis.reasoning,
                    }
                    
                    # Append tool context to the prompt with explicit instructions
                    if tool_context:
                        # Check if web search actually returned useful results
                        no_results_indicators = [
                            "no results found",
                            "no web search results",
                            "search returned no",
                            "couldn't find",
                            "no relevant results",
                        ]
                        search_failed = any(
                            indicator in tool_context.lower() 
                            for indicator in no_results_indicators
                        )
                        
                        if search_failed:
                            # Web search failed - instruct model to use its training knowledge
                            tool_instruction = (
                                "\n\n=== NOTE: WEB SEARCH RETURNED NO RESULTS ===\n"
                                "A web search was attempted but returned no results. "
                                "This is fine - please answer using your training knowledge.\n\n"
                                "IMPORTANT: You have extensive knowledge about this topic from your training. "
                                "Do NOT say you cannot answer or that you lack information. "
                                "Provide a complete, accurate answer based on your knowledge:\n"
                            )
                            logger.warning("Web search returned no results, falling back to model knowledge")
                        else:
                            # Web search succeeded - use the real-time data
                            tool_instruction = (
                                "\n\n=== IMPORTANT: REAL-TIME DATA BELOW ===\n"
                                "The following information was retrieved from current web searches. "
                                "You MUST use this data to answer the question. Do NOT claim you cannot "
                                "access current information - the data below is current as of today.\n\n"
                                f"{tool_context}\n"
                                "=== END OF REAL-TIME DATA ===\n\n"
                                "CRITICAL INSTRUCTIONS:\n"
                                "1. Use the real-time data above as your PRIMARY source, but supplement with your knowledge if needed\n"
                                "2. If asked for a numbered list (e.g., 'top 10'), provide ALL items requested using the search data\n"
                                "3. If the search data doesn't have enough items, supplement with your training knowledge\n"
                                "4. Include specific details from the sources (names, versions, capabilities)\n"
                                "5. Do NOT say 'I cannot access' or 'I don't have real-time data' - you DO have current data above\n"
                                "Now provide a complete, accurate answer based on the real-time data:"
                            )
                            logger.info("Tool context added to prompt with instructions (%d chars)", len(tool_context))
                        
                        base_prompt = f"{base_prompt}{tool_instruction}"
            except Exception as e:
                logger.warning("Tool Broker failed: %s", e)
        
        # ========================================================================
        # STEP 2: INTELLIGENT MODEL SELECTION (Based on agent_mode and task)
        # ========================================================================
        # Check agent_mode: "team" = multi-model ensemble, "single" = best single model
        agent_mode = orchestration_config.get("agent_mode", "team")
        is_team_mode = agent_mode == "team"
        
        # Check if we should use automatic model selection
        is_automatic_mode = (
            not request.models or  # No models provided
            len(request.models) == 0 or  # Empty list
            (len(request.models) == 1 and request.models[0].lower() in ["automatic", "auto"])
        )
        
        if is_automatic_mode:
            logger.info(
                "Intelligent model selection: agent_mode=%s, task_type='%s'",
                agent_mode, detected_task_type
            )
            
            # Determine if tools are needed (web search was used or could be needed)
            tools_needed = bool(tool_context)  # Web search was executed
            
            if is_team_mode:
                # TEAM MODE: Select multiple diverse models for ensemble orchestration
                # Uses Pinecone rankings + complementary strengths + tool support
                accuracy_lvl = orchestration_config.get("accuracy_level", 3)
                accuracy_priority = accuracy_lvl >= 3
                
                # Determine number of models based on accuracy level AND complexity
                # Simple queries should use fewer models for speed
                if detected_complexity == "simple":
                    # Simple factual queries: use only 1 model for speed
                    num_team_models = 1
                    logger.info("Simple query detected: using single model for fast response")
                elif accuracy_lvl >= 4:
                    num_team_models = min(4, len(available_providers))  # High accuracy: 4 models
                elif accuracy_lvl >= 3:
                    num_team_models = min(3, len(available_providers))  # Standard: 3 models
                else:
                    num_team_models = min(2, len(available_providers))  # Fast: 2 models
                
                # Use intelligent Pinecone-backed selection
                # This gets: top-ranked models for category + complementary models + tool-capable models
                auto_selected = get_intelligent_models_sync(
                    task_type=detected_task_type,
                    num_models=num_team_models,
                    require_tools=tools_needed,
                    available_models=available_providers,
                    accuracy_priority=accuracy_priority,
                )
                
                # Fallback to basic diverse ensemble if intelligent selection failed
                if len(auto_selected) < num_team_models:
                    auto_selected = get_diverse_ensemble(
                        detected_task_type,
                        available_models=available_providers,
                        num_models=num_team_models,
                    )
                
                logger.info(
                    "TEAM mode: Selected %d models for ensemble (tools=%s): %s",
                    len(auto_selected), tools_needed, auto_selected
                )
            else:
                # SINGLE MODE: Select just the ONE best model for the task
                # Still uses intelligent selection for optimal single-model choice
                auto_selected = get_intelligent_models_sync(
                    task_type=detected_task_type,
                    num_models=1,
                    require_tools=tools_needed,
                    available_models=available_providers,
                    accuracy_priority=True,
                )
                
                # Fallback
                if not auto_selected:
                    auto_selected = get_best_models_for_task(
                        detected_task_type,
                        available_models=available_providers,
                        num_models=1,
                        criteria=criteria_settings,
                    )
                
                logger.info(
                    "SINGLE mode: Selected best model (tools=%s): %s",
                    tools_needed, auto_selected[0] if auto_selected else "default"
                )
            
            # Map selected models to actual provider names
            actual_models = []
            user_model_names = []
            for model_id in auto_selected:
                mapped = _map_model_to_provider(model_id, available_providers)
                if mapped not in actual_models:
                    actual_models.append(mapped)
                    user_model_names.append(_get_display_name(model_id))
            
            logger.info(
                "Intelligent model selection: agent_mode=%s, task=%s -> models=%s",
                agent_mode, detected_task_type, actual_models,
            )
        
        # Enhance prompt with reasoning method template
        # NOTE: Only apply complex reasoning templates at accuracy_level >= 4 to avoid template echo issues
        accuracy_level = orchestration_config.get("accuracy_level", 3)
        if accuracy_level >= 4:
            enhanced_prompt = get_reasoning_prompt_template(
                reasoning_method,
                base_prompt,
                domain_pack=request.domain_pack.value,
            )
        else:
            # PHASE 4: Use category-specific optimized prompts for lower accuracy levels
            # These are simpler and less likely to cause LLM echo issues
            enhanced_prompt = get_category_prompt(detected_task_type, base_prompt)
            if enhanced_prompt != base_prompt:
                logger.info("Phase4: Applied category prompt for task=%s", detected_task_type)
        
        # ===========================================================================
        # SPECIAL HANDLING: Reasoning and Multi-step Tasks
        # ===========================================================================
        # These task types need specialized prompts to improve quality
        
        # Re-detect task type to ensure we catch reasoning/multi_step
        task_type_for_special = _detect_task_type(base_prompt)
        
        if task_type_for_special == "reasoning":
            # Apply chain-of-thought prompt for reasoning tasks
            # This prompt forces detailed step-by-step reasoning with explicit work shown
            reasoning_cot_prompt = """IMPORTANT: You MUST solve this problem by showing ALL your work step-by-step. 
Do NOT just give the final answer. The user specifically needs to see your reasoning process.

## Problem:
{question}

## Your Solution (MUST include ALL of these sections):

### Step 1: Define Variables
- Identify all unknown quantities
- Assign variable names (e.g., let c = number of chickens, r = number of rabbits)
- List what each variable represents

### Step 2: Set Up Equations
- Translate the problem constraints into mathematical equations
- Write each equation clearly with explanation
- Example: "Since each animal has 1 head: c + r = 35"

### Step 3: Solve the Equations
- Show each algebraic step
- Substitute and simplify
- Show the calculation for each unknown

### Step 4: Verify Your Answer
- Plug your answers back into the original equations
- Check that all constraints are satisfied
- Confirm the answer makes sense

### Step 5: Final Answer
State your answer clearly: "The answer is: [specific values]"

Now solve this problem completely, showing ALL work:"""
            enhanced_prompt = reasoning_cot_prompt.replace("{question}", base_prompt)
            logger.info("Applied specialized chain-of-thought prompt for reasoning task")
        
        elif task_type_for_special == "multi_step":
            # Apply task decomposition prompt for multi-step tasks
            # This prompt ensures comprehensive coverage of all requirements
            multi_step_prompt = """IMPORTANT: This is a complex request with MULTIPLE requirements. You MUST address EVERY part completely.

## The Request:
{question}

## Your Response MUST:

### 1. First, Identify All Requirements
Read the request carefully and list EVERY specific requirement mentioned.
Number each one: "Requirement 1:", "Requirement 2:", etc.
Do not miss any - the user expects ALL parts to be addressed.

### 2. Address Each Requirement Completely
For EACH requirement you identified:
- State which requirement you're addressing
- Provide a COMPLETE and DETAILED solution for that specific part
- Include all necessary details, examples, or specifications
- Do not give partial or vague responses

### 3. For Technical/Design Tasks, Include:
- Clear structure and organization
- Specific implementation details
- Examples where helpful
- Best practices and considerations

### 4. Final Checklist
Before finishing, verify:
☐ All numbered requirements are addressed
☐ Each part has complete details (not just mentioned)
☐ The response is organized and easy to follow
☐ Nothing from the original request is missing

Now provide your complete response, addressing EVERY requirement:"""
            enhanced_prompt = multi_step_prompt.replace("{question}", base_prompt)
            # Enable HRM for multi-step tasks if not already enabled
            if not orchestration_config.get("use_hrm"):
                orchestration_config["use_hrm"] = True
                logger.info("Enabled HRM for multi-step task decomposition")
            logger.info("Applied task decomposition prompt for multi-step task")
        
        elif task_type_for_special == "code_generation":
            # Apply language enforcement for coding tasks
            # Detect the programming language from the prompt
            prompt_lower = base_prompt.lower()
            detected_language = None
            language_patterns = [
                (r'\bpython\b', 'Python'),
                (r'\bjavascript\b|\bjs\b', 'JavaScript'),
                (r'\btypescript\b|\bts\b', 'TypeScript'),
                (r'\bjava\b(?!script)', 'Java'),
                (r'\bc\+\+\b|\bcpp\b', 'C++'),
                (r'\bc#\b|\bcsharp\b', 'C#'),
                (r'\bruby\b', 'Ruby'),
                (r'\bgo\b|\bgolang\b', 'Go'),
                (r'\brust\b', 'Rust'),
                (r'\bswift\b', 'Swift'),
                (r'\bkotlin\b', 'Kotlin'),
                (r'\bphp\b', 'PHP'),
                (r'\bsql\b', 'SQL'),
                (r'\bbash\b|\bshell\b', 'Bash'),
            ]
            for pattern, lang in language_patterns:
                if re.search(pattern, prompt_lower):
                    detected_language = lang
                    break
            
            if detected_language:
                # Add explicit language enforcement to the prompt
                code_enforcement_prompt = f"""IMPORTANT: You MUST write your code in {detected_language}. 
Do NOT use any other programming language.

{base_prompt}

REMINDER: Your response MUST be in {detected_language}. Use {detected_language} syntax and conventions."""
                enhanced_prompt = code_enforcement_prompt
                logger.info("Applied language enforcement for %s code task", detected_language)
        
        # ===========================================================================
        # Apply reasoning hacks for non-reasoning models to unlock deeper thinking
        # ===========================================================================
        reasoning_hack_applied = False
        reasoning_hack_level = None
        
        # Import reasoning hacker for advanced prompt transformation
        try:
            from ..orchestration.reasoning_hacker import (
                get_hack_prompt,
                get_recommended_hack_level,
                get_separated_reasoning_prompt,
                extract_final_answer,
                is_response_leaked_template,
                ReasoningHackLevel,
                REASONING_HACK_PROMPTS,
            )
            REASONING_HACKER_AVAILABLE = True
        except ImportError:
            REASONING_HACKER_AVAILABLE = False
        
        if MODEL_INTELLIGENCE_AVAILABLE and actual_models:
            primary_model = actual_models[0]
            profile = get_model_profile(primary_model)
            
            if profile:
                # Check if model needs reasoning hacks (not native reasoning like o1)
                from ..knowledge.model_intelligence import ReasoningCapability
                
                if ReasoningCapability.NATIVE_COT not in profile.reasoning_capabilities:
                    # Model can benefit from reasoning hacks
                    accuracy_lvl = orchestration_config.get("accuracy_level", 3)
                    
                    # PHASE 16: Use SEPARATED reasoning prompts to prevent template leakage
                    # System instructions go in system message, question stays clean
                    if REASONING_HACKER_AVAILABLE and accuracy_lvl >= 4:
                        # Determine hack level based on task and accuracy
                        if accuracy_lvl >= 5:
                            reasoning_hack_level = ReasoningHackLevel.HEAVY
                        else:
                            reasoning_hack_level = ReasoningHackLevel.MEDIUM
                        
                        # High-stakes domains get maximum hacking
                        high_stakes = ["health_medical", "legal_analysis", "financial_analysis"]
                        if detected_task_type in high_stakes and accuracy_lvl >= 3:
                            reasoning_hack_level = ReasoningHackLevel.MAXIMUM
                        
                        # PHASE 16: Use separated prompts to avoid template leakage
                        separated = get_separated_reasoning_prompt(
                            level=reasoning_hack_level,
                            question=enhanced_prompt,
                            task_type=detected_task_type,
                        )
                        
                        # Store the system message for the orchestrator to use
                        # The enhanced_prompt stays clean (just the question)
                        orchestration_config["reasoning_system_message"] = separated.system_message
                        orchestration_config["reasoning_extraction_pattern"] = separated.extraction_pattern
                        
                        # Keep enhanced_prompt clean - no scaffolding!
                        # The system message contains the reasoning instructions
                        enhanced_prompt = separated.user_message
                        reasoning_hack_applied = True
                        
                        logger.info(
                            "PHASE 16: Applied separated reasoning (level=%s) for %s - no template leakage",
                            reasoning_hack_level.value,
                            profile.display_name,
                        )
                    else:
                        # For accuracy_level < 4, use simple category prompts (already working well)
                        pass  # Category prompts are applied earlier in the flow
                    
                    # Log model's native hack capability
                    if profile.reasoning_hack_method and not reasoning_hack_applied:
                        logger.debug(
                            "Model %s supports reasoning via: %s",
                            profile.display_name,
                            profile.reasoning_hack_method[:100],
                        )
        
        logger.info(
            "Running orchestration: method=%s, domain=%s, agent_mode=%s, models=%s, "
            "hrm=%s, adaptive=%s, accuracy=%d",
            reasoning_method.value,
            orchestration_config["domain_pack"],
            orchestration_config["agent_mode"],
            actual_models,
            orchestration_config.get("use_hrm", False),
            orchestration_config.get("use_adaptive_routing", False),
            orchestration_config.get("accuracy_level", 3),
        )
        
        # Use PromptOps task type if available, otherwise detect from prompt
        task_type = detected_task_type if detected_task_type != "general" else _detect_task_type(base_prompt)
        accuracy_level = orchestration_config.get("accuracy_level", 3)
        
        # Determine if we should use elite orchestration
        # Elite orchestration requires TEAM mode with multiple models
        #
        # NOTE: When HRM (Hierarchical Role Management) is enabled for complex queries,
        # the HRM pathway takes precedence over elite orchestration. HRM decomposes
        # complex queries into sub-steps and executes them sequentially, which is more
        # appropriate for research-level or multi-part questions than parallel ensemble
        # strategies like "parallel_race" or "best_of_n".
        #
        # If use_hrm=True (either explicitly set or auto-enabled for complex queries),
        # we skip elite orchestration and let the standard orchestrator run with HRM.
        use_hrm = orchestration_config.get("use_hrm", False)
        use_elite = (
            ELITE_AVAILABLE and 
            is_team_mode and  # Only use elite in TEAM mode
            accuracy_level >= 3 and 
            len(actual_models) >= 2 and
            not use_hrm  # HRM takes precedence over elite orchestration
        )
        
        elite_result = None
        
        if use_elite:
            logger.info(
                "Using ELITE orchestration: task=%s, accuracy=%d, strategy=auto",
                task_type, accuracy_level
            )
            
            elite = _get_elite_orchestrator()
            if elite:
                try:
                    # Reuse prior successful orchestration pattern if available
                    kb_strategy = None
                    if KNOWLEDGE_BASE_AVAILABLE:
                        kb = _get_knowledge_base()
                        if kb:
                            kb_strategy = await kb.get_best_strategy(
                                query_type=task_type,
                                user_id=user_id,
                            )
                            if kb_strategy:
                                logger.info(
                                    "Using learned strategy from KB: %s (models=%s)",
                                    kb_strategy[0],
                                    kb_strategy[1],
                                )
                                selected_strategy = kb_strategy[0]
                                if kb_strategy[1]:
                                    actual_models = kb_strategy[1]
                    
                    # Select strategy based on accuracy, task, complexity, and user criteria
                    strategy = selected_strategy or _select_elite_strategy(
                        accuracy_level=accuracy_level,
                        task_type=task_type,
                        num_models=len(actual_models),
                        complexity=detected_complexity,
                        criteria=criteria_settings,
                        prompt_spec=prompt_spec,
                    )
                    selected_strategy = strategy
                    
                    elite_result = await elite.orchestrate(
                        enhanced_prompt,
                        task_type=task_type,
                        available_models=actual_models,
                        strategy=strategy,
                        quality_threshold=0.7,
                        max_parallel=min(3, len(actual_models)),
                    )
                    
                    final_text = elite_result.final_answer
                    
                    logger.info(
                        "Elite orchestration complete: strategy=%s, quality=%.2f, models=%s",
                        elite_result.strategy_used,
                        elite_result.quality_score,
                        elite_result.models_used,
                    )
                except Exception as e:
                    logger.warning("Elite orchestration failed, falling back: %s", e)
                    use_elite = False
        
        if not use_elite or elite_result is None:
            # Standard orchestration path
            # Note: skip_injection_check=True because we already did the check on the raw user prompt
            # in STEP -1 above. The enhanced_prompt contains system instructions which would
            # falsely trigger injection detection (e.g., "act as a planner").
            artifacts = await _orchestrator.orchestrate(
                enhanced_prompt,
                actual_models,
                use_hrm=orchestration_config.get("use_hrm", False),
                use_adaptive_routing=orchestration_config.get("use_adaptive_routing", False),
                use_deep_consensus=orchestration_config.get("use_deep_consensus", False),
                use_prompt_diffusion=orchestration_config.get("use_prompt_diffusion", False),
                accuracy_level=accuracy_level,
                skip_injection_check=True,  # Already checked on raw prompt
            )
            final_text = artifacts.final_response.content
        
        # Apply quality boosting for high accuracy requests
        # NOTE: Quality booster disabled at level 4 - causes over-summarization
        # resulting in terse responses that miss contextual keywords
        # TODO: Fix quality booster to preserve context before re-enabling
        if QUALITY_BOOSTER_AVAILABLE and accuracy_level >= 5:  # Only level 5+
            booster = _get_quality_booster()
            if booster:
                try:
                    logger.info("Applying quality boost for maximum-accuracy request")
                    boost_result = await booster.boost(
                        base_prompt,
                        final_text,
                        techniques=["reflection", "verification"],
                        max_iterations=1,
                    )
                    if boost_result.quality_improvement > 0:
                        final_text = boost_result.boosted_response
                        logger.info(
                            "Quality boost applied: improvement=%.2f, techniques=%s",
                            boost_result.quality_improvement,
                            boost_result.techniques_applied,
                        )
                except Exception as e:
                    logger.warning("Quality boost failed: %s", e)
        
        # Distill multi-model/agent outputs into reusable knowledge
        if KNOWLEDGE_BASE_AVAILABLE:
            try:
                kb = _get_knowledge_base()
                if kb:
                    used_models = []
                    if elite_result and getattr(elite_result, "models_used", None):
                        used_models = elite_result.models_used
                    elif artifacts and getattr(artifacts, "models_used", None):
                        used_models = artifacts.models_used
                    if used_models and len(used_models) > 1:
                        distilled_content = f"Distilled consensus for: {original_prompt[:200]}\nModels: {', '.join(used_models)}\nAnswer:\n{final_text[:1800]}"
                await kb.store_answer(
                            query=original_prompt[:500],
                            answer=distilled_content,
                            models_used=used_models,
                            record_type=RecordType.DOMAIN_KNOWLEDGE,
                            quality_score=0.6,
                            domain=request.domain_pack.value,
                            user_id=user_id,
                            project_id=project_id,
                    org_id=org_id,
                            metadata={"multi_agent_distilled": True},
                        )
            except Exception as e:
                logger.debug("Failed to distill multi-agent output: %s", e)
        
        # ========================================================================
        # STEP 4: TOOL-BASED VERIFICATION (For code/math/factual tasks)
        # ========================================================================
        verification_confidence = 1.0
        verification_issues: List[str] = []
        
        # Only verify for tasks that benefit from deterministic verification
        should_verify = (
            TOOL_VERIFICATION_AVAILABLE and
            VERIFICATION_ENABLED and
            task_type in ["code_generation", "debugging", "math_problem", "factual_question"]
        )
        
        if should_verify:
            try:
                verification_pipeline = get_verification_pipeline()
                
                verified_text, verification_confidence, verification_issues = (
                    await verification_pipeline.verify_answer(
                        final_text,
                        base_prompt,
                        fix_errors=True,  # Auto-correct math/code errors
                    )
                )
                
                if verification_issues:
                    logger.warning(
                        "Verification found %d issues (confidence=%.2f): %s",
                        len(verification_issues),
                        verification_confidence,
                        verification_issues[:3],
                    )
                    final_text = verified_text  # Use corrected version
                else:
                    logger.info(
                        "Verification passed: task=%s, confidence=%.2f",
                        task_type,
                        verification_confidence,
                    )
                verification_result = {
                    "passed": len(verification_issues) == 0,
                    "confidence": verification_confidence,
                }
            except Exception as e:
                logger.warning("Tool verification failed: %s", e)
        
        # ========================================================================
        # FINAL STEP: ALWAYS-ON ANSWER REFINEMENT
        # ========================================================================
        if REFINER_AVAILABLE and REFINER_ALWAYS_ON:
            try:
                # Detect output format from PromptOps analysis, allow user override, then profile default
                output_format = OutputFormat.PARAGRAPH
                requested_format = request.format_style or (user_profile.default_format_style if user_profile else None)
                if prompt_spec and prompt_spec.analysis.output_format:
                    requested_format = requested_format or prompt_spec.analysis.output_format
                
                if requested_format:
                    fmt = requested_format
                    # Check for strict format (e.g., "json_strict" means output ONLY JSON)
                    if fmt.endswith("_strict"):
                        is_strict_format = True
                        fmt = fmt.replace("_strict", "")
                    
                    format_map = {
                        "json": OutputFormat.JSON,
                        "markdown": OutputFormat.MARKDOWN,
                        "code": OutputFormat.CODE,
                        "list": OutputFormat.NUMBERED,  # "list" should be numbered (1, 2, 3...)
                        "numbered": OutputFormat.NUMBERED,
                        "bullet": OutputFormat.BULLET,
                        "bullet_points": OutputFormat.BULLET,
                        "table": OutputFormat.TABLE,
                        "executive_summary": OutputFormat.EXEC_SUMMARY,
                        "exec_summary": OutputFormat.EXEC_SUMMARY,
                        "qa": OutputFormat.QA,
                        "paragraph": OutputFormat.PARAGRAPH,
                    }
                    output_format = format_map.get(fmt, OutputFormat.PARAGRAPH)
                    
                    # For strict JSON, extract only the JSON from the response
                    if is_strict_format and fmt == "json":
                        # Find JSON object or array in the response (re is imported at module level)
                        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])', final_text, re.DOTALL)
                        if json_match:
                            final_text = json_match.group(1)
                            logger.info("Strict JSON format: extracted JSON from response")
                
                # Extract word limit from constraints if specified
                max_words = None
                if prompt_spec and prompt_spec.analysis.constraints:
                    for constraint in prompt_spec.analysis.constraints:
                        if "Maximum" in constraint and "words" in constraint:
                            # re is imported at module level
                            match = re.search(r'Maximum\s+(\d+)\s+words', constraint)
                            if match:
                                max_words = int(match.group(1))
                                logger.info(f"Word limit detected: {max_words} words")
                
                # Tone override from request or profile
                tone_style = ToneStyle.PROFESSIONAL
                tone_requested = request.tone_style or (user_profile.default_tone_style if user_profile else None)
                if tone_requested:
                    try:
                        tone_style = ToneStyle(tone_requested)
                    except Exception:
                        logger.warning("Unknown tone_style '%s', using professional", tone_requested)
                
                include_conf = accuracy_level >= 4
                if request.show_confidence is not None:
                    include_conf = bool(request.show_confidence)
                elif user_profile and user_profile.show_confidence is not None:
                    include_conf = bool(user_profile.show_confidence)

                # Preserve full detailed content for reasoning/multi-step tasks
                # These task types need comprehensive answers, not summaries
                task_for_preserve = _detect_task_type(base_prompt)
                should_preserve_reasoning = (
                    task_for_preserve in ("reasoning", "multi_step") or
                    "show your" in base_prompt.lower() or
                    "step by step" in base_prompt.lower() or
                    "show work" in base_prompt.lower() or
                    "design" in base_prompt.lower() or
                    "api" in base_prompt.lower()
                )
                
                refiner_config = RefinementConfig(
                    output_format=output_format,
                    tone=tone_style,
                    include_confidence=include_conf,
                    include_citations=accuracy_level >= 3,
                    preserve_structure=True,
                    max_words=max_words,
                    preserve_reasoning_steps=should_preserve_reasoning,
                )
                
                refiner = AnswerRefiner(providers=_orchestrator.providers)
                refined_answer = await refiner.refine(
                    final_text,
                    query=base_prompt,
                    config=refiner_config,
                )
                
                if refined_answer and refined_answer.refined_content:
                    refined_text = refined_answer.refined_content
                    final_text = refined_text
                    logger.info(
                        "Answer refined: %d improvements, format=%s",
                        len(refined_answer.improvements_made),
                        refined_answer.format_applied.value,
                    )
                
                # Final safeguard for strict JSON output
                if is_strict_format and (prompt_spec and prompt_spec.analysis.output_format and prompt_spec.analysis.output_format.startswith("json")):
                    import json as _json  # re is imported at module level
                    json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])', final_text, re.DOTALL)
                    if json_match:
                        candidate = json_match.group(1)
                        try:
                            _json.loads(candidate)
                            final_text = candidate
                            logger.info("Strict JSON: validated JSON extraction after refinement")
                        except Exception:
                            final_text = candidate
                            logger.warning("Strict JSON: extracted JSON but parsing failed; returning best-effort JSON text")
                    else:
                        logger.warning("Strict JSON requested but no JSON found after refinement; returning original text")
            except Exception as e:
                logger.warning("Answer refinement failed (using unrefined): %s", e)
        
        # Build agent traces from artifacts (if available)
        traces: list[AgentTrace] = []
        
        # Extract token usage and other metrics
        token_usage = None
        quality_score = None
        
        if elite_result:
            # Use elite orchestrator metrics
            token_usage = elite_result.total_tokens
            quality_score = elite_result.quality_score
            actual_models_used = elite_result.models_used
        elif 'artifacts' in dir() and artifacts:
            if hasattr(artifacts.final_response, 'tokens_used'):
                token_usage = artifacts.final_response.tokens_used
            actual_models_used = actual_models
        else:
            actual_models_used = actual_models
        
        # Calculate latency
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Build extra data
        extra: Dict[str, Any] = {
            "orchestration_settings": {
                "accuracy_level": orchestration_config.get("accuracy_level", 3),
                "hrm_enabled": orchestration_config.get("use_hrm", False),
                "adaptive_routing_enabled": orchestration_config.get("use_adaptive_routing", False),
                "deep_consensus_enabled": orchestration_config.get("use_deep_consensus", False),
                "prompt_diffusion_enabled": orchestration_config.get("use_prompt_diffusion", False),
            },
        }
        
        # Add elite orchestrator info if used
        if elite_result:
            extra["elite_orchestration"] = {
                "enabled": True,
                "strategy": elite_result.strategy_used,
                "synthesis_method": elite_result.synthesis_method,
                "quality_score": elite_result.quality_score,
                "confidence": elite_result.confidence,
                "responses_generated": elite_result.responses_generated,
                "primary_model": elite_result.primary_model,
                "consensus_score": getattr(elite_result, "consensus_score", None),
            }
            extra["performance_notes"] = elite_result.performance_notes
        else:
            if 'artifacts' in dir() and artifacts:
                extra["initial_responses_count"] = len(artifacts.initial_responses)
                extra["critiques_count"] = len(artifacts.critiques)
                extra["improvements_count"] = len(artifacts.improvements)
                # Add consensus notes if available
                if hasattr(artifacts, 'consensus_notes') and artifacts.consensus_notes:
                    extra["consensus_notes"] = artifacts.consensus_notes
        
        # Add task type detected
        extra["task_type"] = task_type
        
        # Add clarification questions if generated (frontend can optionally display)
        if clarification_questions:
            extra["clarification"] = {
                "suggested_questions": clarification_questions,
                "note": "These questions could help refine the answer. Consider asking them as follow-up.",
            }
        
        # Add verification results to extra
        if should_verify:
            extra["verification"] = {
                "performed": True,
                "confidence": verification_confidence,
                "issues_found": len(verification_issues),
                "issues": verification_issues[:5] if verification_issues else [],
                "corrected": bool(verification_issues),
            }
        else:
            extra["verification"] = {"performed": False}
        
        # Add tool broker results to extra
        extra["tool_broker"] = tool_results_info
        
        # Add models used info to extra
        extra["models_requested"] = request.models or []
        extra["models_mapped"] = actual_models
        
        # PR5: Add budget info to extra
        if budget_constraints:
            extra["budget"] = {
                "max_cost_usd": budget_constraints.max_cost_usd,
                "prefer_cheaper": budget_constraints.prefer_cheaper,
                "estimated_tokens": budget_constraints.estimated_tokens,
            }
        
        # Add cost tracking information if available
        cost_info = None
        generation_id = None
        if 'artifacts' in dir() and artifacts and hasattr(artifacts, 'final_response'):
            cost_info = getattr(artifacts.final_response, 'cost_info', None)
            generation_id = getattr(artifacts.final_response, 'generation_id', None)
        
        if cost_info:
            extra["cost_tracking"] = {
                "generation_id": generation_id,
                "prompt_tokens": cost_info.get("prompt_tokens", 0),
                "completion_tokens": cost_info.get("completion_tokens", 0),
                "total_tokens": cost_info.get("total_tokens", 0),
                "model_used": cost_info.get("model_used", "unknown"),
                "provider": cost_info.get("provider", "unknown"),
            }
            # Include native token counts if available (from OpenRouter)
            if "native_prompt_tokens" in cost_info:
                extra["cost_tracking"]["native_prompt_tokens"] = cost_info["native_prompt_tokens"]
            if "native_completion_tokens" in cost_info:
                extra["cost_tracking"]["native_completion_tokens"] = cost_info["native_completion_tokens"]
        elif token_usage:
            # Basic cost tracking from token_usage when cost_info not available
            extra["cost_tracking"] = {
                "total_tokens": token_usage if isinstance(token_usage, int) else 0,
                "provider": "unknown",
            }
        
        # CRITICAL SAFEGUARD: Never return empty message
        # If final_text is empty after all processing, provide a fallback
        if not final_text or not final_text.strip():
            logger.error(
                "CRITICAL: final_text is empty after orchestration! "
                "Prompt: %s, Models: %s",
                request.prompt[:100],
                actual_models,
            )
            final_text = (
                "I apologize, but I was unable to generate a response to your query. "
                "Please try again or rephrase your question."
            )
        
        # ========================================================================
        # PHASE 2: MATH OUTPUT VALIDATION
        # Ensure calculator results are present in math responses
        # ========================================================================
        if tool_results_info.get("calculator_result") is not None:
            calc_result = tool_results_info["calculator_result"]
            calc_expr = tool_results_info.get("calculator_expression", "")
            
            # Format the result nicely
            if isinstance(calc_result, float):
                # Format as currency if it looks like a money calculation
                if "$" in base_prompt or "dollar" in base_prompt.lower():
                    formatted_result = f"${calc_result:,.2f}"
                else:
                    formatted_result = f"{calc_result:,.2f}"
            else:
                formatted_result = str(calc_result)
            
            # Check if the result is already in the response
            result_in_response = (
                formatted_result in final_text or
                str(round(calc_result, 2)) in final_text or
                str(round(calc_result, 0)).replace('.0', '') in final_text
            )
            
            if not result_in_response:
                # The calculator result is missing - inject it
                logger.warning("PHASE 2: Calculator result missing from response, injecting")
                
                # Prepend the correct result
                injection = f"**Calculated Result: {formatted_result}**\n\n"
                final_text = injection + final_text
                logger.info("PHASE 2: Injected calculator result: %s", formatted_result)
        
        # ========================================================================
        # FINAL CLEANUP: Strip any internal scaffolding from the response
        # For reasoning/multi-step tasks, keep detailed content but remove ugly markers
        # ========================================================================
        detected_task = _detect_task_type(base_prompt)
        needs_detailed_output = (
            detected_task in ("reasoning", "multi_step") or
            "show your" in base_prompt.lower() or
            "step by step" in base_prompt.lower() or
            "show work" in base_prompt.lower() or
            "design" in base_prompt.lower() or  # Design tasks need full details
            "api" in base_prompt.lower()  # API designs need full details
        )
        # Store calculator result before cleanup in case we need it
        calc_result_for_fallback = None
        if tool_results_info.get("calculator_result") is not None:
            calc_result = tool_results_info["calculator_result"]
            if isinstance(calc_result, float):
                if calc_result >= 1000:
                    calc_result_for_fallback = f"${calc_result:,.2f}"
                else:
                    calc_result_for_fallback = f"{calc_result:,.2f}"
            else:
                calc_result_for_fallback = str(calc_result)
        
        if needs_detailed_output:
            # Clean up scaffold markers but preserve detailed content
            final_text = _clean_reasoning_output(final_text)
            logger.info("Cleaned detailed output for %s task (preserved content)", detected_task)
        else:
            original_text = final_text  # Save original before stripping
            final_text = _strip_internal_scaffolding(final_text)
            
            # If stripping resulted in empty/short text, use fallback
            if not final_text or len(final_text.strip()) < 20:
                logger.warning("Stripped text too short, using fallback")
                if calc_result_for_fallback:
                    # For math problems with calculator, provide clean answer
                    final_text = f"The answer is **{calc_result_for_fallback}**."
                    logger.info("Using calculator result as fallback: %s", calc_result_for_fallback)
                else:
                    # For non-math, try to salvage original
                    final_text = original_text
        
        # ========================================================================
        # PHASE 3: OUTPUT VALIDATION & RETRY LOGIC
        # Detect incomplete/fragment responses and retry if needed
        # NOTE: Skip retry for math tasks if calculator was used (results are verified)
        # ========================================================================
        def _is_incomplete_response(text: str, task: str, calc_used: bool) -> bool:
            """Check if response appears to be incomplete or a fragment."""
            # Skip validation for math tasks with calculator results
            if task == "math_problem" and calc_used:
                return False  # Calculator results are verified, no retry needed
            
            if not text or len(text.strip()) < 20:
                return True
            
            text_lower = text.lower().strip()
            
            # Fragment indicators - starts with lowercase continuation words
            fragment_starts = ['is ', 'are ', 'was ', 'were ', 'to ', 'and ', 'but ', 'or ', 'the ']
            if any(text_lower.startswith(fs) for fs in fragment_starts):
                return True
            
            # Check for incomplete sentences (ends mid-word or with certain patterns)
            if text.rstrip().endswith(('...', ' the', ' a', ' an', ' to', ' of')):
                return True
            
            # Task-specific validation
            if task == "math_problem":
                # Math responses should contain numbers
                if not any(c.isdigit() for c in text):
                    return True
            
            if task == "code_generation":
                # Code responses should contain code markers or keywords
                code_indicators = ['def ', 'function ', 'class ', '```', 'return ', 'const ', 'let ', 'var ']
                if not any(ind in text for ind in code_indicators):
                    return True
            
            return False
        
        # Check if calculator was used for this query
        calculator_was_used = tool_results_info.get("used", False) and tool_results_info.get("calculator_result") is not None
        
        # Check if response needs retry (skip for validated math)
        retry_attempted = False
        if _is_incomplete_response(final_text, detected_task, calculator_was_used):
            logger.warning("PHASE 3: Detected incomplete response, attempting retry")
            
            # IMPORTANT: Don't retry - just log. Retry was causing stub fallback issues.
            # Instead, ensure the original response quality is maintained.
            logger.info("PHASE 3: Skipping retry to avoid stub fallback issues")
        
        # ========================================================================
        # PHASE 4: FINAL TEMPLATE LEAKAGE SAFEGUARD
        # Last chance to detect and remove any template leakage before returning
        # This is a non-breaking safeguard - falls back to original if extraction fails
        # ========================================================================
        
        # PHASE 16: Use reasoning_hacker extraction if available
        extraction_pattern = orchestration_config.get("reasoning_extraction_pattern")
        
        # Try to use the advanced extraction from reasoning_hacker module first
        try:
            from ..orchestration.reasoning_hacker import (
                is_response_leaked_template,
                extract_final_answer,
            )
            HAS_ADVANCED_EXTRACTION = True
        except ImportError:
            HAS_ADVANCED_EXTRACTION = False
        
        if HAS_ADVANCED_EXTRACTION and is_response_leaked_template(final_text):
            logger.warning("PHASE 16: Template leakage detected, applying advanced extraction")
            original_length = len(final_text)
            extracted = extract_final_answer(final_text, extraction_pattern)
            
            # Validate extraction - must be substantial and different from original
            if extracted and len(extracted) > 30 and extracted != final_text:
                logger.info("PHASE 16: Extracted clean content (%d -> %d chars)", original_length, len(extracted))
                final_text = extracted
            else:
                logger.info("PHASE 16: Advanced extraction insufficient, trying fallback")
        
        # Fallback: Local detection and extraction (for backwards compatibility)
        def _detect_template_leakage(text: str) -> bool:
            """Detect if response contains obvious template leakage."""
            leakage_indicators = [
                "=== Step 1:",
                "=== PROBLEM ===",
                "=== UNDERSTANDING ===",
                "Phase 1 - Planning:",
                "Phase 2 - Solution:",
                "IMPORTANT: This is a complex request",
                "You MUST address EVERY part",
                "Solve this problem. You MUST express confidence",
                "## The Request:",
                "**Problem:**\n\nIMPORTANT:",
                "Rate your confidence from 1-10",
                "thinking step by step as requested",
                "[restate the core question]",
                "[list any constraints]",
                "=== ATTEMPT 1 ===",
            ]
            return any(indicator in text for indicator in leakage_indicators)
        
        def _extract_actual_content(text: str) -> str:
            """Try to extract the actual answer from a leaked template response."""
            # Try to find content after common template markers
            extraction_patterns = [
                (r'(?:Final Answer|ANSWER|Solution):\s*\n*(.*?)(?:$|\n\n---)', re.DOTALL | re.IGNORECASE),
                (r'(?:In conclusion|Therefore|Thus|The answer is)[:,]?\s*(.*?)(?:$|\n\n)', re.DOTALL | re.IGNORECASE),
                (r'\*\*(?:Answer|Result|Solution)\*\*:?\s*(.*?)(?:$|\n\n)', re.DOTALL),
                # For multi-step, try to get the recommendation/conclusion section
                (r'(?:Recommend(?:ation)?|Conclusion):\s*\n*(.*?)$', re.DOTALL | re.IGNORECASE),
            ]
            
            for pattern, flags in extraction_patterns:
                match = re.search(pattern, text, flags)
                if match:
                    extracted = match.group(1).strip()
                    # Only use if substantial content
                    if len(extracted) > 50:
                        return extracted
            
            # Fallback: remove known template prefixes
            cleaned = text
            prefix_removals = [
                r'^.*?=== Step \d+:.*?===\s*\n*',
                r'^.*?Phase \d+ - \w+:\s*\n*',
                r'^Sure,?\s*let\'s address.*?step-by-step\.\s*\n*',
                r'^.*?IMPORTANT:.*?completely\.\s*\n*',
            ]
            for pattern in prefix_removals:
                cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
            
            return cleaned.strip() if cleaned.strip() else text
        
        # Apply fallback safeguard if leakage still detected
        if _detect_template_leakage(final_text):
            logger.warning("PHASE 4: Template leakage still detected, applying fallback extraction")
            original_length = len(final_text)
            extracted = _extract_actual_content(final_text)
            
            # Only use extraction if it's substantial (at least 30% of original)
            if len(extracted) > 50 and len(extracted) >= original_length * 0.3:
                logger.info("PHASE 4: Extracted clean content (%d -> %d chars)", original_length, len(extracted))
                final_text = extracted
            else:
                logger.info("PHASE 4: Extraction insufficient, keeping original")
        
        # Build response with models_used
        response = ChatResponse(
            message=final_text,
            models_used=user_model_names,
            reasoning_mode=request.reasoning_mode,
            reasoning_method=request.reasoning_method,
            domain_pack=request.domain_pack,
            agent_mode=request.agent_mode,
            used_tuning=request.tuning,
            metadata=request.metadata,
            tokens_used=token_usage,
            latency_ms=latency_ms,
            agent_traces=traces,
            extra=extra,
        )
        
        logger.info(
            "Orchestration completed: latency=%dms, tokens=%s",
            latency_ms,
            token_usage or "unknown",
        )
        
        # ========================================================================
        # STEP FINAL: STORE ANSWER FOR LEARNING (If Vector RAG is enabled)
        # ========================================================================
        if enable_rag and KNOWLEDGE_BASE_AVAILABLE:
            try:
                # Calculate quality score based on verification and refinement
                quality_score = 0.7  # Base score
                if verification_result and verification_result.get("passed"):
                    quality_score += 0.2
                if refined_text and refined_text != final_text:
                    quality_score += 0.1
                
                # Store the final answer for future RAG retrieval
                await _store_answer_for_learning(
                    query=original_prompt,
                    answer=final_text,
                    models_used=actual_models,
                    quality_score=min(quality_score, 1.0),
                    domain=request.domain_pack.value,
                    user_id=user_id,
                    project_id=project_id,
                    org_id=org_id,
                    is_partial=False,
                )
                
                # Learn the orchestration pattern
                await _learn_orchestration_pattern(
                    query_type=detected_task_type,
                    strategy_used=selected_strategy,
                    models_used=actual_models,
                    success=True,
                    latency_ms=latency_ms,
                    quality_score=min(quality_score, 1.0),
                    user_id=user_id,
                )
                
            except Exception as e:
                logger.warning(f"Failed to store answer for learning: {e}")
        
        # ========================================================================
        # PHASE 5: LOG PERFORMANCE FOR ADAPTIVE ROUTING
        # Feed performance data to tracker for future model selection
        # ========================================================================
        if PERFORMANCE_TRACKER_AVAILABLE and performance_tracker:
            try:
                performance_tracker.log_run(
                    models_used=actual_models,
                    success_flag=True,  # Got a response
                    latency_ms=latency_ms,
                    domain=task_type,
                    strategy=selected_strategy if 'selected_strategy' in locals() else None,
                    task_type=task_type,
                    quality_score=quality_score if 'quality_score' in locals() else 0.8,
                )
                logger.debug("Logged performance for %d models", len(actual_models))
            except Exception as e:
                logger.debug("Performance logging failed (non-critical): %s", e)
        
        return response
        
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("Orchestration failed: %s", exc)
        
        # Raise proper HTTP exceptions instead of returning error in 200 OK
        from fastapi import HTTPException, status
        
        # Import error types for proper handling
        try:
            from ..errors import ProviderError, ErrorCode, LLMHiveError
            
            if isinstance(exc, ProviderError):
                # Provider-specific errors - surface with details
                error_detail = {
                    "error": str(exc.message),
                    "error_code": exc.code.value,
                    "provider": exc.provider,
                    "model": exc.model,
                    "details": exc.details,
                    "latency_ms": latency_ms,
                    "recoverable": exc.recoverable,
                }
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=error_detail,
                ) from exc
            elif isinstance(exc, LLMHiveError):
                # Other LLMHive errors
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": exc.message,
                        "error_code": exc.code.value,
                        "latency_ms": latency_ms,
                        "recoverable": exc.recoverable,
                    },
                ) from exc
        except ImportError:
            pass  # Error types not available, fall through
        
        # Generic errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"Orchestration failed: {str(exc)}",
                "error_type": type(exc).__name__,
                "latency_ms": latency_ms,
            },
        ) from exc
    finally:
        # Audit logging (best-effort)
        try:
            log_audit_event(
                org_id=org_id,
                user_id=user_id,
                action="query",
                details={
                    "prompt": request.prompt[:200],
                    "models": actual_models if 'actual_models' in locals() else [],
                    "latency_ms": int((time.perf_counter() - start_time) * 1000),
                },
            )
        except Exception:
            pass

