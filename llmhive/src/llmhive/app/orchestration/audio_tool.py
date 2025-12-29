"""Audio Tool for LLMHive Tool Broker.

Q4 2025: Provides speech-to-text transcription as a tool for the orchestrator.
Integrates with the AudioAgent for comprehensive audio processing.

Usage:
    tool = AudioTool(transcribe_fn=my_transcribe_function)
    result = await tool.execute("path/to/audio.mp3")
"""
import time
import logging
from typing import Optional, Callable, Any

from .tool_broker import BaseTool, ToolType, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class AudioTool(BaseTool):
    """Speech-to-text transcription tool.
    
    Backend provided via transcribe_fn, which should accept audio input
    (path, URL, or base64) and return transcribed text.
    """

    def __init__(self, transcribe_fn: Optional[Callable] = None):
        """Initialize the audio tool.
        
        Args:
            transcribe_fn: Async or sync function that takes audio input
                          and returns transcription text.
        """
        self._transcribe_fn = transcribe_fn

    @property
    def tool_type(self) -> ToolType:
        return ToolType.AUDIO

    def is_available(self) -> bool:
        return True

    async def execute(self, query: str, **kwargs) -> ToolResult:
        """Execute audio transcription.
        
        Args:
            query: Audio source (path, URL, or base64)
            **kwargs: Additional options like language, timestamps, etc.
            
        Returns:
            ToolResult with transcription text
        """
        start_time = time.time()
        audio_source = kwargs.get("audio") or kwargs.get("audio_source") or query
        
        try:
            if self._transcribe_fn:
                result = self._transcribe_fn(audio_source, **kwargs)
                if callable(getattr(result, "__await__", None)):
                    result = await result  # type: ignore
                
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=result,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="audio_transcription",
                    status=ToolStatus.SUCCESS,
                )
            else:
                # No transcription function provided - return placeholder
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data="Audio transcription not enabled. Provide transcribe_fn to enable speech-to-text.",
                    latency_ms=(time.time() - start_time) * 1000,
                    source="audio_placeholder",
                    status=ToolStatus.SUCCESS,
                )
        except Exception as e:
            logger.warning("Audio tool failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )


def create_audio_tool_from_agent(audio_agent: Any) -> AudioTool:
    """Create an AudioTool backed by an AudioAgent.
    
    Args:
        audio_agent: Instance of AudioAgent with transcribe_audio method
        
    Returns:
        AudioTool configured to use the agent
    """
    async def transcribe_fn(audio_source: str, **kwargs):
        from ..agents.audio_agent import TranscriptionRequest
        
        request = TranscriptionRequest(
            audio_source=audio_source,
            language=kwargs.get("language"),
            timestamps=kwargs.get("timestamps", False),
        )
        result = await audio_agent.transcribe_audio(request)
        
        if result.success and result.transcription:
            return result.transcription
        else:
            raise ValueError(result.error or "Transcription failed")
    
    return AudioTool(transcribe_fn=transcribe_fn)
