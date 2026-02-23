"""Google Gemini Provider for LLMHive.

Integrates Google's Gemini models via the google-generativeai SDK.
Model IDs are resolved dynamically through ``google_model_discovery``.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from llmhive.app.providers.google_model_discovery import (
        get_google_model_cached,
        select_best_google_model,
        GoogleModel,
    )
    _HAS_DISCOVERY = True
except ImportError:
    _HAS_DISCOVERY = False


@dataclass
class GeminiResult:
    """Result from Gemini generation."""
    content: str
    text: str  # Alias for content
    model: str
    tokens_used: int
    finish_reason: Optional[str] = None
    safety_ratings: Optional[List[Dict]] = None


class GeminiProvider:
    """Provider for Google Gemini models.

    Model names are resolved dynamically via ``google_model_discovery``.
    Legacy aliases (``gemini-1.5-pro``, ``gemini-pro``, etc.) are mapped
    to the best available model at runtime.
    """
    
    ORCHESTRATION_KWARGS = {
        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
        'session_id', 'user_id', 'user_tier', 'enable_tools',
        'knowledge_snippets', 'context', 'plan', 'db_session',
    }

    _VARIANT_ALIASES = {
        "gemini-pro": "pro",
        "gemini-flash": "flash",
    }

    _discovered_models: Optional[List["GoogleModel"]] = None
    
    def __init__(self, api_key: Optional[str] = None):
        self.name = "gemini"
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
        
        if not self.api_key:
            raise ValueError("Gemini API key not provided")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai
            self._default_model: Optional[str] = None
            logger.info("Gemini provider initialized")
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
    
    def _map_model_name(self, model: str) -> str:
        """Resolve *model* to the best available Gemini model ID.

        Pure aliases (``gemini-pro`` -> ``pro`` workload) are resolved
        via discovery.  Direct model IDs are passed through.
        """
        model_lower = model.lower().strip()

        if model_lower in self._VARIANT_ALIASES:
            workload = self._VARIANT_ALIASES[model_lower]
            if _HAS_DISCOVERY and GeminiProvider._discovered_models:
                try:
                    return select_best_google_model(
                        GeminiProvider._discovered_models, workload=workload,
                    )
                except ValueError:
                    pass

        if "gemini" in model_lower:
            return model_lower

        return model
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> GeminiResult:
        """Generate a response using Gemini.

        *model* is resolved through auto-discovery if ``None`` or an alias.
        """
        # Filter out orchestration-specific kwargs
        api_kwargs = {
            k: v for k, v in kwargs.items() 
            if k not in self.ORCHESTRATION_KWARGS
        }

        if model is None:
            if self._default_model:
                model = self._default_model
            elif _HAS_DISCOVERY and GeminiProvider._discovered_models:
                try:
                    model = select_best_google_model(
                        GeminiProvider._discovered_models, workload="speed",
                    )
                except ValueError:
                    model = "gemini-2.5-flash"
            else:
                model = "gemini-2.5-flash"

        actual_model = self._map_model_name(model)
        
        try:
            # Get the generative model
            gen_model = self._genai.GenerativeModel(actual_model)
            
            # Configure generation parameters
            generation_config = self._genai.GenerationConfig(
                max_output_tokens=api_kwargs.get("max_tokens", 2048),
                temperature=api_kwargs.get("temperature", 0.7),
            )
            
            # Generate content
            response = gen_model.generate_content(
                prompt,
                generation_config=generation_config,
            )
            
            # Extract response text
            content = ""
            if response.text:
                content = response.text
            elif response.parts:
                content = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            
            # Estimate token count (Gemini doesn't always return this)
            # Rough estimate: ~4 chars per token
            tokens_used = len(prompt + content) // 4
            
            # Extract safety ratings if available
            safety_ratings = None
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                safety_ratings = [
                    {"category": str(r.category), "probability": str(r.probability)}
                    for r in getattr(response.prompt_feedback, 'safety_ratings', [])
                ]
            
            return GeminiResult(
                content=content,
                text=content,
                model=actual_model,
                tokens_used=tokens_used,
                finish_reason=getattr(response, 'finish_reason', None),
                safety_ratings=safety_ratings,
            )
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> GeminiResult:
        """Alias for generate() — used by orchestration components."""
        return await self.generate(prompt, model=model, **kwargs)
    
    def supports_model(self, model: str) -> bool:
        """Check if this provider supports the given model."""
        model_lower = model.lower()
        if "gemini" in model_lower:
            return True
        if model_lower in self._VARIANT_ALIASES:
            return True
        return False
    
    def list_models(self) -> List[str]:
        """List available models (from discovery cache if available)."""
        if _HAS_DISCOVERY and GeminiProvider._discovered_models:
            return [m.model_id for m in GeminiProvider._discovered_models]
        return []

