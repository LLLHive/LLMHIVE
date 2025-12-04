"""Audio Agent for LLMHive.

This on-demand agent handles audio processing tasks using the multimodal AudioProcessor.
Provides comprehensive audio capabilities including:
- Speech-to-text transcription (Whisper)
- Text-to-speech synthesis (OpenAI TTS, ElevenLabs)
- Audio analysis (format detection, metadata)
- Speech translation

Integrates with OpenAI Whisper, OpenAI TTS, ElevenLabs, and local Whisper.
"""
from __future__ import annotations

import base64
import io
import logging
import os
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from collections import deque

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


# ============================================================
# Audio Analysis Data Classes
# ============================================================

@dataclass
class AudioMetadata:
    """Metadata extracted from audio."""
    format: str = "unknown"
    duration_seconds: float = 0.0
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_depth: Optional[int] = None
    file_size_bytes: int = 0
    estimated_bitrate_kbps: Optional[int] = None


@dataclass
class TranscriptionRequest:
    """Request for audio transcription."""
    audio_source: str  # File path, URL, or base64
    source_type: str = "auto"  # "path", "url", "base64", "bytes", "auto"
    language: Optional[str] = None  # Language code (e.g., "en", "es")
    prompt: Optional[str] = None  # Optional transcription prompt
    timestamps: bool = False  # Include word/segment timestamps


@dataclass
class SynthesisRequest:
    """Request for speech synthesis."""
    text: str
    voice: str = "alloy"  # OpenAI: alloy, echo, fable, onyx, nova, shimmer
    model: str = "tts-1"  # tts-1 or tts-1-hd
    speed: float = 1.0  # 0.25 to 4.0
    output_format: str = "mp3"


@dataclass 
class AudioAnalysisResult:
    """Result of audio analysis."""
    success: bool
    metadata: Optional[AudioMetadata] = None
    transcription: Optional[str] = None
    language_detected: Optional[str] = None
    confidence: float = 0.0
    provider_used: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: int = 0


# ============================================================
# Audio Format Detection and Analysis
# ============================================================

# Audio file signatures
AUDIO_SIGNATURES = {
    b"ID3": ("mp3", "ID3 tag"),
    b"\xff\xfb": ("mp3", "MPEG audio"),
    b"\xff\xfa": ("mp3", "MPEG audio"),
    b"\xff\xf3": ("mp3", "MPEG audio"),
    b"RIFF": ("wav", "RIFF WAVE"),
    b"fLaC": ("flac", "FLAC"),
    b"OggS": ("ogg", "Ogg container"),
    b"\x00\x00\x00\x1cftyp": ("m4a", "MPEG-4 audio"),
    b"\x00\x00\x00 ftyp": ("m4a", "MPEG-4 audio"),
}


def detect_audio_format(audio_data: bytes) -> tuple[str, str]:
    """
    Detect audio format from file signature.
    
    Returns:
        Tuple of (format, description)
    """
    for sig, (fmt, desc) in AUDIO_SIGNATURES.items():
        if audio_data.startswith(sig):
            return fmt, desc
    
    # Check for more signatures
    if len(audio_data) > 8:
        # Check for MP4/M4A
        if b"ftyp" in audio_data[:12]:
            return "m4a", "MPEG-4 audio"
        # Check for WebM
        if audio_data.startswith(b"\x1a\x45\xdf\xa3"):
            return "webm", "WebM audio"
    
    return "unknown", "Unknown format"


def analyze_wav_header(audio_data: bytes) -> AudioMetadata:
    """Extract metadata from WAV file header."""
    metadata = AudioMetadata(format="wav", file_size_bytes=len(audio_data))
    
    try:
        if len(audio_data) < 44:
            return metadata
        
        # RIFF header
        if audio_data[:4] != b"RIFF":
            return metadata
        
        # WAVE format
        if audio_data[8:12] != b"WAVE":
            return metadata
        
        # fmt chunk
        fmt_offset = audio_data.find(b"fmt ")
        if fmt_offset == -1:
            return metadata
        
        # Parse fmt chunk
        audio_format = struct.unpack_from("<H", audio_data, fmt_offset + 8)[0]
        channels = struct.unpack_from("<H", audio_data, fmt_offset + 10)[0]
        sample_rate = struct.unpack_from("<I", audio_data, fmt_offset + 12)[0]
        byte_rate = struct.unpack_from("<I", audio_data, fmt_offset + 16)[0]
        bits_per_sample = struct.unpack_from("<H", audio_data, fmt_offset + 22)[0]
        
        metadata.channels = channels
        metadata.sample_rate = sample_rate
        metadata.bit_depth = bits_per_sample
        metadata.estimated_bitrate_kbps = (byte_rate * 8) // 1000
        
        # Find data chunk for duration
        data_offset = audio_data.find(b"data")
        if data_offset != -1:
            data_size = struct.unpack_from("<I", audio_data, data_offset + 4)[0]
            if byte_rate > 0:
                metadata.duration_seconds = data_size / byte_rate
        
    except Exception as e:
        logger.debug("Error parsing WAV header: %s", e)
    
    return metadata


def analyze_audio_data(audio_data: bytes) -> AudioMetadata:
    """
    Analyze audio data and extract metadata.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        AudioMetadata with extracted information
    """
    format_name, format_desc = detect_audio_format(audio_data)
    
    metadata = AudioMetadata(
        format=format_name,
        file_size_bytes=len(audio_data),
    )
    
    # WAV-specific analysis
    if format_name == "wav":
        metadata = analyze_wav_header(audio_data)
    
    # MP3 estimation (rough)
    elif format_name == "mp3":
        # Estimate duration from file size assuming ~128 kbps
        metadata.estimated_bitrate_kbps = 128
        metadata.duration_seconds = (len(audio_data) * 8) / (128 * 1000)
    
    # Estimate bitrate from file size and duration
    if metadata.duration_seconds > 0 and metadata.estimated_bitrate_kbps is None:
        metadata.estimated_bitrate_kbps = int(
            (len(audio_data) * 8) / (metadata.duration_seconds * 1000)
        )
    
    return metadata


# ============================================================
# Audio Agent Implementation
# ============================================================

class AudioAgent(BaseAgent):
    """Agent that handles audio processing tasks.
    
    Responsibilities:
    - Transcribe audio to text (speech-to-text)
    - Synthesize speech from text (text-to-speech)
    - Analyze audio files (format, duration, metadata)
    - Translate speech (via Whisper translation)
    
    Task Types:
    - transcribe: Convert speech to text
    - synthesize: Convert text to speech
    - analyze_audio: Extract audio metadata and features
    - translate: Translate speech to English
    - get_voices: List available TTS voices
    - estimate_cost: Estimate processing cost
    
    Supported Audio Sources:
    - File paths (local files)
    - Base64 encoded audio
    - Raw bytes
    
    Providers:
    - OpenAI Whisper (transcription, translation)
    - Local Whisper (transcription, when installed)
    - OpenAI TTS (synthesis)
    - ElevenLabs (synthesis)
    """
    
    # Supported audio formats
    SUPPORTED_FORMATS = ["mp3", "wav", "flac", "ogg", "m4a", "webm", "mp4", "mpeg"]
    
    # Maximum audio file size (25MB for Whisper API)
    MAX_FILE_SIZE_MB = 25
    
    # Voice aliases for convenience
    VOICE_ALIASES = {
        "default": "alloy",
        "female": "nova",
        "male": "onyx",
        "friendly": "alloy",
        "professional": "echo",
        "storyteller": "fable",
        "warm": "shimmer",
    }
    
    def __init__(self, config: Optional[AgentConfig] = None, blackboard: Optional[Any] = None):
        if config is None:
            config = AgentConfig(
                name="audio_agent",
                agent_type=AgentType.ON_DEMAND,
                priority=AgentPriority.HIGH,
                max_tokens_per_run=3000,
                max_runtime_seconds=120,  # Audio processing can take time
                allowed_tools=["whisper", "tts", "eleven_labs"],
                memory_namespace="audio",
            )
        super().__init__(config)
        self.blackboard = blackboard
        self._processor = None
        self._task_history: deque[Dict[str, Any]] = deque(maxlen=100)
        
        # Statistics
        self._total_transcriptions = 0
        self._total_syntheses = 0
        self._total_audio_seconds = 0.0
        self._total_characters_synthesized = 0
    
    def _get_processor(self):
        """Lazy load the AudioProcessor to avoid import issues."""
        if self._processor is None:
            try:
                from ..multimodal.audio_processor import AudioProcessor
                self._processor = AudioProcessor()
                logger.info("AudioProcessor initialized for AudioAgent")
            except ImportError as e:
                logger.error("Failed to import AudioProcessor: %s", e)
                self._processor = None
        return self._processor
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute audio processing task.
        
        Args:
            task: AgentTask with task_type and payload
            
        Returns:
            AgentResult with processing output
        """
        start_time = datetime.now()
        
        if not task:
            return AgentResult(
                success=False,
                error="No task provided. Provide task with audio data or text in payload.",
            )
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "transcribe":
                return await self._transcribe(payload, start_time)
            
            elif task_type == "synthesize":
                return await self._synthesize(payload, start_time)
            
            elif task_type == "analyze_audio":
                return await self._analyze_audio(payload, start_time)
            
            elif task_type == "translate":
                return await self._translate(payload, start_time)
            
            elif task_type == "get_voices":
                return self._get_voices()
            
            elif task_type == "estimate_cost":
                return self._estimate_cost(payload)
            
            elif task_type == "get_capabilities":
                return AgentResult(
                    success=True,
                    output=self.get_capabilities(),
                )
            
            elif task_type == "get_history":
                return AgentResult(
                    success=True,
                    output={
                        "history": list(self._task_history)[-20:],
                        "statistics": {
                            "total_transcriptions": self._total_transcriptions,
                            "total_syntheses": self._total_syntheses,
                            "total_audio_seconds": round(self._total_audio_seconds, 2),
                            "total_characters_synthesized": self._total_characters_synthesized,
                        },
                    },
                )
            
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown task type: {task_type}. Supported: transcribe, synthesize, analyze_audio, translate, get_voices, estimate_cost",
                )
                
        except Exception as e:
            logger.error("Audio Agent execution failed: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=f"Audio processing failed: {str(e)}",
            )
    
    # ========================================================================
    # Transcription (Speech-to-Text)
    # ========================================================================
    
    async def _transcribe(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Transcribe audio to text."""
        # Get audio source
        audio_source = (
            payload.get("audio_source") or 
            payload.get("audio") or 
            payload.get("file") or
            payload.get("audio_data")
        )
        
        if not audio_source:
            return AgentResult(
                success=False,
                error="No audio_source provided. Provide file path, base64 audio, or audio bytes.",
            )
        
        # Load audio data
        audio_data, error = self._load_audio(audio_source)
        if error:
            return AgentResult(success=False, error=error)
        
        # Check file size
        if len(audio_data) > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            return AgentResult(
                success=False,
                error=f"Audio file too large. Maximum: {self.MAX_FILE_SIZE_MB}MB",
            )
        
        # Get processor
        processor = self._get_processor()
        if processor is None:
            return self._fallback_transcription_error(start_time)
        
        # Extract options
        language = payload.get("language")
        prompt = payload.get("prompt")
        
        try:
            # Perform transcription
            result = await processor.transcribe(
                audio_data,
                language=language,
                prompt=prompt,
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Update statistics
            self._total_transcriptions += 1
            if result.duration_seconds:
                self._total_audio_seconds += result.duration_seconds
            
            # Track in history
            self._track_task("transcribe", result.success, processing_time, {
                "text_length": len(result.text) if result.text else 0,
                "language": result.language,
            })
            
            if not result.success:
                return AgentResult(
                    success=False,
                    error=result.error or "Transcription failed",
                    metadata={"processing_time_ms": processing_time},
                )
            
            return AgentResult(
                success=True,
                output={
                    "text": result.text,
                    "language": result.language,
                    "duration_seconds": result.duration_seconds,
                    "word_count": result.word_count,
                    "segments": result.segments if payload.get("timestamps") else None,
                    "provider": result.provider_used,
                    "confidence": result.confidence,
                },
                metadata={
                    "agent": "audio_agent",
                    "task_type": "transcribe",
                    "processing_time_ms": processing_time,
                },
            )
            
        except Exception as e:
            logger.error("Transcription error: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=f"Transcription failed: {str(e)}",
            )
    
    # ========================================================================
    # Speech Synthesis (Text-to-Speech)
    # ========================================================================
    
    async def _synthesize(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Synthesize speech from text."""
        text = payload.get("text", "")
        
        if not text.strip():
            return AgentResult(
                success=False,
                error="No text provided for synthesis.",
            )
        
        # Get processor
        processor = self._get_processor()
        if processor is None:
            return self._fallback_synthesis_error(start_time)
        
        # Extract options
        voice = payload.get("voice", "alloy")
        # Handle voice aliases
        voice = self.VOICE_ALIASES.get(voice.lower(), voice)
        
        speed = payload.get("speed", 1.0)
        output_format = payload.get("format", "mp3")
        
        # Map format string to enum
        try:
            from ..multimodal.audio_processor import AudioFormat, TTSVoice, TTSModel
            
            format_enum = AudioFormat(output_format.lower())
            model = TTSModel(payload.get("model", "tts-1"))
            
        except (ValueError, ImportError):
            format_enum = None
            model = None
        
        try:
            # Perform synthesis
            result = await processor.synthesize(
                text,
                voice=voice,
                model=model,
                format=format_enum if format_enum else None,
                speed=speed,
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Update statistics
            self._total_syntheses += 1
            self._total_characters_synthesized += len(text)
            
            # Track in history
            self._track_task("synthesize", result.success, processing_time, {
                "text_length": len(text),
                "voice": voice,
            })
            
            if not result.success:
                return AgentResult(
                    success=False,
                    error=result.error or "Synthesis failed",
                    metadata={"processing_time_ms": processing_time},
                )
            
            return AgentResult(
                success=True,
                output={
                    "audio_base64": result.audio_base64,
                    "audio_size_bytes": len(result.audio_bytes) if result.audio_bytes else 0,
                    "format": result.format.value if result.format else output_format,
                    "duration_seconds": result.duration_seconds,
                    "voice": result.voice_used,
                    "provider": result.provider_used,
                    "cost_estimate_usd": result.cost_estimate_usd,
                },
                metadata={
                    "agent": "audio_agent",
                    "task_type": "synthesize",
                    "processing_time_ms": processing_time,
                    "text_length": len(text),
                },
            )
            
        except Exception as e:
            logger.error("Synthesis error: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=f"Speech synthesis failed: {str(e)}",
            )
    
    # ========================================================================
    # Audio Analysis
    # ========================================================================
    
    async def _analyze_audio(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Analyze audio file and extract metadata."""
        audio_source = (
            payload.get("audio_source") or 
            payload.get("audio") or 
            payload.get("file")
        )
        
        if not audio_source:
            return AgentResult(
                success=False,
                error="No audio_source provided.",
            )
        
        # Load audio data
        audio_data, error = self._load_audio(audio_source)
        if error:
            return AgentResult(success=False, error=error)
        
        # Analyze audio
        metadata = analyze_audio_data(audio_data)
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Optionally transcribe for content analysis
        include_transcription = payload.get("include_transcription", False)
        transcription_text = None
        detected_language = None
        
        if include_transcription:
            processor = self._get_processor()
            if processor:
                try:
                    result = await processor.transcribe(audio_data)
                    if result.success:
                        transcription_text = result.text
                        detected_language = result.language
                except Exception as e:
                    logger.debug("Transcription during analysis failed: %s", e)
        
        # Track in history
        self._track_task("analyze_audio", True, processing_time, {
            "format": metadata.format,
            "size_bytes": metadata.file_size_bytes,
        })
        
        return AgentResult(
            success=True,
            output={
                "format": metadata.format,
                "duration_seconds": round(metadata.duration_seconds, 2),
                "sample_rate": metadata.sample_rate,
                "channels": metadata.channels,
                "bit_depth": metadata.bit_depth,
                "file_size_bytes": metadata.file_size_bytes,
                "file_size_mb": round(metadata.file_size_bytes / (1024 * 1024), 2),
                "estimated_bitrate_kbps": metadata.estimated_bitrate_kbps,
                "transcription": transcription_text,
                "detected_language": detected_language,
            },
            metadata={
                "agent": "audio_agent",
                "task_type": "analyze_audio",
                "processing_time_ms": processing_time,
            },
        )
    
    # ========================================================================
    # Translation
    # ========================================================================
    
    async def _translate(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Translate speech to English using Whisper translation API."""
        audio_source = (
            payload.get("audio_source") or 
            payload.get("audio") or 
            payload.get("file")
        )
        
        if not audio_source:
            return AgentResult(
                success=False,
                error="No audio_source provided for translation.",
            )
        
        # Load audio data
        audio_data, error = self._load_audio(audio_source)
        if error:
            return AgentResult(success=False, error=error)
        
        # Check for OpenAI availability
        processor = self._get_processor()
        if processor is None:
            return AgentResult(
                success=False,
                error="Translation requires OpenAI API. Configure OPENAI_API_KEY.",
            )
        
        # Use OpenAI translation endpoint
        try:
            import openai
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return AgentResult(
                    success=False,
                    error="OPENAI_API_KEY required for translation.",
                )
            
            client = openai.AsyncOpenAI(api_key=api_key)
            
            # Create file-like object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.mp3"
            
            # Call translation API
            response = await client.audio.translations.create(
                model="whisper-1",
                file=audio_file,
            )
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Track in history
            self._track_task("translate", True, processing_time, {
                "text_length": len(response.text),
            })
            
            return AgentResult(
                success=True,
                output={
                    "translated_text": response.text,
                    "target_language": "en",
                    "word_count": len(response.text.split()),
                    "provider": "openai_whisper",
                },
                metadata={
                    "agent": "audio_agent",
                    "task_type": "translate",
                    "processing_time_ms": processing_time,
                },
            )
            
        except ImportError:
            return AgentResult(
                success=False,
                error="OpenAI package not installed. Run: pip install openai",
            )
        except Exception as e:
            logger.error("Translation error: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=f"Translation failed: {str(e)}",
            )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _load_audio(self, source: Union[str, bytes]) -> tuple[Optional[bytes], Optional[str]]:
        """
        Load audio from various sources.
        
        Returns:
            Tuple of (audio_bytes, error_message)
        """
        # Already bytes
        if isinstance(source, bytes):
            return source, None
        
        # Base64 encoded
        if isinstance(source, str):
            # Check for data URL
            if source.startswith("data:audio"):
                try:
                    # Extract base64 part
                    header, data = source.split(",", 1)
                    return base64.b64decode(data), None
                except Exception as e:
                    return None, f"Invalid data URL: {e}"
            
            # Check if base64 (no path separators, long string)
            if "/" not in source and "\\" not in source and len(source) > 500:
                try:
                    return base64.b64decode(source), None
                except Exception:
                    pass  # Not base64, try as path
            
            # Treat as file path
            path = Path(source)
            if not path.exists():
                return None, f"Audio file not found: {source}"
            
            try:
                return path.read_bytes(), None
            except Exception as e:
                return None, f"Failed to read audio file: {e}"
        
        return None, f"Unsupported audio source type: {type(source)}"
    
    def _get_voices(self) -> AgentResult:
        """Get list of available TTS voices."""
        processor = self._get_processor()
        
        voices = []
        
        # OpenAI voices
        openai_voices = [
            {"id": "alloy", "name": "Alloy", "provider": "openai", "description": "Neutral, balanced"},
            {"id": "echo", "name": "Echo", "provider": "openai", "description": "Professional, clear"},
            {"id": "fable", "name": "Fable", "provider": "openai", "description": "Expressive, storytelling"},
            {"id": "onyx", "name": "Onyx", "provider": "openai", "description": "Deep, authoritative"},
            {"id": "nova", "name": "Nova", "provider": "openai", "description": "Warm, friendly"},
            {"id": "shimmer", "name": "Shimmer", "provider": "openai", "description": "Soft, gentle"},
        ]
        
        # Check if OpenAI is available
        if processor and hasattr(processor, "_available_synthesis"):
            from ..multimodal.audio_processor import SpeechSynthesisProvider
            if SpeechSynthesisProvider.OPENAI_TTS in processor._available_synthesis:
                voices.extend(openai_voices)
        else:
            # Add voices but mark as potentially unavailable
            for v in openai_voices:
                v["available"] = bool(os.getenv("OPENAI_API_KEY"))
            voices.extend(openai_voices)
        
        return AgentResult(
            success=True,
            output={
                "voices": voices,
                "voice_aliases": self.VOICE_ALIASES,
                "default_voice": "alloy",
            },
        )
    
    def _estimate_cost(self, payload: Dict[str, Any]) -> AgentResult:
        """Estimate cost for audio processing."""
        operation = payload.get("operation", "transcribe")
        
        # Whisper transcription cost
        if operation == "transcribe":
            duration_seconds = payload.get("duration_seconds", 60)
            minutes = duration_seconds / 60
            cost = minutes * 0.006  # $0.006/minute
            
            return AgentResult(
                success=True,
                output={
                    "operation": "transcribe",
                    "duration_seconds": duration_seconds,
                    "estimated_cost_usd": round(cost, 4),
                    "provider": "openai_whisper",
                    "rate": "$0.006/minute",
                },
            )
        
        # TTS synthesis cost
        elif operation == "synthesize":
            text = payload.get("text", "")
            model = payload.get("model", "tts-1")
            char_count = len(text)
            
            # Cost per million characters
            cost_per_million = 15.0 if model == "tts-1" else 30.0
            cost = (char_count / 1_000_000) * cost_per_million
            
            return AgentResult(
                success=True,
                output={
                    "operation": "synthesize",
                    "character_count": char_count,
                    "model": model,
                    "estimated_cost_usd": round(cost, 6),
                    "provider": "openai_tts",
                    "rate": f"${cost_per_million}/1M characters",
                },
            )
        
        # Translation cost (same as transcription)
        elif operation == "translate":
            duration_seconds = payload.get("duration_seconds", 60)
            minutes = duration_seconds / 60
            cost = minutes * 0.006
            
            return AgentResult(
                success=True,
                output={
                    "operation": "translate",
                    "duration_seconds": duration_seconds,
                    "estimated_cost_usd": round(cost, 4),
                    "provider": "openai_whisper",
                    "rate": "$0.006/minute",
                },
            )
        
        return AgentResult(
            success=False,
            error=f"Unknown operation: {operation}. Supported: transcribe, synthesize, translate",
        )
    
    def _fallback_transcription_error(self, start_time: datetime) -> AgentResult:
        """Return error when no transcription provider is available."""
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return AgentResult(
            success=False,
            error="No transcription providers available. Configure OPENAI_API_KEY or install local whisper.",
            metadata={"processing_time_ms": processing_time},
            recommendations=[
                "Set OPENAI_API_KEY environment variable for Whisper API",
                "Or install whisper package: pip install openai-whisper",
            ],
        )
    
    def _fallback_synthesis_error(self, start_time: datetime) -> AgentResult:
        """Return error when no synthesis provider is available."""
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        return AgentResult(
            success=False,
            error="No TTS providers available. Configure OPENAI_API_KEY or ELEVEN_LABS_API_KEY.",
            metadata={"processing_time_ms": processing_time},
            recommendations=[
                "Set OPENAI_API_KEY for OpenAI TTS",
                "Or set ELEVEN_LABS_API_KEY for ElevenLabs TTS",
            ],
        )
    
    def _track_task(
        self,
        task_type: str,
        success: bool,
        processing_time_ms: int,
        details: Dict[str, Any],
    ) -> None:
        """Track task in history."""
        self._task_history.append({
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "success": success,
            "processing_time_ms": processing_time_ms,
            **details,
        })
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities description."""
        processor = self._get_processor()
        
        transcription_providers = []
        synthesis_providers = []
        
        if processor:
            transcription_providers = [p.value for p in processor._available_transcription]
            synthesis_providers = [p.value for p in processor._available_synthesis]
        
        return {
            "name": "Audio Agent",
            "type": "on_demand",
            "purpose": "Process audio for transcription, synthesis, and analysis",
            "task_types": [
                "transcribe",
                "synthesize", 
                "analyze_audio",
                "translate",
                "get_voices",
                "estimate_cost",
                "get_capabilities",
                "get_history",
            ],
            "supported_formats": self.SUPPORTED_FORMATS,
            "max_file_size_mb": self.MAX_FILE_SIZE_MB,
            "transcription_providers": transcription_providers or ["openai_whisper (requires API key)"],
            "synthesis_providers": synthesis_providers or ["openai_tts (requires API key)"],
            "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            "voice_aliases": self.VOICE_ALIASES,
            "features": [
                "Speech-to-text transcription",
                "Text-to-speech synthesis",
                "Audio format detection",
                "Metadata extraction",
                "Speech translation to English",
                "Cost estimation",
            ],
            "statistics": {
                "total_transcriptions": self._total_transcriptions,
                "total_syntheses": self._total_syntheses,
                "total_audio_seconds": round(self._total_audio_seconds, 2),
            },
        }
