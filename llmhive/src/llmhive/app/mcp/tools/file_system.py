"""File system tools for MCP."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Safe base paths for file operations (configurable)
SAFE_BASE_PATHS = [
    "/tmp/llmhive",
    "./llmhive_workspace",
]


def _is_safe_path(file_path: str) -> bool:
    """Check if a file path is within safe boundaries.

    Args:
        file_path: File path to check

    Returns:
        True if path is safe
    """
    try:
        abs_path = os.path.abspath(file_path)
        for safe_base in SAFE_BASE_PATHS:
            safe_abs = os.path.abspath(safe_base)
            if abs_path.startswith(safe_abs):
                return True
        return False
    except Exception:
        return False


async def file_read_tool(
    path: str,
) -> Dict[str, Any]:
    """Read a file from the file system.

    Args:
        path: File path (must be within safe directories)

    Returns:
        File contents
    """
    try:
        if not _is_safe_path(path):
            return {
                "path": path,
                "error": "File path is not within allowed directories",
                "content": None,
            }

        file_path = Path(path)
        if not file_path.exists():
            return {
                "path": path,
                "error": "File does not exist",
                "content": None,
            }

        if not file_path.is_file():
            return {
                "path": path,
                "error": "Path is not a file",
                "content": None,
            }

        # Limit file size (1MB)
        if file_path.stat().st_size > 1024 * 1024:
            return {
                "path": path,
                "error": "File too large (max 1MB)",
                "content": None,
            }

        content = file_path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": path,
            "content": content,
            "size": len(content),
        }
    except Exception as exc:
        logger.error(f"File read failed: {exc}", exc_info=True)
        return {
            "path": path,
            "error": str(exc),
            "content": None,
        }


async def file_write_tool(
    path: str,
    content: str,
    append: bool = False,
) -> Dict[str, Any]:
    """Write content to a file.

    Args:
        path: File path (must be within safe directories)
        content: Content to write
        append: If True, append to file; otherwise overwrite

    Returns:
        Write result
    """
    try:
        if not _is_safe_path(path):
            return {
                "path": path,
                "error": "File path is not within allowed directories",
                "success": False,
            }

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if append and file_path.exists():
            file_path.open("a", encoding="utf-8").write(content)
        else:
            file_path.write_text(content, encoding="utf-8")

        return {
            "path": path,
            "success": True,
            "size": len(content),
        }
    except Exception as exc:
        logger.error(f"File write failed: {exc}", exc_info=True)
        return {
            "path": path,
            "error": str(exc),
            "success": False,
        }


async def file_list_tool(
    directory: str,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """List files in a directory.

    Args:
        directory: Directory path (must be within safe directories)
        pattern: Optional file pattern filter

    Returns:
        List of files
    """
    try:
        if not _is_safe_path(directory):
            return {
                "directory": directory,
                "error": "Directory path is not within allowed directories",
                "files": [],
            }

        dir_path = Path(directory)
        if not dir_path.exists():
            return {
                "directory": directory,
                "error": "Directory does not exist",
                "files": [],
            }

        if not dir_path.is_dir():
            return {
                "directory": directory,
                "error": "Path is not a directory",
                "files": [],
            }

        files = []
        for item in dir_path.iterdir():
            if pattern and pattern not in item.name:
                continue
            files.append({
                "name": item.name,
                "path": str(item),
                "is_file": item.is_file(),
                "size": item.stat().st_size if item.is_file() else 0,
            })

        return {
            "directory": directory,
            "files": files,
            "count": len(files),
        }
    except Exception as exc:
        logger.error(f"File list failed: {exc}", exc_info=True)
        return {
            "directory": directory,
            "error": str(exc),
            "files": [],
        }


# Register the tools
from ..tool_registry import register_tool

register_tool(
    name="read_file",
    description="Read a file from the file system (within safe directories)",
    parameters={
        "path": {
            "type": "string",
            "description": "File path to read",
            "required": True,
        },
    },
    handler=file_read_tool,
)

register_tool(
    name="write_file",
    description="Write content to a file (within safe directories)",
    parameters={
        "path": {
            "type": "string",
            "description": "File path to write",
            "required": True,
        },
        "content": {
            "type": "string",
            "description": "Content to write",
            "required": True,
        },
        "append": {
            "type": "boolean",
            "description": "If true, append to file; otherwise overwrite",
            "default": False,
            "required": False,
        },
    },
    handler=file_write_tool,
)

register_tool(
    name="list_files",
    description="List files in a directory (within safe directories)",
    parameters={
        "directory": {
            "type": "string",
            "description": "Directory path to list",
            "required": True,
        },
        "pattern": {
            "type": "string",
            "description": "Optional file pattern filter",
            "required": False,
        },
    },
    handler=file_list_tool,
)

