"""Orchestrator module for LLMHive - provides unified interface for LLM orchestration."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

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
    """
    
    def __init__(self):
        """Initialize orchestrator with available providers."""
        self.providers: Dict[str, Any] = {}
        self.mcp_client = None  # MCP client (optional)
        
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
                self.providers["openai"] = type('OpenAIProvider', (), {
                    'name': 'openai',
                    'client': OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                })()
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        # Initialize Grok provider
        if os.getenv("GROK_API_KEY"):
            try:
                # Grok uses xAI API
                self.providers["grok"] = type('GrokProvider', (), {
                    'name': 'grok',
                    'api_key': os.getenv("GROK_API_KEY")
                })()
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
                self.providers["anthropic"] = type('AnthropicProvider', (), {
                    'name': 'anthropic',
                    'client': anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                })()
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
            **kwargs: Additional orchestration parameters
            
        Returns:
            OrchestrationArtifacts or dict with results
        """
        logger.info(f"Orchestrating request with {len(models or [])} model(s)")
        
        # For now, return a simple result structure
        # This can be enhanced with actual orchestration logic
        if OrchestrationArtifacts:
            return OrchestrationArtifacts(
                responses=[],
                models_used=models or ["stub"],
                reasoning_used="simple"
            )
        else:
            # Fallback to dict if OrchestrationArtifacts not available
            return {
                "responses": [],
                "models_used": models or ["stub"],
                "reasoning_used": "simple",
                "prompt": prompt
            }

