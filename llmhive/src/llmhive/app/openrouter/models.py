"""OpenRouter Database Models.

SQLAlchemy models for:
- OpenRouter model catalog (models table)
- Model endpoints/providers (endpoints table)
- Usage telemetry for rankings (telemetry table)
- Prompt templates (templates table)
- Saved runs (runs table)

Data Dictionary:
================
Each field is documented with its source (OpenRouter API) or derivation logic.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================

class ModelModality(str, Enum):
    """Model input/output modalities."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class EndpointStatus(str, Enum):
    """Endpoint availability status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class TemplateVisibility(str, Enum):
    """Prompt template visibility."""
    PRIVATE = "private"
    WORKSPACE = "workspace"
    PUBLIC = "public"


# =============================================================================
# OpenRouter Model (Catalog)
# =============================================================================

class OpenRouterModel(Base):
    """OpenRouter model catalog entry.
    
    Data Dictionary:
    ----------------
    Field                     | Source/Derivation
    --------------------------|--------------------------------------------------
    id                        | OpenRouter: model.id (primary key for inference)
    name                      | OpenRouter: model.name
    description               | OpenRouter: model.description
    context_length            | OpenRouter: model.context_length
    architecture_modality     | OpenRouter: model.architecture.modality
    architecture_tokenizer    | OpenRouter: model.architecture.tokenizer
    architecture_instruct     | OpenRouter: model.architecture.instruct_type
    
    # Pricing (normalized to decimals)
    pricing_prompt            | OpenRouter: model.pricing.prompt (per token)
    pricing_completion        | OpenRouter: model.pricing.completion (per token)
    pricing_image             | OpenRouter: model.pricing.image (per image)
    pricing_request           | OpenRouter: model.pricing.request (per request)
    
    # Derived pricing metrics
    price_per_1m_prompt       | Derived: pricing_prompt * 1_000_000
    price_per_1m_completion   | Derived: pricing_completion * 1_000_000
    
    # Top provider info
    top_provider_context      | OpenRouter: model.top_provider.context_length
    top_provider_max_tokens   | OpenRouter: model.top_provider.max_completion_tokens
    top_provider_moderation   | OpenRouter: model.top_provider.is_moderated
    
    # Supported parameters
    supported_params          | OpenRouter: model.supported_parameters (JSON array)
    default_params            | OpenRouter: model.parameters (JSON object)
    
    # Derived capability flags
    supports_tools            | Derived: 'tools' in supported_params or 'functions' in supported_params
    supports_structured       | Derived: 'response_format' in supported_params
    supports_streaming        | Derived: 'stream' in supported_params (default True)
    multimodal_input          | Derived: architecture_modality contains 'image'/'audio'
    multimodal_output         | Derived: architecture_modality contains image/audio output
    
    # Derived operational flags
    is_free                   | Derived: all pricing fields == 0
    availability_score        | Derived: from endpoint statuses (0-100)
    
    # Derived strengths/weaknesses (non-authoritative)
    strengths_derived         | Derived: based on context_length, pricing, modality, params
    weaknesses_derived        | Derived: based on limitations, missing params
    
    # Audit fields
    raw_json                  | OpenRouter: complete raw API response (for forward compat)
    content_hash              | Derived: SHA256(raw_json) for change detection
    fetched_at                | System: timestamp of last API fetch
    last_seen_at              | System: timestamp model was last in API response
    created_at                | System: record creation timestamp
    updated_at                | System: record update timestamp
    is_active                 | System: False if model removed from API
    """
    __tablename__ = "openrouter_models"
    
    # Primary key - exact model ID for inference
    id = Column(String(255), primary_key=True, index=True)
    
    # Basic info (Source: OpenRouter API)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    context_length = Column(Integer, nullable=True)
    
    # Architecture (Source: OpenRouter model.architecture)
    architecture_modality = Column(String(100), nullable=True)  # e.g., "text->text", "text+image->text"
    architecture_tokenizer = Column(String(100), nullable=True)
    architecture_instruct = Column(String(100), nullable=True)
    
    # Pricing - normalized to Decimal for precision (Source: OpenRouter model.pricing)
    pricing_prompt = Column(Numeric(20, 12), nullable=True)      # Per token
    pricing_completion = Column(Numeric(20, 12), nullable=True)  # Per token
    pricing_image = Column(Numeric(20, 12), nullable=True)       # Per image
    pricing_request = Column(Numeric(20, 12), nullable=True)     # Per request
    
    # Derived pricing metrics (computed on save)
    price_per_1m_prompt = Column(Numeric(20, 6), nullable=True)
    price_per_1m_completion = Column(Numeric(20, 6), nullable=True)
    
    # Top provider info (Source: OpenRouter model.top_provider)
    top_provider_context = Column(Integer, nullable=True)
    top_provider_max_tokens = Column(Integer, nullable=True)
    top_provider_moderation = Column(Boolean, nullable=True)
    
    # Supported parameters (Source: OpenRouter model.supported_parameters)
    supported_params = Column(JSON, nullable=True)  # List of param names
    default_params = Column(JSON, nullable=True)    # Default param values
    
    # Derived capability flags (computed on save)
    supports_tools = Column(Boolean, default=False)
    supports_structured = Column(Boolean, default=False)
    supports_streaming = Column(Boolean, default=True)
    multimodal_input = Column(Boolean, default=False)
    multimodal_output = Column(Boolean, default=False)
    
    # Derived operational flags
    is_free = Column(Boolean, default=False)
    availability_score = Column(Float, default=100.0)  # 0-100
    
    # Derived strengths/weaknesses (non-authoritative, labeled as derived)
    strengths_derived = Column(JSON, nullable=True)   # List of strings
    weaknesses_derived = Column(JSON, nullable=True)  # List of strings
    
    # Category/tags (if present in API)
    categories = Column(JSON, nullable=True)  # List of category strings
    
    # Raw data for forward compatibility
    raw_json = Column(JSON, nullable=True)
    content_hash = Column(String(64), nullable=True)  # SHA256
    
    # Audit timestamps
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    endpoints = relationship("OpenRouterEndpoint", back_populates="model", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_openrouter_models_pricing", "price_per_1m_prompt", "price_per_1m_completion"),
        Index("ix_openrouter_models_context", "context_length"),
        Index("ix_openrouter_models_capabilities", "supports_tools", "supports_structured", "multimodal_input"),
        Index("ix_openrouter_models_active_name", "is_active", "name"),
    )
    
    def compute_derived_fields(self) -> None:
        """Compute derived fields from source data."""
        # Derived pricing
        if self.pricing_prompt is not None:
            self.price_per_1m_prompt = Decimal(str(self.pricing_prompt)) * 1_000_000
        if self.pricing_completion is not None:
            self.price_per_1m_completion = Decimal(str(self.pricing_completion)) * 1_000_000
        
        # Derived capabilities from supported_params
        params = self.supported_params or []
        self.supports_tools = "tools" in params or "functions" in params or "function_call" in params
        self.supports_structured = "response_format" in params or "json_schema" in params
        self.supports_streaming = "stream" in params or True  # Default True
        
        # Multimodal from architecture
        modality = (self.architecture_modality or "").lower()
        self.multimodal_input = "image" in modality or "audio" in modality or "video" in modality
        self.multimodal_output = modality.endswith("image") or modality.endswith("audio")
        
        # Is free
        self.is_free = all([
            (self.pricing_prompt or 0) == 0,
            (self.pricing_completion or 0) == 0,
            (self.pricing_image or 0) == 0,
            (self.pricing_request or 0) == 0,
        ])
        
        # Compute strengths/weaknesses (non-authoritative)
        self._compute_strengths_weaknesses()
        
        # Content hash for change detection
        if self.raw_json:
            self.content_hash = hashlib.sha256(
                json.dumps(self.raw_json, sort_keys=True).encode()
            ).hexdigest()
    
    def _compute_strengths_weaknesses(self) -> None:
        """Compute derived strengths and weaknesses from observable attributes."""
        strengths = []
        weaknesses = []
        
        # Context length analysis
        ctx = self.context_length or 0
        if ctx >= 128000:
            strengths.append(f"Very long context window ({ctx:,} tokens)")
        elif ctx >= 32000:
            strengths.append(f"Long context window ({ctx:,} tokens)")
        elif ctx < 4096:
            weaknesses.append(f"Limited context window ({ctx:,} tokens)")
        
        # Pricing analysis
        prompt_cost = float(self.price_per_1m_prompt or 0)
        if self.is_free:
            strengths.append("Free to use (no token costs)")
        elif prompt_cost < 0.5:
            strengths.append(f"Very low cost (${prompt_cost:.2f}/M input tokens)")
        elif prompt_cost < 2.0:
            strengths.append(f"Affordable pricing (${prompt_cost:.2f}/M input tokens)")
        elif prompt_cost > 30:
            weaknesses.append(f"High cost (${prompt_cost:.2f}/M input tokens)")
        
        # Capability analysis
        if self.supports_tools:
            strengths.append("Supports function/tool calling")
        else:
            weaknesses.append("No function/tool calling support")
        
        if self.supports_structured:
            strengths.append("Supports structured JSON output")
        
        if self.multimodal_input:
            strengths.append("Accepts image/audio input (multimodal)")
        else:
            weaknesses.append("Text-only input")
        
        if self.multimodal_output:
            strengths.append("Can generate images/audio")
        
        # Moderation
        if self.top_provider_moderation:
            weaknesses.append("Content moderation enabled (may limit some outputs)")
        
        self.strengths_derived = strengths if strengths else None
        self.weaknesses_derived = weaknesses if weaknesses else None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "OpenRouterModel":
        """Create model from OpenRouter API response."""
        model = cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            description=data.get("description"),
            context_length=data.get("context_length"),
            raw_json=data,
            fetched_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        
        # Architecture
        arch = data.get("architecture", {})
        model.architecture_modality = arch.get("modality")
        model.architecture_tokenizer = arch.get("tokenizer")
        model.architecture_instruct = arch.get("instruct_type")
        
        # Pricing
        pricing = data.get("pricing", {})
        if pricing.get("prompt"):
            model.pricing_prompt = Decimal(str(pricing["prompt"]))
        if pricing.get("completion"):
            model.pricing_completion = Decimal(str(pricing["completion"]))
        if pricing.get("image"):
            model.pricing_image = Decimal(str(pricing["image"]))
        if pricing.get("request"):
            model.pricing_request = Decimal(str(pricing["request"]))
        
        # Top provider
        top_provider = data.get("top_provider", {})
        model.top_provider_context = top_provider.get("context_length")
        model.top_provider_max_tokens = top_provider.get("max_completion_tokens")
        model.top_provider_moderation = top_provider.get("is_moderated")
        
        # Parameters
        model.supported_params = data.get("supported_parameters", [])
        model.default_params = data.get("parameters", {})
        
        # Compute derived fields
        model.compute_derived_fields()
        
        return model
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "context_length": self.context_length,
            "architecture": {
                "modality": self.architecture_modality,
                "tokenizer": self.architecture_tokenizer,
                "instruct_type": self.architecture_instruct,
            },
            "pricing": {
                "prompt": float(self.pricing_prompt) if self.pricing_prompt else None,
                "completion": float(self.pricing_completion) if self.pricing_completion else None,
                "image": float(self.pricing_image) if self.pricing_image else None,
                "request": float(self.pricing_request) if self.pricing_request else None,
                "per_1m_prompt": float(self.price_per_1m_prompt) if self.price_per_1m_prompt else None,
                "per_1m_completion": float(self.price_per_1m_completion) if self.price_per_1m_completion else None,
            },
            "capabilities": {
                "supports_tools": self.supports_tools,
                "supports_structured": self.supports_structured,
                "supports_streaming": self.supports_streaming,
                "multimodal_input": self.multimodal_input,
                "multimodal_output": self.multimodal_output,
            },
            "is_free": self.is_free,
            "availability_score": self.availability_score,
            "strengths": self.strengths_derived,  # Labeled as derived in field name
            "weaknesses": self.weaknesses_derived,
            "categories": self.categories,
            "is_active": self.is_active,
            "last_updated": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


# =============================================================================
# OpenRouter Endpoint (Provider Details)
# =============================================================================

class OpenRouterEndpoint(Base):
    """OpenRouter model endpoint/provider details.
    
    Data Dictionary:
    ----------------
    Field                 | Source
    ----------------------|--------------------------------------------------
    id                    | System: composite key (model_id + provider + tag)
    model_id              | OpenRouter: parent model ID
    provider_name         | OpenRouter: endpoint.provider
    endpoint_tag          | OpenRouter: endpoint.tag (e.g., "extended", "nitro")
    
    # Endpoint-specific pricing
    endpoint_pricing_*    | OpenRouter: endpoint.pricing.*
    
    # Endpoint-specific limits
    context_length        | OpenRouter: endpoint.context_length
    max_completion_tokens | OpenRouter: endpoint.max_completion_tokens
    
    # Parameters and features
    supported_params      | OpenRouter: endpoint.supported_parameters
    quantization          | OpenRouter: endpoint.quantization (if present)
    supports_caching      | OpenRouter: endpoint.supports_prompt_caching
    
    # Status and health
    status                | OpenRouter: endpoint.status or derived from uptime
    uptime_percent        | OpenRouter: endpoint.uptime (if available)
    
    # Audit
    raw_json              | OpenRouter: complete endpoint response
    """
    __tablename__ = "openrouter_endpoints"
    
    # Composite primary key
    id = Column(String(512), primary_key=True)  # model_id::provider::tag
    
    # Foreign key to model
    model_id = Column(String(255), ForeignKey("openrouter_models.id"), nullable=False, index=True)
    
    # Provider info
    provider_name = Column(String(100), nullable=False, index=True)
    endpoint_tag = Column(String(100), nullable=True)
    
    # Endpoint-specific pricing
    endpoint_pricing_prompt = Column(Numeric(20, 12), nullable=True)
    endpoint_pricing_completion = Column(Numeric(20, 12), nullable=True)
    endpoint_pricing_image = Column(Numeric(20, 12), nullable=True)
    endpoint_pricing_request = Column(Numeric(20, 12), nullable=True)
    
    # Endpoint-specific limits
    context_length = Column(Integer, nullable=True)
    max_completion_tokens = Column(Integer, nullable=True)
    
    # Parameters and features
    supported_params = Column(JSON, nullable=True)
    quantization = Column(String(50), nullable=True)
    supports_caching = Column(Boolean, nullable=True)
    
    # Status and health
    status = Column(SQLEnum(EndpointStatus), default=EndpointStatus.UNKNOWN)
    uptime_percent = Column(Float, nullable=True)
    
    # Raw data
    raw_json = Column(JSON, nullable=True)
    
    # Audit timestamps
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Relationship
    model = relationship("OpenRouterModel", back_populates="endpoints")
    
    __table_args__ = (
        UniqueConstraint("model_id", "provider_name", "endpoint_tag", name="uq_endpoint_composite"),
        Index("ix_openrouter_endpoints_provider", "provider_name"),
        Index("ix_openrouter_endpoints_status", "status"),
    )
    
    @classmethod
    def generate_id(cls, model_id: str, provider: str, tag: Optional[str] = None) -> str:
        """Generate composite ID."""
        return f"{model_id}::{provider}::{tag or 'default'}"
    
    @classmethod
    def from_api_response(cls, model_id: str, data: Dict[str, Any]) -> "OpenRouterEndpoint":
        """Create endpoint from API response."""
        provider = data.get("provider", "unknown")
        tag = data.get("tag")
        
        endpoint = cls(
            id=cls.generate_id(model_id, provider, tag),
            model_id=model_id,
            provider_name=provider,
            endpoint_tag=tag,
            raw_json=data,
            fetched_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        
        # Pricing
        pricing = data.get("pricing", {})
        if pricing.get("prompt"):
            endpoint.endpoint_pricing_prompt = Decimal(str(pricing["prompt"]))
        if pricing.get("completion"):
            endpoint.endpoint_pricing_completion = Decimal(str(pricing["completion"]))
        
        # Limits
        endpoint.context_length = data.get("context_length")
        endpoint.max_completion_tokens = data.get("max_completion_tokens")
        
        # Features
        endpoint.supported_params = data.get("supported_parameters")
        endpoint.quantization = data.get("quantization")
        endpoint.supports_caching = data.get("supports_prompt_caching")
        
        # Status
        status_str = data.get("status", "unknown").lower()
        try:
            endpoint.status = EndpointStatus(status_str)
        except ValueError:
            endpoint.status = EndpointStatus.UNKNOWN
        
        endpoint.uptime_percent = data.get("uptime")
        
        return endpoint


# =============================================================================
# Usage Telemetry (for Rankings)
# =============================================================================

class OpenRouterUsageTelemetry(Base):
    """Usage telemetry for building rankings.
    
    Aggregated usage metrics from our inference gateway.
    No raw prompts/responses stored (privacy).
    
    Data Dictionary:
    ----------------
    All fields are derived from our internal inference gateway telemetry.
    No OpenRouter-sourced ranking data (compliance requirement).
    """
    __tablename__ = "openrouter_usage_telemetry"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Dimensions
    model_id = Column(String(255), ForeignKey("openrouter_models.id"), nullable=False, index=True)
    provider_name = Column(String(100), nullable=True)
    tenant_id = Column(String(100), nullable=True, index=True)  # For per-tenant analytics
    
    # Time bucket (hourly aggregation)
    time_bucket = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Usage metrics
    request_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Token metrics
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    
    # Cost metrics
    total_cost_usd = Column(Numeric(12, 6), default=0)
    
    # Latency metrics (milliseconds)
    total_latency_ms = Column(Integer, default=0)
    min_latency_ms = Column(Integer, nullable=True)
    max_latency_ms = Column(Integer, nullable=True)
    p50_latency_ms = Column(Integer, nullable=True)
    p95_latency_ms = Column(Integer, nullable=True)
    
    # Tool usage
    tool_call_count = Column(Integer, default=0)
    tool_success_count = Column(Integer, default=0)
    
    # Streaming
    streaming_request_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index("ix_telemetry_model_time", "model_id", "time_bucket"),
        Index("ix_telemetry_tenant_time", "tenant_id", "time_bucket"),
        UniqueConstraint("model_id", "provider_name", "tenant_id", "time_bucket", name="uq_telemetry_bucket"),
    )
    
    @property
    def success_rate(self) -> float:
        """Compute success rate."""
        total = self.request_count or 0
        return (self.success_count or 0) / total if total > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        """Compute average latency."""
        total = self.request_count or 0
        return (self.total_latency_ms or 0) / total if total > 0 else 0.0


# =============================================================================
# Prompt Templates
# =============================================================================

class PromptTemplate(Base):
    """Saved prompt templates.
    
    Supports variables, versioning, and workspace sharing.
    """
    __tablename__ = "openrouter_prompt_templates"
    
    id = Column(String(36), primary_key=True)  # UUID
    
    # Ownership
    user_id = Column(String(100), nullable=False, index=True)
    workspace_id = Column(String(100), nullable=True, index=True)
    
    # Template info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    
    # Template content
    system_prompt = Column(Text, nullable=True)
    user_prompt_template = Column(Text, nullable=False)  # May contain {{variables}}
    
    # Variables schema
    variables = Column(JSON, nullable=True)  # [{name, type, default, description}]
    
    # Model configuration
    default_model_id = Column(String(255), nullable=True)
    default_params = Column(JSON, nullable=True)  # {temperature, max_tokens, etc.}
    
    # Requirements
    required_capabilities = Column(JSON, nullable=True)  # ["tools", "vision", etc.]
    
    # Versioning
    version = Column(Integer, default=1)
    version_notes = Column(Text, nullable=True)
    parent_version_id = Column(String(36), nullable=True)
    
    # Visibility
    visibility = Column(SQLEnum(TemplateVisibility), default=TemplateVisibility.PRIVATE)
    
    # Usage stats
    use_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("ix_templates_user_name", "user_id", "name"),
        Index("ix_templates_category", "category"),
    )


# =============================================================================
# Saved Runs (Redacted)
# =============================================================================

class SavedRun(Base):
    """Saved prompt runs with redacted content.
    
    By default, only stores metadata and hashed content summaries.
    Full content storage requires explicit user opt-in.
    """
    __tablename__ = "openrouter_saved_runs"
    
    id = Column(String(36), primary_key=True)  # UUID
    
    # Ownership
    user_id = Column(String(100), nullable=False, index=True)
    workspace_id = Column(String(100), nullable=True)
    
    # Associated template (optional)
    template_id = Column(String(36), ForeignKey("openrouter_prompt_templates.id"), nullable=True)
    
    # Model used
    model_id = Column(String(255), nullable=False, index=True)
    provider_used = Column(String(100), nullable=True)
    
    # Run metadata (always stored)
    run_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    latency_ms = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(12, 6), nullable=True)
    success = Column(Boolean, default=True)
    error_type = Column(String(100), nullable=True)
    
    # Parameters used
    params_used = Column(JSON, nullable=True)
    
    # Content (redacted by default)
    # If store_content=False: only hashes/lengths stored
    store_content = Column(Boolean, default=False)
    prompt_hash = Column(String(64), nullable=True)  # SHA256
    prompt_length = Column(Integer, nullable=True)
    response_hash = Column(String(64), nullable=True)
    response_length = Column(Integer, nullable=True)
    
    # Opt-in full content (encrypted)
    prompt_content = Column(Text, nullable=True)  # Only if store_content=True
    response_content = Column(Text, nullable=True)
    
    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5
    user_notes = Column(Text, nullable=True)
    
    # OpenRouter generation ID (for cost retrieval)
    generation_id = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index("ix_runs_user_time", "user_id", "run_at"),
        Index("ix_runs_model", "model_id"),
    )

