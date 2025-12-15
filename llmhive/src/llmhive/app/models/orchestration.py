"""Pydantic models for chat/orchestration API contract."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReasoningMode(str, Enum):
    """Reasoning depth mode (simple)."""
    fast = "fast"
    standard = "standard"
    deep = "deep"


class ReasoningMethod(str, Enum):
    """Advanced reasoning methods for LLM orchestration.
    
    Based on research: "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
    """
    # Original methods
    chain_of_thought = "chain-of-thought"
    tree_of_thought = "tree-of-thought"
    react = "react"
    plan_and_solve = "plan-and-solve"
    self_consistency = "self-consistency"
    reflexion = "reflexion"
    
    # Research methods from "Implementing Advanced Reasoning Methods with Optimal LLMs (2025)"
    hierarchical_decomposition = "hierarchical-decomposition"  # HRM-style
    iterative_refinement = "iterative-refinement"  # Diffusion-inspired
    confidence_filtering = "confidence-filtering"  # DeepConf
    dynamic_planning = "dynamic-planning"  # Test-time decision-making


class DomainPack(str, Enum):
    """Domain/industry pack for specialized prompts."""
    default = "default"
    medical = "medical"
    legal = "legal"
    marketing = "marketing"
    coding = "coding"
    research = "research"
    finance = "finance"


class AgentMode(str, Enum):
    """Agent collaboration mode."""
    single = "single"
    team = "team"


class TuningOptions(BaseModel):
    """Tuning options for orchestration."""
    prompt_optimization: bool = Field(default=True, description="Enable prompt optimization")
    output_validation: bool = Field(default=True, description="Enable output validation")
    answer_structure: bool = Field(default=True, description="Enable structured answer formatting")
    learn_from_chat: bool = Field(default=True, description="Enable learning from conversation history")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt_optimization": True,
                "output_validation": True,
                "answer_structure": True,
                "learn_from_chat": True,
            }
        }
    )


class CriteriaSettings(BaseModel):
    """Dynamic criteria settings for quality/speed/creativity balance."""
    accuracy: int = Field(default=70, ge=0, le=100, description="Accuracy priority (0-100)")
    speed: int = Field(default=70, ge=0, le=100, description="Speed priority (0-100)")
    creativity: int = Field(default=50, ge=0, le=100, description="Creativity priority (0-100)")


class ChatMetadata(BaseModel):
    """Optional metadata for chat tracking."""
    chat_id: Optional[str] = Field(default=None, description="Chat/conversation ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    project_id: Optional[str] = Field(default=None, description="Project ID")
    org_id: Optional[str] = Field(default=None, description="Organization ID")
    criteria: Optional[CriteriaSettings] = Field(
        default=None,
        description="Dynamic criteria settings for quality/speed/creativity balance"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chat_id": "conv-123",
                "user_id": "user-456",
                "project_id": "proj-789",
            "org_id": "org-001",
                "criteria": {"accuracy": 70, "speed": 70, "creativity": 50},
            }
        }
    )


class EliteStrategy(str, Enum):
    """Elite orchestration strategies."""
    automatic = "automatic"
    single_best = "single_best"
    parallel_race = "parallel_race"
    best_of_n = "best_of_n"
    quality_weighted_fusion = "quality_weighted_fusion"
    expert_panel = "expert_panel"
    challenge_and_refine = "challenge_and_refine"


class OrchestrationSettings(BaseModel):
    """Orchestration Studio settings for advanced orchestration control."""
    accuracy_level: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Accuracy vs Speed slider (1=fastest, 5=most accurate)"
    )
    enable_hrm: bool = Field(
        default=False,
        description="Enable Hierarchical Role Management (HRM)"
    )
    enable_prompt_diffusion: bool = Field(
        default=False,
        description="Enable Prompt Diffusion & Refinement"
    )
    enable_deep_consensus: bool = Field(
        default=False,
        description="Enable Deep Consensus (multi-round debate)"
    )
    enable_adaptive_ensemble: bool = Field(
        default=False,
        description="Enable Adaptive Ensemble Logic"
    )
    enable_live_research: bool = Field(
        default=False,
        description="Enable real-time web research for current data (auto-enabled for temporal queries)"
    )
    # Elite orchestration settings (from frontend)
    elite_strategy: Optional[str] = Field(
        default=None,
        description="Elite orchestration strategy"
    )
    quality_options: Optional[List[str]] = Field(
        default=None,
        description="Quality boosting options"
    )
    # Standard LLM parameters
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0,
        le=2,
        description="Temperature for response generation"
    )
    max_tokens: Optional[int] = Field(
        default=2000,
        ge=100,
        le=4000,
        description="Maximum tokens in response"
    )
    top_p: Optional[float] = Field(
        default=0.9,
        ge=0,
        le=1,
        description="Top-p nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        default=0,
        ge=0,
        le=2,
        description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=0,
        ge=0,
        le=2,
        description="Presence penalty"
    )
    # Feature toggles
    enable_tool_broker: Optional[bool] = Field(
        default=True,
        description="Enable automatic tool detection and execution"
    )
    enable_verification: Optional[bool] = Field(
        default=True,
        description="Enable code/math verification"
    )
    enable_vector_rag: Optional[bool] = Field(
        default=False,
        description="Enable Vector RAG with Pinecone"
    )
    enable_memory: Optional[bool] = Field(
        default=False,
        description="Enable memory augmentation"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "accuracy_level": 3,
                "enable_hrm": False,
                "enable_prompt_diffusion": False,
                "enable_deep_consensus": False,
                "enable_adaptive_ensemble": False,
                "elite_strategy": "automatic",
                "quality_options": ["verification", "consensus"],
                "temperature": 0.7,
                "max_tokens": 2000,
                "enable_vector_rag": False,
            }
        }
    )


class ChatRequest(BaseModel):
    """Request model for chat orchestration."""
    prompt: str = Field(..., description="User prompt/question")
    models: Optional[List[str]] = Field(
        default=None,
        description="List of model IDs to use for orchestration (e.g., ['gpt-5', 'claude-sonnet-4.5', 'grok-4']). If not provided, models will be auto-selected."
    )
    reasoning_mode: ReasoningMode = Field(default=ReasoningMode.standard, description="Reasoning depth mode (fast/standard/deep)")
    reasoning_method: Optional[ReasoningMethod] = Field(
        default=None,
        description="Advanced reasoning method (chain-of-thought, tree-of-thought, react, plan-and-solve, self-consistency, reflexion). If not provided, will be inferred from reasoning_mode."
    )
    domain_pack: DomainPack = Field(default=DomainPack.default, description="Domain specialization pack")
    agent_mode: AgentMode = Field(default=AgentMode.team, description="Agent collaboration mode")
    format_style: Optional[str] = Field(
        default=None,
        description="Answer format style (paragraph, bullet_points, markdown, table, json, executive_summary, qa)",
    )
    tone_style: Optional[str] = Field(
        default=None,
        description="Answer tone/style (formal, casual, technical, simplified, educational, conversational, authoritative)",
    )
    show_confidence: Optional[bool] = Field(
        default=True,
        description="Whether to append confidence indicator in textual output (ignored for JSON format)",
    )
    tuning: TuningOptions = Field(default_factory=TuningOptions, description="Tuning options")
    orchestration: OrchestrationSettings = Field(
        default_factory=OrchestrationSettings,
        description="Orchestration Studio settings"
    )
    metadata: ChatMetadata = Field(default_factory=ChatMetadata, description="Optional metadata")
    history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Conversation history as list of {role, content} dicts"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "What is the capital of France?",
                "reasoning_mode": "standard",
                "domain_pack": "default",
                "agent_mode": "team",
                "tuning": {
                    "prompt_optimization": True,
                    "output_validation": True,
                    "answer_structure": True,
                    "learn_from_chat": True,
                },
                "metadata": {
                    "chat_id": "conv-123",
                },
                "history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help?"},
                ],
            }
        }
    )


class AgentTrace(BaseModel):
    """Trace information for agent contributions."""
    agent_id: Optional[str] = Field(default=None, description="Agent identifier")
    agent_name: Optional[str] = Field(default=None, description="Agent name/type")
    contribution: Optional[str] = Field(default=None, description="Agent's contribution")
    confidence: Optional[float] = Field(default=None, description="Confidence score")
    timestamp: Optional[float] = Field(default=None, description="Processing timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_id": "agent-1",
                "agent_name": "researcher",
                "contribution": "Verified fact about France",
                "confidence": 0.95,
            }
        }
    )


class ChatResponse(BaseModel):
    """Response model for chat orchestration."""
    message: str = Field(..., description="Final assistant answer/message")
    models_used: List[str] = Field(default_factory=list, description="List of models that participated in orchestration")
    reasoning_mode: ReasoningMode = Field(..., description="Reasoning mode used")
    reasoning_method: Optional[ReasoningMethod] = Field(
        default=None,
        description="Advanced reasoning method used (if specified)"
    )
    domain_pack: DomainPack = Field(..., description="Domain pack used")
    agent_mode: AgentMode = Field(..., description="Agent mode used")
    used_tuning: TuningOptions = Field(..., description="Tuning options that were applied")
    metadata: ChatMetadata = Field(..., description="Metadata (echoed from request)")
    tokens_used: Optional[int] = Field(default=None, description="Total tokens consumed")
    latency_ms: Optional[int] = Field(default=None, description="Processing latency in milliseconds")
    agent_traces: List[AgentTrace] = Field(default_factory=list, description="Agent trace information")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Additional response data")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "The capital of France is Paris.",
                "reasoning_mode": "standard",
                "domain_pack": "default",
                "agent_mode": "team",
                "used_tuning": {
                    "prompt_optimization": True,
                    "output_validation": True,
                    "answer_structure": True,
                    "learn_from_chat": True,
                },
                "metadata": {
                    "chat_id": "conv-123",
                },
                "tokens_used": 150,
                "latency_ms": 1200,
                "agent_traces": [],
                "extra": {},
            }
        }
    )


# ==============================================================================
# Clarification Models
# ==============================================================================

class ClarificationStatus(str, Enum):
    """Status of the clarification process."""
    not_needed = "not_needed"
    pending_query = "pending_query"
    pending_preferences = "pending_preferences"
    completed = "completed"
    skipped = "skipped"


class DetailLevel(str, Enum):
    """Level of detail for the answer."""
    brief = "brief"
    standard = "standard"
    detailed = "detailed"
    exhaustive = "exhaustive"


class AnswerFormat(str, Enum):
    """Format for the answer."""
    paragraph = "paragraph"
    bullet_points = "bullet_points"
    numbered_list = "numbered_list"
    code_focused = "code_focused"
    table = "table"
    structured = "structured"
    conversational = "conversational"
    markdown = "markdown"
    json = "json"
    executive_summary = "executive_summary"
    qa = "qa"


class AnswerTone(str, Enum):
    """Tone/style for the answer."""
    formal = "formal"
    casual = "casual"
    technical = "technical"
    simplified = "simplified"
    educational = "educational"


class ClarificationQuestion(BaseModel):
    """A single clarification question."""
    id: str = Field(..., description="Unique question identifier")
    question: str = Field(..., description="The clarification question")
    category: str = Field(..., description="Category: 'query' or 'preference'")
    options: Optional[List[str]] = Field(default=None, description="Multiple choice options")
    default_answer: Optional[str] = Field(default=None, description="Default answer if skipped")
    required: bool = Field(default=True, description="Whether answer is required")


class AnswerPreferences(BaseModel):
    """User's preferences for answer format and style."""
    detail_level: DetailLevel = Field(default=DetailLevel.standard, description="Level of detail")
    format: AnswerFormat = Field(default=AnswerFormat.paragraph, description="Answer format")
    tone: AnswerTone = Field(default=AnswerTone.formal, description="Answer tone/style")
    max_length: Optional[int] = Field(default=None, description="Optional word limit")
    include_examples: bool = Field(default=True, description="Include examples")
    include_citations: bool = Field(default=False, description="Include citations")
    custom_instructions: Optional[str] = Field(default=None, description="Custom instructions")


class ClarificationRequest(BaseModel):
    """Request for clarification from the user."""
    status: ClarificationStatus = Field(..., description="Clarification status")
    original_query: str = Field(..., description="Original user query")
    ambiguity_summary: Optional[str] = Field(default=None, description="Why clarification is needed")
    clarification_round: int = Field(default=1, description="Current clarification round (1-based)")
    query_questions: List[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions about the query (up to 3)"
    )
    preference_questions: List[ClarificationQuestion] = Field(
        default_factory=list,
        description="Questions about answer preferences (3 standard questions)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "pending_query",
                "original_query": "Tell me about the Phoenix project",
                "ambiguity_summary": "The term 'Phoenix project' could refer to multiple things.",
                "query_questions": [
                    {
                        "id": "q1",
                        "question": "Which Phoenix project are you referring to?",
                        "category": "query",
                        "options": ["NASA Phoenix Mars Mission", "Phoenix Framework", "The Phoenix Project book"],
                        "required": True
                    }
                ],
                "preference_questions": [
                    {
                        "id": "pref_detail",
                        "question": "How detailed of an answer would you like?",
                        "category": "preference",
                        "options": ["Brief", "Standard", "Detailed", "Exhaustive"],
                        "default_answer": "Standard",
                        "required": False
                    }
                ]
            }
        }
    )


class ClarificationResponse(BaseModel):
    """User's responses to clarification questions."""
    query_answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Answers to query questions (question_id -> answer)"
    )
    preference_answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Answers to preference questions"
    )
    skipped: bool = Field(default=False, description="Whether user skipped clarification")
    proceed_with_assumption: bool = Field(default=False, description="Proceed with best guess if still ambiguous")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_answers": {
                    "q1": "NASA Phoenix Mars Mission"
                },
                "preference_answers": {
                    "pref_detail": "Detailed",
                    "pref_format": "Bullet Points",
                    "pref_tone": "Educational"
                },
                "skipped": False
            }
        }
    )


class ChatRequestWithClarification(ChatRequest):
    """Extended chat request that includes clarification responses."""
    clarification_response: Optional[ClarificationResponse] = Field(
        default=None,
        description="User's responses to clarification questions"
    )
    skip_clarification: bool = Field(
        default=False,
        description="Skip the clarification step"
    )


class ChatResponseWithClarification(BaseModel):
    """Response that may include clarification request instead of answer."""
    needs_clarification: bool = Field(..., description="Whether clarification is needed")
    clarification_request: Optional[ClarificationRequest] = Field(
        default=None,
        description="Clarification questions if needed"
    )
    response: Optional[ChatResponse] = Field(
        default=None,
        description="Chat response if no clarification needed"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "needs_clarification": True,
                "clarification_request": {
                    "status": "pending_query",
                    "original_query": "Tell me about the Phoenix project",
                    "query_questions": [{"id": "q1", "question": "Which Phoenix project?", "category": "query", "required": True}],
                    "preference_questions": []
                },
                "response": None
            }
        }
    )

