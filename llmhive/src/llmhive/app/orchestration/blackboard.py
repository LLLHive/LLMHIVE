"""Blackboard pattern for shared state management between agents."""
from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class Blackboard:
    """Thread-safe shared scratchpad for agent collaboration.

    The Blackboard pattern allows agents to:
    - Store intermediate results
    - Share reasoning steps
    - Collaborate on complex tasks
    - Access shared context

    This is a core component of the patent vision for multi-agent orchestration.
    """

    def __init__(self, initial_context: Optional[str] = None) -> None:
        """Initialize blackboard.

        Args:
            initial_context: Optional initial context string
        """
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._history: list[Dict[str, Any]] = []
        
        if initial_context:
            self.set("initial_context", initial_context)

    def set(
        self,
        key: str,
        value: Any,
        agent_role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set a value on the blackboard.

        Args:
            key: Key to store value under
            value: Value to store
            agent_role: Optional agent role that set this value
            metadata: Optional metadata about this value
        """
        with self._lock:
            self._data[key] = value
            
            # Store metadata
            if agent_role:
                self._metadata[key]["agent_role"] = agent_role
            if metadata:
                self._metadata[key].update(metadata)
            
            self._metadata[key]["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Record in history
            self._history.append({
                "action": "set",
                "key": key,
                "agent_role": agent_role,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            logger.debug(f"Blackboard set: {key} by {agent_role or 'unknown'}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the blackboard.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        with self._lock:
            return self._data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if a key exists on the blackboard.

        Args:
            key: Key to check

        Returns:
            True if key exists
        """
        with self._lock:
            return key in self._data

    def update(self, key: str, value: Any, agent_role: Optional[str] = None) -> None:
        """Update a value on the blackboard (same as set, but logs as update).

        Args:
            key: Key to update
            value: New value
            agent_role: Optional agent role that updated this value
        """
        with self._lock:
            if key not in self._data:
                logger.warning(f"Updating non-existent key: {key}")
            
            self.set(key, value, agent_role=agent_role)
            
            # Record in history
            self._history.append({
                "action": "update",
                "key": key,
                "agent_role": agent_role,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def append(self, key: str, value: Any, agent_role: Optional[str] = None) -> None:
        """Append to a list value on the blackboard.

        Args:
            key: Key to append to
            value: Value to append
            agent_role: Optional agent role that appended this value
        """
        with self._lock:
            if key not in self._data:
                self._data[key] = []
            elif not isinstance(self._data[key], list):
                raise ValueError(f"Key '{key}' is not a list, cannot append")
            
            self._data[key].append(value)
            
            # Record in history
            self._history.append({
                "action": "append",
                "key": key,
                "agent_role": agent_role,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            logger.debug(f"Blackboard append: {key} by {agent_role or 'unknown'}")

    def get_all(self) -> Dict[str, Any]:
        """Get all data from the blackboard.

        Returns:
            Copy of all blackboard data
        """
        with self._lock:
            return self._data.copy()

    def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for a key.

        Args:
            key: Key to get metadata for

        Returns:
            Metadata dictionary
        """
        with self._lock:
            return self._metadata.get(key, {}).copy()

    def get_history(self, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """Get blackboard operation history.

        Args:
            limit: Optional limit on number of history entries

        Returns:
            List of history entries
        """
        with self._lock:
            if limit:
                return self._history[-limit:]
            return self._history.copy()

    def clear(self) -> None:
        """Clear all data from the blackboard."""
        with self._lock:
            self._data.clear()
            self._metadata.clear()
            self._history.clear()
            logger.debug("Blackboard cleared")

    def snapshot(self) -> Dict[str, Any]:
        """Create a snapshot of the blackboard state.

        Returns:
            Snapshot dictionary with data, metadata, and summary
        """
        with self._lock:
            return {
                "data": self._data.copy(),
                "metadata": {
                    k: v.copy() for k, v in self._metadata.items()
                },
                "summary": {
                    "total_keys": len(self._data),
                    "total_operations": len(self._history),
                    "keys": list(self._data.keys()),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

