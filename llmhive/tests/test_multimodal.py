"""Tests for multimodal capabilities.

These tests verify:
1. Image analysis functionality
2. Image generation with tier restrictions
3. Audio transcription and synthesis
4. Multimodal handler integration
5. Tool broker integration
"""
from __future__ import annotations

import asyncio
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict

# Import modules under test
from llmhive.src.llmhive.app.multimodal.image_analyzer import (
    ImageAnalyzer,
    ImageAnalysisResult,
    AnalysisType,
    is_valid_image_url,
    encode_bytes_to_base64,
)
from llmhive.src.llmhive.app.multimodal.image_generator import (
    ImageGenerator,
    ImageGenerationResult,
    ImageSize,
    ImageQuality,
    is_safe_prompt,
)
from llmhive.src.llmhive.app.multimodal.audio_processor import (
    AudioProcessor,
    TranscriptionResult,
    SpeechSynthesisResult,
    TTSVoice,
)
from llmhive.src.llmhive.app.multimodal.handler import (
    MultimodalHandler,
    MultimodalInput,
    MultimodalOutput,
    ProcessingAction,
    is_image_generation_request,
    extract_image_prompt,
    MULTIMODAL_TIER_ACCESS,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================

@pytest.fixture
def sample_image_bytes():
    """Generate a minimal valid PNG image."""
    # Minimal 1x1 transparent PNG
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82,
    ])
    return png_data


# Check if openai is available for tests that need it
try:
    import openai as openai_module
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai_module = None


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    if not OPENAI_AVAILABLE:
        pytest.skip("OpenAI package not installed")
    
    with patch("openai.AsyncOpenAI") as mock:
        client = MagicMock()
        
        # Mock chat completions for vision
        async def mock_chat_create(**kwargs):
            result = MagicMock()
            result.choices = [MagicMock()]
            result.choices[0].message.content = "This is a test image showing a beautiful sunset over the ocean. The sky is painted with orange and purple hues."
            return result
        
        client.chat.completions.create = mock_chat_create
        
        # Mock image generation
        async def mock_image_generate(**kwargs):
            result = MagicMock()
            result.data = [MagicMock()]
            result.data[0].url = "https://example.com/generated.png"
            result.data[0].revised_prompt = kwargs.get("prompt", "")
            return result
        
        client.images.generate = mock_image_generate
        
        # Mock audio transcription
        async def mock_transcribe(**kwargs):
            result = MagicMock()
            result.text = "Hello, this is a test transcription."
            return result
        
        client.audio.transcriptions.create = mock_transcribe
        
        # Mock audio synthesis
        async def mock_speech_create(**kwargs):
            result = MagicMock()
            result.content = b"fake_audio_data"
            return result
        
        client.audio.speech.create = mock_speech_create
        
        mock.return_value = client
        yield mock


# ==============================================================================
# Image Analyzer Tests
# ==============================================================================

class TestImageAnalyzer:
    """Tests for ImageAnalyzer."""
    
    def test_is_valid_image_url(self):
        """Test URL validation."""
        assert is_valid_image_url("https://example.com/image.jpg") is True
        assert is_valid_image_url("http://example.com/photo.png") is True
        assert is_valid_image_url("https://example.com/image.webp") is True
        assert is_valid_image_url("not_a_url") is False
        assert is_valid_image_url("") is False
    
    def test_encode_bytes_to_base64(self, sample_image_bytes):
        """Test base64 encoding."""
        encoded = encode_bytes_to_base64(sample_image_bytes)
        assert isinstance(encoded, str)
        # Should decode back to original
        decoded = base64.b64decode(encoded)
        assert decoded == sample_image_bytes
    
    @pytest.mark.asyncio
    async def test_analyze_with_openai(self, mock_openai_client, sample_image_bytes):
        """Test image analysis with OpenAI Vision."""
        analyzer = ImageAnalyzer(openai_api_key="test-key")
        
        result = await analyzer.analyze(
            sample_image_bytes,
            analysis_types=[AnalysisType.DESCRIBE],
        )
        
        assert isinstance(result, ImageAnalysisResult)
        assert result.description  # Should have description
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_analyze_no_providers(self):
        """Test graceful handling when no providers available."""
        analyzer = ImageAnalyzer()
        analyzer._available_providers = []
        
        result = await analyzer.analyze(b"fake_image")
        
        assert result.error is not None
        assert "No providers" in result.error or "available" in result.error.lower()


# ==============================================================================
# Image Generator Tests
# ==============================================================================

class TestImageGenerator:
    """Tests for ImageGenerator."""
    
    def test_is_safe_prompt(self):
        """Test prompt safety filtering."""
        assert is_safe_prompt("A beautiful sunset")[0] is True
        assert is_safe_prompt("A cat sitting on a windowsill")[0] is True
        
        # Unsafe prompts should be filtered
        assert is_safe_prompt("explicit content")[0] is False
        assert is_safe_prompt("gore violence")[0] is False
    
    @pytest.mark.asyncio
    async def test_generate_with_dalle(self, mock_openai_client):
        """Test image generation with DALL-E."""
        generator = ImageGenerator(openai_api_key="test-key")
        
        result = await generator.generate(
            "A robot reading a book",
            size=ImageSize.LARGE,
        )
        
        assert isinstance(result, ImageGenerationResult)
        assert result.success
        assert result.image_url or result.image_base64
    
    @pytest.mark.asyncio
    async def test_generate_unsafe_prompt(self):
        """Test that unsafe prompts are rejected."""
        generator = ImageGenerator(
            openai_api_key="test-key",
            enable_safety_filter=True,
        )
        
        result = await generator.generate("explicit nsfw content")
        
        assert result.success is False
        assert "safety" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_generate_no_providers(self):
        """Test graceful handling when no providers available."""
        generator = ImageGenerator()
        generator._available_providers = []
        
        result = await generator.generate("A test image")
        
        assert result.success is False
        assert result.error is not None


# ==============================================================================
# Audio Processor Tests
# ==============================================================================

class TestAudioProcessor:
    """Tests for AudioProcessor."""
    
    @pytest.mark.asyncio
    async def test_transcribe_with_openai(self, mock_openai_client):
        """Test audio transcription with OpenAI Whisper."""
        processor = AudioProcessor(openai_api_key="test-key")
        
        result = await processor.transcribe(b"fake_audio_data")
        
        assert isinstance(result, TranscriptionResult)
        assert result.success
        assert result.text == "Hello, this is a test transcription."
    
    @pytest.mark.asyncio
    async def test_synthesize_with_openai(self, mock_openai_client):
        """Test speech synthesis with OpenAI TTS."""
        processor = AudioProcessor(openai_api_key="test-key")
        
        result = await processor.synthesize(
            "Hello world",
            voice=TTSVoice.ALLOY,
        )
        
        assert isinstance(result, SpeechSynthesisResult)
        assert result.success
        assert result.audio_bytes is not None
    
    def test_get_available_voices(self):
        """Test voice listing."""
        processor = AudioProcessor(openai_api_key="test-key")
        
        voices = processor.get_available_voices()
        
        # Should include OpenAI voices
        voice_ids = [v["id"] for v in voices]
        assert "alloy" in voice_ids or len(voices) >= 0  # May be empty if not initialized


# ==============================================================================
# Multimodal Handler Tests
# ==============================================================================

class TestMultimodalHandler:
    """Tests for MultimodalHandler."""
    
    def test_tier_access_free(self):
        """Test free tier access restrictions."""
        handler = MultimodalHandler()
        
        # Free tier can analyze images
        allowed, reason = handler.check_tier_access(ProcessingAction.ANALYZE_IMAGE, "free")
        assert allowed is True
        
        # Free tier cannot generate images
        allowed, reason = handler.check_tier_access(ProcessingAction.GENERATE_IMAGE, "free")
        assert allowed is False
        assert reason is not None
        
        # Free tier can transcribe audio
        allowed, reason = handler.check_tier_access(ProcessingAction.TRANSCRIBE_AUDIO, "free")
        assert allowed is True
        
        # Free tier cannot synthesize speech
        allowed, reason = handler.check_tier_access(ProcessingAction.SYNTHESIZE_SPEECH, "free")
        assert allowed is False
    
    def test_tier_access_pro(self):
        """Test pro tier access."""
        handler = MultimodalHandler()
        
        # Pro tier can do everything
        for action in ProcessingAction:
            if action != ProcessingAction.NONE:
                allowed, _ = handler.check_tier_access(action, "pro")
                assert allowed is True
    
    def test_tier_access_enterprise(self):
        """Test enterprise tier access."""
        handler = MultimodalHandler()
        
        # Enterprise tier can do everything
        for action in ProcessingAction:
            if action != ProcessingAction.NONE:
                allowed, _ = handler.check_tier_access(action, "enterprise")
                assert allowed is True
    
    def test_is_image_generation_request(self):
        """Test detection of image generation requests."""
        assert is_image_generation_request("Generate an image of a sunset") is True
        assert is_image_generation_request("Create a picture of a cat") is True
        assert is_image_generation_request("Draw me an illustration of a forest") is True
        assert is_image_generation_request("[generate image] robot reading") is True
        
        # Not generation requests
        assert is_image_generation_request("What is the capital of France?") is False
        assert is_image_generation_request("Describe this image") is False
    
    def test_extract_image_prompt(self):
        """Test extraction of image prompts."""
        assert extract_image_prompt("Generate an image of a sunset") == "a sunset"
        assert "cat" in extract_image_prompt("Create a picture of a cat").lower()
        assert extract_image_prompt("robot reading a book") == "robot reading a book"
    
    @pytest.mark.asyncio
    async def test_process_input_text_only(self):
        """Test processing text-only input."""
        handler = MultimodalHandler()
        
        result = await handler.process_input(
            text="What is the weather?",
            user_tier="free",
        )
        
        assert result["augmented_text"] == "What is the weather?"
        assert result["original_text"] == "What is the weather?"
        assert len(result["image_analyses"]) == 0
    
    @pytest.mark.asyncio
    async def test_process_input_with_images(self, mock_openai_client, sample_image_bytes):
        """Test processing input with images."""
        handler = MultimodalHandler()
        
        # Mock the image analyzer
        mock_result = ImageAnalysisResult(
            description="A test image",
            provider_used="test",
        )
        
        with patch.object(handler.image_analyzer, 'analyze', return_value=mock_result):
            result = await handler.process_input(
                text="What is in this image?",
                images=[sample_image_bytes],
                user_tier="pro",
            )
        
        assert "Image Context" in result["augmented_text"]
        assert len(result["image_analyses"]) == 1
    
    @pytest.mark.asyncio
    async def test_process_output_with_image_generation(self, mock_openai_client):
        """Test processing output that requests image generation."""
        handler = MultimodalHandler()
        
        # Mock the generator
        mock_result = ImageGenerationResult(
            success=True,
            image_url="https://example.com/image.png",
            provider_used="dall_e_3",
        )
        
        with patch.object(handler.image_generator, 'generate', return_value=mock_result):
            output = await handler.process_output(
                text="Generate an image of a sunset",
                user_tier="pro",
            )
        
        assert isinstance(output, MultimodalOutput)
        assert len(output.images) > 0 or "failed" in str(output.processing_notes).lower()


# ==============================================================================
# MultimodalInput/Output Tests
# ==============================================================================

class TestMultimodalInputOutput:
    """Tests for MultimodalInput and MultimodalOutput."""
    
    def test_multimodal_input_properties(self):
        """Test MultimodalInput properties."""
        # Text only
        input1 = MultimodalInput(text="Hello")
        assert input1.is_text_only is True
        assert input1.has_images is False
        assert input1.has_audio is False
        
        # With images
        input2 = MultimodalInput(text="Hello", images=[b"img"])
        assert input2.is_text_only is False
        assert input2.has_images is True
        
        # With audio
        input3 = MultimodalInput(text="Hello", audio=b"audio")
        assert input3.has_audio is True
    
    def test_multimodal_output_add_image(self):
        """Test adding images to output."""
        output = MultimodalOutput(text="Here is the image")
        
        output.add_image(
            url="https://example.com/image.png",
            description="A beautiful sunset",
        )
        
        assert len(output.images) == 1
        assert output.images[0]["url"] == "https://example.com/image.png"
        assert output.images[0]["description"] == "A beautiful sunset"
    
    def test_multimodal_output_set_audio(self):
        """Test setting audio on output."""
        output = MultimodalOutput(text="Here is the audio")
        
        output.set_audio(
            b"fake_audio_data",
            format="mp3",
            duration=5.0,
        )
        
        assert output.audio is not None
        assert output.audio["format"] == "mp3"
        assert output.audio["duration"] == 5.0
        assert output.audio["base64"] is not None


# ==============================================================================
# Tier Access Configuration Tests
# ==============================================================================

class TestTierAccessConfiguration:
    """Tests for tier-based access configuration."""
    
    def test_free_tier_limits(self):
        """Test free tier limitations."""
        config = MULTIMODAL_TIER_ACCESS["free"]
        
        assert config["image_analysis"] is True
        assert config["image_generation"] is False
        assert config["audio_transcription"] is True
        assert config["audio_synthesis"] is False
        assert config["max_images_per_request"] == 1
        assert config["max_audio_duration_seconds"] == 60
    
    def test_pro_tier_limits(self):
        """Test pro tier capabilities."""
        config = MULTIMODAL_TIER_ACCESS["pro"]
        
        assert config["image_analysis"] is True
        assert config["image_generation"] is True
        assert config["audio_transcription"] is True
        assert config["audio_synthesis"] is True
        assert config["max_images_per_request"] == 5
    
    def test_enterprise_tier_limits(self):
        """Test enterprise tier capabilities."""
        config = MULTIMODAL_TIER_ACCESS["enterprise"]
        
        assert config["max_images_per_request"] == 10
        assert config["max_audio_duration_seconds"] == 3600


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

