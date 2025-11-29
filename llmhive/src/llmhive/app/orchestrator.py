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
            **kwargs: Additional orchestration parameters
            
        Returns:
            ProtocolResult-like object with final_response, initial_responses, etc.
        """
        logger.info(f"Orchestrating request with {len(models or [])} model(s)")
        
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
        
        # Select models to use (default to stub if none provided)
        models_to_use = models or ["stub"]
        if not models_to_use:
            models_to_use = ["stub"]
        
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
                        provider_result = await provider.generate(prompt, model=model_name, **kwargs)
                    else:
                        provider_result = provider.generate(prompt, model=model_name, **kwargs)
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
                    content = f"Stub response: {prompt[:100]}..."
                    model_name = "stub"
                    tokens = 0
                
                result = LLMResult(
                    content=content,
                    model=model_name,
                    tokens=tokens
                )
            except Exception as e:
                logger.error(f"Error generating response from provider: {e}")
                result = LLMResult(
                    content=f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again.",
                    model=models_to_use[0] if models_to_use else "stub",
                    tokens=0
                )
        
        # Return ProtocolResult structure expected by orchestrator_adapter
        return ProtocolResult(
            final_response=result,
            initial_responses=[result],
            critiques=[],
            improvements=[],
            consensus_notes=[f"Response generated using {result.model}"],
            step_outputs={"answer": [result]},
            supporting_notes=[],
            quality_assessments={}
        )

