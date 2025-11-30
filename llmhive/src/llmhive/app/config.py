"""Configuration settings for LLMHive."""
from __future__ import annotations

import os
from typing import List


class Settings:
    """Application settings loaded from environment variables."""
    
    # Default models for orchestration
    default_models: List[str] = ["gpt-4o-mini", "claude-3-haiku"]
    
    # API key (optional, for authentication)
    api_key: str | None = os.getenv("API_KEY")
    
    # Provider API keys (loaded from environment)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    grok_api_key: str | None = os.getenv("GROK_API_KEY")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    manus_api_key: str | None = os.getenv("MANUS_API_KEY")
    
    # Provider timeouts (optional)
    openai_timeout_seconds: int | None = None
    anthropic_timeout_seconds: int | None = None
    grok_timeout_seconds: int | None = None
    gemini_timeout_seconds: int | None = None
    deepseek_timeout_seconds: int | None = None
    manus_timeout_seconds: int | None = None
    
    # Vector Database Configuration (Pinecone)
    pinecone_api_key: str | None = os.getenv("PINECONE_API_KEY")
    pinecone_environment: str = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "llmhive-memory")
    
    # Embedding Model Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    
    # Memory Configuration
    memory_namespace_per_user: bool = os.getenv("MEMORY_NAMESPACE_PER_USER", "true").lower() == "true"
    memory_ttl_days: int = int(os.getenv("MEMORY_TTL_DAYS", "90"))
    memory_max_results: int = int(os.getenv("MEMORY_MAX_RESULTS", "10"))
    memory_min_score: float = float(os.getenv("MEMORY_MIN_SCORE", "0.7"))


# Global settings instance
settings = Settings()

