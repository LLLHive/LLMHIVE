"""Multimodal Tools for Tool Broker Integration.

This module provides tool definitions for multimodal capabilities
that can be registered with the ToolBroker.

Usage:
    from llmhive.app.multimodal.tools import register_multimodal_tools
    register_multimodal_tools(tool_broker)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..tool_broker import ToolBroker, ToolDefinition, ToolCategory

from .handler import (
    MultimodalHandler,
    get_multimodal_handler,
    is_image_generation_request,
    extract_image_prompt,
)
from .image_analyzer import (
    ImageAnalyzer,
    AnalysisType,
    get_image_analyzer,
)
from .image_generator import (
    ImageGenerator,
    ImageSize,
    ImageQuality,
    get_image_generator,
)
from .audio_processor import (
    AudioProcessor,
    TTSVoice,
    get_audio_processor,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Tool Handlers
# ==============================================================================

async def _tool_analyze_image(args: str, user_tier: str = "pro") -> str:
    """
    Analyze an image and return description.
    
    Args format:
        URL or path to image, optionally with question after |
        Example: "https://example.com/image.jpg | What is this?"
    
    Returns:
        Image analysis description
    """
    parts = args.split("|", 1)
    image_source = parts[0].strip()
    question = parts[1].strip() if len(parts) > 1 else None
    
    analyzer = get_image_analyzer()
    
    try:
        result = await analyzer.analyze(
            image_source,
            analysis_types=[AnalysisType.DESCRIBE, AnalysisType.OCR, AnalysisType.LANDMARKS],
            question=question,
        )
        
        if result.error:
            return f"Image analysis error: {result.error}"
        
        output_parts = [f"Description: {result.description}"]
        
        if result.all_text:
            output_parts.append(f"Text in image: {result.all_text}")
        
        if result.landmarks:
            output_parts.append(f"Landmarks: {', '.join(result.landmarks)}")
        
        if result.detected_objects:
            objects = ", ".join(o.name for o in result.detected_objects[:5])
            output_parts.append(f"Objects: {objects}")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        logger.error("Image analysis tool error: %s", e)
        return f"Image analysis failed: {str(e)}"


async def _tool_generate_image(args: str, user_tier: str = "pro") -> str:
    """
    Generate an image from a text prompt.
    
    Args format:
        Text description of the image to generate
        Optionally add |size=1024x1024 or |quality=hd
    
    Returns:
        Image URL or generation status
    """
    # Parse optional parameters
    parts = args.split("|")
    prompt = parts[0].strip()
    
    size = ImageSize.LARGE
    quality = ImageQuality.STANDARD
    
    for part in parts[1:]:
        part = part.strip().lower()
        if part.startswith("size="):
            size_str = part.split("=")[1]
            for s in ImageSize:
                if s.value == size_str:
                    size = s
                    break
        elif part.startswith("quality="):
            q_str = part.split("=")[1]
            if q_str == "hd":
                quality = ImageQuality.HD
    
    # Check tier access
    handler = get_multimodal_handler()
    allowed, reason = handler.check_tier_access(
        handler.ProcessingAction.GENERATE_IMAGE if hasattr(handler, 'ProcessingAction') else None,
        user_tier,
    )
    
    if not allowed and reason:
        return reason
    
    generator = get_image_generator()
    
    try:
        result = await generator.generate(
            prompt,
            size=size,
            quality=quality,
        )
        
        if result.success:
            output = f"Image generated successfully."
            if result.image_url:
                output += f"\nURL: {result.image_url}"
            if result.revised_prompt:
                output += f"\nRevised prompt: {result.revised_prompt}"
            output += f"\nEstimated cost: ${result.cost_estimate_usd:.4f}"
            return output
        else:
            return f"Image generation failed: {result.error}"
            
    except Exception as e:
        logger.error("Image generation tool error: %s", e)
        return f"Image generation failed: {str(e)}"


async def _tool_transcribe_audio(args: str, user_tier: str = "free") -> str:
    """
    Transcribe audio to text.
    
    Args format:
        URL or path to audio file
        Optionally add |language=en
    
    Returns:
        Transcribed text
    """
    parts = args.split("|")
    audio_source = parts[0].strip()
    
    language = None
    for part in parts[1:]:
        part = part.strip().lower()
        if part.startswith("language="):
            language = part.split("=")[1]
    
    processor = get_audio_processor()
    
    try:
        result = await processor.transcribe(audio_source, language=language)
        
        if result.success:
            output = result.text
            if result.language:
                output += f"\n[Language: {result.language}]"
            return output
        else:
            return f"Transcription failed: {result.error}"
            
    except Exception as e:
        logger.error("Transcription tool error: %s", e)
        return f"Transcription failed: {str(e)}"


async def _tool_synthesize_speech(args: str, user_tier: str = "pro") -> str:
    """
    Synthesize speech from text.
    
    Args format:
        Text to convert to speech
        Optionally add |voice=alloy
    
    Returns:
        Base64 audio data or URL
    """
    parts = args.split("|")
    text = parts[0].strip()
    
    voice = TTSVoice.ALLOY
    for part in parts[1:]:
        part = part.strip().lower()
        if part.startswith("voice="):
            voice_str = part.split("=")[1]
            for v in TTSVoice:
                if v.value == voice_str:
                    voice = v
                    break
    
    processor = get_audio_processor()
    
    try:
        result = await processor.synthesize(text, voice=voice)
        
        if result.success:
            output = "Speech synthesized successfully."
            output += f"\nVoice: {result.voice_used}"
            output += f"\nFormat: {result.format.value}"
            if result.audio_base64:
                output += f"\nAudio data: [base64 encoded, {len(result.audio_base64)} characters]"
            output += f"\nEstimated cost: ${result.cost_estimate_usd:.4f}"
            return output
        else:
            return f"Speech synthesis failed: {result.error}"
            
    except Exception as e:
        logger.error("Speech synthesis tool error: %s", e)
        return f"Speech synthesis failed: {str(e)}"


def _tool_analyze_image_sync(args: str) -> str:
    """Synchronous wrapper for image analysis."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_tool_analyze_image(args))
    finally:
        loop.close()


# ==============================================================================
# Tool Registration
# ==============================================================================

def register_multimodal_tools(tool_broker: 'ToolBroker') -> None:
    """
    Register multimodal tools with a ToolBroker instance.
    
    Args:
        tool_broker: ToolBroker instance to register tools with
    """
    from ..tool_broker import ToolDefinition, ToolCategory
    
    # Image Analysis Tool
    tool_broker.register_tool(
        ToolDefinition(
            name="analyze_image",
            description="Analyze an image to get description, detect text (OCR), identify landmarks and objects. Usage: [TOOL:analyze_image] image_url | optional question",
            category=ToolCategory.API,
            handler=lambda args: asyncio.new_event_loop().run_until_complete(_tool_analyze_image(args)),
            is_async=False,  # Wrapped as sync
            allowed_tiers={"free", "pro", "enterprise"},
            parameters={
                "image_url": "URL or path to the image",
                "question": "Optional specific question about the image (separated by |)",
            },
        )
    )
    
    # Image Generation Tool
    tool_broker.register_tool(
        ToolDefinition(
            name="generate_image",
            description="Generate an image from a text description using AI (DALL-E/Stable Diffusion). Usage: [TOOL:generate_image] description | size=1024x1024 | quality=hd",
            category=ToolCategory.API,
            handler=lambda args: asyncio.new_event_loop().run_until_complete(_tool_generate_image(args)),
            is_async=False,
            allowed_tiers={"pro", "enterprise"},  # Not available for free tier
            parameters={
                "description": "Text description of the image to generate",
                "size": "Optional size (256x256, 512x512, 1024x1024, 1792x1024, 1024x1792)",
                "quality": "Optional quality (standard, hd)",
            },
        )
    )
    
    # Audio Transcription Tool
    tool_broker.register_tool(
        ToolDefinition(
            name="transcribe_audio",
            description="Transcribe audio to text using speech recognition. Usage: [TOOL:transcribe_audio] audio_url | language=en",
            category=ToolCategory.API,
            handler=lambda args: asyncio.new_event_loop().run_until_complete(_tool_transcribe_audio(args)),
            is_async=False,
            allowed_tiers={"free", "pro", "enterprise"},
            parameters={
                "audio_url": "URL or path to the audio file",
                "language": "Optional language code (e.g., en, es, fr)",
            },
        )
    )
    
    # Speech Synthesis Tool
    tool_broker.register_tool(
        ToolDefinition(
            name="synthesize_speech",
            description="Convert text to speech audio. Usage: [TOOL:synthesize_speech] text to speak | voice=alloy",
            category=ToolCategory.API,
            handler=lambda args: asyncio.new_event_loop().run_until_complete(_tool_synthesize_speech(args)),
            is_async=False,
            allowed_tiers={"pro", "enterprise"},
            parameters={
                "text": "Text to convert to speech",
                "voice": "Optional voice (alloy, echo, fable, onyx, nova, shimmer)",
            },
        )
    )
    
    # Update tier tools mapping
    tool_broker.tier_tools["free"].update({"analyze_image", "transcribe_audio"})
    tool_broker.tier_tools["pro"].update({"analyze_image", "generate_image", "transcribe_audio", "synthesize_speech"})
    tool_broker.tier_tools["enterprise"].update({"analyze_image", "generate_image", "transcribe_audio", "synthesize_speech"})
    
    logger.info("Registered multimodal tools with ToolBroker")


def get_multimodal_tool_definitions() -> Dict[str, Dict[str, Any]]:
    """
    Get tool definitions for multimodal tools.
    
    Returns:
        Dict of tool name -> definition info
    """
    return {
        "analyze_image": {
            "name": "analyze_image",
            "description": "Analyze an image to get description, detect text (OCR), identify landmarks and objects",
            "category": "api",
            "allowed_tiers": ["free", "pro", "enterprise"],
            "parameters": {
                "image_url": {
                    "type": "string",
                    "description": "URL or path to the image",
                    "required": True,
                },
                "question": {
                    "type": "string",
                    "description": "Optional question about the image",
                    "required": False,
                },
            },
        },
        "generate_image": {
            "name": "generate_image",
            "description": "Generate an image from a text description using AI",
            "category": "api",
            "allowed_tiers": ["pro", "enterprise"],
            "parameters": {
                "description": {
                    "type": "string",
                    "description": "Text description of the image to generate",
                    "required": True,
                },
                "size": {
                    "type": "string",
                    "description": "Image size (1024x1024, 1792x1024, 1024x1792)",
                    "required": False,
                    "default": "1024x1024",
                },
                "quality": {
                    "type": "string",
                    "description": "Image quality (standard, hd)",
                    "required": False,
                    "default": "standard",
                },
            },
        },
        "transcribe_audio": {
            "name": "transcribe_audio",
            "description": "Transcribe audio to text using speech recognition",
            "category": "api",
            "allowed_tiers": ["free", "pro", "enterprise"],
            "parameters": {
                "audio_url": {
                    "type": "string",
                    "description": "URL or path to the audio file",
                    "required": True,
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., en, es, fr)",
                    "required": False,
                },
            },
        },
        "synthesize_speech": {
            "name": "synthesize_speech",
            "description": "Convert text to speech audio",
            "category": "api",
            "allowed_tiers": ["pro", "enterprise"],
            "parameters": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech",
                    "required": True,
                },
                "voice": {
                    "type": "string",
                    "description": "Voice to use (alloy, echo, fable, onyx, nova, shimmer)",
                    "required": False,
                    "default": "alloy",
                },
            },
        },
    }

