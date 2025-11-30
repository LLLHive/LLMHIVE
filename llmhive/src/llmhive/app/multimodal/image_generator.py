"""Image Generation Tools for LLMHive.

This module provides image generation capabilities:
- DALL-E 3 (OpenAI) - High quality, creative images
- Stable Diffusion (via API) - Open source alternative
- Image editing and variations

Usage:
    generator = ImageGenerator()
    result = await generator.generate("A robot reading a book in a cozy library")
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class ImageGenerationProvider(str, Enum):
    """Supported image generation providers."""
    DALL_E_3 = "dall_e_3"
    DALL_E_2 = "dall_e_2"
    STABLE_DIFFUSION = "stable_diffusion"
    MIDJOURNEY = "midjourney"  # Future


class ImageSize(str, Enum):
    """Standard image sizes."""
    SMALL = "256x256"
    MEDIUM = "512x512"
    LARGE = "1024x1024"
    WIDE = "1792x1024"
    TALL = "1024x1792"


class ImageQuality(str, Enum):
    """Image quality levels."""
    STANDARD = "standard"
    HD = "hd"


class ImageStyle(str, Enum):
    """Image generation styles."""
    VIVID = "vivid"
    NATURAL = "natural"


@dataclass(slots=True)
class ImageGenerationResult:
    """Result of image generation."""
    success: bool
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    revised_prompt: Optional[str] = None
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    cost_estimate_usd: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def save_to_file(self, path: Union[str, Path]) -> bool:
        """Save the generated image to a file."""
        if not self.image_base64:
            return False
        
        try:
            image_data = base64.b64decode(self.image_base64)
            Path(path).write_bytes(image_data)
            return True
        except Exception as e:
            logger.error("Failed to save image: %s", e)
            return False


# Safety content filters
CONTENT_FILTERS = [
    r"\b(nude|naked|explicit|porn|xxx|nsfw|sexual)\b",
    r"\b(gore|violence|blood|murder|kill)\b",
    r"\b(racist|hate\s*speech|slur)\b",
    r"\b(child|minor|underage)\s+(sexual|nude|naked)",
    r"\b(weapon|bomb|explosive)\s+(make|build|create|how\s*to)",
]


def is_safe_prompt(prompt: str) -> tuple[bool, Optional[str]]:
    """Check if a prompt is safe for image generation."""
    prompt_lower = prompt.lower()
    
    for pattern in CONTENT_FILTERS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return False, f"Prompt contains potentially unsafe content matching: {pattern}"
    
    return True, None


# ==============================================================================
# Image Generator
# ==============================================================================

class ImageGenerator:
    """Generate images using AI models.
    
    Supports:
    - DALL-E 3 (OpenAI) - Best quality
    - DALL-E 2 (OpenAI) - Faster, cheaper
    - Stable Diffusion (via API)
    
    Usage:
        generator = ImageGenerator()
        result = await generator.generate("A sunset over mountains")
    """
    
    # Cost estimates (USD per image)
    COST_ESTIMATES = {
        "dall_e_3_standard_1024": 0.04,
        "dall_e_3_hd_1024": 0.08,
        "dall_e_3_standard_wide": 0.08,
        "dall_e_3_hd_wide": 0.12,
        "dall_e_2_256": 0.016,
        "dall_e_2_512": 0.018,
        "dall_e_2_1024": 0.02,
        "stable_diffusion": 0.01,
    }
    
    def __init__(
        self,
        *,
        preferred_provider: Optional[ImageGenerationProvider] = None,
        openai_api_key: Optional[str] = None,
        stability_api_key: Optional[str] = None,
        enable_safety_filter: bool = True,
    ):
        """
        Initialize the ImageGenerator.
        
        Args:
            preferred_provider: Preferred provider to use
            openai_api_key: OpenAI API key
            stability_api_key: Stability AI API key
            enable_safety_filter: Whether to filter unsafe prompts
        """
        self.preferred_provider = preferred_provider
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.stability_api_key = stability_api_key or os.getenv("STABILITY_API_KEY")
        self.enable_safety_filter = enable_safety_filter
        
        # Initialize available providers
        self._available_providers: List[ImageGenerationProvider] = []
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize and detect available providers."""
        # Check OpenAI
        if self.openai_api_key:
            try:
                import openai  # noqa: F401
                self._available_providers.append(ImageGenerationProvider.DALL_E_3)
                self._available_providers.append(ImageGenerationProvider.DALL_E_2)
                logger.info("DALL-E available")
            except ImportError:
                logger.debug("OpenAI package not installed")
        
        # Check Stability AI
        if self.stability_api_key:
            self._available_providers.append(ImageGenerationProvider.STABLE_DIFFUSION)
            logger.info("Stable Diffusion available")
        
        if self._available_providers:
            logger.info("Available image generators: %s", 
                       [p.value for p in self._available_providers])
    
    def get_best_provider(self) -> Optional[ImageGenerationProvider]:
        """Get the best available provider."""
        if self.preferred_provider and self.preferred_provider in self._available_providers:
            return self.preferred_provider
        
        # Prefer DALL-E 3 for quality
        if ImageGenerationProvider.DALL_E_3 in self._available_providers:
            return ImageGenerationProvider.DALL_E_3
        
        return self._available_providers[0] if self._available_providers else None
    
    async def generate(
        self,
        prompt: str,
        *,
        size: ImageSize = ImageSize.LARGE,
        quality: ImageQuality = ImageQuality.STANDARD,
        style: ImageStyle = ImageStyle.VIVID,
        n: int = 1,
        return_base64: bool = False,
    ) -> ImageGenerationResult:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            size: Image size
            quality: Image quality (for DALL-E 3)
            style: Image style (for DALL-E 3)
            n: Number of images to generate (usually 1 for DALL-E 3)
            return_base64: Whether to return base64 data instead of URL
            
        Returns:
            ImageGenerationResult with URL or base64 data
        """
        # Safety check
        if self.enable_safety_filter:
            is_safe, reason = is_safe_prompt(prompt)
            if not is_safe:
                return ImageGenerationResult(
                    success=False,
                    error=f"Prompt rejected by safety filter: {reason}",
                )
        
        # Get provider
        provider = self.get_best_provider()
        
        if provider is None:
            return ImageGenerationResult(
                success=False,
                error="No image generation providers available. Configure OPENAI_API_KEY or STABILITY_API_KEY.",
            )
        
        logger.info("Generating image with provider: %s", provider.value)
        
        try:
            if provider in (ImageGenerationProvider.DALL_E_3, ImageGenerationProvider.DALL_E_2):
                return await self._generate_with_dalle(
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    style=style,
                    n=n,
                    return_base64=return_base64,
                    use_dalle3=(provider == ImageGenerationProvider.DALL_E_3),
                )
            
            elif provider == ImageGenerationProvider.STABLE_DIFFUSION:
                return await self._generate_with_stable_diffusion(
                    prompt=prompt,
                    size=size,
                    return_base64=return_base64,
                )
            
            else:
                return ImageGenerationResult(
                    success=False,
                    error=f"Provider not implemented: {provider.value}",
                )
                
        except Exception as e:
            logger.error("Image generation failed: %s", e)
            return ImageGenerationResult(
                success=False,
                error=str(e),
                provider_used=provider.value if provider else None,
            )
    
    async def _generate_with_dalle(
        self,
        prompt: str,
        size: ImageSize,
        quality: ImageQuality,
        style: ImageStyle,
        n: int,
        return_base64: bool,
        use_dalle3: bool,
    ) -> ImageGenerationResult:
        """Generate image using DALL-E."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # DALL-E 3 only supports certain sizes
        if use_dalle3:
            model = "dall-e-3"
            # Validate size for DALL-E 3
            valid_sizes = [ImageSize.LARGE.value, ImageSize.WIDE.value, ImageSize.TALL.value]
            if size.value not in valid_sizes:
                size = ImageSize.LARGE
        else:
            model = "dall-e-2"
            # DALL-E 2 sizes
            valid_sizes = [ImageSize.SMALL.value, ImageSize.MEDIUM.value, ImageSize.LARGE.value]
            if size.value not in valid_sizes:
                size = ImageSize.LARGE
        
        # Build request
        kwargs: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": 1 if use_dalle3 else n,  # DALL-E 3 only supports n=1
            "size": size.value,
            "response_format": "b64_json" if return_base64 else "url",
        }
        
        if use_dalle3:
            kwargs["quality"] = quality.value
            kwargs["style"] = style.value
        
        # Make API call
        response = await client.images.generate(**kwargs)
        
        # Parse response
        image_data = response.data[0]
        
        # Estimate cost
        cost_key = f"dall_e_{'3' if use_dalle3 else '2'}_{quality.value}_{size.value.split('x')[0]}"
        cost = self.COST_ESTIMATES.get(cost_key, 0.04)
        
        return ImageGenerationResult(
            success=True,
            image_url=image_data.url if hasattr(image_data, 'url') else None,
            image_base64=image_data.b64_json if hasattr(image_data, 'b64_json') else None,
            revised_prompt=image_data.revised_prompt if hasattr(image_data, 'revised_prompt') else None,
            provider_used=ImageGenerationProvider.DALL_E_3.value if use_dalle3 else ImageGenerationProvider.DALL_E_2.value,
            model_used=model,
            cost_estimate_usd=cost,
            metadata={
                "size": size.value,
                "quality": quality.value,
                "style": style.value,
            },
        )
    
    async def _generate_with_stable_diffusion(
        self,
        prompt: str,
        size: ImageSize,
        return_base64: bool,
    ) -> ImageGenerationResult:
        """Generate image using Stable Diffusion via Stability AI API."""
        import httpx
        
        # Parse size
        try:
            width, height = map(int, size.value.split('x'))
        except ValueError:
            width, height = 1024, 1024
        
        # Stability AI API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.stability_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [{"text": prompt, "weight": 1}],
                    "cfg_scale": 7,
                    "height": height,
                    "width": width,
                    "samples": 1,
                    "steps": 30,
                },
                timeout=60.0,
            )
            
            if response.status_code != 200:
                return ImageGenerationResult(
                    success=False,
                    error=f"Stability API error: {response.status_code} - {response.text}",
                )
            
            data = response.json()
            artifacts = data.get("artifacts", [])
            
            if not artifacts:
                return ImageGenerationResult(
                    success=False,
                    error="No images generated",
                )
            
            image_base64 = artifacts[0].get("base64")
            
            return ImageGenerationResult(
                success=True,
                image_base64=image_base64,
                provider_used=ImageGenerationProvider.STABLE_DIFFUSION.value,
                model_used="stable-diffusion-xl-1024-v1-0",
                cost_estimate_usd=self.COST_ESTIMATES.get("stable_diffusion", 0.01),
                metadata={"size": size.value},
            )
    
    async def create_variation(
        self,
        image: Union[str, Path, bytes],
        *,
        size: ImageSize = ImageSize.LARGE,
        n: int = 1,
    ) -> ImageGenerationResult:
        """
        Create a variation of an existing image.
        
        Note: Only supported by DALL-E 2.
        
        Args:
            image: Original image (path or bytes)
            size: Size of the variation
            n: Number of variations
            
        Returns:
            ImageGenerationResult with variation
        """
        if ImageGenerationProvider.DALL_E_2 not in self._available_providers:
            return ImageGenerationResult(
                success=False,
                error="Image variations require DALL-E 2 (OpenAI)",
            )
        
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Load image
        if isinstance(image, (str, Path)):
            image_bytes = Path(image).read_bytes()
        else:
            image_bytes = image
        
        # Create variation
        response = await client.images.create_variation(
            image=image_bytes,
            n=n,
            size=size.value,
        )
        
        image_data = response.data[0]
        
        return ImageGenerationResult(
            success=True,
            image_url=image_data.url if hasattr(image_data, 'url') else None,
            provider_used=ImageGenerationProvider.DALL_E_2.value,
            model_used="dall-e-2",
        )
    
    async def edit_image(
        self,
        image: Union[str, Path, bytes],
        prompt: str,
        mask: Optional[Union[str, Path, bytes]] = None,
        *,
        size: ImageSize = ImageSize.LARGE,
    ) -> ImageGenerationResult:
        """
        Edit an image using a mask and prompt.
        
        Note: Only supported by DALL-E 2.
        
        Args:
            image: Original image
            prompt: Description of the edit
            mask: Mask image (transparent areas will be edited)
            size: Output size
            
        Returns:
            ImageGenerationResult with edited image
        """
        if ImageGenerationProvider.DALL_E_2 not in self._available_providers:
            return ImageGenerationResult(
                success=False,
                error="Image editing requires DALL-E 2 (OpenAI)",
            )
        
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Load image
        if isinstance(image, (str, Path)):
            image_bytes = Path(image).read_bytes()
        else:
            image_bytes = image
        
        # Load mask if provided
        mask_bytes = None
        if mask is not None:
            if isinstance(mask, (str, Path)):
                mask_bytes = Path(mask).read_bytes()
            else:
                mask_bytes = mask
        
        # Edit image
        kwargs: Dict[str, Any] = {
            "image": image_bytes,
            "prompt": prompt,
            "n": 1,
            "size": size.value,
        }
        
        if mask_bytes:
            kwargs["mask"] = mask_bytes
        
        response = await client.images.edit(**kwargs)
        
        image_data = response.data[0]
        
        return ImageGenerationResult(
            success=True,
            image_url=image_data.url if hasattr(image_data, 'url') else None,
            provider_used=ImageGenerationProvider.DALL_E_2.value,
            model_used="dall-e-2",
        )


# ==============================================================================
# Convenience Functions
# ==============================================================================

_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """Get global ImageGenerator instance."""
    global _generator
    if _generator is None:
        _generator = ImageGenerator()
    return _generator


async def generate_image(
    prompt: str,
    *,
    size: ImageSize = ImageSize.LARGE,
    quality: ImageQuality = ImageQuality.STANDARD,
    style: ImageStyle = ImageStyle.VIVID,
) -> ImageGenerationResult:
    """
    Generate an image using the global generator.
    
    Args:
        prompt: Text description of the image
        size: Image size
        quality: Image quality
        style: Image style
        
    Returns:
        ImageGenerationResult
    """
    generator = get_image_generator()
    return await generator.generate(
        prompt,
        size=size,
        quality=quality,
        style=style,
    )

