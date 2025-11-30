"""Multimodal capabilities for LLMHive.

This module provides image and audio processing capabilities:
- Image analysis (OCR, captioning, object detection)
- Image generation (DALL-E, Stable Diffusion)
- Audio processing (speech-to-text, text-to-speech)
"""
from __future__ import annotations

# Image tools
try:
    from .image_analyzer import (
        ImageAnalyzer,
        ImageAnalysisResult,
        analyze_image,
        analyze_image_url,
    )
    IMAGE_ANALYSIS_AVAILABLE = True
except ImportError:
    IMAGE_ANALYSIS_AVAILABLE = False
    ImageAnalyzer = None  # type: ignore
    ImageAnalysisResult = None  # type: ignore

# Image generation
try:
    from .image_generator import (
        ImageGenerator,
        ImageGenerationResult,
        generate_image,
    )
    IMAGE_GENERATION_AVAILABLE = True
except ImportError:
    IMAGE_GENERATION_AVAILABLE = False
    ImageGenerator = None  # type: ignore
    ImageGenerationResult = None  # type: ignore

# Audio tools
try:
    from .audio_processor import (
        AudioProcessor,
        TranscriptionResult,
        SpeechSynthesisResult,
        transcribe_audio,
        synthesize_speech,
    )
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    AudioProcessor = None  # type: ignore
    TranscriptionResult = None  # type: ignore
    SpeechSynthesisResult = None  # type: ignore

# Multimodal handler
try:
    from .handler import (
        MultimodalHandler,
        MultimodalInput,
        MultimodalOutput,
        process_multimodal_input,
    )
    MULTIMODAL_HANDLER_AVAILABLE = True
except ImportError:
    MULTIMODAL_HANDLER_AVAILABLE = False
    MultimodalHandler = None  # type: ignore
    MultimodalInput = None  # type: ignore
    MultimodalOutput = None  # type: ignore

# Tool broker integration
try:
    from .tools import (
        register_multimodal_tools,
        get_multimodal_tool_definitions,
    )
    MULTIMODAL_TOOLS_AVAILABLE = True
except ImportError:
    MULTIMODAL_TOOLS_AVAILABLE = False
    register_multimodal_tools = None  # type: ignore
    get_multimodal_tool_definitions = None  # type: ignore


__all__ = [
    "IMAGE_ANALYSIS_AVAILABLE",
    "IMAGE_GENERATION_AVAILABLE",
    "AUDIO_AVAILABLE",
    "MULTIMODAL_HANDLER_AVAILABLE",
]

if IMAGE_ANALYSIS_AVAILABLE:
    __all__.extend([
        "ImageAnalyzer",
        "ImageAnalysisResult",
        "analyze_image",
        "analyze_image_url",
    ])

if IMAGE_GENERATION_AVAILABLE:
    __all__.extend([
        "ImageGenerator",
        "ImageGenerationResult",
        "generate_image",
    ])

if AUDIO_AVAILABLE:
    __all__.extend([
        "AudioProcessor",
        "TranscriptionResult",
        "SpeechSynthesisResult",
        "transcribe_audio",
        "synthesize_speech",
    ])

if MULTIMODAL_HANDLER_AVAILABLE:
    __all__.extend([
        "MultimodalHandler",
        "MultimodalInput",
        "MultimodalOutput",
        "process_multimodal_input",
    ])

if MULTIMODAL_TOOLS_AVAILABLE:
    __all__.extend([
        "register_multimodal_tools",
        "get_multimodal_tool_definitions",
    ])

