"""Image Analysis Tools for LLMHive.

This module provides image analysis capabilities:
- OCR (Optical Character Recognition) for text in images
- Image captioning and description
- Object detection and landmark identification
- Integration with OpenAI Vision API and local models

Supports multiple backends:
1. OpenAI Vision (GPT-4 Vision) - Best quality
2. Local Tesseract OCR - For text extraction
3. CLIP/BLIP models - For local captioning
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class ImageAnalysisProvider(str, Enum):
    """Supported image analysis providers."""
    OPENAI_VISION = "openai_vision"
    ANTHROPIC_VISION = "anthropic_vision"
    TESSERACT_OCR = "tesseract_ocr"
    LOCAL_CLIP = "local_clip"
    GOOGLE_VISION = "google_vision"


class AnalysisType(str, Enum):
    """Types of image analysis."""
    DESCRIBE = "describe"  # General description
    OCR = "ocr"  # Text extraction
    OBJECTS = "objects"  # Object detection
    LANDMARKS = "landmarks"  # Landmark identification
    FACES = "faces"  # Face detection (if allowed)
    LABELS = "labels"  # Label classification


@dataclass(slots=True)
class DetectedObject:
    """A detected object in an image."""
    name: str
    confidence: float
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # x, y, width, height
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedText:
    """Text extracted from an image."""
    text: str
    confidence: float
    language: Optional[str] = None
    bounding_box: Optional[Tuple[int, int, int, int]] = None


@dataclass(slots=True)
class ImageAnalysisResult:
    """Result of image analysis."""
    description: str
    extracted_text: List[ExtractedText] = field(default_factory=list)
    detected_objects: List[DetectedObject] = field(default_factory=list)
    landmarks: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    image_size: Optional[Tuple[int, int]] = None
    provider_used: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def all_text(self) -> str:
        """Get all extracted text concatenated."""
        return " ".join(t.text for t in self.extracted_text)
    
    @property
    def summary(self) -> str:
        """Get a summary of the analysis."""
        parts = [self.description]
        
        if self.extracted_text:
            parts.append(f"Text found: {self.all_text[:200]}")
        
        if self.detected_objects:
            objects = ", ".join(o.name for o in self.detected_objects[:5])
            parts.append(f"Objects detected: {objects}")
        
        if self.landmarks:
            parts.append(f"Landmarks: {', '.join(self.landmarks[:3])}")
        
        return " | ".join(parts)


# ==============================================================================
# Image Utilities
# ==============================================================================

def encode_image_to_base64(image_path: Union[str, Path]) -> str:
    """Encode an image file to base64."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def encode_bytes_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64."""
    return base64.b64encode(image_bytes).decode("utf-8")


def get_image_mime_type(image_path: Union[str, Path]) -> str:
    """Get the MIME type of an image based on extension."""
    path = Path(image_path)
    extension = path.suffix.lower()
    
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    
    return mime_types.get(extension, "image/jpeg")


def is_valid_image_url(url: str) -> bool:
    """Check if a URL appears to be a valid image URL."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    
    # Check for common image extensions
    path_lower = parsed.path.lower()
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    
    if any(path_lower.endswith(ext) for ext in image_extensions):
        return True
    
    # Could also be a dynamic image URL
    return True  # Allow any HTTP(S) URL


# ==============================================================================
# Image Analyzer
# ==============================================================================

class ImageAnalyzer:
    """Analyze images using various providers.
    
    Supports:
    - OpenAI Vision API (GPT-4 Vision)
    - Anthropic Vision (Claude Vision)
    - Tesseract OCR (local)
    - Google Cloud Vision
    
    Usage:
        analyzer = ImageAnalyzer()
        result = await analyzer.analyze("path/to/image.jpg", analysis_types=[AnalysisType.DESCRIBE, AnalysisType.OCR])
    """
    
    def __init__(
        self,
        *,
        preferred_provider: Optional[ImageAnalysisProvider] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        google_credentials_path: Optional[str] = None,
        enable_ocr: bool = True,
        enable_local_fallback: bool = True,
    ):
        """
        Initialize the ImageAnalyzer.
        
        Args:
            preferred_provider: Preferred provider to use
            openai_api_key: OpenAI API key (or uses OPENAI_API_KEY env var)
            anthropic_api_key: Anthropic API key (or uses ANTHROPIC_API_KEY env var)
            google_credentials_path: Path to Google Cloud credentials
            enable_ocr: Whether to enable OCR analysis
            enable_local_fallback: Whether to use local models as fallback
        """
        self.preferred_provider = preferred_provider
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.google_credentials_path = google_credentials_path
        self.enable_ocr = enable_ocr
        self.enable_local_fallback = enable_local_fallback
        
        # Initialize available providers
        self._available_providers: List[ImageAnalysisProvider] = []
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize and detect available providers."""
        # Check OpenAI
        if self.openai_api_key:
            try:
                import openai  # noqa: F401
                self._available_providers.append(ImageAnalysisProvider.OPENAI_VISION)
                logger.info("OpenAI Vision available")
            except ImportError:
                logger.debug("OpenAI package not installed")
        
        # Check Anthropic
        if self.anthropic_api_key:
            try:
                import anthropic  # noqa: F401
                self._available_providers.append(ImageAnalysisProvider.ANTHROPIC_VISION)
                logger.info("Anthropic Vision available")
            except ImportError:
                logger.debug("Anthropic package not installed")
        
        # Check Tesseract OCR
        if self.enable_ocr:
            try:
                import pytesseract  # noqa: F401
                self._available_providers.append(ImageAnalysisProvider.TESSERACT_OCR)
                logger.info("Tesseract OCR available")
            except ImportError:
                logger.debug("pytesseract not installed")
        
        # Log available providers
        if self._available_providers:
            logger.info("Available image analysis providers: %s", 
                       [p.value for p in self._available_providers])
        else:
            logger.warning("No image analysis providers available")
    
    def get_best_provider(
        self,
        analysis_types: Optional[List[AnalysisType]] = None,
    ) -> Optional[ImageAnalysisProvider]:
        """Get the best available provider for the requested analysis types."""
        if self.preferred_provider and self.preferred_provider in self._available_providers:
            return self.preferred_provider
        
        # Prefer cloud providers for quality
        cloud_providers = [
            ImageAnalysisProvider.OPENAI_VISION,
            ImageAnalysisProvider.ANTHROPIC_VISION,
            ImageAnalysisProvider.GOOGLE_VISION,
        ]
        
        for provider in cloud_providers:
            if provider in self._available_providers:
                return provider
        
        # For OCR-only, prefer Tesseract
        if analysis_types and all(t == AnalysisType.OCR for t in analysis_types):
            if ImageAnalysisProvider.TESSERACT_OCR in self._available_providers:
                return ImageAnalysisProvider.TESSERACT_OCR
        
        # Return first available
        return self._available_providers[0] if self._available_providers else None
    
    async def analyze(
        self,
        image: Union[str, Path, bytes],
        *,
        analysis_types: Optional[List[AnalysisType]] = None,
        question: Optional[str] = None,
        max_tokens: int = 500,
    ) -> ImageAnalysisResult:
        """
        Analyze an image.
        
        Args:
            image: Image path, URL, or bytes
            analysis_types: Types of analysis to perform (default: describe)
            question: Optional specific question about the image
            max_tokens: Maximum tokens for response
            
        Returns:
            ImageAnalysisResult with analysis details
        """
        if analysis_types is None:
            analysis_types = [AnalysisType.DESCRIBE]
        
        # Determine image source
        if isinstance(image, bytes):
            image_base64 = encode_bytes_to_base64(image)
            image_url = None
            mime_type = "image/jpeg"
        elif isinstance(image, (str, Path)) and Path(image).exists():
            image_base64 = encode_image_to_base64(image)
            image_url = None
            mime_type = get_image_mime_type(image)
        elif isinstance(image, str) and is_valid_image_url(image):
            image_base64 = None
            image_url = image
            mime_type = None
        else:
            return ImageAnalysisResult(
                description="",
                error=f"Invalid image source: {image}",
            )
        
        # Get provider
        provider = self.get_best_provider(analysis_types)
        
        if provider is None:
            return ImageAnalysisResult(
                description="No image analysis providers available.",
                error="No providers configured",
            )
        
        logger.info("Analyzing image with provider: %s", provider.value)
        
        try:
            if provider == ImageAnalysisProvider.OPENAI_VISION:
                return await self._analyze_with_openai(
                    image_base64=image_base64,
                    image_url=image_url,
                    mime_type=mime_type,
                    analysis_types=analysis_types,
                    question=question,
                    max_tokens=max_tokens,
                )
            
            elif provider == ImageAnalysisProvider.ANTHROPIC_VISION:
                return await self._analyze_with_anthropic(
                    image_base64=image_base64,
                    image_url=image_url,
                    mime_type=mime_type,
                    analysis_types=analysis_types,
                    question=question,
                    max_tokens=max_tokens,
                )
            
            elif provider == ImageAnalysisProvider.TESSERACT_OCR:
                return await self._analyze_with_tesseract(
                    image_base64=image_base64,
                )
            
            else:
                return ImageAnalysisResult(
                    description="",
                    error=f"Provider not implemented: {provider.value}",
                )
                
        except Exception as e:
            logger.error("Image analysis failed: %s", e)
            return ImageAnalysisResult(
                description="",
                error=str(e),
                provider_used=provider.value if provider else None,
            )
    
    async def _analyze_with_openai(
        self,
        image_base64: Optional[str],
        image_url: Optional[str],
        mime_type: Optional[str],
        analysis_types: List[AnalysisType],
        question: Optional[str],
        max_tokens: int,
    ) -> ImageAnalysisResult:
        """Analyze image using OpenAI Vision."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Build prompt
        prompt = self._build_analysis_prompt(analysis_types, question)
        
        # Build image content
        if image_url:
            image_content = {
                "type": "image_url",
                "image_url": {"url": image_url},
            }
        else:
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}",
                },
            }
        
        # Make API call
        response = await client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o with vision
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        image_content,
                    ],
                },
            ],
            max_tokens=max_tokens,
        )
        
        # Parse response
        content = response.choices[0].message.content or ""
        
        # Extract structured data from response
        result = self._parse_analysis_response(content, analysis_types)
        result.provider_used = ImageAnalysisProvider.OPENAI_VISION.value
        result.raw_response = {"model": "gpt-4o", "content": content}
        
        return result
    
    async def _analyze_with_anthropic(
        self,
        image_base64: Optional[str],
        image_url: Optional[str],
        mime_type: Optional[str],
        analysis_types: List[AnalysisType],
        question: Optional[str],
        max_tokens: int,
    ) -> ImageAnalysisResult:
        """Analyze image using Anthropic Claude Vision."""
        import anthropic
        import httpx
        
        client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)
        
        # Build prompt
        prompt = self._build_analysis_prompt(analysis_types, question)
        
        # Handle URL - need to download for Anthropic
        if image_url and not image_base64:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(image_url)
                image_base64 = base64.b64encode(response.content).decode("utf-8")
                content_type = response.headers.get("content-type", "image/jpeg")
                mime_type = content_type.split(";")[0]
        
        # Make API call
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",  # Use Claude with vision
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type or "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                },
            ],
        )
        
        # Parse response
        content = response.content[0].text if response.content else ""
        
        # Extract structured data
        result = self._parse_analysis_response(content, analysis_types)
        result.provider_used = ImageAnalysisProvider.ANTHROPIC_VISION.value
        result.raw_response = {"model": "claude-sonnet-4-20250514", "content": content}
        
        return result
    
    async def _analyze_with_tesseract(
        self,
        image_base64: Optional[str],
    ) -> ImageAnalysisResult:
        """Analyze image using Tesseract OCR."""
        import pytesseract
        from PIL import Image
        
        # Decode image
        if image_base64:
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
        else:
            return ImageAnalysisResult(
                description="",
                error="No image data for OCR",
            )
        
        # Run OCR in thread pool
        loop = asyncio.get_event_loop()
        ocr_result = await loop.run_in_executor(
            None,
            pytesseract.image_to_data,
            image,
            {"output_type": pytesseract.Output.DICT},
        )
        
        # Extract text
        extracted_text = []
        full_text = pytesseract.image_to_string(image)
        
        if full_text.strip():
            extracted_text.append(ExtractedText(
                text=full_text.strip(),
                confidence=0.9,
            ))
        
        return ImageAnalysisResult(
            description=f"OCR extracted text: {full_text[:200]}..." if len(full_text) > 200 else full_text,
            extracted_text=extracted_text,
            image_size=image.size,
            provider_used=ImageAnalysisProvider.TESSERACT_OCR.value,
        )
    
    def _build_analysis_prompt(
        self,
        analysis_types: List[AnalysisType],
        question: Optional[str],
    ) -> str:
        """Build the analysis prompt based on requested types."""
        parts = []
        
        if question:
            parts.append(f"Question about this image: {question}")
            parts.append("")
        
        parts.append("Please analyze this image and provide:")
        
        for atype in analysis_types:
            if atype == AnalysisType.DESCRIBE:
                parts.append("- A detailed description of what you see")
            elif atype == AnalysisType.OCR:
                parts.append("- Any text visible in the image (transcribe it)")
            elif atype == AnalysisType.OBJECTS:
                parts.append("- A list of objects/items you can identify")
            elif atype == AnalysisType.LANDMARKS:
                parts.append("- Any landmarks, buildings, or notable places you recognize")
            elif atype == AnalysisType.LABELS:
                parts.append("- Labels/categories that describe this image")
        
        parts.append("")
        parts.append("Format your response clearly with sections for each type of analysis.")
        
        return "\n".join(parts)
    
    def _parse_analysis_response(
        self,
        content: str,
        analysis_types: List[AnalysisType],
    ) -> ImageAnalysisResult:
        """Parse the analysis response into structured result."""
        # Extract sections from response
        description = content
        extracted_text = []
        detected_objects = []
        landmarks = []
        labels = []
        
        # Try to extract text sections
        text_patterns = [
            r"text[:\s]+(.+?)(?=\n\n|\Z)",
            r"transcription[:\s]+(.+?)(?=\n\n|\Z)",
            r"reads?[:\s]+['\"]?(.+?)['\"]?(?=\n|$)",
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if match.strip():
                    extracted_text.append(ExtractedText(
                        text=match.strip(),
                        confidence=0.8,
                    ))
        
        # Try to extract objects
        object_patterns = [
            r"objects?[:\s]+(.+?)(?=\n\n|\Z)",
            r"items?[:\s]+(.+?)(?=\n\n|\Z)",
        ]
        
        for pattern in object_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Split by commas or newlines
                items = re.split(r'[,\n]', match)
                for item in items:
                    item = item.strip().strip('-').strip('*').strip()
                    if item:
                        detected_objects.append(DetectedObject(
                            name=item[:100],
                            confidence=0.7,
                        ))
        
        # Try to extract landmarks
        landmark_patterns = [
            r"landmarks?[:\s]+(.+?)(?=\n\n|\Z)",
            r"building[:\s]+(.+?)(?=\n|$)",
            r"(eiffel tower|statue of liberty|big ben|taj mahal|great wall|colosseum|pyramids?|stonehenge)",
        ]
        
        for pattern in landmark_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str) and match.strip():
                    landmarks.append(match.strip())
        
        return ImageAnalysisResult(
            description=description,
            extracted_text=extracted_text,
            detected_objects=detected_objects[:10],  # Limit
            landmarks=landmarks[:5],
            labels=labels,
        )


# ==============================================================================
# Convenience Functions
# ==============================================================================

_analyzer: Optional[ImageAnalyzer] = None


def get_image_analyzer() -> ImageAnalyzer:
    """Get global ImageAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ImageAnalyzer()
    return _analyzer


async def analyze_image(
    image: Union[str, Path, bytes],
    *,
    analysis_types: Optional[List[AnalysisType]] = None,
    question: Optional[str] = None,
) -> ImageAnalysisResult:
    """
    Analyze an image using the global analyzer.
    
    Args:
        image: Image path, URL, or bytes
        analysis_types: Types of analysis to perform
        question: Optional question about the image
        
    Returns:
        ImageAnalysisResult
    """
    analyzer = get_image_analyzer()
    return await analyzer.analyze(
        image,
        analysis_types=analysis_types,
        question=question,
    )


async def analyze_image_url(
    url: str,
    question: Optional[str] = None,
) -> ImageAnalysisResult:
    """Analyze an image from URL."""
    return await analyze_image(
        url,
        analysis_types=[AnalysisType.DESCRIBE, AnalysisType.OCR, AnalysisType.LANDMARKS],
        question=question,
    )

