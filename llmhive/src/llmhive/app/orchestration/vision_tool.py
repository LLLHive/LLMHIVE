import time
import logging
from typing import Optional, Callable, Any

from .tool_broker import BaseTool, ToolType, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


class VisionTool(BaseTool):
    """General image caption/OCR tool; backend provided via vision_fn."""

    def __init__(self, vision_fn: Optional[Callable] = None):
        self._vision_fn = vision_fn

    @property
    def tool_type(self) -> ToolType:
        return ToolType.VISION

    def is_available(self) -> bool:
        return True

    async def execute(self, query: str, **kwargs) -> ToolResult:
        start_time = time.time()
        image = kwargs.get("image") or query
        try:
            if self._vision_fn:
                result = self._vision_fn(image)
                if callable(getattr(result, "__await__", None)):
                    result = await result  # type: ignore
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data=result,
                    latency_ms=(time.time() - start_time) * 1000,
                    source="vision",
                    status=ToolStatus.SUCCESS,
                )
            else:
                return ToolResult(
                    tool_type=self.tool_type,
                    success=True,
                    data="Vision not enabled. Provide vision_fn to enable caption/OCR.",
                    latency_ms=(time.time() - start_time) * 1000,
                    source="vision_placeholder",
                    status=ToolStatus.SUCCESS,
                )
        except Exception as e:
            logger.warning("Vision tool failed: %s", e)
            return ToolResult(
                tool_type=self.tool_type,
                success=False,
                data=None,
                error_message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
                status=ToolStatus.FAILED,
            )
