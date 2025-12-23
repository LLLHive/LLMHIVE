"""
Deep Model Intelligence - Comprehensive profiles for intelligent orchestration.

This module contains detailed knowledge about each model including:
- Architecture and engineering details
- Strengths and weaknesses with specifics
- Context windows and token limits
- Cost structures (input/output pricing)
- Latency characteristics
- Reasoning capabilities and how to unlock them
- Best use cases and anti-patterns
- Team composition strategies
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class ModelTier(str, Enum):
    """Model quality/cost tier."""
    FLAGSHIP = "flagship"           # Best quality, highest cost
    REASONING = "reasoning"         # Specialized for complex reasoning
    BALANCED = "balanced"           # Good quality/cost ratio
    FAST = "fast"                   # Speed optimized, lower cost
    SPECIALIZED = "specialized"     # Domain-specific (medical, code, etc.)
    BUDGET = "budget"               # Lowest cost, acceptable quality


class ReasoningCapability(str, Enum):
    """Native reasoning capabilities."""
    NATIVE_COT = "native_cot"               # Built-in chain-of-thought (o1, o3)
    PROMPTED_COT = "prompted_cot"           # Responds well to CoT prompts
    SELF_VERIFICATION = "self_verification" # Can verify own answers
    MULTI_STEP = "multi_step"               # Good at multi-step problems
    REFLECTION = "reflection"               # Can reflect and improve
    PLANNING = "planning"                   # Good at planning tasks


@dataclass
class ModelCosts:
    """Pricing structure per million tokens."""
    input_per_million: float    # $ per 1M input tokens
    output_per_million: float   # $ per 1M output tokens
    cached_input: Optional[float] = None  # Cached/prompt caching price


@dataclass
class LatencyProfile:
    """Latency characteristics."""
    time_to_first_token_ms: int     # TTFT in milliseconds
    tokens_per_second: int           # Generation speed
    is_streaming: bool = True        # Supports streaming
    reasoning_overhead_ms: int = 0   # Extra time for reasoning models


@dataclass  
class ModelProfile:
    """Comprehensive model profile for intelligent orchestration."""
    
    # Identity
    model_id: str                    # OpenRouter model ID
    display_name: str                # Human-readable name
    provider: str                    # Provider name
    tier: ModelTier                  # Quality/cost tier
    
    # Architecture
    architecture: str                # e.g., "Transformer", "MoE"
    parameter_count: Optional[str]   # e.g., "175B", "70B", "Unknown"
    context_window: int              # Max context tokens
    max_output_tokens: int           # Max output tokens
    training_cutoff: str             # Knowledge cutoff date
    
    # Capabilities
    strengths: List[str]             # What it excels at
    weaknesses: List[str]            # Known limitations
    best_for: List[str]              # Ideal use cases
    avoid_for: List[str]             # Anti-patterns
    
    # Reasoning
    reasoning_capabilities: Set[ReasoningCapability]
    reasoning_score: int             # 0-100 reasoning ability
    can_be_hacked_to_reason: bool    # Can prompting unlock reasoning?
    reasoning_hack_method: Optional[str]  # How to unlock reasoning
    
    # Costs
    costs: ModelCosts
    
    # Performance
    latency: LatencyProfile
    
    # Special features
    supports_tools: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    supports_structured_output: bool = True
    
    # Team composition
    complements_well_with: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    
    # Quality scores (0-100)
    coding_score: int = 50
    creative_score: int = 50
    factual_score: int = 50
    instruction_following: int = 50


# =============================================================================
# COMPREHENSIVE MODEL PROFILES (December 2025)
# =============================================================================

MODEL_PROFILES: Dict[str, ModelProfile] = {
    
    # =========================================================================
    # OPENAI MODELS
    # =========================================================================
    
    "openai/gpt-5": ModelProfile(
        model_id="openai/gpt-5",
        display_name="GPT-5",
        provider="OpenAI",
        tier=ModelTier.FLAGSHIP,
        
        architecture="Transformer (GPT-5 architecture)",
        parameter_count="Unknown (estimated 1T+)",
        context_window=256000,
        max_output_tokens=32768,
        training_cutoff="October 2025",
        
        strengths=[
            "State-of-the-art general intelligence",
            "Exceptional instruction following",
            "Strong multi-step reasoning",
            "Excellent code generation and debugging",
            "Superior factual accuracy",
            "Best-in-class tool use",
            "Handles ambiguous queries well",
        ],
        weaknesses=[
            "Highest cost tier",
            "Can be verbose for simple tasks",
            "May overthink straightforward questions",
            "Slower than GPT-4o for simple tasks",
        ],
        best_for=[
            "Complex multi-step problems",
            "Research and analysis",
            "Code architecture decisions",
            "Medical/legal/financial analysis",
            "Tasks requiring high accuracy",
        ],
        avoid_for=[
            "Simple Q&A (use GPT-4o-mini)",
            "High-volume low-complexity tasks",
            "Cost-sensitive applications",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.MULTI_STEP,
            ReasoningCapability.PLANNING,
            ReasoningCapability.REFLECTION,
        },
        reasoning_score=92,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="Use explicit 'Let's think step by step' + structured output format",
        
        costs=ModelCosts(
            input_per_million=5.00,
            output_per_million=15.00,
            cached_input=2.50,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=400,
            tokens_per_second=80,
        ),
        
        supports_vision=True,
        supports_audio=True,
        
        complements_well_with=["anthropic/claude-opus-4-20250514", "google/gemini-2.0-pro"],
        conflicts_with=[],
        
        coding_score=95,
        creative_score=85,
        factual_score=95,
        instruction_following=98,
    ),
    
    "openai/o1": ModelProfile(
        model_id="openai/o1",
        display_name="o1",
        provider="OpenAI",
        tier=ModelTier.REASONING,
        
        architecture="Reasoning-optimized Transformer with internal chain-of-thought",
        parameter_count="Unknown",
        context_window=200000,
        max_output_tokens=100000,
        training_cutoff="October 2024",
        
        strengths=[
            "NATIVE chain-of-thought reasoning (no prompting needed)",
            "Exceptional at math and logic problems",
            "Best-in-class for complex multi-step reasoning",
            "Self-verification built into the model",
            "Can solve PhD-level problems",
            "Excellent at code debugging and analysis",
            "Handles edge cases well",
        ],
        weaknesses=[
            "SLOW - uses internal reasoning tokens",
            "EXPENSIVE - bills for hidden reasoning tokens",
            "Cannot be streamed (all reasoning happens first)",
            "Overkill for simple questions",
            "May refuse creative tasks",
            "Less good at open-ended creative writing",
        ],
        best_for=[
            "Complex mathematics",
            "Logic puzzles and proofs",
            "Code debugging requiring deep analysis",
            "Scientific reasoning",
            "Problems requiring multiple verification steps",
            "Competitive programming",
        ],
        avoid_for=[
            "Simple factual questions",
            "Creative writing",
            "Chat/conversation",
            "Time-sensitive applications",
            "Cost-sensitive applications",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.NATIVE_COT,
            ReasoningCapability.SELF_VERIFICATION,
            ReasoningCapability.MULTI_STEP,
            ReasoningCapability.REFLECTION,
            ReasoningCapability.PLANNING,
        },
        reasoning_score=98,
        can_be_hacked_to_reason=False,  # Already native
        reasoning_hack_method=None,
        
        costs=ModelCosts(
            input_per_million=15.00,
            output_per_million=60.00,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=5000,  # Very slow TTFT due to reasoning
            tokens_per_second=40,
            is_streaming=False,
            reasoning_overhead_ms=10000,
        ),
        
        supports_vision=True,
        supports_tools=False,  # Limited tool support
        
        complements_well_with=["openai/gpt-4o", "anthropic/claude-sonnet-4-20250514"],
        conflicts_with=[],
        
        coding_score=95,
        creative_score=60,
        factual_score=90,
        instruction_following=85,
    ),
    
    "openai/gpt-4o": ModelProfile(
        model_id="openai/gpt-4o",
        display_name="GPT-4o",
        provider="OpenAI",
        tier=ModelTier.BALANCED,
        
        architecture="Omni Transformer (multimodal native)",
        parameter_count="Unknown",
        context_window=128000,
        max_output_tokens=16384,
        training_cutoff="October 2023",
        
        strengths=[
            "Fast and reliable",
            "Native multimodal (vision, audio)",
            "Good balance of speed and quality",
            "Excellent tool/function calling",
            "Strong instruction following",
            "Good for most general tasks",
        ],
        weaknesses=[
            "Not as strong at deep reasoning as o1",
            "Can be generic in responses",
            "Less creative than Claude",
            "Older knowledge cutoff",
        ],
        best_for=[
            "General-purpose tasks",
            "Multimodal applications",
            "Tool-heavy workflows",
            "Interactive applications",
            "Balanced speed/quality needs",
        ],
        avoid_for=[
            "Complex mathematical proofs (use o1)",
            "Highly creative content (use Claude)",
            "Very recent events",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.MULTI_STEP,
        },
        reasoning_score=85,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="""Use structured prompting:
1. "Let's approach this step-by-step:"
2. Force numbered steps in output
3. Add "Before giving the final answer, verify each step"
4. Use XML tags: <reasoning>...</reasoning><answer>...</answer>""",
        
        costs=ModelCosts(
            input_per_million=2.50,
            output_per_million=10.00,
            cached_input=1.25,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=200,
            tokens_per_second=100,
        ),
        
        supports_vision=True,
        supports_audio=True,
        
        complements_well_with=["openai/o1", "anthropic/claude-sonnet-4-20250514"],
        conflicts_with=[],
        
        coding_score=88,
        creative_score=80,
        factual_score=85,
        instruction_following=92,
    ),
    
    "openai/gpt-4o-mini": ModelProfile(
        model_id="openai/gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider="OpenAI",
        tier=ModelTier.FAST,
        
        architecture="Optimized small Transformer",
        parameter_count="Unknown (smaller)",
        context_window=128000,
        max_output_tokens=16384,
        training_cutoff="October 2023",
        
        strengths=[
            "Very fast",
            "Very cheap",
            "Good for simple tasks",
            "Efficient for high-volume",
            "Still supports tools and vision",
        ],
        weaknesses=[
            "Limited reasoning depth",
            "More likely to make errors",
            "Less nuanced responses",
            "Not suitable for complex tasks",
        ],
        best_for=[
            "Simple Q&A",
            "Classification tasks",
            "Quick summarization",
            "High-volume processing",
            "First-pass filtering",
        ],
        avoid_for=[
            "Complex reasoning",
            "Medical/legal advice",
            "Code architecture",
            "Research tasks",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
        },
        reasoning_score=70,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="Basic CoT works but limited depth. Use for simple reasoning only.",
        
        costs=ModelCosts(
            input_per_million=0.15,
            output_per_million=0.60,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=100,
            tokens_per_second=150,
        ),
        
        supports_vision=True,
        
        complements_well_with=["openai/gpt-4o"],
        conflicts_with=[],
        
        coding_score=75,
        creative_score=70,
        factual_score=75,
        instruction_following=85,
    ),
    
    # =========================================================================
    # ANTHROPIC MODELS
    # =========================================================================
    
    "anthropic/claude-opus-4-20250514": ModelProfile(
        model_id="anthropic/claude-opus-4-20250514",
        display_name="Claude Opus 4",
        provider="Anthropic",
        tier=ModelTier.FLAGSHIP,
        
        architecture="Constitutional AI Transformer",
        parameter_count="Unknown (very large)",
        context_window=200000,
        max_output_tokens=32000,
        training_cutoff="April 2025",
        
        strengths=[
            "BEST for nuanced, complex analysis",
            "Exceptional creative writing",
            "Deep reasoning with natural flow",
            "Excellent at understanding context",
            "Strong ethical reasoning",
            "Best for long-form content",
            "Superior at following complex instructions",
            "Excellent for medical/legal analysis",
        ],
        weaknesses=[
            "Can be overly cautious/refuse edge cases",
            "Expensive",
            "Can be verbose",
            "Slower than Sonnet",
            "Sometimes overexplains",
        ],
        best_for=[
            "Complex research and analysis",
            "Creative writing and storytelling",
            "Medical and legal analysis",
            "Nuanced ethical discussions",
            "Long document analysis",
            "Tasks requiring deep understanding",
        ],
        avoid_for=[
            "Simple factual lookups",
            "Time-critical applications",
            "Tasks requiring quick, short answers",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.SELF_VERIFICATION,
            ReasoningCapability.MULTI_STEP,
            ReasoningCapability.REFLECTION,
            ReasoningCapability.PLANNING,
        },
        reasoning_score=95,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="""Claude responds extremely well to:
1. "Think through this carefully, step by step"
2. Using <thinking>...</thinking> tags for internal reasoning
3. Asking to "consider multiple perspectives"
4. "Before answering, identify potential issues or counterarguments"
5. Extended thinking mode with budget: {"thinking": {"type": "enabled", "budget_tokens": 10000}}""",
        
        costs=ModelCosts(
            input_per_million=15.00,
            output_per_million=75.00,
            cached_input=1.50,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=500,
            tokens_per_second=60,
        ),
        
        supports_vision=True,
        
        complements_well_with=["openai/gpt-5", "openai/o1", "google/gemini-2.0-pro"],
        conflicts_with=[],
        
        coding_score=92,
        creative_score=98,
        factual_score=92,
        instruction_following=95,
    ),
    
    "anthropic/claude-sonnet-4-20250514": ModelProfile(
        model_id="anthropic/claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        provider="Anthropic",
        tier=ModelTier.BALANCED,
        
        architecture="Constitutional AI Transformer (optimized)",
        parameter_count="Unknown (medium-large)",
        context_window=200000,
        max_output_tokens=16000,
        training_cutoff="April 2025",
        
        strengths=[
            "Best balance of speed/quality in Claude family",
            "Excellent for coding",
            "Strong reasoning without Opus cost",
            "Good creative abilities",
            "Reliable and consistent",
            "Fast enough for interactive use",
        ],
        weaknesses=[
            "Not as deep as Opus for complex analysis",
            "Can still be verbose",
            "May refuse edge cases",
        ],
        best_for=[
            "Coding and debugging",
            "Day-to-day analysis",
            "Interactive applications",
            "Balanced quality/cost needs",
            "Code review and explanation",
        ],
        avoid_for=[
            "Very complex research (use Opus)",
            "Budget-constrained high-volume (use Haiku)",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.SELF_VERIFICATION,
            ReasoningCapability.MULTI_STEP,
            ReasoningCapability.REFLECTION,
        },
        reasoning_score=90,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="""Same as Opus but slightly less effective:
1. Use step-by-step prompting
2. <thinking> tags work well
3. "Let me work through this systematically"
4. Extended thinking available but with lower budget""",
        
        costs=ModelCosts(
            input_per_million=3.00,
            output_per_million=15.00,
            cached_input=0.30,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=250,
            tokens_per_second=90,
        ),
        
        supports_vision=True,
        
        complements_well_with=["openai/gpt-4o", "anthropic/claude-opus-4-20250514"],
        conflicts_with=[],
        
        coding_score=95,
        creative_score=88,
        factual_score=88,
        instruction_following=92,
    ),
    
    # =========================================================================
    # GOOGLE MODELS
    # =========================================================================
    
    "google/gemini-2.0-pro": ModelProfile(
        model_id="google/gemini-2.0-pro",
        display_name="Gemini 2.0 Pro",
        provider="Google",
        tier=ModelTier.FLAGSHIP,
        
        architecture="Mixture of Experts Transformer",
        parameter_count="Unknown (MoE, effective ~300B)",
        context_window=2000000,  # 2M context!
        max_output_tokens=8192,
        training_cutoff="November 2024",
        
        strengths=[
            "MASSIVE 2M token context window",
            "Excellent for research and long documents",
            "Strong multimodal capabilities",
            "Fast despite size",
            "Good at factual accuracy",
            "Native grounding with Google Search",
            "Strong at structured data analysis",
        ],
        weaknesses=[
            "Can be inconsistent on some tasks",
            "Sometimes produces generic responses",
            "Less creative than Claude",
            "Occasional formatting issues",
        ],
        best_for=[
            "Long document analysis",
            "Research across many sources",
            "Multimodal tasks",
            "Factual Q&A with verification",
            "Large codebase analysis",
        ],
        avoid_for=[
            "Highly creative content",
            "Nuanced ethical discussions",
            "Tasks requiring personality",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.SELF_VERIFICATION,
            ReasoningCapability.MULTI_STEP,
            ReasoningCapability.PLANNING,
        },
        reasoning_score=90,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="""Gemini responds well to:
1. Explicit step-by-step instructions
2. "Think carefully and verify your answer"
3. Using structured output (JSON mode)
4. Grounding: Enable Google Search for factual verification
5. "Consider multiple sources and cross-reference""",
        
        costs=ModelCosts(
            input_per_million=1.25,
            output_per_million=5.00,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=300,
            tokens_per_second=85,
        ),
        
        supports_vision=True,
        supports_audio=True,
        
        complements_well_with=["anthropic/claude-opus-4-20250514", "openai/gpt-5"],
        conflicts_with=[],
        
        coding_score=88,
        creative_score=75,
        factual_score=92,
        instruction_following=88,
    ),
    
    "google/med-palm-3": ModelProfile(
        model_id="google/med-palm-3",
        display_name="Med-PaLM 3",
        provider="Google",
        tier=ModelTier.SPECIALIZED,
        
        architecture="Medical-specialized Transformer",
        parameter_count="Unknown",
        context_window=128000,
        max_output_tokens=8192,
        training_cutoff="2024",
        
        strengths=[
            "STATE-OF-THE-ART for medical tasks",
            "Trained on medical literature",
            "Understands clinical terminology",
            "Accurate medical reasoning",
            "Appropriate medical caution",
        ],
        weaknesses=[
            "Only suitable for medical domain",
            "Not for general tasks",
            "Limited creativity",
            "Restricted availability",
        ],
        best_for=[
            "Medical question answering",
            "Clinical decision support",
            "Medical literature analysis",
            "Drug interaction queries",
            "Symptom analysis",
        ],
        avoid_for=[
            "Non-medical tasks",
            "Creative writing",
            "General coding",
            "Anything outside healthcare",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.SELF_VERIFICATION,
            ReasoningCapability.MULTI_STEP,
        },
        reasoning_score=92,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="Use clinical reasoning frameworks. Ask for differential diagnosis format.",
        
        costs=ModelCosts(
            input_per_million=3.00,
            output_per_million=12.00,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=400,
            tokens_per_second=70,
        ),
        
        supports_vision=True,  # Medical imaging
        
        complements_well_with=["anthropic/claude-opus-4-20250514", "openai/gpt-5"],
        conflicts_with=[],
        
        coding_score=50,
        creative_score=40,
        factual_score=98,  # For medical facts
        instruction_following=90,
    ),
    
    # =========================================================================
    # META MODELS
    # =========================================================================
    
    "meta-llama/llama-4-70b": ModelProfile(
        model_id="meta-llama/llama-4-70b",
        display_name="Llama 4 70B",
        provider="Meta",
        tier=ModelTier.BALANCED,
        
        architecture="Open-weight Transformer",
        parameter_count="70B",
        context_window=128000,
        max_output_tokens=8192,
        training_cutoff="2024",
        
        strengths=[
            "Open weights - can be fine-tuned",
            "Strong general performance",
            "Good cost-effectiveness",
            "Excellent coding abilities",
            "Active community and tooling",
        ],
        weaknesses=[
            "Not quite at GPT-5/Claude Opus level",
            "Can be inconsistent",
            "Less polished responses",
        ],
        best_for=[
            "Cost-effective general tasks",
            "Coding assistance",
            "Tasks where fine-tuning helps",
            "Open-source deployments",
        ],
        avoid_for=[
            "Highest-stakes decisions",
            "Tasks requiring maximum accuracy",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.MULTI_STEP,
        },
        reasoning_score=85,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="Standard CoT prompting works. Use clear step-by-step instructions.",
        
        costs=ModelCosts(
            input_per_million=0.50,
            output_per_million=1.50,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=200,
            tokens_per_second=90,
        ),
        
        complements_well_with=["openai/gpt-4o", "anthropic/claude-sonnet-4-20250514"],
        conflicts_with=[],
        
        coding_score=88,
        creative_score=80,
        factual_score=85,
        instruction_following=85,
    ),
    
    # =========================================================================
    # MISTRAL MODELS
    # =========================================================================
    
    "mistralai/mistral-large-2": ModelProfile(
        model_id="mistralai/mistral-large-2",
        display_name="Mistral Large 2",
        provider="Mistral AI",
        tier=ModelTier.BALANCED,
        
        architecture="Mixture of Experts",
        parameter_count="Unknown (MoE)",
        context_window=128000,
        max_output_tokens=8192,
        training_cutoff="2024",
        
        strengths=[
            "Excellent multilingual support",
            "Strong reasoning abilities",
            "Good code generation",
            "European compliance focus",
            "Fast for its capability level",
        ],
        weaknesses=[
            "Less known/tested than OpenAI/Anthropic",
            "Smaller ecosystem",
            "Occasional consistency issues",
        ],
        best_for=[
            "Multilingual applications",
            "European deployments",
            "Balanced cost/quality needs",
            "Code generation",
        ],
        avoid_for=[
            "Maximum accuracy requirements",
            "US-centric compliance needs",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.MULTI_STEP,
        },
        reasoning_score=85,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="Standard CoT works well. Responds to structured prompts.",
        
        costs=ModelCosts(
            input_per_million=2.00,
            output_per_million=6.00,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=200,
            tokens_per_second=100,
        ),
        
        complements_well_with=["openai/gpt-4o", "anthropic/claude-sonnet-4-20250514"],
        conflicts_with=[],
        
        coding_score=88,
        creative_score=82,
        factual_score=85,
        instruction_following=88,
    ),
    
    # =========================================================================
    # SPECIALIZED MODELS
    # =========================================================================
    
    "deepseek/deepseek-chat": ModelProfile(
        model_id="deepseek/deepseek-chat",
        display_name="DeepSeek V3",
        provider="DeepSeek",
        tier=ModelTier.SPECIALIZED,
        
        architecture="MoE Transformer",
        parameter_count="671B (37B active)",
        context_window=128000,
        max_output_tokens=8192,
        training_cutoff="2024",
        
        strengths=[
            "EXCEPTIONAL for coding (near GPT-5 level)",
            "Extremely cost-effective",
            "Strong mathematical abilities",
            "Good reasoning for the price",
            "Open weights available",
        ],
        weaknesses=[
            "Less polished for creative tasks",
            "Chinese company (some restrictions)",
            "Less consistent on non-technical tasks",
            "Knowledge gaps on some topics",
        ],
        best_for=[
            "Code generation and debugging",
            "Mathematical problems",
            "Technical writing",
            "Cost-sensitive applications",
        ],
        avoid_for=[
            "Creative writing",
            "Sensitive/regulated domains",
            "Tasks requiring cultural nuance",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.SELF_VERIFICATION,
            ReasoningCapability.MULTI_STEP,
        },
        reasoning_score=88,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="""DeepSeek responds well to:
1. Explicit step-by-step instructions
2. Code-style structured thinking
3. "Let's break this down systematically"
4. Using markdown headers for organization""",
        
        costs=ModelCosts(
            input_per_million=0.27,
            output_per_million=1.10,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=200,
            tokens_per_second=100,
        ),
        
        complements_well_with=["anthropic/claude-sonnet-4-20250514", "openai/gpt-4o"],
        conflicts_with=[],
        
        coding_score=96,  # Near top
        creative_score=70,
        factual_score=82,
        instruction_following=85,
    ),
    
    "x-ai/grok-2": ModelProfile(
        model_id="x-ai/grok-2",
        display_name="Grok 2",
        provider="xAI",
        tier=ModelTier.BALANCED,
        
        architecture="Transformer",
        parameter_count="Unknown",
        context_window=131072,
        max_output_tokens=8192,
        training_cutoff="Real-time (X integration)",
        
        strengths=[
            "REAL-TIME knowledge via X/Twitter",
            "Less restrictive than other models",
            "Good for current events",
            "Strong personality/wit",
            "Fast responses",
        ],
        weaknesses=[
            "Can be too casual/irreverent",
            "X data may have biases",
            "Less consistent for formal tasks",
            "Newer, less battle-tested",
        ],
        best_for=[
            "Current events questions",
            "Social media analysis",
            "Informal/creative tasks",
            "Real-time information needs",
        ],
        avoid_for=[
            "Formal business documents",
            "Medical/legal advice",
            "Tasks requiring maximum accuracy",
        ],
        
        reasoning_capabilities={
            ReasoningCapability.PROMPTED_COT,
            ReasoningCapability.MULTI_STEP,
        },
        reasoning_score=82,
        can_be_hacked_to_reason=True,
        reasoning_hack_method="Standard CoT prompting. May need to explicitly request formal tone.",
        
        costs=ModelCosts(
            input_per_million=2.00,
            output_per_million=10.00,
        ),
        
        latency=LatencyProfile(
            time_to_first_token_ms=200,
            tokens_per_second=90,
        ),
        
        complements_well_with=["openai/gpt-4o", "anthropic/claude-sonnet-4-20250514"],
        conflicts_with=[],
        
        coding_score=82,
        creative_score=88,
        factual_score=85,  # Real-time helps
        instruction_following=80,
    ),
}


# =============================================================================
# REASONING METHOD PROFILES
# =============================================================================

@dataclass
class ReasoningMethodProfile:
    """Profile for an advanced reasoning method."""
    
    name: str
    description: str
    when_to_use: List[str]
    when_not_to_use: List[str]
    
    # Implementation
    prompt_template: str
    requires_multiple_calls: bool
    typical_token_overhead: float  # Multiplier (e.g., 2.0 = doubles tokens)
    
    # Effectiveness
    effectiveness_by_task: Dict[str, int]  # task_type -> 0-100 score
    
    # Model compatibility
    best_models: List[str]
    works_with_any: bool


REASONING_METHODS: Dict[str, ReasoningMethodProfile] = {
    
    "chain_of_thought": ReasoningMethodProfile(
        name="Chain of Thought (CoT)",
        description="Step-by-step reasoning where the model shows its work",
        when_to_use=[
            "Math problems",
            "Logic puzzles",
            "Multi-step reasoning",
            "Problems requiring explanation",
        ],
        when_not_to_use=[
            "Simple factual questions",
            "Creative writing",
            "Speed-critical tasks",
        ],
        prompt_template="""Let's work through this step by step.

{question}

Think through each step carefully, showing your reasoning. Then provide your final answer.""",
        requires_multiple_calls=False,
        typical_token_overhead=2.0,
        effectiveness_by_task={
            "math_problem": 95,
            "logic_puzzle": 90,
            "code_debugging": 85,
            "factual_question": 60,
            "creative_writing": 40,
        },
        best_models=["openai/o1", "anthropic/claude-opus-4-20250514", "openai/gpt-5"],
        works_with_any=True,
    ),
    
    "self_consistency": ReasoningMethodProfile(
        name="Self-Consistency",
        description="Generate multiple solutions and pick the most common answer",
        when_to_use=[
            "Math problems with definite answers",
            "Classification tasks",
            "When verification is critical",
        ],
        when_not_to_use=[
            "Open-ended questions",
            "Creative tasks",
            "Budget-constrained scenarios",
        ],
        prompt_template="""Solve this problem three different ways, then compare your answers.

{question}

Approach 1: [solve independently]
Approach 2: [solve using a different method]
Approach 3: [solve again independently]

Final Answer: [most consistent result]""",
        requires_multiple_calls=True,  # Or can be done in one call
        typical_token_overhead=3.5,
        effectiveness_by_task={
            "math_problem": 95,
            "classification": 90,
            "factual_question": 85,
            "code_generation": 70,
            "creative_writing": 30,
        },
        best_models=["openai/gpt-5", "anthropic/claude-opus-4-20250514", "google/gemini-2.0-pro"],
        works_with_any=True,
    ),
    
    "tree_of_thought": ReasoningMethodProfile(
        name="Tree of Thought (ToT)",
        description="Explore multiple reasoning paths and evaluate each",
        when_to_use=[
            "Complex problems with multiple valid approaches",
            "Strategic planning",
            "Creative problem-solving",
            "When the best approach is unclear",
        ],
        when_not_to_use=[
            "Simple questions",
            "Time-critical tasks",
            "Well-defined procedures",
        ],
        prompt_template="""Let's explore multiple approaches to solve this.

{question}

Generate 3 distinct solution approaches:
1. [Approach A]: Brief description, promise, next steps
2. [Approach B]: Brief description, promise, next steps  
3. [Approach C]: Brief description, promise, next steps

Evaluate each approach and select the most promising. Develop it fully.
If it fails, backtrack to the next best.

Final Answer: [best solution]""",
        requires_multiple_calls=False,
        typical_token_overhead=4.0,
        effectiveness_by_task={
            "strategic_planning": 95,
            "complex_reasoning": 90,
            "code_architecture": 88,
            "creative_problem_solving": 85,
            "simple_math": 50,
        },
        best_models=["anthropic/claude-opus-4-20250514", "openai/gpt-5", "openai/o1"],
        works_with_any=True,
    ),
    
    "reflexion": ReasoningMethodProfile(
        name="Reflexion",
        description="Generate answer, critique it, then improve",
        when_to_use=[
            "When quality matters more than speed",
            "Complex analysis",
            "Writing tasks",
            "Code review",
        ],
        when_not_to_use=[
            "Simple factual questions",
            "Time-critical tasks",
        ],
        prompt_template="""Solve this problem, then reflect and improve.

{question}

Step 1 - Initial Solution:
[Provide your first attempt]

Step 2 - Critical Review:
- What errors or gaps exist?
- What could be improved?
- Are there edge cases not handled?

Step 3 - Improved Solution:
[Revised solution addressing the issues]

Final Answer: [polished result]""",
        requires_multiple_calls=False,
        typical_token_overhead=2.5,
        effectiveness_by_task={
            "writing": 95,
            "code_review": 92,
            "complex_analysis": 90,
            "problem_solving": 85,
            "factual_question": 60,
        },
        best_models=["anthropic/claude-opus-4-20250514", "openai/gpt-5", "anthropic/claude-sonnet-4-20250514"],
        works_with_any=True,
    ),
    
    "react": ReasoningMethodProfile(
        name="ReAct (Reasoning + Acting)",
        description="Interleave reasoning with tool use",
        when_to_use=[
            "Tasks requiring external information",
            "Multi-step tool use",
            "Research tasks",
            "Complex workflows",
        ],
        when_not_to_use=[
            "Pure reasoning tasks",
            "When tools aren't available",
            "Simple questions",
        ],
        prompt_template="""Use this format to solve the problem:

Thought: [your reasoning]
Action: [tool_name(input)]
Observation: [result]
... repeat as needed ...
Final Answer: [answer]

Question: {question}

Available tools: search, calculate, lookup, code_execute""",
        requires_multiple_calls=True,
        typical_token_overhead=3.0,
        effectiveness_by_task={
            "research": 95,
            "fact_checking": 92,
            "multi_step_tasks": 90,
            "tool_heavy_workflows": 95,
            "pure_reasoning": 60,
        },
        best_models=["openai/gpt-5", "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514"],
        works_with_any=False,  # Requires tool-capable models
    ),
}


# =============================================================================
# REASONING HACKS FOR TRADITIONAL MODELS
# =============================================================================

REASONING_HACKS = {
    "force_step_by_step": {
        "description": "Force any model to show reasoning steps",
        "effectiveness": 85,
        "template": """Before answering, you MUST:
1. Identify what the question is really asking
2. List the key facts or constraints
3. Work through the logic step by step
4. Verify your answer before stating it

Question: {question}

Step 1 - Understanding:
Step 2 - Key Facts:
Step 3 - Reasoning:
Step 4 - Verification:
Final Answer:""",
    },
    
    "xml_thinking_tags": {
        "description": "Use XML tags to separate reasoning from answer",
        "effectiveness": 90,
        "template": """Analyze this problem using the following format:

<thinking>
[Your step-by-step reasoning goes here]
[Consider multiple angles]
[Identify potential issues]
</thinking>

<verification>
[Check your reasoning for errors]
[Verify the answer makes sense]
</verification>

<answer>
[Your final, concise answer]
</answer>

Question: {question}""",
    },
    
    "role_as_expert": {
        "description": "Assign expert role to improve domain reasoning",
        "effectiveness": 80,
        "template": """You are an expert {domain} specialist with decades of experience.

Before answering, think like an expert would:
1. What would a specialist consider first?
2. What nuances might a novice miss?
3. What's the most rigorous way to approach this?

Question: {question}

Expert Analysis:""",
    },
    
    "multi_perspective": {
        "description": "Force consideration of multiple viewpoints",
        "effectiveness": 85,
        "template": """Consider this problem from multiple perspectives:

Question: {question}

Perspective 1 - Optimistic view:
[What's the best case interpretation?]

Perspective 2 - Critical view:
[What are the potential problems?]

Perspective 3 - Balanced synthesis:
[What's the most reasonable conclusion considering both?]

Final Answer:""",
    },
    
    "confidence_calibration": {
        "description": "Force model to express and calibrate confidence",
        "effectiveness": 75,
        "template": """Answer this question and rate your confidence:

{question}

Your answer:

Confidence: [0-100%]
- Most certain aspect:
- Least certain aspect:
- What would increase your confidence:""",
    },
}


# =============================================================================
# TEAM COMPOSITION STRATEGIES
# =============================================================================

@dataclass
class TeamStrategy:
    """Strategy for composing a model team."""
    
    name: str
    description: str
    models: List[str]
    roles: Dict[str, str]  # model_id -> role
    orchestration: str  # How to combine results
    best_for: List[str]
    cost_tier: str  # "premium", "balanced", "budget"


TEAM_STRATEGIES: Dict[str, TeamStrategy] = {
    
    "accuracy_critical": TeamStrategy(
        name="Accuracy Critical",
        description="Maximum accuracy for high-stakes decisions",
        models=[
            "anthropic/claude-opus-4-20250514",
            "openai/gpt-5",
            "google/gemini-2.0-pro",
        ],
        roles={
            "anthropic/claude-opus-4-20250514": "Primary analyzer (deep reasoning)",
            "openai/gpt-5": "Secondary verification (different perspective)",
            "google/gemini-2.0-pro": "Fact checker (search grounding)",
        },
        orchestration="expert_panel",
        best_for=["Medical", "Legal", "Financial", "Research"],
        cost_tier="premium",
    ),
    
    "coding_excellence": TeamStrategy(
        name="Coding Excellence",
        description="Best team for code generation and debugging",
        models=[
            "anthropic/claude-sonnet-4-20250514",
            "deepseek/deepseek-chat",
            "openai/gpt-5",
        ],
        roles={
            "anthropic/claude-sonnet-4-20250514": "Primary coder (architecture & implementation)",
            "deepseek/deepseek-chat": "Code optimization (efficiency)",
            "openai/gpt-5": "Code review (best practices)",
        },
        orchestration="challenge_and_refine",
        best_for=["Code generation", "Debugging", "Architecture"],
        cost_tier="balanced",
    ),
    
    "creative_writing": TeamStrategy(
        name="Creative Excellence",
        description="Best team for creative content",
        models=[
            "anthropic/claude-opus-4-20250514",
            "x-ai/grok-2",
            "anthropic/claude-sonnet-4-20250514",
        ],
        roles={
            "anthropic/claude-opus-4-20250514": "Primary creative (nuanced writing)",
            "x-ai/grok-2": "Fresh perspective (wit and edge)",
            "anthropic/claude-sonnet-4-20250514": "Editor (polish and consistency)",
        },
        orchestration="quality_weighted_fusion",
        best_for=["Stories", "Marketing", "Creative content"],
        cost_tier="premium",
    ),
    
    "research_analysis": TeamStrategy(
        name="Research Deep Dive",
        description="Best team for research and analysis",
        models=[
            "google/gemini-2.0-pro",
            "anthropic/claude-opus-4-20250514",
            "openai/o1",
        ],
        roles={
            "google/gemini-2.0-pro": "Primary researcher (long context, grounding)",
            "anthropic/claude-opus-4-20250514": "Analysis synthesizer (nuanced conclusions)",
            "openai/o1": "Logical verification (complex reasoning)",
        },
        orchestration="expert_panel",
        best_for=["Academic research", "Market analysis", "Technical investigation"],
        cost_tier="premium",
    ),
    
    "fast_accurate": TeamStrategy(
        name="Fast & Accurate",
        description="Balanced speed and quality",
        models=[
            "openai/gpt-4o",
            "anthropic/claude-sonnet-4-20250514",
        ],
        roles={
            "openai/gpt-4o": "Primary responder (fast, reliable)",
            "anthropic/claude-sonnet-4-20250514": "Quality check (nuance)",
        },
        orchestration="parallel_race",
        best_for=["General tasks", "Interactive apps", "Moderate complexity"],
        cost_tier="balanced",
    ),
    
    "budget_effective": TeamStrategy(
        name="Budget Effective",
        description="Good quality at low cost",
        models=[
            "deepseek/deepseek-chat",
            "meta-llama/llama-4-70b",
        ],
        roles={
            "deepseek/deepseek-chat": "Primary (coding/technical)",
            "meta-llama/llama-4-70b": "General backup",
        },
        orchestration="single_best",
        best_for=["Cost-sensitive", "High volume", "Development"],
        cost_tier="budget",
    ),
    
    "medical_specialist": TeamStrategy(
        name="Medical Specialist",
        description="Healthcare-focused team",
        models=[
            "google/med-palm-3",
            "anthropic/claude-opus-4-20250514",
            "openai/gpt-5",
        ],
        roles={
            "google/med-palm-3": "Medical specialist (clinical knowledge)",
            "anthropic/claude-opus-4-20250514": "Medical reasoning (complex cases)",
            "openai/gpt-5": "General medical verification",
        },
        orchestration="expert_panel",
        best_for=["Medical Q&A", "Clinical support", "Health research"],
        cost_tier="premium",
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model_profile(model_id: str) -> Optional[ModelProfile]:
    """Get the full profile for a model."""
    return MODEL_PROFILES.get(model_id)


def get_best_models_for_task(
    task_type: str,
    num_models: int = 3,
    max_cost_tier: Optional[ModelTier] = None,
    require_tools: bool = False,
) -> List[str]:
    """Get the best models for a specific task type."""
    candidates = []
    
    for model_id, profile in MODEL_PROFILES.items():
        # Filter by cost tier
        if max_cost_tier:
            tier_order = [ModelTier.BUDGET, ModelTier.FAST, ModelTier.BALANCED, 
                         ModelTier.SPECIALIZED, ModelTier.REASONING, ModelTier.FLAGSHIP]
            if tier_order.index(profile.tier) > tier_order.index(max_cost_tier):
                continue
        
        # Filter by tool support
        if require_tools and not profile.supports_tools:
            continue
        
        # Score based on task
        score = 0
        if task_type in profile.best_for:
            score += 20
        if task_type in profile.avoid_for:
            score -= 50
        
        # Add capability scores
        if "coding" in task_type.lower():
            score += profile.coding_score
        elif "creative" in task_type.lower():
            score += profile.creative_score
        elif any(x in task_type.lower() for x in ["medical", "legal", "factual"]):
            score += profile.factual_score
        else:
            score += profile.instruction_following
        
        score += profile.reasoning_score // 2
        
        candidates.append((model_id, score))
    
    # Sort by score descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    return [model_id for model_id, _ in candidates[:num_models]]


def get_team_for_task(task_type: str) -> Optional[TeamStrategy]:
    """Get the best team strategy for a task."""
    task_lower = task_type.lower()
    
    if any(x in task_lower for x in ["medical", "health", "clinical"]):
        return TEAM_STRATEGIES["medical_specialist"]
    elif any(x in task_lower for x in ["code", "debug", "programming"]):
        return TEAM_STRATEGIES["coding_excellence"]
    elif any(x in task_lower for x in ["creative", "write", "story", "marketing"]):
        return TEAM_STRATEGIES["creative_writing"]
    elif any(x in task_lower for x in ["research", "analysis", "investigate"]):
        return TEAM_STRATEGIES["research_analysis"]
    elif any(x in task_lower for x in ["legal", "financial", "accuracy"]):
        return TEAM_STRATEGIES["accuracy_critical"]
    else:
        return TEAM_STRATEGIES["fast_accurate"]


def get_reasoning_hack(model_id: str, task_type: str) -> Optional[str]:
    """Get the best reasoning hack for a model and task."""
    profile = get_model_profile(model_id)
    if not profile:
        return REASONING_HACKS["force_step_by_step"]["template"]
    
    if profile.reasoning_hack_method:
        # Model has specific hack
        if "xml" in profile.reasoning_hack_method.lower() or "thinking" in profile.reasoning_hack_method.lower():
            return REASONING_HACKS["xml_thinking_tags"]["template"]
    
    # Default based on task
    if any(x in task_type.lower() for x in ["math", "logic", "reason"]):
        return REASONING_HACKS["force_step_by_step"]["template"]
    elif any(x in task_type.lower() for x in ["medical", "legal", "expert"]):
        return REASONING_HACKS["role_as_expert"]["template"]
    elif any(x in task_type.lower() for x in ["analysis", "compare", "evaluate"]):
        return REASONING_HACKS["multi_perspective"]["template"]
    else:
        return REASONING_HACKS["xml_thinking_tags"]["template"]


# =============================================================================
# EMERGING ARCHITECTURES & DEVELOPMENTS (Beyond Current Transformers)
# =============================================================================
# These are next-generation developments that may disrupt current LLM landscape

@dataclass
class EmergingArchitecture:
    """Profile for emerging AI architectures that may outperform transformers."""
    
    name: str
    category: str  # "sub_quadratic", "diffusion", "recurrent", "hybrid", "reasoning"
    description: str
    
    # Technical characteristics
    complexity: str  # O(n), O(n log n), O(n²)
    key_innovation: str
    advantages: List[str]
    disadvantages: List[str]
    
    # Availability
    available_models: List[str]
    production_ready: bool
    estimated_adoption: str  # "2024", "2025", "2026+"
    
    # Strategic implications
    when_to_use: List[str]
    competitive_threat: str  # "high", "medium", "low"


EMERGING_ARCHITECTURES: Dict[str, EmergingArchitecture] = {
    
    # =========================================================================
    # SUB-QUADRATIC ARCHITECTURES (Better than O(n²) attention)
    # =========================================================================
    
    "mamba": EmergingArchitecture(
        name="Mamba (State Space Models)",
        category="sub_quadratic",
        description="""Selective State Space Model that achieves linear time complexity O(n) 
        vs quadratic O(n²) of transformers. Uses selective scan instead of attention.
        Inspired by control theory and signal processing.""",
        
        complexity="O(n) - LINEAR time and memory",
        key_innovation="""Selective state space with input-dependent parameters. 
        Unlike fixed RNNs, selection mechanism allows content-aware processing.
        Hardware-aware algorithm optimizes memory access patterns.""",
        
        advantages=[
            "5x faster inference than transformers on long sequences",
            "Linear memory scaling - can process million+ token contexts",
            "No attention computation bottleneck",
            "Better at modeling long-range dependencies in some tasks",
            "Efficient for streaming/real-time applications",
            "Lower energy consumption per token",
        ],
        disadvantages=[
            "Slightly lower quality on some benchmarks vs top transformers",
            "Less mature tooling and infrastructure",
            "Harder to parallelize training (sequential nature)",
            "May miss some fine-grained attention patterns",
            "Fewer pretrained checkpoints available",
        ],
        
        available_models=["mamba-7b", "mamba-2.8b", "jamba (Mamba+Transformer hybrid)"],
        production_ready=True,
        estimated_adoption="2024-2025",
        
        when_to_use=[
            "Very long context processing (100K+ tokens)",
            "Real-time/streaming applications",
            "Resource-constrained deployments",
            "When inference speed is critical",
        ],
        competitive_threat="high",
    ),
    
    "rwkv": EmergingArchitecture(
        name="RWKV (Receptance Weighted Key Value)",
        category="sub_quadratic",
        description="""Combines transformer expressiveness with RNN efficiency.
        Linear attention mechanism with O(n) complexity. Open-source and community-driven.
        'The Best of Both Worlds' - transformer quality with RNN efficiency.""",
        
        complexity="O(n) - LINEAR",
        key_innovation="""WKV (Weighted Key Value) mechanism replaces quadratic attention.
        Time-mixing and channel-mixing blocks. Can run like RNN at inference
        but train like transformer.""",
        
        advantages=[
            "Constant memory usage during inference (like RNN)",
            "Can be trained at scale like transformers",
            "Open source with active community (RWKV-7 latest)",
            "Good performance on language modeling benchmarks",
            "Efficient for edge deployment",
            "Supports infinite context length theoretically",
        ],
        disadvantages=[
            "Still catching up to top transformer performance",
            "Smaller ecosystem than transformer-based models",
            "Less battle-tested in production",
            "Fewer fine-tuning resources available",
        ],
        
        available_models=["RWKV-7-World", "RWKV-6-14B", "RWKV-5-7B"],
        production_ready=True,
        estimated_adoption="2024-2025",
        
        when_to_use=[
            "Edge/mobile deployment",
            "Infinite context streaming",
            "When open-source is required",
            "Resource-constrained environments",
        ],
        competitive_threat="medium",
    ),
    
    "linear_attention": EmergingArchitecture(
        name="Linear Attention Variants",
        category="sub_quadratic",
        description="""Various approaches to linearize attention: Performer, Linear Transformer,
        FNet, Hyena, Based. Replace O(n²) softmax attention with O(n) alternatives.""",
        
        complexity="O(n) or O(n log n)",
        key_innovation="""Different approaches:
        - Performer: Random feature approximation of softmax
        - FNet: Replace attention with Fourier transform
        - Hyena: Learned convolutions instead of attention
        - Based: Combination of linear attention + sliding window""",
        
        advantages=[
            "Significant speedup on long sequences",
            "Can be retrofitted to existing architectures",
            "Active research area with rapid improvements",
            "Some variants maintain transformer compatibility",
        ],
        disadvantages=[
            "Quality gap vs full attention on many tasks",
            "Each variant has different tradeoffs",
            "Less mature than standard attention",
            "May require retraining from scratch",
        ],
        
        available_models=["Hyena-7B", "Based models", "RetNet variants"],
        production_ready=False,
        estimated_adoption="2025-2026",
        
        when_to_use=[
            "Research and experimentation",
            "Specific long-context applications",
            "When willing to trade quality for speed",
        ],
        competitive_threat="medium",
    ),
    
    # =========================================================================
    # DIFFUSION-BASED LANGUAGE MODELS
    # =========================================================================
    
    "diffusion_lm": EmergingArchitecture(
        name="Diffusion Language Models",
        category="diffusion",
        description="""Apply diffusion process to text generation. Instead of autoregressive
        left-to-right generation, denoise entire sequence iteratively. Models like MDLM,
        Mercury, and Plaid show promising results.""",
        
        complexity="O(n × steps) - depends on diffusion steps",
        key_innovation="""Non-autoregressive generation via iterative denoising.
        Can edit/refine entire sequences, better for controllable generation.
        Parallel decoding possible. Better handling of bidirectional context.""",
        
        advantages=[
            "Parallel generation (not sequential token-by-token)",
            "Better at global coherence and planning",
            "Natural for editing and infilling tasks",
            "Controllable generation via guidance",
            "May be better for structured outputs",
            "Can leverage bidirectional context naturally",
        ],
        disadvantages=[
            "Multiple forward passes needed (slower per sequence)",
            "Discrete text diffusion is harder than continuous (images)",
            "Quality still behind top autoregressive models",
            "Sampling can be slow without optimization",
            "Less intuitive to control than autoregressive",
        ],
        
        available_models=["MDLM", "Mercury", "Plaid", "SSD-LM"],
        production_ready=False,
        estimated_adoption="2025-2026",
        
        when_to_use=[
            "Document editing and revision",
            "Controllable generation with constraints",
            "When global coherence matters more than speed",
            "Structured output generation",
        ],
        competitive_threat="medium",
    ),
    
    # =========================================================================
    # CONTINUOUS REASONING ARCHITECTURES
    # =========================================================================
    
    "continuous_thought_machine": EmergingArchitecture(
        name="Continuous Thought Machine (CTM)",
        category="reasoning",
        description="""Neural architecture where thinking happens in continuous latent space
        over time, not discrete tokens. Allows 'thinking' to take variable time based on
        problem difficulty. Developed by Sakana AI and others.""",
        
        complexity="O(n × thinking_time)",
        key_innovation="""Latent reasoning that isn't bound to token-by-token generation.
        Internal representation evolves continuously until ready to output.
        Thinking time scales with problem difficulty automatically.
        More brain-like than discrete token reasoning.""",
        
        advantages=[
            "Reasoning time adapts to problem complexity",
            "Not constrained to human-readable thinking chains",
            "More efficient than verbose chain-of-thought",
            "Can develop internal representations not expressible in text",
            "Potentially better for abstract reasoning",
        ],
        disadvantages=[
            "Hard to interpret internal reasoning",
            "Less controllable than explicit CoT",
            "Still experimental/research stage",
            "Training is challenging",
            "Harder to verify correctness of reasoning",
        ],
        
        available_models=["Research prototypes only"],
        production_ready=False,
        estimated_adoption="2026+",
        
        when_to_use=[
            "Complex reasoning where explicit CoT is wasteful",
            "Problems requiring deep abstract thinking",
            "When interpretability is less important than correctness",
        ],
        competitive_threat="high (long-term)",
    ),
    
    "test_time_compute": EmergingArchitecture(
        name="Test-Time Compute Scaling (o1/o3 paradigm)",
        category="reasoning",
        description="""Instead of just scaling model size, scale compute at inference time.
        Models like o1 and o3 use internal reasoning tokens to 'think longer' on hard problems.
        Represents paradigm shift from 'bigger models' to 'smarter inference'.""",
        
        complexity="O(n × reasoning_budget)",
        key_innovation="""Inference-time scaling: spend more compute on harder problems.
        Internal chain-of-thought that may not be shown to user.
        Verification and self-correction during generation.
        Quality improves with thinking time budget.""",
        
        advantages=[
            "Same model handles easy AND hard problems efficiently",
            "Can achieve expert-level reasoning on complex tasks",
            "More cost-effective than always using largest model",
            "Self-verification reduces errors",
            "Matches human 'thinking harder' on difficult problems",
        ],
        disadvantages=[
            "Unpredictable latency (depends on problem)",
            "Hidden reasoning tokens increase costs",
            "Can overthink simple problems",
            "Streaming not possible during reasoning phase",
            "Hard to estimate costs upfront",
        ],
        
        available_models=["openai/o1", "openai/o3", "deepseek/deepseek-r1"],
        production_ready=True,
        estimated_adoption="2024 (now)",
        
        when_to_use=[
            "Math and logic problems",
            "Complex coding challenges",
            "Scientific reasoning",
            "When accuracy matters more than speed",
        ],
        competitive_threat="high (already impacting)",
    ),
    
    # =========================================================================
    # HYBRID AND NEURO-SYMBOLIC
    # =========================================================================
    
    "neuro_symbolic": EmergingArchitecture(
        name="Neuro-Symbolic AI",
        category="hybrid",
        description="""Combines neural networks with symbolic reasoning systems.
        Neural handles perception/pattern matching, symbolic handles logic/planning.
        Addresses hallucination and reasoning failures of pure neural approaches.""",
        
        complexity="Varies by implementation",
        key_innovation="""Symbolic reasoning layer over neural foundation.
        Can enforce logical constraints and rules.
        Verifiable reasoning chains.
        Examples: Amazon's Vulcan, Wolfram integration with LLMs.""",
        
        advantages=[
            "Reduced hallucinations through symbolic verification",
            "Explainable reasoning with logical traces",
            "Can enforce domain constraints (legal, medical)",
            "Better at math and formal reasoning",
            "Combines flexibility of neural with rigor of symbolic",
        ],
        disadvantages=[
            "Complex to implement and maintain",
            "May be slower due to symbolic reasoning overhead",
            "Requires domain-specific rule engineering",
            "Not end-to-end learnable",
            "Integration challenges between neural and symbolic",
        ],
        
        available_models=["Wolfram Alpha + GPT", "Amazon Vulcan (internal)", "Various research systems"],
        production_ready=True,  # In limited forms
        estimated_adoption="2024-2025",
        
        when_to_use=[
            "High-stakes domains requiring verification",
            "Math and scientific computation",
            "When explainability is required",
            "Compliance-heavy applications",
        ],
        competitive_threat="high",
    ),
    
    "memory_augmented": EmergingArchitecture(
        name="Memory-Augmented / Retrieval Systems",
        category="hybrid",
        description="""Systems with explicit memory components beyond context window.
        Includes RAG, but also newer approaches with surprise-based memory,
        continuous learning, and structured knowledge stores.""",
        
        complexity="O(n + retrieval)",
        key_innovation="""External memory that persists and updates over time.
        Surprise-based learning: store unexpected information.
        Continuous/online learning without retraining.
        Structured memory (graphs) vs unstructured (vectors).""",
        
        advantages=[
            "Effectively infinite knowledge",
            "Can be updated without retraining",
            "Factual grounding reduces hallucination",
            "Personalization through memory",
            "Lower training costs (knowledge in memory, not weights)",
        ],
        disadvantages=[
            "Retrieval latency and accuracy challenges",
            "Memory management complexity",
            "Potential for stale or conflicting information",
            "Security/privacy of memory contents",
        ],
        
        available_models=["All models via RAG", "MemGPT", "Infinite Memory Transformer"],
        production_ready=True,
        estimated_adoption="2024 (now)",
        
        when_to_use=[
            "Knowledge-intensive applications",
            "Personalized assistants",
            "Domain-specific expertise",
            "When information changes frequently",
        ],
        competitive_threat="high (essential for production)",
    ),
}


# =============================================================================
# ADVANCED REASONING DEVELOPMENTS (Beyond Basic CoT)
# =============================================================================

ADVANCED_REASONING_DEVELOPMENTS = {
    
    "chain_of_reasoning": {
        "name": "Chain-of-Reasoning (CoR) - Microsoft",
        "description": """Unifies natural language, code, and symbolic reasoning in one chain.
        Model chooses optimal representation for each step.""",
        "key_insight": "Don't force all reasoning into natural language",
        "implementation": """Let model switch between:
        - Natural language for conceptual steps
        - Code for computation
        - Symbolic logic for formal reasoning
        Then synthesize at the end.""",
        "effectiveness_gain": "20-40% improvement on math problems",
    },
    
    "self_reflection_loops": {
        "name": "Self-Reflection and Critique Loops",
        "description": """Model critiques its own output and iteratively improves.
        Multiple passes with self-assessment.""",
        "key_insight": "One-shot generation is often suboptimal",
        "implementation": """
        1. Generate initial response
        2. Critique: 'What's wrong with this?'
        3. Improve based on critique
        4. Repeat until confident or budget exhausted""",
        "effectiveness_gain": "10-25% quality improvement",
    },
    
    "multi_agent_debate": {
        "name": "Multi-Agent Debate/Verification",
        "description": """Multiple model instances debate and verify each other's answers.
        Consensus or synthesis emerges from disagreement.""",
        "key_insight": "Diverse perspectives catch more errors",
        "implementation": """
        - Agent A generates answer
        - Agent B critiques A's answer
        - Agent C synthesizes or arbitrates
        - Or: Agents argue until consensus""",
        "effectiveness_gain": "15-35% error reduction",
    },
    
    "process_reward_models": {
        "name": "Process Reward Models (PRM)",
        "description": """Reward each step of reasoning, not just final answer.
        Enables better credit assignment and error localization.""",
        "key_insight": "Intermediate steps matter as much as final answer",
        "implementation": """
        - Train verifier on step-level correctness
        - Use during inference to select better reasoning paths
        - Backtrack when step verifier detects error""",
        "effectiveness_gain": "Major improvement on multi-step problems",
    },
    
    "latent_space_reasoning": {
        "name": "Latent Space Reasoning (non-verbal thinking)",
        "description": """Reasoning happens in continuous representation space,
        not forced into discrete tokens. Think without 'speaking'.""",
        "key_insight": "Human-readable chains may not be optimal for machines",
        "implementation": """
        - Allow model to iterate in latent space
        - Only decode to text when ready
        - Thinking time proportional to difficulty""",
        "effectiveness_gain": "Potentially 50%+ on abstract reasoning",
    },
}


# =============================================================================
# STRATEGIC IMPLICATIONS FOR ORCHESTRATION
# =============================================================================

STRATEGIC_IMPLICATIONS = {
    
    "model_selection": {
        "current": "Select based on transformer capabilities and benchmarks",
        "emerging": """
        - Consider sub-quadratic models (Mamba, RWKV) for long-context tasks
        - Use test-time compute (o1/o3) for complex reasoning
        - Add neuro-symbolic verification for high-stakes domains
        - Evaluate diffusion models for editing/revision tasks""",
    },
    
    "reasoning_strategy": {
        "current": "Prompt-based CoT, multi-model synthesis",
        "emerging": """
        - Chain-of-Reasoning (code + math + language)
        - Self-reflection loops with critique
        - Multi-agent debate for verification
        - Test-time compute scaling (thinking budgets)
        - Latent reasoning for efficiency""",
    },
    
    "architecture_diversity": {
        "current": "All transformers, different sizes/training",
        "emerging": """
        - Mix transformer + Mamba for speed/quality tradeoff
        - Use RNN-like (RWKV) for streaming
        - Diffusion for editing workflows
        - Neuro-symbolic for verification
        - Ensemble different architectures""",
    },
    
    "competitive_threats": [
        "Test-time compute scaling (o1/o3) making brute-force model scaling obsolete",
        "Sub-quadratic models enabling longer contexts at lower cost",
        "Open-source catching up (DeepSeek-R1, RWKV, Mamba)",
        "Neuro-symbolic reducing hallucination gap",
        "Diffusion models enabling new workflows",
    ],
    
    "opportunities": [
        "Orchestrate across architecture types (transformer + Mamba + symbolic)",
        "Dynamic compute allocation based on problem difficulty",
        "Memory-augmented systems for personalization",
        "Multi-agent debate for verification",
        "Hybrid reasoning (code + language + symbolic)",
    ],
}


def get_architecture_for_task(task_type: str, constraints: Dict[str, Any] = None) -> List[str]:
    """
    Recommend architectures based on task and constraints.
    
    Args:
        task_type: Type of task
        constraints: Dict with keys like 'max_latency_ms', 'max_context', 'require_verification'
        
    Returns:
        List of recommended architecture names
    """
    constraints = constraints or {}
    recommendations = []
    
    max_context = constraints.get("max_context", 8000)
    require_verification = constraints.get("require_verification", False)
    latency_critical = constraints.get("max_latency_ms", 10000) < 1000
    
    # Long context needs sub-quadratic
    if max_context > 100000:
        recommendations.extend(["mamba", "rwkv", "memory_augmented"])
    
    # Verification needs neuro-symbolic
    if require_verification or any(x in task_type.lower() for x in ["medical", "legal", "financial"]):
        recommendations.append("neuro_symbolic")
    
    # Complex reasoning needs test-time compute
    if any(x in task_type.lower() for x in ["math", "logic", "proof", "complex"]):
        recommendations.append("test_time_compute")
    
    # Latency critical needs fast architectures
    if latency_critical:
        recommendations.extend(["mamba", "rwkv"])
    
    # Editing/revision tasks suit diffusion
    if any(x in task_type.lower() for x in ["edit", "revise", "improve", "rewrite"]):
        recommendations.append("diffusion_lm")
    
    return list(set(recommendations)) if recommendations else ["test_time_compute"]


def get_reasoning_development(task_type: str) -> Optional[Dict]:
    """Get the most applicable advanced reasoning development for a task."""
    task_lower = task_type.lower()
    
    if any(x in task_lower for x in ["math", "code", "compute"]):
        return ADVANCED_REASONING_DEVELOPMENTS["chain_of_reasoning"]
    elif any(x in task_lower for x in ["verify", "check", "accurate"]):
        return ADVANCED_REASONING_DEVELOPMENTS["multi_agent_debate"]
    elif any(x in task_lower for x in ["creative", "write", "improve"]):
        return ADVANCED_REASONING_DEVELOPMENTS["self_reflection_loops"]
    elif any(x in task_lower for x in ["complex", "multi-step", "hard"]):
        return ADVANCED_REASONING_DEVELOPMENTS["process_reward_models"]
    else:
        return ADVANCED_REASONING_DEVELOPMENTS["self_reflection_loops"]


# =============================================================================
# CUTTING-EDGE DEVELOPMENTS (18-Month Horizon - Late 2024 to Mid 2026)
# =============================================================================
# These are the specific breakthroughs that will reshape the AI landscape

CUTTING_EDGE_DEVELOPMENTS = {
    
    # =========================================================================
    # BRAIN-INSPIRED ARCHITECTURES (Beyond Traditional Neural Networks)
    # =========================================================================
    
    "dragon_hatchling": {
        "name": "Dragon Hatchling (Pathway AI)",
        "category": "brain_inspired",
        "published": "November 2024",
        "source": "Pathway AI startup",
        
        "key_innovation": """Dynamic neural plasticity - updates internal connections 
        in real-time like human brain. Not just learning weights, but learning 
        the STRUCTURE of connections.""",
        
        "how_it_works": """
        1. Graph-based neural architecture (not fixed layers)
        2. Connections dynamically created/pruned during inference
        3. "Developmental" approach - starts simple, grows complex
        4. Continuous learning without catastrophic forgetting
        5. Processes data as graph flows, not sequential tokens""",
        
        "advantages": [
            "Continuous learning and adaptation (no retraining)",
            "Generalizes better with less data",
            "Moves toward AGI-like flexibility",
            "Can process sequential AND parallel data",
            "More sample-efficient than transformers",
        ],
        
        "current_limitations": [
            "Still early - comparable to GPT-2 level",
            "Not yet production-ready",
            "Training infrastructure still developing",
            "Unclear scaling properties",
        ],
        
        "competitive_implication": """If this scales, it could make static pretrained 
        models obsolete. Models that continuously learn and adapt from interaction 
        would have massive advantage. Watch closely for 2025-2026 developments.""",
        
        "threat_level": "HIGH (long-term)",
    },
    
    "hierarchical_reasoning_model": {
        "name": "Hierarchical Reasoning Model (HRM) - Sapient",
        "category": "brain_inspired",
        "published": "August 2024",
        "source": "Sapient AI",
        
        "key_innovation": """Two-level recurrent design mimicking brain's hierarchical 
        processing. Only 27 MILLION parameters outperforming billion-parameter LLMs 
        on reasoning tasks.""",
        
        "how_it_works": """
        1. Fast loop: rapid pattern matching (like brain's fast intuition)
        2. Slow loop: deliberate reasoning (like System 2 thinking)
        3. Multi-timescale processing
        4. Information flows hierarchically like cortical columns
        5. Recurrent connections enable iterative refinement""",
        
        "benchmark_results": {
            "ARC-AGI-1": "Outperformed GPT-4",
            "Sudoku-Extreme": "Solved puzzles larger LLMs couldn't",
            "parameters": "27M (vs billions in LLMs)",
        },
        
        "advantages": [
            "Massively more efficient (1000x fewer parameters)",
            "Better reasoning on abstract tasks",
            "Doesn't rely on memorization",
            "More interpretable reasoning process",
        ],
        
        "competitive_implication": """Proves that architecture matters MORE than 
        scale for reasoning. Our orchestrator should prioritize reasoning-optimized 
        architectures over just 'biggest model'.""",
        
        "threat_level": "HIGH",
    },
    
    # =========================================================================
    # HYBRID ARCHITECTURES (Best of Multiple Worlds)
    # =========================================================================
    
    "sambay_hybrid": {
        "name": "SambaY Hybrid Architecture (Microsoft Phi-4-mini-flash)",
        "category": "hybrid",
        "published": "July 2025",
        "source": "Microsoft Research",
        
        "key_innovation": """Combines Mamba (state space) with transformer attention. 
        10x higher throughput, 2-3x lower latency, same reasoning quality.""",
        
        "how_it_works": """
        1. Mamba layers for efficient sequence processing (O(n))
        2. Sparse attention layers for critical reasoning steps
        3. Dynamic switching based on input complexity
        4. Optimized for edge/mobile deployment""",
        
        "performance": {
            "throughput": "10x higher than pure transformer",
            "latency": "2-3x lower average",
            "quality": "Matches pure transformer reasoning",
        },
        
        "advantages": [
            "Production-ready hybrid architecture",
            "Works on resource-constrained devices",
            "Proves hybrid approach is viable",
            "Maintained by Microsoft (enterprise support)",
        ],
        
        "competitive_implication": """We should explore hybrid model selection - 
        use Mamba-based for speed-critical paths, transformers for reasoning.""",
        
        "threat_level": "MEDIUM-HIGH",
    },
    
    "jamba_hybrid": {
        "name": "Jamba (AI21 Labs)",
        "category": "hybrid",
        "published": "March 2024",
        "source": "AI21 Labs",
        
        "key_innovation": """Production hybrid: Mamba + Transformer layers interleaved.
        256K context window with linear memory scaling.""",
        
        "how_it_works": """
        1. Alternates Mamba and Transformer blocks
        2. Mamba handles long-range dependencies efficiently
        3. Transformer attention for local precision
        4. MoE (Mixture of Experts) for efficiency""",
        
        "advantages": [
            "256K context with manageable memory",
            "First production hybrid model",
            "Open weights available",
            "Competitive with pure transformer quality",
        ],
        
        "competitive_implication": """Proves hybrid is production-ready NOW, 
        not just research. Consider for long-context tasks.""",
        
        "threat_level": "MEDIUM",
    },
    
    # =========================================================================
    # REASONING BREAKTHROUGHS
    # =========================================================================
    
    "deepseek_r1": {
        "name": "DeepSeek-R1",
        "category": "reasoning",
        "published": "January 2025",
        "source": "DeepSeek (China)",
        
        "key_innovation": """Open-weight reasoning model matching OpenAI o1 at 
        fraction of the cost. 671B parameters, open weights.""",
        
        "how_it_works": """
        1. Reinforcement learning for reasoning (like o1)
        2. Internal chain-of-thought before answering
        3. Self-verification and correction
        4. Open weights allow fine-tuning and study""",
        
        "cost_comparison": {
            "vs_o1": "~90% cheaper to operate",
            "inference": "$0.14/M input, $2.19/M output",
            "training": "Published methodology",
        },
        
        "competitive_implication": """The 'reasoning premium' is collapsing. 
        Open-source matching proprietary. Cost advantage disappearing. 
        Must differentiate on orchestration, not just model access.""",
        
        "threat_level": "VERY HIGH",
    },
    
    "gpt5_dynamic_router": {
        "name": "GPT-5 Dynamic Routing",
        "category": "reasoning",
        "published": "August 2025",
        "source": "OpenAI",
        
        "key_innovation": """Single model with internal router - decides when to 
        think deeply vs respond quickly. Adaptive compute allocation.""",
        
        "how_it_works": """
        1. Classifier determines query complexity
        2. Simple queries: fast path (minimal compute)
        3. Complex queries: deep reasoning path (more compute)
        4. Seamless switching - user doesn't see difference""",
        
        "advantages": [
            "One model handles all complexity levels",
            "Cost-efficient (only uses compute when needed)",
            "PhD-level performance when reasoning engaged",
            "Fast for simple tasks",
        ],
        
        "competitive_implication": """Our orchestrator already does this externally. 
        But internal routing may be more efficient. Consider hybrid approach.""",
        
        "threat_level": "HIGH",
    },
    
    # =========================================================================
    # MATHEMATICAL AI BREAKTHROUGHS
    # =========================================================================
    
    "alphageometry2": {
        "name": "AlphaGeometry 2 (DeepMind)",
        "category": "math",
        "published": "February 2025",
        "source": "DeepMind",
        
        "key_innovation": """Solved 25/30 IMO geometry problems - gold medalist level.
        Combines LLM intuition with symbolic geometry engine.""",
        
        "how_it_works": """
        1. LLM generates proof strategies (intuition)
        2. Symbolic engine verifies each step (rigor)
        3. Iterative refinement until proof complete
        4. Can construct auxiliary points (creative geometry)""",
        
        "implications": [
            "AI can match humans on creative math",
            "Hybrid neuro-symbolic is key for math",
            "Verification is tractable with symbolic methods",
        ],
        
        "competitive_implication": """For math-heavy domains, pure LLM is not enough. 
        Need symbolic verification layer. Consider adding Wolfram-style integration.""",
        
        "threat_level": "MEDIUM (specialized)",
    },
    
    "proof2hybrid": {
        "name": "Proof2Hybrid Benchmark Framework",
        "category": "evaluation",
        "published": "August 2025",
        "source": "Research community",
        
        "key_innovation": """Automatically generates proof-centric math benchmarks 
        from natural language papers. Scalable evaluation of math reasoning.""",
        
        "how_it_works": """
        1. Parse mathematical papers
        2. Extract theorems and proofs
        3. Generate question-answer pairs
        4. Create verifiable benchmark problems""",
        
        "implications": [
            "Can evaluate math ability at scale",
            "Catches memorization vs true reasoning",
            "Continuously updated from new papers",
        ],
        
        "competitive_implication": """Use for internal evaluation of our models' 
        actual math reasoning vs pattern matching.""",
        
        "threat_level": "LOW (tool, not threat)",
    },
    
    # =========================================================================
    # CONTINUOUS LEARNING & MEMORY
    # =========================================================================
    
    "surprise_memory": {
        "name": "Surprise-Based Memory Systems",
        "category": "memory",
        "published": "2024-2025 (various)",
        "source": "Multiple research groups",
        
        "key_innovation": """Store information based on novelty/surprise, not just 
        everything. Like human memory - remember unexpected things better.""",
        
        "how_it_works": """
        1. Measure 'surprise' of new information (prediction error)
        2. High surprise → store in long-term memory
        3. Low surprise → may already know, skip storage
        4. Enables efficient memory management
        5. Prioritizes learning novel information""",
        
        "advantages": [
            "More efficient than storing everything",
            "Focuses learning on what matters",
            "Mimics human memory consolidation",
            "Enables continuous learning",
        ],
        
        "competitive_implication": """For RAG systems - don't just retrieve by similarity. 
        Weight by surprise/novelty of information. Prioritize unexpected facts.""",
        
        "threat_level": "MEDIUM",
    },
    
    "coherent_internal_map": {
        "name": "Coherent Internal World Models",
        "category": "memory",
        "published": "2024-2025",
        "source": "Various (DeepMind, OpenAI, academia)",
        
        "key_innovation": """Models that maintain consistent internal representation 
        of the world/conversation. Self-reflected confidence values.""",
        
        "how_it_works": """
        1. Build internal 'world model' during conversation
        2. Check new information against internal model
        3. Detect and flag inconsistencies
        4. Confidence calibration for each belief
        5. Update model as new facts arrive""",
        
        "advantages": [
            "Reduces hallucination (detects inconsistency)",
            "Better multi-turn coherence",
            "Knows what it knows (calibrated confidence)",
            "Can say 'I'm not sure' appropriately",
        ],
        
        "competitive_implication": """Essential for reliability. Models should 
        track confidence and internal consistency. Add confidence checking to 
        verification pipeline.""",
        
        "threat_level": "HIGH (essential capability)",
    },
    
    # =========================================================================
    # LATENT/PRIVATE REASONING
    # =========================================================================
    
    "private_thought": {
        "name": "Private Chain-of-Thought / Latent Reasoning",
        "category": "reasoning",
        "published": "2024 (o1) onwards",
        "source": "OpenAI, DeepSeek, others",
        
        "key_innovation": """Reasoning happens in internal representation, NOT 
        forced into human-readable tokens. 'Think without speaking.'""",
        
        "why_it_matters": """
        Traditional CoT: Forces model to verbalize every step (inefficient)
        Private thought: Model reasons in latent space, only outputs conclusion
        
        Human analogy: You don't verbalize every thought when solving a puzzle.
        The internal process is often non-verbal, non-sequential.""",
        
        "advantages": [
            "More efficient (fewer tokens generated)",
            "Can explore non-verbal reasoning patterns",
            "Not constrained to human-readable chains",
            "May unlock more abstract reasoning",
        ],
        
        "challenges": [
            "Harder to interpret/debug",
            "Training is more complex",
            "Can't 'show work' for verification",
        ],
        
        "competitive_implication": """For complex reasoning, private thought may be 
        superior. But for explainability, explicit CoT still needed. 
        Orchestrator should choose based on requirement.""",
        
        "threat_level": "HIGH",
    },
    
    # =========================================================================
    # REAL-TIME UPDATEABLE SYSTEMS
    # =========================================================================
    
    "realtime_rag": {
        "name": "Real-Time Updateable RAG",
        "category": "memory",
        "published": "2024-2025",
        "source": "Various implementations",
        
        "key_innovation": """RAG systems that update their knowledge base in 
        real-time, not just at indexing time. Live learning from interactions.""",
        
        "how_it_works": """
        1. Separate 'training data' from 'live data'
        2. Live data updated continuously
        3. Model learns from corrections/interactions
        4. Temporal weighting (recent = more relevant)
        5. User-specific memory layers""",
        
        "examples": [
            "Perplexity's live search integration",
            "Grok's X/Twitter real-time data",
            "Memory-augmented assistants (MemGPT)",
        ],
        
        "competitive_implication": """Our RAG should have tiered memory:
        1. Static knowledge (pretrained)
        2. Session knowledge (conversation)
        3. User knowledge (personalization)
        4. Live knowledge (real-time search)""",
        
        "threat_level": "HIGH (competitive necessity)",
    },
}


# =============================================================================
# TRANSFORMER VS LLM - THE DISTINCTION
# =============================================================================

TRANSFORMER_VS_LLM = {
    "key_insight": """'Transformer' is the architecture. 'LLM' is the application.
    The transformer architecture will likely outlive the current LLM paradigm.""",
    
    "why_transformers_persist": [
        "Attention mechanism is mathematically powerful",
        "Highly parallelizable for training",
        "Flexible architecture (vision, audio, text, everything)",
        "Massive infrastructure investment (GPUs, frameworks)",
        "Well-understood training dynamics",
    ],
    
    "why_llms_may_evolve": [
        "Autoregressive generation may not be optimal",
        "Token-by-token is slow and error-prone",
        "Forcing all knowledge into weights is inefficient",
        "Context window limitations are fundamental",
        "Hallucination from pure pattern matching",
    ],
    
    "likely_future": """
    Transformers will remain important but:
    1. Hybrid with state-space (Mamba) for efficiency
    2. Augmented with external memory (not just weights)
    3. Combined with symbolic reasoning (neuro-symbolic)
    4. Dynamic compute allocation (think more on hard problems)
    5. Continuous learning (not frozen after training)
    
    The 'pure LLM' (just predict next token) will be seen as primitive.""",
    
    "strategic_implication": """
    Don't bet everything on transformer LLMs. 
    Build architecture-agnostic orchestration.
    Be ready to integrate non-transformer models (Mamba, RWKV, hybrids).
    The future is hybrid, memory-augmented, and continuously learning.""",
}


# =============================================================================
# COMPETITIVE THREAT ASSESSMENT
# =============================================================================

COMPETITIVE_LANDSCAPE = {
    "immediate_threats": [
        {
            "threat": "DeepSeek-R1 matching o1 at 90% lower cost",
            "timeline": "NOW",
            "response": "Can't compete on cost. Must differentiate on orchestration quality.",
        },
        {
            "threat": "Open-source catching up (Llama, OLMo, RWKV)",
            "timeline": "NOW",
            "response": "Use open models where appropriate. Add value through integration.",
        },
        {
            "threat": "GPT-5 dynamic routing doing what orchestrators do",
            "timeline": "August 2025",
            "response": "Multi-model orchestration still better than single-model routing.",
        },
    ],
    
    "medium_term_threats": [
        {
            "threat": "Hybrid architectures (SambaY) becoming standard",
            "timeline": "2025-2026",
            "response": "Integrate hybrid models. Don't assume transformer-only.",
        },
        {
            "threat": "HRM-style efficient reasoning (27M beats billions)",
            "timeline": "2025-2026",
            "response": "Quality over size. Prioritize reasoning-optimized models.",
        },
    ],
    
    "long_term_threats": [
        {
            "threat": "Continuous learning systems (Dragon Hatchling)",
            "timeline": "2026+",
            "response": "Monitor closely. Prepare for paradigm shift from static to adaptive.",
        },
        {
            "threat": "Fully integrated neuro-symbolic systems",
            "timeline": "2026+",
            "response": "Build symbolic verification into pipeline NOW.",
        },
    ],
    
    "our_advantages": [
        "Multi-model orchestration (no single point of failure)",
        "Reasoning method selection (CoT, ToT, Reflexion, etc.)",
        "Team composition strategies",
        "Real-time model selection based on task",
        "Architecture-agnostic (can integrate new models)",
    ],
    
    "areas_to_strengthen": [
        "Symbolic verification layer (like AlphaGeometry)",
        "Continuous learning / memory updates",
        "Confidence calibration and uncertainty quantification",
        "Hybrid model integration (Mamba, RWKV)",
        "Latent/private reasoning for efficiency",
    ],
}

