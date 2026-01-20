"""Multimodal Handler for LLMHive.

This module orchestrates multimodal inputs and outputs:
- Detects and processes image/audio in user inputs
- Integrates multimodal context with text prompts
- Handles image/audio generation requests
- Manages tier-based access to multimodal features

Usage:
    handler = MultimodalHandler()
    result = await handler.process_input(
        text="What is in this image?",
        images=[image_bytes],
    )
"""
from __future__ import annotations

import asyncio
import base64
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .image_analyzer import (
    ImageAnalyzer,
    ImageAnalysisResult,
    AnalysisType,
    get_image_analyzer,
)
from .image_generator import (
    ImageGenerator,
    ImageGenerationResult,
    ImageSize,
    ImageQuality,
    get_image_generator,
)
from .audio_processor import (
    AudioProcessor,
    TranscriptionResult,
    SpeechSynthesisResult,
    TTSVoice,
    get_audio_processor,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class MultimodalType(str, Enum):
    """Types of multimodal content."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"  # Future


class ProcessingAction(str, Enum):
    """Actions for multimodal processing."""
    ANALYZE_IMAGE = "analyze_image"
    GENERATE_IMAGE = "generate_image"
    TRANSCRIBE_AUDIO = "transcribe_audio"
    SYNTHESIZE_SPEECH = "synthesize_speech"
    NONE = "none"


@dataclass(slots=True)
class MultimodalInput:
    """Represents multimodal input to the system."""
    text: str = ""
    images: List[bytes] = field(default_factory=list)
    image_urls: List[str] = field(default_factory=list)
    audio: Optional[bytes] = None
    audio_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_images(self) -> bool:
        return bool(self.images or self.image_urls)
    
    @property
    def has_audio(self) -> bool:
        return bool(self.audio or self.audio_url)
    
    @property
    def is_text_only(self) -> bool:
        return not self.has_images and not self.has_audio


@dataclass(slots=True)
class MultimodalOutput:
    """Represents multimodal output from the system."""
    text: str = ""
    images: List[Dict[str, Any]] = field(default_factory=list)  # [{url, base64, description}]
    audio: Optional[Dict[str, Any]] = None  # {bytes, base64, format, duration}
    processing_notes: List[str] = field(default_factory=list)
    image_analysis_results: List[ImageAnalysisResult] = field(default_factory=list)
    cost_estimate_usd: float = 0.0
    
    def add_image(
        self,
        *,
        url: Optional[str] = None,
        base64_data: Optional[str] = None,
        description: str = "",
    ) -> None:
        """Add an image to the output."""
        self.images.append({
            "url": url,
            "base64": base64_data,
            "description": description,
        })
    
    def set_audio(
        self,
        audio_bytes: bytes,
        *,
        format: str = "mp3",
        duration: float = 0.0,
    ) -> None:
        """Set audio output."""
        self.audio = {
            "bytes": audio_bytes,
            "base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "format": format,
            "duration": duration,
        }


# Tier-based feature access - SIMPLIFIED 4-TIER STRUCTURE (January 2026)
MULTIMODAL_TIER_ACCESS = {
    "lite": {
        "image_analysis": True,
        "image_generation": False,
        "audio_transcription": True,
        "audio_synthesis": False,
        "max_images_per_request": 2,
        "max_audio_duration_seconds": 120,
    },
    "pro": {
        "image_analysis": True,
        "image_generation": True,
        "audio_transcription": True,
        "audio_synthesis": True,
        "max_images_per_request": 5,
        "max_audio_duration_seconds": 300,
    },
    "enterprise": {
        "image_analysis": True,
        "image_generation": True,
        "audio_transcription": True,
        "audio_synthesis": True,
        "max_images_per_request": 10,
        "max_audio_duration_seconds": 3600,
    },
    "maximum": {
        "image_analysis": True,
        "image_generation": True,
        "audio_transcription": True,
        "audio_synthesis": True,
        "max_images_per_request": 25,
        "max_audio_duration_seconds": 7200,  # 2 hours
    },
    "free": {
        "image_analysis": True,
        "image_generation": False,
        "audio_transcription": True,
        "audio_synthesis": False,
        "max_images_per_request": 1,
        "max_audio_duration_seconds": 60,
    },
}


# Image generation request patterns
IMAGE_GENERATION_PATTERNS = [
    r"(?:generate|create|make|draw|show me|produce)\s+(?:an?\s+)?image\s+(?:of|showing|depicting)",
    r"(?:generate|create|make|draw)\s+(?:a|an|the|me\s+an?)?\s*(?:picture|illustration|artwork|photo)",
    r"(?:can you|please|would you)\s+(?:generate|create|make|draw)\s+(?:an?\s+)?(?:image|picture)",
    r"(?:draw|create|generate)\s+me\s+(?:a|an)\s+",
    r"image\s+generation:\s*",
    r"\[generate\s+image\]",
]


def is_image_generation_request(text: str) -> bool:
    """Check if the text is requesting image generation."""
    text_lower = text.lower()
    for pattern in IMAGE_GENERATION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def extract_image_prompt(text: str) -> str:
    """Extract the image generation prompt from user text."""
    text_lower = text.lower()
    
    # Remove common prefixes
    prefixes = [
        r"(?:please\s+)?(?:generate|create|make|draw|show me)\s+(?:an?\s+)?image\s+(?:of|showing|depicting)\s*:?\s*",
        r"(?:please\s+)?(?:generate|create|make|draw)\s+(?:a|an|the)?\s*(?:picture|illustration|artwork|photo)\s+(?:of|showing)?\s*:?\s*",
        r"image\s+generation:\s*",
        r"\[generate\s+image\]\s*",
    ]
    
    result = text
    for pattern in prefixes:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
    
    return result if result else text


# ==============================================================================
# Multimodal Handler
# ==============================================================================

class MultimodalHandler:
    """Handles multimodal inputs and outputs for LLMHive.
    
    This handler:
    1. Detects multimodal content in user inputs
    2. Processes images/audio before sending to LLM
    3. Detects and handles image generation requests
    4. Optionally synthesizes response audio
    
    Usage:
        handler = MultimodalHandler()
        
        # Process input with image
        result = await handler.process_input(
            text="What is shown in this image?",
            images=[image_bytes],
            user_tier="pro",
        )
        
        # Use augmented text for LLM
        print(result.augmented_text)
    """
    
    def __init__(
        self,
        *,
        image_analyzer: Optional[ImageAnalyzer] = None,
        image_generator: Optional[ImageGenerator] = None,
        audio_processor: Optional[AudioProcessor] = None,
    ):
        """
        Initialize the MultimodalHandler.
        
        Args:
            image_analyzer: Custom ImageAnalyzer instance
            image_generator: Custom ImageGenerator instance
            audio_processor: Custom AudioProcessor instance
        """
        self._image_analyzer = image_analyzer
        self._image_generator = image_generator
        self._audio_processor = audio_processor
    
    @property
    def image_analyzer(self) -> ImageAnalyzer:
        if self._image_analyzer is None:
            self._image_analyzer = get_image_analyzer()
        return self._image_analyzer
    
    @property
    def image_generator(self) -> ImageGenerator:
        if self._image_generator is None:
            self._image_generator = get_image_generator()
        return self._image_generator
    
    @property
    def audio_processor(self) -> AudioProcessor:
        if self._audio_processor is None:
            self._audio_processor = get_audio_processor()
        return self._audio_processor
    
    def check_tier_access(
        self,
        action: ProcessingAction,
        user_tier: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check if user tier has access to the action."""
        tier = user_tier.lower()
        access = MULTIMODAL_TIER_ACCESS.get(tier, MULTIMODAL_TIER_ACCESS["free"])
        
        if action == ProcessingAction.ANALYZE_IMAGE:
            if access["image_analysis"]:
                return True, None
            return False, "Image analysis requires Pro or Enterprise tier."
        
        elif action == ProcessingAction.GENERATE_IMAGE:
            if access["image_generation"]:
                return True, None
            return False, "Image generation requires Pro or Enterprise tier. Please upgrade to access."
        
        elif action == ProcessingAction.TRANSCRIBE_AUDIO:
            if access["audio_transcription"]:
                return True, None
            return False, "Audio transcription requires Pro tier."
        
        elif action == ProcessingAction.SYNTHESIZE_SPEECH:
            if access["audio_synthesis"]:
                return True, None
            return False, "Speech synthesis requires Pro or Enterprise tier."
        
        return True, None
    
    async def process_input(
        self,
        text: str,
        *,
        images: Optional[List[bytes]] = None,
        image_urls: Optional[List[str]] = None,
        audio: Optional[bytes] = None,
        audio_url: Optional[str] = None,
        user_tier: str = "free",
        analyze_images: bool = True,
        transcribe_audio: bool = True,
    ) -> Dict[str, Any]:
        """
        Process multimodal input and return augmented context.
        
        Args:
            text: User's text input
            images: List of image bytes
            image_urls: List of image URLs
            audio: Audio bytes
            audio_url: Audio URL
            user_tier: User's tier for access control
            analyze_images: Whether to analyze images
            transcribe_audio: Whether to transcribe audio
            
        Returns:
            Dict with:
            - augmented_text: Text with multimodal context prepended
            - image_analyses: List of ImageAnalysisResult
            - transcription: TranscriptionResult if audio was provided
            - processing_notes: List of processing notes
            - cost_estimate: Total cost estimate
        """
        images = images or []
        image_urls = image_urls or []
        
        result = {
            "augmented_text": text,
            "original_text": text,
            "image_analyses": [],
            "transcription": None,
            "processing_notes": [],
            "cost_estimate": 0.0,
        }
        
        # Check tier access
        tier_access = MULTIMODAL_TIER_ACCESS.get(user_tier.lower(), MULTIMODAL_TIER_ACCESS["free"])
        
        # Limit images based on tier
        max_images = tier_access["max_images_per_request"]
        all_images = images[:max_images] + image_urls[:max(0, max_images - len(images))]
        
        if len(images) + len(image_urls) > max_images:
            result["processing_notes"].append(
                f"Limited to {max_images} images for {user_tier} tier. Upgrade for more."
            )
        
        # Process images
        if all_images and analyze_images:
            allowed, reason = self.check_tier_access(ProcessingAction.ANALYZE_IMAGE, user_tier)
            
            if allowed:
                context_parts = []
                
                for i, img in enumerate(all_images):
                    try:
                        if isinstance(img, bytes):
                            analysis = await self.image_analyzer.analyze(
                                img,
                                analysis_types=[AnalysisType.DESCRIBE, AnalysisType.OCR, AnalysisType.LANDMARKS],
                            )
                        else:
                            analysis = await self.image_analyzer.analyze(
                                img,
                                analysis_types=[AnalysisType.DESCRIBE, AnalysisType.OCR, AnalysisType.LANDMARKS],
                            )
                        
                        result["image_analyses"].append(analysis)
                        
                        if analysis.error:
                            result["processing_notes"].append(f"Image {i+1} analysis error: {analysis.error}")
                        else:
                            context_parts.append(f"[Image {i+1} Description]: {analysis.description}")
                            
                            if analysis.all_text:
                                context_parts.append(f"[Image {i+1} Text Content]: {analysis.all_text}")
                            
                            if analysis.landmarks:
                                context_parts.append(f"[Image {i+1} Landmarks]: {', '.join(analysis.landmarks)}")
                        
                    except Exception as e:
                        logger.error("Failed to analyze image %d: %s", i+1, e)
                        result["processing_notes"].append(f"Image {i+1} processing failed: {str(e)}")
                
                # Prepend image context to text
                if context_parts:
                    image_context = "\n".join(context_parts)
                    result["augmented_text"] = f"=== Image Context ===\n{image_context}\n\n=== User Question ===\n{text}"
            else:
                result["processing_notes"].append(reason)
        
        # Process audio
        if (audio or audio_url) and transcribe_audio:
            allowed, reason = self.check_tier_access(ProcessingAction.TRANSCRIBE_AUDIO, user_tier)
            
            if allowed:
                try:
                    audio_data = audio
                    if audio_url and not audio_data:
                        # Download audio from URL
                        import httpx
                        async with httpx.AsyncClient() as client:
                            response = await client.get(audio_url)
                            audio_data = response.content
                    
                    if audio_data:
                        transcription = await self.audio_processor.transcribe(audio_data)
                        result["transcription"] = transcription
                        
                        if transcription.success and transcription.text:
                            # If no text was provided, use transcription as the query
                            if not text.strip():
                                result["augmented_text"] = transcription.text
                            else:
                                # Append transcription context
                                result["augmented_text"] = f"{result['augmented_text']}\n\n[Audio Transcription]: {transcription.text}"
                            
                            result["processing_notes"].append(
                                f"Audio transcribed: {transcription.word_count} words"
                            )
                        else:
                            result["processing_notes"].append(
                                f"Audio transcription failed: {transcription.error}"
                            )
                        
                except Exception as e:
                    logger.error("Failed to process audio: %s", e)
                    result["processing_notes"].append(f"Audio processing failed: {str(e)}")
            else:
                result["processing_notes"].append(reason)
        
        return result
    
    async def process_output(
        self,
        text: str,
        *,
        user_tier: str = "free",
        generate_images: bool = True,
        generate_audio: bool = False,
        audio_voice: Optional[TTSVoice] = None,
    ) -> MultimodalOutput:
        """
        Process LLM output for potential multimodal generation.
        
        Args:
            text: LLM's text output
            user_tier: User's tier for access control
            generate_images: Whether to generate images if requested
            generate_audio: Whether to generate audio response
            audio_voice: Voice to use for audio synthesis
            
        Returns:
            MultimodalOutput with text and any generated media
        """
        output = MultimodalOutput(text=text)
        
        # Check for image generation requests in the output
        if generate_images and is_image_generation_request(text):
            allowed, reason = self.check_tier_access(ProcessingAction.GENERATE_IMAGE, user_tier)
            
            if allowed:
                prompt = extract_image_prompt(text)
                
                try:
                    generation_result = await self.image_generator.generate(prompt)
                    
                    if generation_result.success:
                        output.add_image(
                            url=generation_result.image_url,
                            base64_data=generation_result.image_base64,
                            description=generation_result.revised_prompt or prompt,
                        )
                        output.cost_estimate_usd += generation_result.cost_estimate_usd
                        output.processing_notes.append(
                            f"Generated image using {generation_result.provider_used}"
                        )
                    else:
                        output.processing_notes.append(
                            f"Image generation failed: {generation_result.error}"
                        )
                        
                except Exception as e:
                    logger.error("Image generation failed: %s", e)
                    output.processing_notes.append(f"Image generation failed: {str(e)}")
            else:
                output.processing_notes.append(reason)
        
        # Generate audio response if requested
        if generate_audio:
            allowed, reason = self.check_tier_access(ProcessingAction.SYNTHESIZE_SPEECH, user_tier)
            
            if allowed:
                try:
                    synthesis_result = await self.audio_processor.synthesize(
                        text,
                        voice=audio_voice,
                    )
                    
                    if synthesis_result.success and synthesis_result.audio_bytes:
                        output.set_audio(
                            synthesis_result.audio_bytes,
                            format=synthesis_result.format.value,
                            duration=synthesis_result.duration_seconds,
                        )
                        output.cost_estimate_usd += synthesis_result.cost_estimate_usd
                        output.processing_notes.append(
                            f"Generated audio using {synthesis_result.provider_used}"
                        )
                    else:
                        output.processing_notes.append(
                            f"Audio synthesis failed: {synthesis_result.error}"
                        )
                        
                except Exception as e:
                    logger.error("Audio synthesis failed: %s", e)
                    output.processing_notes.append(f"Audio synthesis failed: {str(e)}")
            else:
                output.processing_notes.append(reason)
        
        return output
    
    async def generate_image(
        self,
        prompt: str,
        *,
        user_tier: str = "free",
        size: ImageSize = ImageSize.LARGE,
        quality: ImageQuality = ImageQuality.STANDARD,
    ) -> ImageGenerationResult:
        """
        Generate an image from a prompt.
        
        Args:
            prompt: Image description
            user_tier: User's tier
            size: Image size
            quality: Image quality
            
        Returns:
            ImageGenerationResult
        """
        allowed, reason = self.check_tier_access(ProcessingAction.GENERATE_IMAGE, user_tier)
        
        if not allowed:
            return ImageGenerationResult(
                success=False,
                error=reason,
            )
        
        return await self.image_generator.generate(
            prompt,
            size=size,
            quality=quality,
        )
    
    async def analyze_image(
        self,
        image: Union[str, Path, bytes],
        *,
        question: Optional[str] = None,
        user_tier: str = "free",
    ) -> ImageAnalysisResult:
        """
        Analyze an image.
        
        Args:
            image: Image path, URL, or bytes
            question: Optional question about the image
            user_tier: User's tier
            
        Returns:
            ImageAnalysisResult
        """
        allowed, reason = self.check_tier_access(ProcessingAction.ANALYZE_IMAGE, user_tier)
        
        if not allowed:
            return ImageAnalysisResult(
                description="",
                error=reason,
            )
        
        return await self.image_analyzer.analyze(
            image,
            analysis_types=[AnalysisType.DESCRIBE, AnalysisType.OCR, AnalysisType.LANDMARKS],
            question=question,
        )
    
    async def transcribe(
        self,
        audio: Union[str, Path, bytes],
        *,
        user_tier: str = "free",
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio file or bytes
            user_tier: User's tier
            language: Optional language code
            
        Returns:
            TranscriptionResult
        """
        allowed, reason = self.check_tier_access(ProcessingAction.TRANSCRIBE_AUDIO, user_tier)
        
        if not allowed:
            return TranscriptionResult(
                success=False,
                error=reason,
            )
        
        return await self.audio_processor.transcribe(audio, language=language)
    
    async def synthesize_speech(
        self,
        text: str,
        *,
        user_tier: str = "free",
        voice: Optional[TTSVoice] = None,
    ) -> SpeechSynthesisResult:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            user_tier: User's tier
            voice: Voice to use
            
        Returns:
            SpeechSynthesisResult
        """
        allowed, reason = self.check_tier_access(ProcessingAction.SYNTHESIZE_SPEECH, user_tier)
        
        if not allowed:
            return SpeechSynthesisResult(
                success=False,
                error=reason,
            )
        
        return await self.audio_processor.synthesize(text, voice=voice)


# ==============================================================================
# Convenience Functions
# ==============================================================================

_handler: Optional[MultimodalHandler] = None


def get_multimodal_handler() -> MultimodalHandler:
    """Get global MultimodalHandler instance."""
    global _handler
    if _handler is None:
        _handler = MultimodalHandler()
    return _handler


async def process_multimodal_input(
    text: str,
    *,
    images: Optional[List[bytes]] = None,
    image_urls: Optional[List[str]] = None,
    audio: Optional[bytes] = None,
    user_tier: str = "free",
) -> Dict[str, Any]:
    """
    Process multimodal input using the global handler.
    
    Args:
        text: User's text input
        images: List of image bytes
        image_urls: List of image URLs
        audio: Audio bytes
        user_tier: User's tier
        
    Returns:
        Dict with augmented_text and processing results
    """
    handler = get_multimodal_handler()
    return await handler.process_input(
        text,
        images=images,
        image_urls=image_urls,
        audio=audio,
        user_tier=user_tier,
    )

