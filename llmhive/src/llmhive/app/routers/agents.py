"""Agents API router for LLMHive.

Provides endpoints to list available LLM models/agents based on configured providers.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])


class AgentInfo(BaseModel):
    """Information about an available agent/model."""
    id: str
    name: str
    provider: str
    available: bool
    description: Optional[str] = None
    capabilities: Optional[dict] = None


class AgentsResponse(BaseModel):
    """Response containing list of available agents."""
    agents: List[AgentInfo]
    source: str = "backend"


# Model definitions matching frontend lib/models.ts
KNOWN_MODELS = {
    "openai": [
        AgentInfo(
            id="gpt-4o",
            name="GPT-4o",
            provider="openai",
            available=True,
            description="OpenAI's flagship multimodal model",
            capabilities={"vision": True, "codeExecution": True, "webSearch": True, "reasoning": True},
        ),
        AgentInfo(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider="openai",
            available=True,
            description="Fast and cost-effective OpenAI model",
            capabilities={"vision": True, "codeExecution": True, "webSearch": True, "reasoning": False},
        ),
    ],
    "anthropic": [
        AgentInfo(
            id="claude-sonnet-4",
            name="Claude Sonnet 4",
            provider="anthropic",
            available=True,
            description="Anthropic's latest and most capable model",
            capabilities={"vision": True, "codeExecution": True, "webSearch": False, "reasoning": True},
        ),
        AgentInfo(
            id="claude-3.5-haiku",
            name="Claude 3.5 Haiku",
            provider="anthropic",
            available=True,
            description="Fast and efficient Claude model",
            capabilities={"vision": True, "codeExecution": False, "webSearch": False, "reasoning": False},
        ),
    ],
    "google": [
        AgentInfo(
            id="gemini-2.5-pro",
            name="Gemini 2.5 Pro",
            provider="google",
            available=True,
            description="Google's most capable multimodal model",
            capabilities={"vision": True, "codeExecution": True, "webSearch": True, "reasoning": True},
        ),
        AgentInfo(
            id="gemini-2.5-flash",
            name="Gemini 2.5 Flash",
            provider="google",
            available=True,
            description="Fast and efficient Gemini model",
            capabilities={"vision": True, "codeExecution": True, "webSearch": True, "reasoning": False},
        ),
    ],
    "xai": [
        AgentInfo(
            id="grok-2",
            name="Grok 2",
            provider="xai",
            available=True,
            description="xAI's conversational AI with real-time knowledge",
            capabilities={"vision": True, "codeExecution": False, "webSearch": True, "reasoning": True},
        ),
    ],
    "deepseek": [
        AgentInfo(
            id="deepseek-chat",
            name="DeepSeek V3",
            provider="deepseek",
            available=True,
            description="DeepSeek's flagship conversational AI",
            capabilities={"vision": False, "codeExecution": True, "webSearch": False, "reasoning": True},
        ),
    ],
}

# Map environment variable names to provider keys
PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "google": "GEMINI_API_KEY",
    "xai": "GROK_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}


def _is_provider_configured(provider: str) -> bool:
    """Check if a provider has API keys configured."""
    env_vars = PROVIDER_ENV_VARS.get(provider)
    if env_vars is None:
        return False
    
    if isinstance(env_vars, list):
        return any(os.getenv(var) for var in env_vars)
    return bool(os.getenv(env_vars))


def _get_available_agents() -> List[AgentInfo]:
    """Get list of available agents based on configured providers."""
    agents = []
    
    for provider, models in KNOWN_MODELS.items():
        is_available = _is_provider_configured(provider)
        
        for model in models:
            agent = AgentInfo(
                id=model.id,
                name=model.name,
                provider=model.provider,
                available=is_available,
                description=model.description,
                capabilities=model.capabilities,
            )
            agents.append(agent)
    
    return agents


@router.get("/agents", response_model=AgentsResponse, status_code=status.HTTP_200_OK)
@router.get("/v1/agents", response_model=AgentsResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
async def list_agents() -> AgentsResponse:
    """
    List available LLM models/agents.
    
    Returns all known models with their availability status based on
    whether the corresponding provider API keys are configured.
    
    Returns:
        AgentsResponse with list of agents and source identifier.
    """
    try:
        agents = _get_available_agents()
        
        # Log configured providers
        configured = [p for p in PROVIDER_ENV_VARS if _is_provider_configured(p)]
        logger.info("Agents endpoint called. Configured providers: %s", configured)
        
        return AgentsResponse(agents=agents, source="backend")
        
    except Exception as exc:
        logger.exception("Error listing agents: %s", exc)
        # Return all agents as unavailable on error
        all_agents = []
        for models in KNOWN_MODELS.values():
            for model in models:
                model.available = False
                all_agents.append(model)
        return AgentsResponse(agents=all_agents, source="backend-error")
