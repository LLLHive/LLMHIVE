"""Tests for the Audio Agent.

Tests cover:
- Audio format detection and analysis
- Transcription (mocked API)
- Speech synthesis (mocked API)
- Translation (mocked API)
- Error handling
- Voice management
- Cost estimation
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add the src directory to the path for imports
src_path = str(Path(__file__).parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from llmhive.app.agents.audio_agent import (
    AudioAgent,
    AudioMetadata,
    detect_audio_format,
    analyze_audio_data,
    analyze_wav_header,
)
from llmhive.app.agents.base import AgentTask, AgentPriority


# ============================================================
# Audio Format Detection Tests
# ============================================================

class TestAudioFormatDetection:
    """Tests for audio format detection."""
    
    def test_detect_mp3_id3(self):
        """Test MP3 detection with ID3 tag."""
        audio_data = b"ID3" + b"\x00" * 100
        fmt, desc = detect_audio_format(audio_data)
        assert fmt == "mp3"
        assert "ID3" in desc
    
    def test_detect_mp3_frame(self):
        """Test MP3 detection with frame sync."""
        audio_data = b"\xff\xfb" + b"\x00" * 100
        fmt, desc = detect_audio_format(audio_data)
        assert fmt == "mp3"
    
    def test_detect_wav(self):
        """Test WAV detection."""
        audio_data = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100
        fmt, desc = detect_audio_format(audio_data)
        assert fmt == "wav"
    
    def test_detect_flac(self):
        """Test FLAC detection."""
        audio_data = b"fLaC" + b"\x00" * 100
        fmt, desc = detect_audio_format(audio_data)
        assert fmt == "flac"
    
    def test_detect_ogg(self):
        """Test OGG detection."""
        audio_data = b"OggS" + b"\x00" * 100
        fmt, desc = detect_audio_format(audio_data)
        assert fmt == "ogg"
    
    def test_detect_unknown(self):
        """Test unknown format detection."""
        audio_data = b"UNKNOWN_FORMAT" + b"\x00" * 100
        fmt, desc = detect_audio_format(audio_data)
        assert fmt == "unknown"


class TestAudioAnalysis:
    """Tests for audio data analysis."""
    
    def test_analyze_mp3_data(self):
        """Test MP3 analysis."""
        # Simple MP3 header
        audio_data = b"ID3" + b"\x00" * 10000
        metadata = analyze_audio_data(audio_data)
        
        assert metadata.format == "mp3"
        assert metadata.file_size_bytes == len(audio_data)
        assert metadata.estimated_bitrate_kbps == 128  # Default estimate
    
    def test_analyze_wav_data(self):
        """Test WAV analysis with proper header."""
        # Create minimal WAV header
        wav_header = bytearray(44)
        wav_header[0:4] = b"RIFF"
        wav_header[8:12] = b"WAVE"
        wav_header[12:16] = b"fmt "
        wav_header[16:20] = (16).to_bytes(4, 'little')  # chunk size
        wav_header[20:22] = (1).to_bytes(2, 'little')  # audio format (PCM)
        wav_header[22:24] = (2).to_bytes(2, 'little')  # channels
        wav_header[24:28] = (44100).to_bytes(4, 'little')  # sample rate
        wav_header[28:32] = (176400).to_bytes(4, 'little')  # byte rate
        wav_header[34:36] = (16).to_bytes(2, 'little')  # bits per sample
        wav_header[36:40] = b"data"
        wav_header[40:44] = (1000).to_bytes(4, 'little')  # data size
        
        audio_data = bytes(wav_header) + b"\x00" * 1000
        metadata = analyze_audio_data(audio_data)
        
        assert metadata.format == "wav"
        assert metadata.channels == 2
        assert metadata.sample_rate == 44100
        assert metadata.bit_depth == 16
    
    def test_analyze_empty_data(self):
        """Test analysis of empty data."""
        metadata = analyze_audio_data(b"")
        assert metadata.format == "unknown"
        assert metadata.file_size_bytes == 0


# ============================================================
# Audio Agent Tests
# ============================================================

@pytest.mark.asyncio
class TestAudioAgent:
    """Tests for the AudioAgent class."""
    
    @pytest.fixture
    def agent(self):
        """Create an audio agent instance."""
        return AudioAgent()
    
    async def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.name == "audio_agent"
        assert agent._total_transcriptions == 0
        assert agent._total_syntheses == 0
    
    async def test_get_capabilities(self, agent):
        """Test get_capabilities task."""
        task = AgentTask(
            task_id="test-caps",
            task_type="get_capabilities",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert "task_types" in result.output
        assert "transcribe" in result.output["task_types"]
        assert "synthesize" in result.output["task_types"]
        assert "analyze_audio" in result.output["task_types"]
    
    async def test_get_voices(self, agent):
        """Test get_voices task."""
        task = AgentTask(
            task_id="test-voices",
            task_type="get_voices",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert "voices" in result.output
        assert "voice_aliases" in result.output
        # Voices list may be empty if no API keys configured, but structure should exist
        assert isinstance(result.output["voices"], list)
        assert "default_voice" in result.output
    
    async def test_estimate_transcription_cost(self, agent):
        """Test cost estimation for transcription."""
        task = AgentTask(
            task_id="test-cost-1",
            task_type="estimate_cost",
            payload={
                "operation": "transcribe",
                "duration_seconds": 120,  # 2 minutes
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["operation"] == "transcribe"
        assert result.output["estimated_cost_usd"] == pytest.approx(0.012, abs=0.001)
    
    async def test_estimate_synthesis_cost(self, agent):
        """Test cost estimation for synthesis."""
        task = AgentTask(
            task_id="test-cost-2",
            task_type="estimate_cost",
            payload={
                "operation": "synthesize",
                "text": "Hello world! " * 100,
                "model": "tts-1",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["operation"] == "synthesize"
        assert "estimated_cost_usd" in result.output
        assert result.output["character_count"] == len("Hello world! " * 100)
    
    async def test_unknown_task_type(self, agent):
        """Test handling of unknown task type."""
        task = AgentTask(
            task_id="test-unknown",
            task_type="unknown_task",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "Unknown task type" in result.error
    
    async def test_no_task_provided(self, agent):
        """Test agent handles no task."""
        result = await agent.execute(None)
        assert not result.success
        assert "No task provided" in result.error
    
    async def test_transcribe_no_audio(self, agent):
        """Test transcription without audio source."""
        task = AgentTask(
            task_id="test-no-audio",
            task_type="transcribe",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "audio_source" in result.error.lower()
    
    async def test_synthesize_no_text(self, agent):
        """Test synthesis without text."""
        task = AgentTask(
            task_id="test-no-text",
            task_type="synthesize",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "text" in result.error.lower()


# ============================================================
# Mocked API Tests
# ============================================================

@pytest.mark.asyncio
class TestAudioAgentWithMockedAPIs:
    """Tests with mocked external APIs."""
    
    @pytest.fixture
    def agent(self):
        """Create an audio agent instance."""
        return AudioAgent()
    
    @pytest.fixture
    def mock_audio_data(self):
        """Create mock MP3 audio data."""
        return b"ID3" + b"\x00" * 1000
    
    async def test_transcribe_with_mocked_processor(self, agent, mock_audio_data):
        """Test transcription with mocked processor."""
        # Create mock processor
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.text = "Hello, this is a test transcription."
        mock_result.language = "en"
        mock_result.duration_seconds = 5.0
        mock_result.word_count = 7
        mock_result.segments = []
        mock_result.provider_used = "openai_whisper"
        mock_result.confidence = 0.95
        
        mock_processor.transcribe = AsyncMock(return_value=mock_result)
        agent._processor = mock_processor
        
        task = AgentTask(
            task_id="test-transcribe",
            task_type="transcribe",
            payload={
                "audio_source": base64.b64encode(mock_audio_data).decode(),
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["text"] == "Hello, this is a test transcription."
        assert result.output["language"] == "en"
        assert result.output["provider"] == "openai_whisper"
        assert agent._total_transcriptions == 1
    
    async def test_synthesize_with_mocked_processor(self, agent):
        """Test synthesis with mocked processor."""
        # Create mock processor
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.audio_bytes = b"mock_audio_data"
        mock_result.audio_base64 = base64.b64encode(b"mock_audio_data").decode()
        mock_result.format = MagicMock()
        mock_result.format.value = "mp3"
        mock_result.duration_seconds = 3.0
        mock_result.voice_used = "alloy"
        mock_result.provider_used = "openai_tts"
        mock_result.cost_estimate_usd = 0.001
        
        mock_processor.synthesize = AsyncMock(return_value=mock_result)
        mock_processor._available_synthesis = []
        agent._processor = mock_processor
        
        task = AgentTask(
            task_id="test-synthesize",
            task_type="synthesize",
            payload={
                "text": "Hello, world!",
                "voice": "alloy",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["voice"] == "alloy"
        assert result.output["provider"] == "openai_tts"
        assert "audio_base64" in result.output
        assert agent._total_syntheses == 1
    
    async def test_analyze_audio_with_base64(self, agent, mock_audio_data):
        """Test audio analysis with base64 input."""
        task = AgentTask(
            task_id="test-analyze",
            task_type="analyze_audio",
            payload={
                "audio_source": base64.b64encode(mock_audio_data).decode(),
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["format"] == "mp3"
        assert result.output["file_size_bytes"] == len(mock_audio_data)
    
    async def test_transcription_failure_handling(self, agent, mock_audio_data):
        """Test handling of transcription failure."""
        # Create mock processor that fails
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "API rate limit exceeded"
        
        mock_processor.transcribe = AsyncMock(return_value=mock_result)
        agent._processor = mock_processor
        
        task = AgentTask(
            task_id="test-fail",
            task_type="transcribe",
            payload={
                "audio_source": base64.b64encode(mock_audio_data).decode(),
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "rate limit" in result.error.lower()
    
    async def test_synthesis_failure_handling(self, agent):
        """Test handling of synthesis failure."""
        # Create mock processor that fails
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "Invalid voice ID"
        
        mock_processor.synthesize = AsyncMock(return_value=mock_result)
        mock_processor._available_synthesis = []
        agent._processor = mock_processor
        
        task = AgentTask(
            task_id="test-synth-fail",
            task_type="synthesize",
            payload={
                "text": "Hello",
                "voice": "invalid_voice",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert not result.success
        assert "Invalid voice" in result.error


# ============================================================
# Voice Alias Tests
# ============================================================

class TestVoiceAliases:
    """Tests for voice alias resolution."""
    
    def test_voice_aliases_defined(self):
        """Test that voice aliases are defined."""
        agent = AudioAgent()
        assert "default" in agent.VOICE_ALIASES
        assert "female" in agent.VOICE_ALIASES
        assert "male" in agent.VOICE_ALIASES
    
    def test_default_resolves_to_alloy(self):
        """Test default voice resolves to alloy."""
        agent = AudioAgent()
        assert agent.VOICE_ALIASES["default"] == "alloy"
    
    def test_female_resolves_to_nova(self):
        """Test female voice resolves to nova."""
        agent = AudioAgent()
        assert agent.VOICE_ALIASES["female"] == "nova"
    
    def test_male_resolves_to_onyx(self):
        """Test male voice resolves to onyx."""
        agent = AudioAgent()
        assert agent.VOICE_ALIASES["male"] == "onyx"


# ============================================================
# Audio Loading Tests
# ============================================================

class TestAudioLoading:
    """Tests for audio loading functionality."""
    
    def test_load_bytes(self):
        """Test loading raw bytes."""
        agent = AudioAgent()
        audio_data = b"test_audio_data"
        loaded, error = agent._load_audio(audio_data)
        
        assert loaded == audio_data
        assert error is None
    
    def test_load_base64(self):
        """Test loading base64 encoded data."""
        agent = AudioAgent()
        # Use a longer string to pass the length check (>500 chars)
        original = b"test_audio_data" * 50  # Make it long enough
        encoded = base64.b64encode(original).decode()
        
        loaded, error = agent._load_audio(encoded)
        
        assert loaded == original
        assert error is None
    
    def test_load_data_url(self):
        """Test loading data URL."""
        agent = AudioAgent()
        original = b"test_audio_data"
        data_url = f"data:audio/mp3;base64,{base64.b64encode(original).decode()}"
        
        loaded, error = agent._load_audio(data_url)
        
        assert loaded == original
        assert error is None
    
    def test_load_missing_file(self):
        """Test loading non-existent file."""
        agent = AudioAgent()
        loaded, error = agent._load_audio("/nonexistent/audio.mp3")
        
        assert loaded is None
        assert "not found" in error.lower()


# ============================================================
# History Tracking Tests
# ============================================================

@pytest.mark.asyncio
class TestHistoryTracking:
    """Tests for task history tracking."""
    
    async def test_history_tracks_tasks(self):
        """Test that tasks are tracked in history."""
        agent = AudioAgent()
        
        # Create mock processor
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.text = "Test"
        mock_result.language = "en"
        mock_result.duration_seconds = 1.0
        mock_result.word_count = 1
        mock_result.segments = []
        mock_result.provider_used = "test"
        mock_result.confidence = 0.9
        mock_processor.transcribe = AsyncMock(return_value=mock_result)
        agent._processor = mock_processor
        
        # Run a transcription task - need enough data to pass base64 length check
        mock_audio = b"ID3" + b"\x00" * 1000
        task = AgentTask(
            task_id="hist-1",
            task_type="transcribe",
            payload={"audio_source": base64.b64encode(mock_audio).decode()},
        )
        agent.add_task(task)
        transcribe_result = await agent.run()
        
        # Verify transcription succeeded before checking history
        assert transcribe_result.success, f"Transcription failed: {transcribe_result.error}"
        
        # Check history
        task = AgentTask(
            task_id="hist-2",
            task_type="get_history",
            payload={},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert len(result.output["history"]) > 0
        assert result.output["statistics"]["total_transcriptions"] == 1


# ============================================================
# Integration-like Tests (No External Calls)
# ============================================================

@pytest.mark.asyncio
class TestAudioAgentIntegration:
    """Integration-like tests without external API calls."""
    
    async def test_full_analyze_workflow(self):
        """Test full audio analysis workflow."""
        agent = AudioAgent()
        
        # Create WAV-like data
        wav_header = bytearray(44)
        wav_header[0:4] = b"RIFF"
        wav_header[8:12] = b"WAVE"
        wav_header[12:16] = b"fmt "
        audio_data = bytes(wav_header) + b"\x00" * 1000
        
        # Analyze
        task = AgentTask(
            task_id="int-1",
            task_type="analyze_audio",
            payload={"audio": base64.b64encode(audio_data).decode()},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["format"] == "wav"
        
        # Get capabilities
        task = AgentTask(
            task_id="int-2",
            task_type="get_capabilities",
            payload={},
        )
        agent.add_task(task)
        caps_result = await agent.run()
        
        assert caps_result.success
        assert "analyze_audio" in caps_result.output["task_types"]
    
    async def test_cost_estimation_workflow(self):
        """Test cost estimation for different operations."""
        agent = AudioAgent()
        
        # Test transcription cost
        task = AgentTask(
            task_id="cost-1",
            task_type="estimate_cost",
            payload={"operation": "transcribe", "duration_seconds": 300},
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        assert result.output["estimated_cost_usd"] == pytest.approx(0.03, abs=0.001)
        
        # Test synthesis cost
        task = AgentTask(
            task_id="cost-2",
            task_type="estimate_cost",
            payload={
                "operation": "synthesize",
                "text": "A" * 10000,  # 10k characters
                "model": "tts-1-hd",
            },
        )
        agent.add_task(task)
        result = await agent.run()
        
        assert result.success
        # tts-1-hd is $30/1M chars, so 10k chars = 10000/1000000 * 30 = $0.30
        assert result.output["estimated_cost_usd"] == pytest.approx(0.3, abs=0.01)
