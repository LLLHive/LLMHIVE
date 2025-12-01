"""Google Gemini Provider for LLMHive.

Integrates Google's Gemini models (Gemini 2.5 Pro, Flash, etc.) via the
google-generativeai SDK.

Usage:
    provider = GeminiProvider(api_key="your-api-key")
    result = await provider.generate("Hello, world!", model="gemini-2.0-flash")
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    
    Supports:
    - gemini-2.0-flash-exp (latest)
    - gemini-1.5-pro
    - gemini-1.5-flash
    - gemini-2.5-pro (mapped to gemini-1.5-pro)
    """
    
    # Orchestration kwargs to filter out (not valid for Gemini API)
    ORCHESTRATION_KWARGS = {
        'use_hrm', 'use_adaptive_routing', 'use_deep_consensus', 
        'use_prompt_diffusion', 'use_memory', 'accuracy_level',
        'session_id', 'user_id', 'user_tier', 'enable_tools',
        'knowledge_snippets', 'context', 'plan', 'db_session',
    }
    
    # Model name mapping (UI names to actual Gemini model names)
    # Note: Use "gemini-1.5-flash-latest" or "gemini-1.5-pro-latest" for latest versions
    MODEL_MAPPING = {
        "gemini-2.5-pro": "gemini-1.5-pro-latest",
        "gemini-2.5-flash": "gemini-1.5-flash-latest",
        "gemini-2.0-flash": "gemini-1.5-flash-latest",
        "gemini-pro": "gemini-1.5-pro-latest",
        "gemini-flash": "gemini-1.5-flash-latest",
        "gemini-1.5-pro": "gemini-1.5-pro-latest",
        "gemini-1.5-flash": "gemini-1.5-flash-latest",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key (or uses GEMINI_API_KEY env var)
        """
        self.name = "gemini"
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("Gemini API key not provided")
        
        # Initialize the Google Generative AI client
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai
            logger.info("Gemini provider initialized")
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
    
    def _map_model_name(self, model: str) -> str:
        """Map UI model names to actual Gemini model names."""
        model_lower = model.lower()
        return self.MODEL_MAPPING.get(model_lower, model)
    
    async def generate(
        self,
        prompt: str,
        model: str = "gemini-1.5-flash-latest",
        **kwargs,
    ) -> GeminiResult:
        """
        Generate a response using Gemini.
        
        Args:
            prompt: The input prompt
            model: Model name (e.g., "gemini-1.5-pro", "gemini-2.0-flash-exp")
            **kwargs: Additional parameters (filtered for Gemini API)
            
        Returns:
            GeminiResult with response content and metadata
        """
        # Filter out orchestration-specific kwargs
        api_kwargs = {
            k: v for k, v in kwargs.items() 
            if k not in self.ORCHESTRATION_KWARGS
        }
        
        # Map model name
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
        model: str = "gemini-1.5-flash-latest",
        **kwargs,
    ) -> GeminiResult:
        """Alias for generate() - used by orchestration components."""
        return await self.generate(prompt, model=model, **kwargs)
    
    def supports_model(self, model: str) -> bool:
        """Check if this provider supports the given model."""
        model_lower = model.lower()
        return (
            "gemini" in model_lower or
            model_lower in self.MODEL_MAPPING
        )
    
    def list_models(self) -> List[str]:
        """List available models."""
        return [
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest",
        ]

