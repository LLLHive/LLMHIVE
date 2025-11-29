"""Tool call parser for extracting tool calls from LLM responses."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolCallParser:
    """Parses tool calls from LLM responses."""

    # Pattern to match tool calls in various formats
    TOOL_CALL_PATTERNS = [
        # Format: TOOL_CALL: {"tool": "...", "arguments": {...}}
        # Use a more robust pattern that handles nested braces
        re.compile(r'TOOL_CALL:\s*(\{(?:[^{}]|(?:\{[^{}]*\}))*\})', re.DOTALL | re.IGNORECASE),
        # Format: <tool_call>...</tool_call>
        re.compile(r'<tool_call>(.*?)</tool_call>', re.DOTALL | re.IGNORECASE),
        # Format: ```tool_call\n{...}\n```
        re.compile(r'```tool_call\s*\n(.*?)\n```', re.DOTALL | re.IGNORECASE),
    ]

    @classmethod
    def extract_tool_calls(cls, text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from text.

        Args:
            text: Text to parse

        Returns:
            List of tool call dictionaries
        """
        tool_calls: List[Dict[str, Any]] = []

        for pattern in cls.TOOL_CALL_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    # Try to parse as JSON
                    if isinstance(match, tuple):
                        json_str = match[0] if match else ""
                    else:
                        json_str = match

                    # Clean up the JSON string
                    json_str = json_str.strip()
                    if not json_str:
                        continue

                    # Handle escaped quotes (common in LLM outputs)
                    # Replace escaped quotes with regular quotes
                    json_str = json_str.replace('\\"', '"').replace("\\'", "'")
                    
                    # Try to fix common JSON issues
                    # Remove trailing commas
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)

                    # Parse JSON
                    tool_call = json.loads(json_str)
                    if isinstance(tool_call, dict) and "tool" in tool_call:
                        tool_calls.append(tool_call)
                except (json.JSONDecodeError, ValueError) as exc:
                    logger.debug(f"Failed to parse tool call: {exc}, json_str: {json_str[:100] if 'json_str' in locals() else 'N/A'}")
                    continue

        return tool_calls

    @classmethod
    def extract_tool_call(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extract the first tool call from text.

        Args:
            text: Text to parse

        Returns:
            First tool call dictionary or None
        """
        tool_calls = cls.extract_tool_calls(text)
        return tool_calls[0] if tool_calls else None

    @classmethod
    def remove_tool_calls(cls, text: str) -> str:
        """Remove tool call markers from text.

        Args:
            text: Text to clean

        Returns:
            Text with tool calls removed
        """
        cleaned = text
        for pattern in cls.TOOL_CALL_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        return cleaned.strip()

