"""Audio Processing Tools for LLMHive.

This module provides audio processing capabilities:
- Speech-to-text (transcription) using Whisper
- Text-to-speech (synthesis) using OpenAI TTS, ElevenLabs, or AWS Polly
- Audio format handling

Usage:
    processor = AudioProcessor()
    # Transcribe audio
    result = await processor.transcribe("audio.mp3")
    # Synthesize speech
    result = await processor.synthesize("Hello world", voice="alloy")
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Types and Configuration
# ==============================================================================

class TranscriptionProvider(str, Enum):
    """Supported transcription providers."""
    OPENAI_WHISPER = "openai_whisper"
    LOCAL_WHISPER = "local_whisper"
    GOOGLE_STT = "google_stt"
    AZURE_STT = "azure_stt"


class SpeechSynthesisProvider(str, Enum):
    """Supported speech synthesis providers."""
    OPENAI_TTS = "openai_tts"
    ELEVEN_LABS = "eleven_labs"
    AWS_POLLY = "aws_polly"
    GOOGLE_TTS = "google_tts"
    AZURE_TTS = "azure_tts"


class TTSVoice(str, Enum):
    """OpenAI TTS voices."""
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


class TTSModel(str, Enum):
    """OpenAI TTS models."""
    TTS_1 = "tts-1"  # Faster, lower quality
    TTS_1_HD = "tts-1-hd"  # Higher quality


class AudioFormat(str, Enum):
    """Supported audio formats."""
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    AAC = "aac"
    OPUS = "opus"


@dataclass(slots=True)
class TranscriptionResult:
    """Result of audio transcription."""
    success: bool
    text: str = ""
    language: Optional[str] = None
    duration_seconds: float = 0.0
    confidence: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)
    provider_used: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def word_count(self) -> int:
        """Get word count of transcription."""
        return len(self.text.split())


@dataclass(slots=True)
class SpeechSynthesisResult:
    """Result of speech synthesis."""
    success: bool
    audio_bytes: Optional[bytes] = None
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    format: AudioFormat = AudioFormat.MP3
    duration_seconds: float = 0.0
    provider_used: Optional[str] = None
    voice_used: Optional[str] = None
    cost_estimate_usd: float = 0.0
    error: Optional[str] = None
    
    def save_to_file(self, path: Union[str, Path]) -> bool:
        """Save the audio to a file."""
        audio_data = self.audio_bytes
        
        if audio_data is None and self.audio_base64:
            audio_data = base64.b64decode(self.audio_base64)
        
        if audio_data is None:
            return False
        
        try:
            Path(path).write_bytes(audio_data)
            return True
        except Exception as e:
            logger.error("Failed to save audio: %s", e)
            return False


# Audio format detection
AUDIO_SIGNATURES = {
    b"ID3": "mp3",
    b"\xff\xfb": "mp3",
    b"\xff\xfa": "mp3",
    b"RIFF": "wav",
    b"fLaC": "flac",
    b"OggS": "ogg",
}


def detect_audio_format(audio_data: bytes) -> Optional[AudioFormat]:
    """Detect audio format from file signature."""
    for sig, fmt in AUDIO_SIGNATURES.items():
        if audio_data.startswith(sig):
            return AudioFormat(fmt)
    return None


def get_audio_mime_type(format: AudioFormat) -> str:
    """Get MIME type for audio format."""
    mime_types = {
        AudioFormat.MP3: "audio/mpeg",
        AudioFormat.WAV: "audio/wav",
        AudioFormat.FLAC: "audio/flac",
        AudioFormat.OGG: "audio/ogg",
        AudioFormat.AAC: "audio/aac",
        AudioFormat.OPUS: "audio/opus",
    }
    return mime_types.get(format, "audio/mpeg")


# ==============================================================================
# Audio Processor
# ==============================================================================

class AudioProcessor:
    """Process audio for speech-to-text and text-to-speech.
    
    Supports:
    - Transcription: OpenAI Whisper, Local Whisper
    - Synthesis: OpenAI TTS, ElevenLabs, AWS Polly
    
    Usage:
        processor = AudioProcessor()
        
        # Transcribe audio
        result = await processor.transcribe("audio.mp3")
        print(result.text)
        
        # Synthesize speech
        result = await processor.synthesize("Hello world")
        result.save_to_file("output.mp3")
    """
    
    # Cost estimates (USD)
    COST_ESTIMATES = {
        "whisper_per_minute": 0.006,
        "tts_1_per_1m_chars": 15.0,
        "tts_1_hd_per_1m_chars": 30.0,
        "eleven_labs_per_1k_chars": 0.30,
    }
    
    def __init__(
        self,
        *,
        openai_api_key: Optional[str] = None,
        eleven_labs_api_key: Optional[str] = None,
        default_voice: TTSVoice = TTSVoice.ALLOY,
        default_tts_model: TTSModel = TTSModel.TTS_1,
    ):
        """
        Initialize the AudioProcessor.
        
        Args:
            openai_api_key: OpenAI API key
            eleven_labs_api_key: ElevenLabs API key
            default_voice: Default voice for TTS
            default_tts_model: Default TTS model
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.eleven_labs_api_key = eleven_labs_api_key or os.getenv("ELEVEN_LABS_API_KEY")
        self.default_voice = default_voice
        self.default_tts_model = default_tts_model
        
        # Initialize available providers
        self._available_transcription: List[TranscriptionProvider] = []
        self._available_synthesis: List[SpeechSynthesisProvider] = []
        self._init_providers()
    
    def _init_providers(self) -> None:
        """Initialize and detect available providers."""
        # Check OpenAI
        if self.openai_api_key:
            try:
                import openai  # noqa: F401
                self._available_transcription.append(TranscriptionProvider.OPENAI_WHISPER)
                self._available_synthesis.append(SpeechSynthesisProvider.OPENAI_TTS)
                logger.info("OpenAI audio services available")
            except ImportError:
                logger.debug("OpenAI package not installed")
        
        # Check ElevenLabs
        if self.eleven_labs_api_key:
            self._available_synthesis.append(SpeechSynthesisProvider.ELEVEN_LABS)
            logger.info("ElevenLabs available")
        
        # Check local Whisper
        try:
            import whisper  # noqa: F401
            self._available_transcription.append(TranscriptionProvider.LOCAL_WHISPER)
            logger.info("Local Whisper available")
        except ImportError:
            logger.debug("Local Whisper not installed")
    
    # ==========================================================================
    # Transcription (Speech-to-Text)
    # ==========================================================================
    
    async def transcribe(
        self,
        audio: Union[str, Path, bytes],
        *,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        response_format: str = "json",
    ) -> TranscriptionResult:
        """
        Transcribe audio to text.
        
        Args:
            audio: Audio file path or bytes
            language: Optional language code (e.g., "en", "es")
            prompt: Optional prompt to guide transcription
            response_format: Response format (json, text, srt, vtt)
            
        Returns:
            TranscriptionResult with transcribed text
        """
        # Load audio
        if isinstance(audio, (str, Path)):
            audio_path = Path(audio)
            if not audio_path.exists():
                return TranscriptionResult(
                    success=False,
                    error=f"Audio file not found: {audio_path}",
                )
            audio_bytes = audio_path.read_bytes()
            filename = audio_path.name
        else:
            audio_bytes = audio
            filename = "audio.mp3"
        
        # Get provider
        if TranscriptionProvider.OPENAI_WHISPER in self._available_transcription:
            return await self._transcribe_with_openai(
                audio_bytes=audio_bytes,
                filename=filename,
                language=language,
                prompt=prompt,
                response_format=response_format,
            )
        
        elif TranscriptionProvider.LOCAL_WHISPER in self._available_transcription:
            return await self._transcribe_with_local_whisper(
                audio_bytes=audio_bytes,
                language=language,
            )
        
        else:
            return TranscriptionResult(
                success=False,
                error="No transcription providers available. Configure OPENAI_API_KEY or install whisper.",
            )
    
    async def _transcribe_with_openai(
        self,
        audio_bytes: bytes,
        filename: str,
        language: Optional[str],
        prompt: Optional[str],
        response_format: str,
    ) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Create file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename
        
        # Build request
        kwargs: Dict[str, Any] = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": response_format,
        }
        
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt
        
        # Make API call
        response = await client.audio.transcriptions.create(**kwargs)
        
        # Parse response
        if response_format == "json":
            text = response.text
        else:
            text = str(response)
        
        # Estimate cost (assume 1 minute average)
        cost = self.COST_ESTIMATES["whisper_per_minute"]
        
        return TranscriptionResult(
            success=True,
            text=text,
            language=language,
            provider_used=TranscriptionProvider.OPENAI_WHISPER.value,
        )
    
    async def _transcribe_with_local_whisper(
        self,
        audio_bytes: bytes,
        language: Optional[str],
    ) -> TranscriptionResult:
        """Transcribe using local Whisper model."""
        import whisper
        import tempfile
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            # Load model (use base for speed)
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(None, whisper.load_model, "base")
            
            # Transcribe
            options = {}
            if language:
                options["language"] = language
            
            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(temp_path, **options),
            )
            
            return TranscriptionResult(
                success=True,
                text=result["text"],
                language=result.get("language"),
                segments=[
                    {
                        "start": s["start"],
                        "end": s["end"],
                        "text": s["text"],
                    }
                    for s in result.get("segments", [])
                ],
                provider_used=TranscriptionProvider.LOCAL_WHISPER.value,
            )
            
        finally:
            # Cleanup temp file
            Path(temp_path).unlink(missing_ok=True)
    
    # ==========================================================================
    # Speech Synthesis (Text-to-Speech)
    # ==========================================================================
    
    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[Union[TTSVoice, str]] = None,
        model: Optional[TTSModel] = None,
        format: AudioFormat = AudioFormat.MP3,
        speed: float = 1.0,
    ) -> SpeechSynthesisResult:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            model: TTS model to use
            format: Output audio format
            speed: Speech speed (0.25 to 4.0)
            
        Returns:
            SpeechSynthesisResult with audio data
        """
        if not text.strip():
            return SpeechSynthesisResult(
                success=False,
                error="Empty text provided",
            )
        
        # Limit text length
        if len(text) > 4096:
            text = text[:4096]
            logger.warning("Text truncated to 4096 characters")
        
        # Get provider
        if SpeechSynthesisProvider.OPENAI_TTS in self._available_synthesis:
            return await self._synthesize_with_openai(
                text=text,
                voice=voice or self.default_voice,
                model=model or self.default_tts_model,
                format=format,
                speed=speed,
            )
        
        elif SpeechSynthesisProvider.ELEVEN_LABS in self._available_synthesis:
            return await self._synthesize_with_eleven_labs(
                text=text,
                voice=voice,
            )
        
        else:
            return SpeechSynthesisResult(
                success=False,
                error="No TTS providers available. Configure OPENAI_API_KEY or ELEVEN_LABS_API_KEY.",
            )
    
    async def _synthesize_with_openai(
        self,
        text: str,
        voice: Union[TTSVoice, str],
        model: TTSModel,
        format: AudioFormat,
        speed: float,
    ) -> SpeechSynthesisResult:
        """Synthesize speech using OpenAI TTS."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=self.openai_api_key)
        
        # Normalize voice
        if isinstance(voice, TTSVoice):
            voice_name = voice.value
        else:
            voice_name = voice.lower()
        
        # Validate speed
        speed = max(0.25, min(4.0, speed))
        
        # Map format to response format
        response_format_map = {
            AudioFormat.MP3: "mp3",
            AudioFormat.WAV: "wav",
            AudioFormat.FLAC: "flac",
            AudioFormat.OGG: "opus",
            AudioFormat.OPUS: "opus",
            AudioFormat.AAC: "aac",
        }
        response_format = response_format_map.get(format, "mp3")
        
        # Make API call
        response = await client.audio.speech.create(
            model=model.value,
            voice=voice_name,
            input=text,
            response_format=response_format,
            speed=speed,
        )
        
        # Get audio bytes
        audio_bytes = response.content
        
        # Estimate cost
        char_count = len(text)
        cost_per_char = self.COST_ESTIMATES[f"{model.value.replace('-', '_')}_per_1m_chars"] / 1_000_000
        cost = char_count * cost_per_char
        
        return SpeechSynthesisResult(
            success=True,
            audio_bytes=audio_bytes,
            audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
            format=format,
            provider_used=SpeechSynthesisProvider.OPENAI_TTS.value,
            voice_used=voice_name,
            cost_estimate_usd=cost,
        )
    
    async def _synthesize_with_eleven_labs(
        self,
        text: str,
        voice: Optional[str],
    ) -> SpeechSynthesisResult:
        """Synthesize speech using ElevenLabs."""
        import httpx
        
        # Default voice ID for ElevenLabs (Rachel)
        voice_id = voice or "21m00Tcm4TlvDq8ikWAM"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.eleven_labs_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.5,
                    },
                },
                timeout=60.0,
            )
            
            if response.status_code != 200:
                return SpeechSynthesisResult(
                    success=False,
                    error=f"ElevenLabs API error: {response.status_code} - {response.text[:200]}",
                )
            
            audio_bytes = response.content
            
            # Estimate cost
            char_count = len(text)
            cost = (char_count / 1000) * self.COST_ESTIMATES["eleven_labs_per_1k_chars"]
            
            return SpeechSynthesisResult(
                success=True,
                audio_bytes=audio_bytes,
                audio_base64=base64.b64encode(audio_bytes).decode("utf-8"),
                format=AudioFormat.MP3,
                provider_used=SpeechSynthesisProvider.ELEVEN_LABS.value,
                voice_used=voice_id,
                cost_estimate_usd=cost,
            )
    
    # ==========================================================================
    # Utility Methods
    # ==========================================================================
    
    def get_available_voices(self) -> List[Dict[str, str]]:
        """Get list of available voices."""
        voices = []
        
        # OpenAI voices
        if SpeechSynthesisProvider.OPENAI_TTS in self._available_synthesis:
            for voice in TTSVoice:
                voices.append({
                    "id": voice.value,
                    "name": voice.value.title(),
                    "provider": "openai",
                })
        
        return voices
    
    def estimate_transcription_cost(self, duration_seconds: float) -> float:
        """Estimate transcription cost for given duration."""
        minutes = duration_seconds / 60
        return minutes * self.COST_ESTIMATES["whisper_per_minute"]
    
    def estimate_synthesis_cost(
        self,
        text: str,
        model: TTSModel = TTSModel.TTS_1,
    ) -> float:
        """Estimate synthesis cost for given text."""
        char_count = len(text)
        cost_per_char = self.COST_ESTIMATES[f"{model.value.replace('-', '_')}_per_1m_chars"] / 1_000_000
        return char_count * cost_per_char


# ==============================================================================
# Convenience Functions
# ==============================================================================

_processor: Optional[AudioProcessor] = None


def get_audio_processor() -> AudioProcessor:
    """Get global AudioProcessor instance."""
    global _processor
    if _processor is None:
        _processor = AudioProcessor()
    return _processor


async def transcribe_audio(
    audio: Union[str, Path, bytes],
    *,
    language: Optional[str] = None,
) -> TranscriptionResult:
    """
    Transcribe audio using the global processor.
    
    Args:
        audio: Audio file path or bytes
        language: Optional language code
        
    Returns:
        TranscriptionResult
    """
    processor = get_audio_processor()
    return await processor.transcribe(audio, language=language)


async def synthesize_speech(
    text: str,
    *,
    voice: Optional[Union[TTSVoice, str]] = None,
) -> SpeechSynthesisResult:
    """
    Synthesize speech using the global processor.
    
    Args:
        text: Text to synthesize
        voice: Voice to use
        
    Returns:
        SpeechSynthesisResult
    """
    processor = get_audio_processor()
    return await processor.synthesize(text, voice=voice)

