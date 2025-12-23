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

