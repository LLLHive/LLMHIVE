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
import time
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
from .model_router import (
    get_models_for_reasoning_method,
    map_reasoning_mode_to_method,
    ReasoningMethod as RouterReasoningMethod,
    FALLBACK_GPT_4O,
    FALLBACK_GPT_4O_MINI,
    FALLBACK_CLAUDE_SONNET_4,
    FALLBACK_CLAUDE_3_5,
    FALLBACK_CLAUDE_3_HAIKU,
    FALLBACK_GEMINI_2_5,
    FALLBACK_GEMINI_2_5_FLASH,
    FALLBACK_GROK_2,
    FALLBACK_GROK_BETA,
    FALLBACK_DEEPSEEK,
    # Automatic model selection functions
    get_best_models_for_task,
    get_diverse_ensemble,
    MODEL_CAPABILITIES,
)
from .reasoning_prompts import get_reasoning_prompt_template

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

try:
    from ..orchestration.quality_booster import (
        QualityBooster,
        boost_response,
    )
    QUALITY_BOOSTER_AVAILABLE = True
except ImportError:
    QUALITY_BOOSTER_AVAILABLE = False
    QualityBooster = None

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

logger = logging.getLogger(__name__)

# Configuration
MAX_CHALLENGE_LOOPS = 2  # Max retry attempts on verification failure
VERIFICATION_ENABLED = True  # Enable verification gate
REFINER_ALWAYS_ON = True  # Always run answer refinement

# Global orchestrator instance
_orchestrator = Orchestrator()

# Elite orchestrator instance (initialized on first use)
_elite_orchestrator: Optional[EliteOrchestrator] = None
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
    is_partial: bool = False,
) -> None:
    """Store answer in knowledge base for future learning."""
    kb = _get_knowledge_base()
    if not kb:
        return
    
    try:
        record_type = RecordType.PARTIAL_ANSWER if is_partial else RecordType.FINAL_ANSWER
        await kb.store_answer(
            query=query,
            answer=answer,
            models_used=models_used,
            record_type=record_type,
            quality_score=quality_score,
            domain=domain,
            user_id=user_id,
            project_id=project_id,
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
    """Detect task type from prompt for optimal routing."""
    prompt_lower = prompt.lower()
    
    if any(kw in prompt_lower for kw in ["code", "function", "implement", "debug", "program"]):
        return "code_generation"
    elif any(kw in prompt_lower for kw in ["calculate", "solve", "math", "equation"]):
        return "math_problem"
    elif any(kw in prompt_lower for kw in ["research", "analyze", "comprehensive", "in-depth"]):
        return "research_analysis"
    elif any(kw in prompt_lower for kw in ["explain", "what is", "how does", "why"]):
        return "explanation"
    elif any(kw in prompt_lower for kw in ["compare", "versus", "difference"]):
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
    # PHASE 1: HARD RULES (Task-specific requirements)
    # ========================================================================
    
    # Code and math ALWAYS need verification (non-negotiable)
    if task_type in ["code_generation", "debugging", "math_problem"]:
        # But speed-optimize if user explicitly wants fast
        if speed_priority >= 80 and accuracy_level <= 2:
            logger.info("Strategy: Code/math with high speed priority -> best_of_n")
            return "best_of_n"  # Skip challenge loop but still compare
        logger.info("Strategy: Code/math task -> challenge_and_refine")
        return "challenge_and_refine"
    
    # Factual questions with high accuracy need verification
    if task_type == "factual_question" and accuracy_priority >= 80:
        logger.info("Strategy: Factual question with high accuracy -> challenge_and_refine")
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
    """Map a user-selected model ID to an actual provider/model name.
    
    Latest models (December 2025):
    - OpenAI: GPT-4o, GPT-4o-mini, o1, o1-mini
    - Anthropic: Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3.5 Haiku
    - Google: Gemini 2.5 Pro, Gemini 2.5 Flash
    - xAI: Grok-2, Grok-2-mini
    """
    model_lower = model_id.lower()
    
    # OpenAI models
    if "gpt-5" in model_lower or "gpt-4" in model_lower or "o1" in model_lower:
        if "mini" in model_lower:
            return FALLBACK_GPT_4O_MINI
        return FALLBACK_GPT_4O
    
    # Anthropic Claude models
    elif "claude" in model_lower:
        if "haiku" in model_lower:
            return FALLBACK_CLAUDE_3_HAIKU  # claude-3-5-haiku-20241022
        elif "sonnet-4" in model_lower or "4.5" in model_lower or "opus" in model_lower:
            return FALLBACK_CLAUDE_SONNET_4  # claude-sonnet-4-20250514
        return FALLBACK_CLAUDE_3_5  # claude-3-5-sonnet-20241022
    
    # Google Gemini models
    elif "gemini" in model_lower:
        if "flash" in model_lower:
            return FALLBACK_GEMINI_2_5_FLASH  # gemini-2.5-flash
        return FALLBACK_GEMINI_2_5  # gemini-2.5-pro
    
    # xAI Grok models - Use Grok-2 (latest)
    elif "grok" in model_lower:
        return FALLBACK_GROK_2  # grok-2
    
    # DeepSeek models
    elif "deepseek" in model_lower:
        return FALLBACK_DEEPSEEK  # deepseek-chat
    
    # Llama (local)
    elif "llama" in model_lower:
        if "local" in available_providers:
            return "local"
        return "stub"
    
    # Direct model name match
    elif model_id in available_providers:
        return model_id
    
    else:
        # Default to first available
        return available_providers[0] if available_providers else "stub"


def _get_display_name(model_id: str) -> str:
    """Get a user-friendly display name for a model."""
    display_names = {
        FALLBACK_GPT_4O: "GPT-4o",
        FALLBACK_GPT_4O_MINI: "GPT-4o Mini",
        FALLBACK_CLAUDE_SONNET_4: "Claude Sonnet 4",
        FALLBACK_CLAUDE_3_5: "Claude 3.5 Sonnet",
        FALLBACK_CLAUDE_3_HAIKU: "Claude 3.5 Haiku",
        FALLBACK_GEMINI_2_5: "Gemini 2.5 Pro",
        FALLBACK_GEMINI_2_5_FLASH: "Gemini 2.5 Flash",
        FALLBACK_GROK_2: "Grok-2",
        FALLBACK_DEEPSEEK: "DeepSeek V3",
    }
    return display_names.get(model_id, model_id)


async def run_orchestration(request: ChatRequest) -> ChatResponse:
    """
    Run orchestration with ChatRequest and return ChatResponse.
    
    This adapter builds an orchestration_config from the ChatRequest,
    uses user-selected models if provided, and calls the orchestrator.
    """
    start_time = time.perf_counter()
    
    try:
        # Determine reasoning method
        if request.reasoning_method:
            reasoning_method = RouterReasoningMethod(request.reasoning_method.value)
        else:
            # Infer from reasoning_mode for backward compatibility
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
            # Auto-select models based on reasoning method
            selected_models = get_models_for_reasoning_method(
                reasoning_method,
                available_models=available_providers,
            )
            
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
            "use_hrm": request.orchestration.enable_hrm,
            "use_prompt_diffusion": request.orchestration.enable_prompt_diffusion,
            "use_deep_consensus": request.orchestration.enable_deep_consensus,
            "use_adaptive_routing": request.orchestration.enable_adaptive_ensemble,
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
        # STEP 0: RAG AUGMENTATION (If enabled)
        # ========================================================================
        enable_rag = getattr(request.orchestration, 'enable_vector_rag', False)
        user_id = metadata_dict.get('user_id')
        project_id = metadata_dict.get('project_id')
        
        if enable_rag and KNOWLEDGE_BASE_AVAILABLE:
            try:
                augmented_prompt = await _augment_with_rag(
                    prompt=request.prompt,
                    domain=request.domain_pack.value,
                    user_id=user_id,
                    project_id=project_id,
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
        # STEP 1.5: TOOL BROKER - Automatic Tool Detection and Execution
        # ========================================================================
        tool_context = ""
        tool_results_info: Dict[str, Any] = {"used": False}
        
        if TOOL_BROKER_AVAILABLE and (prompt_spec is None or prompt_spec.analysis.requires_tools):
            try:
                broker = get_tool_broker()
                tool_analysis = broker.analyze_tool_needs(base_prompt)
                
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
                        tool_instruction = (
                            "\n\n=== IMPORTANT: REAL-TIME DATA BELOW ===\n"
                            "The following information was retrieved from current web searches. "
                            "You MUST use this data to answer the question. Do NOT claim you cannot "
                            "access current information - the data below is current as of today.\n\n"
                            f"{tool_context}\n"
                            "=== END OF REAL-TIME DATA ===\n\n"
                            "Based on the real-time data above, provide a comprehensive answer."
                        )
                        base_prompt = f"{base_prompt}{tool_instruction}"
                        logger.info("Tool context added to prompt with instructions (%d chars)", len(tool_context))
            except Exception as e:
                logger.warning("Tool Broker failed: %s", e)
        
        # ========================================================================
        # STEP 2: AUTOMATIC MODEL SELECTION (When user selected "automatic")
        # ========================================================================
        # Check if we should use automatic model selection
        is_automatic_mode = (
            not request.models or  # No models provided
            len(request.models) == 0 or  # Empty list
            (len(request.models) == 1 and request.models[0].lower() in ["automatic", "auto"])
        )
        
        if is_automatic_mode and detected_task_type != "general":
            logger.info("Automatic mode: Re-selecting models based on task type '%s'", detected_task_type)
            
            # Get best models for the detected task type
            auto_selected = get_best_models_for_task(
                detected_task_type,
                available_models=available_providers,
                num_models=3,
                criteria=criteria_settings,
            )
            
            # For ensemble, ensure diversity
            if orchestration_config.get("accuracy_level", 3) >= 3:
                auto_selected = get_diverse_ensemble(
                    detected_task_type,
                    available_models=available_providers,
                    num_models=min(3, len(available_providers)),
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
                "Automatic model selection: task=%s -> models=%s",
                detected_task_type,
                actual_models,
            )
        
        # Enhance prompt with reasoning method template
        enhanced_prompt = get_reasoning_prompt_template(
            reasoning_method,
            base_prompt,
            domain_pack=request.domain_pack.value,
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
        use_elite = (
            ELITE_AVAILABLE and 
            accuracy_level >= 3 and 
            len(actual_models) >= 2
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
                    # Select strategy based on accuracy, task, complexity, and user criteria
                    strategy = _select_elite_strategy(
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
            artifacts = await _orchestrator.orchestrate(
                enhanced_prompt,
                actual_models,
                use_hrm=orchestration_config.get("use_hrm", False),
                use_adaptive_routing=orchestration_config.get("use_adaptive_routing", False),
                use_deep_consensus=orchestration_config.get("use_deep_consensus", False),
                use_prompt_diffusion=orchestration_config.get("use_prompt_diffusion", False),
                accuracy_level=accuracy_level,
            )
            final_text = artifacts.final_response.content
        
        # Apply quality boosting for high accuracy requests
        if QUALITY_BOOSTER_AVAILABLE and accuracy_level >= 4:
            booster = _get_quality_booster()
            if booster:
                try:
                    logger.info("Applying quality boost for high-accuracy request")
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
                # Detect output format from PromptOps analysis
                output_format = OutputFormat.PARAGRAPH
                if prompt_spec and prompt_spec.analysis.output_format:
                    format_map = {
                        "json": OutputFormat.JSON,
                        "markdown": OutputFormat.MARKDOWN,
                        "code": OutputFormat.CODE,
                        "list": OutputFormat.BULLET,
                        "table": OutputFormat.TABLE,
                    }
                    output_format = format_map.get(
                        prompt_spec.analysis.output_format,
                        OutputFormat.PARAGRAPH
                    )
                
                refiner_config = RefinementConfig(
                    output_format=output_format,
                    tone=ToneStyle.PROFESSIONAL,
                    include_confidence=accuracy_level >= 4,
                    include_citations=accuracy_level >= 3,
                    preserve_structure=True,
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
        
        return response
        
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.exception("Orchestration failed: %s", exc)
        
        # Return error response
        return ChatResponse(
            message=f"I apologize, but I encountered an error processing your request: {str(exc)}",
            models_used=request.models or [],
            reasoning_mode=request.reasoning_mode,
            reasoning_method=request.reasoning_method,
            domain_pack=request.domain_pack,
            agent_mode=request.agent_mode,
            used_tuning=request.tuning,
            metadata=request.metadata,
            latency_ms=latency_ms,
            agent_traces=[],
            extra={"error": str(exc)},
        )

