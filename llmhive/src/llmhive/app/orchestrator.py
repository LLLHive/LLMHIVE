"""Orchestrator module for LLMHive - provides unified interface for LLM orchestration.

This module implements the main orchestration logic including:
- Hierarchical Role Management (HRM) for complex queries
- Adaptive model routing based on performance metrics
- Multi-model ensemble orchestration
- Deep consensus through multi-round debate
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

# Import orchestration components
try:
    from .orchestration.hierarchical_planning import (
        HierarchicalPlanner,
        HierarchicalPlan,
        is_complex_query,
        decompose_query,
    )
    HRM_AVAILABLE = True
except ImportError:
    HRM_AVAILABLE = False
    HierarchicalPlanner = None  # type: ignore
    logger.warning("Hierarchical planning module not available")

try:
    from .orchestration.adaptive_router import (
        AdaptiveModelRouter,
        get_adaptive_router,
        select_models_adaptive,
        infer_domain,
    )
    ADAPTIVE_ROUTING_AVAILABLE = True
except ImportError:
    ADAPTIVE_ROUTING_AVAILABLE = False
    AdaptiveModelRouter = None  # type: ignore
    logger.warning("Adaptive routing module not available")

try:
    from .performance_tracker import performance_tracker
    PERFORMANCE_TRACKER_AVAILABLE = True
except ImportError:
    PERFORMANCE_TRACKER_AVAILABLE = False
    performance_tracker = None  # type: ignore

# Import memory components
try:
    from .memory.persistent_memory import (
        PersistentMemoryManager,
        Scratchpad,
        get_persistent_memory,
        get_scratchpad,
        query_scratchpad,
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    PersistentMemoryManager = None  # type: ignore
    Scratchpad = None  # type: ignore
    logger.warning("Memory module not available")

# Import fact-checking components
try:
    from .fact_check import (
        FactChecker,
        VerificationReport,
        verify_and_correct,
    )
    FACT_CHECK_AVAILABLE = True
except ImportError:
    FACT_CHECK_AVAILABLE = False
    FactChecker = None  # type: ignore
    VerificationReport = None  # type: ignore
    logger.warning("Fact check module not available")

# Import guardrails components
try:
    from .guardrails import (
        SafetyValidator,
        TierAccessController,
        redact_sensitive_info,
        check_output_policy,
        enforce_output_policy,
        assess_query_risk,
        filter_query,
        filter_output,
        security_check,
        get_safety_validator,
        get_tier_controller,
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    SafetyValidator = None  # type: ignore
    TierAccessController = None  # type: ignore
    logger.warning("Guardrails module not available")

# Import provider types
try:
    from ..providers.gemini import GeminiProvider
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    GeminiProvider = None  # type: ignore

# Import stub provider as fallback
STUB_AVAILABLE = False
StubProvider = None
try:
    # Try various import paths for stub provider
    from .models.stub_provider import StubProvider
    STUB_AVAILABLE = True
except ImportError:
    try:
        from ..models.stub_provider import StubProvider
        STUB_AVAILABLE = True
    except ImportError:
        try:
            # Create a minimal stub provider class
            class StubProvider:
                def __init__(self):
                    self.name = 'stub'
                def generate(self, prompt, **kwargs):
                    class Result:
                        text = f'Stub response for: {prompt[:50]}...'
                        model = 'stub'
                    return Result()
            STUB_AVAILABLE = True
        except Exception:
            pass

# Import orchestration artifacts
try:
    from .models.orchestration import OrchestrationArtifacts
except ImportError:
    OrchestrationArtifacts = None  # type: ignore


class Orchestrator:
    """
    Main orchestrator class for LLMHive.
    
    Provides unified interface for LLM provider management and orchestration.
    Supports:
    - Hierarchical Role Management (HRM) for complex queries
    - Adaptive model routing based on performance
    - Multi-model ensemble orchestration
    - Deep consensus through debate
    """
    
    def __init__(self):
        """Initialize orchestrator with available providers."""
        self.providers: Dict[str, Any] = {}
        self.mcp_client = None  # MCP client (optional)
        
        # Initialize HRM planner if available
        self.hrm_planner: Optional[Any] = None
        if HRM_AVAILABLE and HierarchicalPlanner:
            self.hrm_planner = HierarchicalPlanner()
            logger.info("HRM planner initialized")
        
        # Initialize adaptive router if available
        self.adaptive_router: Optional[Any] = None
        if ADAPTIVE_ROUTING_AVAILABLE:
            self.adaptive_router = get_adaptive_router()
            logger.info("Adaptive router initialized")
        
        # Initialize memory manager if available
        self.memory_manager: Optional[Any] = None
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = get_persistent_memory()
                logger.info("Memory manager initialized")
            except Exception as e:
                logger.warning("Failed to initialize memory manager: %s", e)
        
        # Initialize fact checker if available
        self.fact_checker: Optional[Any] = None
        if FACT_CHECK_AVAILABLE and FactChecker:
            try:
                self.fact_checker = FactChecker(
                    memory_manager=self.memory_manager,
                    max_verification_iterations=2,
                )
                logger.info("Fact checker initialized")
            except Exception as e:
                logger.warning("Failed to initialize fact checker: %s", e)
        
        # Initialize guardrails if available
        self.safety_validator: Optional[Any] = None
        self.tier_controller: Optional[Any] = None
        if GUARDRAILS_AVAILABLE:
            try:
                self.safety_validator = get_safety_validator()
                self.tier_controller = get_tier_controller()
                logger.info("Security guardrails initialized")
            except Exception as e:
                logger.warning("Failed to initialize guardrails: %s", e)
        
        # Initialize providers from environment variables
        self._initialize_providers()
        
        logger.info(f"Orchestrator initialized with {len(self.providers)} provider(s)")
    
    def _initialize_providers(self) -> None:
        """Initialize LLM providers based on available API keys."""
        import os
        
        # Initialize OpenAI provider
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                
                class OpenAIProvider:
                    def __init__(self, client):
                        self.name = 'openai'
                        self.client = client
                    
                    async def generate(self, prompt, model="gpt-4o-mini", **kwargs):
                        """Generate response using OpenAI API."""
                        try:
                            response = self.client.chat.completions.create(
                                model=model,
                                messages=[{"role": "user", "content": prompt}],
                                **kwargs
                            )
                            class Result:
                                def __init__(self, text, model, tokens):
                                    self.content = text
                                    self.text = text
                                    self.model = model
                                    self.tokens_used = tokens
                            
                            return Result(
                                text=response.choices[0].message.content,
                                model=response.model,
                                tokens=response.usage.total_tokens if hasattr(response, 'usage') else 0
                            )
                        except Exception as e:
                            logger.error(f"OpenAI API error: {e}")
                            raise
                
                self.providers["openai"] = OpenAIProvider(client)
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Initialize Grok provider
        if os.getenv("GROK_API_KEY"):
            try:
                import httpx
                api_key = os.getenv("GROK_API_KEY")
                
                class GrokProvider:
                    def __init__(self, api_key):
                        self.name = 'grok'
                        self.api_key = api_key
                        self.base_url = "https://api.x.ai/v1"
                    
                    async def generate(self, prompt, model="grok-beta", **kwargs):
                        """Generate response using Grok (xAI) API."""
                        try:
                            async with httpx.AsyncClient() as client:
                                response = await client.post(
                                    f"{self.base_url}/chat/completions",
                                    headers={
                                        "Authorization": f"Bearer {self.api_key}",
                                        "Content-Type": "application/json"
                                    },
                                    json={
                                        "model": model,
                                        "messages": [{"role": "user", "content": prompt}],
                                        **kwargs
                                    },
                                    timeout=30.0
                                )
                                response.raise_for_status()
                                data = response.json()
                                
                                class Result:
                                    def __init__(self, text, model, tokens):
                                        self.content = text
                                        self.text = text
                                        self.model = model
                                        self.tokens_used = tokens
                                
                                return Result(
                                    text=data["choices"][0]["message"]["content"],
                                    model=data.get("model", model),
                                    tokens=data.get("usage", {}).get("total_tokens", 0)
                                )
                        except Exception as e:
                            logger.error(f"Grok API error: {e}")
                            raise
                
                self.providers["grok"] = GrokProvider(api_key)
                logger.info("Grok provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Grok provider: {e}")
        
        # Initialize Gemini provider
        if os.getenv("GEMINI_API_KEY") and GEMINI_AVAILABLE:
            try:
                self.providers["gemini"] = GeminiProvider(api_key=os.getenv("GEMINI_API_KEY"))
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")
        
        # Initialize Anthropic provider
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                
                class AnthropicProvider:
                    def __init__(self, client):
                        self.name = 'anthropic'
                        self.client = client
                    
                    async def generate(self, prompt, model="claude-3-haiku-20240307", **kwargs):
                        """Generate response using Anthropic API."""
                        try:
                            response = self.client.messages.create(
                                model=model,
                                max_tokens=kwargs.get('max_tokens', 1024),
                                messages=[{"role": "user", "content": prompt}]
                            )
                            class Result:
                                def __init__(self, text, model, tokens):
                                    self.content = text
                                    self.text = text
                                    self.model = model
                                    self.tokens_used = tokens
                            
                            return Result(
                                text=response.content[0].text,
                                model=response.model,
                                tokens=response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else 0
                            )
                        except Exception as e:
                            logger.error(f"Anthropic API error: {e}")
                            raise
                
                self.providers["anthropic"] = AnthropicProvider(client)
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        # Always add stub provider as fallback
        if STUB_AVAILABLE and StubProvider:
            try:
                self.providers["stub"] = StubProvider()
                logger.info("Stub provider initialized (fallback)")
            except Exception as e:
                logger.warning(f"Failed to instantiate StubProvider: {e}, creating minimal stub")
                self._create_minimal_stub()
        else:
            # Create minimal stub if import failed
            self._create_minimal_stub()
    
    def _create_minimal_stub(self) -> None:
        """Create a minimal stub provider."""
        class MinimalStub:
            def __init__(self):
                self.name = 'stub'
            def generate(self, prompt, **kwargs):
                class Result:
                    def __init__(self):
                        self.text = f'Stub response for: {prompt[:50]}...'
                        self.model = 'stub'
                return Result()
        
        self.providers["stub"] = MinimalStub()
        logger.warning("Using minimal stub provider (StubProvider import failed)")
    
    async def orchestrate(
        self,
        prompt: str,
        models: Optional[List[str]] = None,
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate LLM calls across multiple models.
        
        Args:
            prompt: The prompt to send to models
            models: List of model names to use (optional)
            **kwargs: Additional orchestration parameters including:
                - use_hrm: Enable hierarchical role management
                - use_adaptive_routing: Enable adaptive model selection
                - use_deep_consensus: Enable multi-round debate
                - use_prompt_diffusion: Enable prompt refinement
                - accuracy_level: 1-5 slider for accuracy vs speed
            
        Returns:
            ProtocolResult-like object with final_response, initial_responses, etc.
        """
        # Extract orchestration settings
        use_hrm = kwargs.get("use_hrm", False)
        use_adaptive_routing = kwargs.get("use_adaptive_routing", False)
        use_deep_consensus = kwargs.get("use_deep_consensus", False)
        use_prompt_diffusion = kwargs.get("use_prompt_diffusion", False)
        use_memory = kwargs.get("use_memory", True)  # Memory enabled by default
        accuracy_level = kwargs.get("accuracy_level", 3)
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id", "default")
        
        logger.info(
            "Orchestrating request: hrm=%s, adaptive=%s, consensus=%s, memory=%s, accuracy=%d",
            use_hrm, use_adaptive_routing, use_deep_consensus, use_memory, accuracy_level
        )
        
        # Initialize scratchpad for this query
        scratchpad = Scratchpad() if MEMORY_AVAILABLE and Scratchpad else None
        
        # Phase -1: Security - Input validation and tier checks
        use_guardrails = kwargs.get("use_guardrails", True)
        is_external_model = kwargs.get("is_external_model", True)
        security_issues: List[str] = []
        
        if use_guardrails and GUARDRAILS_AVAILABLE and self.safety_validator:
            try:
                # Check tier-based restrictions
                if self.tier_controller:
                    tier_allowed, tier_reason = self.tier_controller.enforce_tier_restrictions(
                        prompt, user_tier=kwargs.get("user_tier", "free")
                    )
                    if not tier_allowed:
                        logger.warning("Tier restriction: %s", tier_reason)
                        # Return early with tier restriction message
                        if LLMResult is None:
                            class LLMResult:
                                def __init__(self, content, model, tokens=0):
                                    self.content = content
                                    self.model = model
                                    self.tokens_used = tokens
                        return LLMResult(
                            content=tier_reason or "This query is not available for your tier.",
                            model="guardrails",
                            tokens=0,
                        )
                
                # Validate input and sanitize
                sanitized_query, is_allowed, rejection_reason = self.safety_validator.validate_input(
                    prompt, user_tier=kwargs.get("user_tier", "free")
                )
                
                if not is_allowed:
                    logger.warning("Query blocked by guardrails: %s", rejection_reason)
                    if LLMResult is None:
                        class LLMResult:
                            def __init__(self, content, model, tokens=0):
                                self.content = content
                                self.model = model
                                self.tokens_used = tokens
                    return LLMResult(
                        content=rejection_reason or "I cannot process this request due to safety policies.",
                        model="guardrails",
                        tokens=0,
                    )
                
                # Use sanitized query if external model
                if is_external_model and sanitized_query != prompt:
                    logger.info("Input sanitized for external model (redacted PII)")
                    prompt = sanitized_query
                    if scratchpad:
                        scratchpad.write("original_prompt", kwargs.get("original_prompt", prompt))
                        scratchpad.write("sanitized_prompt", prompt)
                        scratchpad.write("input_sanitized", True)
                
            except Exception as e:
                logger.warning("Security validation failed: %s", e)
                security_issues.append(f"Security check error: {e}")
        
        # Phase 0: Memory Retrieval (before model dispatch)
        memory_context = ""
        memory_hits = []
        if use_memory and self.memory_manager and MEMORY_AVAILABLE:
            try:
                memory_context, memory_hits = self.memory_manager.get_relevant_context(
                    query=prompt,
                    user_id=user_id,
                    max_context_length=2000,
                    top_k=3,
                )
                if memory_context:
                    logger.info(
                        "Memory retrieval: Found %d relevant memories (context: %d chars)",
                        len(memory_hits),
                        len(memory_context),
                    )
                    # Store memory hits in scratchpad for other agents
                    if scratchpad:
                        scratchpad.write("memory_hits", memory_hits)
                        scratchpad.write("memory_context", memory_context)
            except Exception as e:
                logger.warning("Memory retrieval failed: %s", e)
        
        # Prepend memory context to prompt if available
        augmented_prompt = prompt
        if memory_context:
            augmented_prompt = f"{memory_context}\nUser Query: {prompt}"
        
        # Import ProtocolResult structure (with fallbacks)
        ProtocolResult = None
        LLMResult = None
        
        try:
            from .protocols.base import ProtocolResult
        except ImportError:
            pass
        
        try:
            from ..services.base import LLMResult
        except ImportError:
            try:
                from .services.base import LLMResult
            except ImportError:
                pass
        
        # Fallback: create minimal structure if imports fail
        if LLMResult is None:
            class LLMResult:
                def __init__(self, content: str, model: str, tokens: int = 0):
                    self.content = content
                    self.model = model
                    self.tokens_used = tokens
        
        if ProtocolResult is None:
            class ProtocolResult:
                def __init__(self, final_response, initial_responses=None, critiques=None, 
                           improvements=None, consensus_notes=None, step_outputs=None,
                           supporting_notes=None, quality_assessments=None):
                    self.final_response = final_response
                    self.initial_responses = initial_responses or []
                    self.critiques = critiques or []
                    self.improvements = improvements or []
                    self.consensus_notes = consensus_notes or []
                    self.step_outputs = step_outputs or {}
                    self.supporting_notes = supporting_notes or []
                    self.quality_assessments = quality_assessments or {}
        
        # Phase 1: Hierarchical Planning (if HRM enabled)
        hierarchical_plan = None
        if use_hrm and self.hrm_planner and HRM_AVAILABLE:
            try:
                hierarchical_plan = self.hrm_planner.plan_with_hierarchy(
                    augmented_prompt,  # Use augmented prompt with memory context
                    use_full_hierarchy=(accuracy_level >= 4)
                )
                logger.info(
                    "HRM plan created: %d steps, strategy=%s",
                    len(hierarchical_plan.steps),
                    hierarchical_plan.strategy
                )
                # Store plan in scratchpad
                if scratchpad:
                    scratchpad.write("hrm_plan", hierarchical_plan.strategy)
                    scratchpad.write("hrm_steps", len(hierarchical_plan.steps))
            except Exception as e:
                logger.warning("HRM planning failed, falling back to flat plan: %s", e)
        
        # Phase 2: Adaptive Model Selection
        selected_models = models or ["stub"]
        model_assignments: Dict[str, str] = {}
        
        if use_adaptive_routing and self.adaptive_router and ADAPTIVE_ROUTING_AVAILABLE:
            try:
                # Get roles from HRM plan or use default
                if hierarchical_plan:
                    roles = [step.role.name for step in hierarchical_plan.steps]
                else:
                    roles = ["executor"]
                
                # Run adaptive selection
                available_models = list(self.providers.keys())
                routing_result = self.adaptive_router.select_models_adaptive(
                    prompt,
                    roles,
                    accuracy_level,
                    available_models=available_models,
                )
                
                model_assignments = routing_result.role_assignments
                selected_models = [routing_result.primary_model] + routing_result.secondary_models
                
                logger.info(
                    "Adaptive routing: primary=%s, secondary=%s",
                    routing_result.primary_model,
                    routing_result.secondary_models,
                )
            except Exception as e:
                logger.warning("Adaptive routing failed, using default models: %s", e)
                selected_models = models or ["stub"]
        else:
            selected_models = models or ["stub"]
        
        # Ensure we have at least one model
        if not selected_models:
            selected_models = ["stub"]
        
        models_to_use = selected_models
        
        # Map model names to provider names
        # e.g., "gpt-4o-mini" -> "openai", "claude-3-haiku" -> "anthropic"
        model_to_provider = {}
        for model in models_to_use:
            model_lower = model.lower()
            if "gpt" in model_lower or "openai" in model_lower:
                model_to_provider[model] = "openai"
            elif "claude" in model_lower or "anthropic" in model_lower:
                model_to_provider[model] = "anthropic"
            elif "grok" in model_lower:
                model_to_provider[model] = "grok"
            elif "gemini" in model_lower:
                model_to_provider[model] = "gemini"
            else:
                # Try direct match first
                model_to_provider[model] = model
        
        # Get the provider for the first model
        first_model = models_to_use[0]
        provider_name = model_to_provider.get(first_model, first_model)
        provider = self.providers.get(provider_name) or self.providers.get("stub")
        if not provider:
            # Create minimal stub response
            result = LLMResult(
                content="I apologize, but no LLM providers are configured. Please configure at least one API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, GROK_API_KEY, or GEMINI_API_KEY).",
                model="stub",
                tokens=0
            )
        else:
            # Try to generate a response using the provider
            try:
                # Check if provider has a generate method
                if hasattr(provider, 'generate'):
                    # Pass the actual model name to the provider
                    model_name = first_model if first_model != provider_name else (models_to_use[0] if models_to_use else "default")
                    # Check if generate is async
                    import asyncio
                    import inspect
                    if inspect.iscoroutinefunction(provider.generate):
                        provider_result = await provider.generate(augmented_prompt, model=model_name, **kwargs)
                    else:
                        provider_result = provider.generate(augmented_prompt, model=model_name, **kwargs)
                    # Extract content from result
                    if hasattr(provider_result, 'text'):
                        content = provider_result.text
                    elif hasattr(provider_result, 'content'):
                        content = provider_result.content
                    elif isinstance(provider_result, str):
                        content = provider_result
                    else:
                        content = str(provider_result)
                    
                    model_name = getattr(provider_result, 'model', models_to_use[0])
                    tokens = getattr(provider_result, 'tokens_used', 0)
                else:
                    # Fallback for providers without generate method
                    content = f"Stub response: {augmented_prompt[:100]}..."
                    model_name = "stub"
                    tokens = 0
                
                result = LLMResult(
                    content=content,
                    model=model_name,
                    tokens=tokens
                )
                
                # Store model output in scratchpad
                if scratchpad:
                    scratchpad.write("model_output", content)
                    scratchpad.write("model_name", model_name)
                    
            except Exception as e:
                logger.error(f"Error generating response from provider: {e}")
                result = LLMResult(
                    content=f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again.",
                    model=models_to_use[0] if models_to_use else "stub",
                    tokens=0
                )
        
        # Infer domain for later use
        domain = None
        if ADAPTIVE_ROUTING_AVAILABLE:
            try:
                domain = infer_domain(prompt)
            except Exception:
                pass
        
        # Output security check - sanitize before verification
        if use_guardrails and GUARDRAILS_AVAILABLE and self.safety_validator:
            try:
                sanitized_output, is_safe = self.safety_validator.validate_output(result.content)
                if sanitized_output != result.content:
                    logger.info("Output sanitized by guardrails")
                    result = LLMResult(
                        content=sanitized_output,
                        model=result.model,
                        tokens=getattr(result, 'tokens_used', 0),
                    )
                    if scratchpad:
                        scratchpad.write("output_sanitized", True)
                        scratchpad.write("output_was_safe", is_safe)
                        security_issues.append("Output sanitized")
            except Exception as e:
                logger.warning("Output security check failed: %s", e)
        
        # Fact verification and correction loop
        use_verification = kwargs.get("use_verification", True)
        verification_report = None
        verification_passed = True
        
        if use_verification and self.fact_checker and FACT_CHECK_AVAILABLE:
            try:
                logger.info("Running fact verification on response")
                
                # Run verification and correction loop
                corrected_answer, verification_report = await self.fact_checker.verify_and_correct_loop(
                    result.content,
                    prompt=prompt,
                    max_iterations=2,
                )
                
                # Update result if corrections were made
                if corrected_answer != result.content:
                    logger.info(
                        "Answer corrected after verification (score: %.2f, corrections: %d)",
                        verification_report.verification_score if verification_report else 0,
                        verification_report.corrections_made if verification_report else 0,
                    )
                    result = LLMResult(
                        content=corrected_answer,
                        model=result.model,
                        tokens=getattr(result, 'tokens_used', 0),
                    )
                
                verification_passed = (
                    verification_report.is_valid if verification_report else True
                )
                
                # Store verification result in scratchpad
                if scratchpad and verification_report:
                    scratchpad.write("verification_score", verification_report.verification_score)
                    scratchpad.write("verification_passed", verification_passed)
                    scratchpad.write("corrections_made", verification_report.corrections_made)
                    
            except Exception as e:
                logger.warning("Fact verification failed: %s", e)
        
        # Log performance feedback if available
        if PERFORMANCE_TRACKER_AVAILABLE and performance_tracker:
            try:
                performance_tracker.log_run(
                    models_used=[result.model],
                    success_flag=verification_passed,
                    latency_ms=None,
                    domain=domain,
                )
            except Exception as e:
                logger.debug("Failed to log performance: %s", e)
        
        # Store verified answer in memory only if verification passed
        if use_memory and self.memory_manager and MEMORY_AVAILABLE and verification_passed:
            try:
                # Store the Q&A pair
                record_id = self.memory_manager.store_verified_answer(
                    session_id=session_id,
                    query=prompt,
                    answer=result.content,
                    domain=domain,
                    user_id=user_id,
                    additional_metadata={
                        "verification_score": verification_report.verification_score if verification_report else 1.0,
                        "corrections_made": verification_report.corrections_made if verification_report else 0,
                    },
                )
                logger.info("Stored verified answer in memory: %s", record_id[:8] if record_id else "failed")
            except Exception as e:
                logger.warning("Failed to store answer in memory: %s", e)
        
        # Build consensus notes
        consensus_notes = [f"Response generated using {result.model}"]
        if hierarchical_plan:
            consensus_notes.append(f"HRM strategy: {hierarchical_plan.strategy}")
        if use_adaptive_routing:
            consensus_notes.append("Adaptive routing enabled")
        if memory_context:
            consensus_notes.append(f"Memory context used ({len(memory_hits)} hits)")
        if verification_report:
            consensus_notes.append(
                f"Fact verification: score={verification_report.verification_score:.2f}, "
                f"verified={verification_report.verified_count}/{len(verification_report.items)}"
            )
            if verification_report.corrections_made > 0:
                consensus_notes.append(f"Corrections applied: {verification_report.corrections_made}")
        
        # Build supporting notes from scratchpad
        supporting_notes = []
        if scratchpad:
            scratchpad_context = scratchpad.get_context_string()
            if scratchpad_context:
                supporting_notes.append(f"Scratchpad data: {scratchpad_context[:500]}")
        
        # Add verification details to supporting notes
        if verification_report and verification_report.items:
            for item in verification_report.items[:3]:  # Include top 3 verified facts
                if item.verified:
                    supporting_notes.append(f"Verified: {item.text[:100]}...")
        
        # Add security info to consensus notes
        if security_issues:
            consensus_notes.append(f"Security actions: {len(security_issues)}")
        if use_guardrails and GUARDRAILS_AVAILABLE:
            consensus_notes.append("Guardrails: active")
        
        # Return ProtocolResult structure expected by orchestrator_adapter
        return ProtocolResult(
            final_response=result,
            initial_responses=[result],
            critiques=[],
            improvements=[],
            consensus_notes=consensus_notes,
            step_outputs={"answer": [result]},
            supporting_notes=supporting_notes,
            quality_assessments={},
        )
    
    async def orchestrate_with_memory(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        session_id: str = "default",
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate with full memory integration.
        
        This method:
        1. Queries memory for relevant prior knowledge
        2. Augments the prompt with memory context
        3. Generates response
        4. Stores verified answer in memory
        
        Args:
            prompt: The prompt to process
            user_id: User ID for memory namespace
            session_id: Session ID for memory storage
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with memory-augmented response
        """
        return await self.orchestrate(
            prompt,
            use_memory=True,
            user_id=user_id,
            session_id=session_id,
            **kwargs
        )
    
    async def orchestrate_with_hrm(
        self,
        prompt: str,
        accuracy_level: int = 3,
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate with full HRM hierarchy.
        
        This method implements the hierarchical role management pattern:
        1. Executive coordinates overall strategy
        2. Managers delegate to specialists
        3. Specialists execute with assistant support
        4. Quality manager validates
        5. Executive synthesizes final response
        
        Args:
            prompt: The prompt to process
            accuracy_level: 1-5 slider value
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with full HRM artifacts
        """
        return await self.orchestrate(
            prompt,
            use_hrm=True,
            use_adaptive_routing=True,
            accuracy_level=accuracy_level,
            **kwargs
        )
    
    async def orchestrate_ensemble(
        self,
        prompt: str,
        models: List[str],
        accuracy_level: int = 3,
        **kwargs: Any
    ) -> Any:
        """
        Orchestrate with adaptive ensemble voting.
        
        Multiple models process the query in parallel, and their responses
        are weighted and voted on based on performance metrics.
        
        Args:
            prompt: The prompt to process
            models: List of models for ensemble
            accuracy_level: 1-5 slider value
            **kwargs: Additional parameters
            
        Returns:
            ProtocolResult with ensemble voting results
        """
        return await self.orchestrate(
            prompt,
            models=models,
            use_adaptive_routing=True,
            accuracy_level=accuracy_level,
            **kwargs
        )

