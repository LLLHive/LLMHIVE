"""Inter-Instance Communication Protocols."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum, auto
import json

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of inter-instance messages."""
    DELEGATE_REQUEST = auto()
    DELEGATE_RESPONSE = auto()
    QUERY = auto()
    QUERY_RESPONSE = auto()
    STATUS_UPDATE = auto()
    COORDINATION = auto()
    HEALTH_CHECK = auto()
    HEALTH_RESPONSE = auto()


@dataclass
class DelegateRequest:
    """Request to delegate a task to another instance."""
    request_id: str
    source_instance: str
    target_instance: str
    task_description: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_ms: int = 300000
    callback_url: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "type": "DELEGATE_REQUEST",
            "request_id": self.request_id,
            "source_instance": self.source_instance,
            "target_instance": self.target_instance,
            "task_description": self.task_description,
            "context": self.context,
            "priority": self.priority,
            "timeout_ms": self.timeout_ms,
            "callback_url": self.callback_url,
            "timestamp": self.timestamp.isoformat(),
        })
    
    @classmethod
    def from_json(cls, data: str) -> "DelegateRequest":
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            request_id=obj["request_id"],
            source_instance=obj["source_instance"],
            target_instance=obj["target_instance"],
            task_description=obj["task_description"],
            context=obj.get("context", {}),
            priority=obj.get("priority", 0),
            timeout_ms=obj.get("timeout_ms", 300000),
            callback_url=obj.get("callback_url"),
            timestamp=datetime.fromisoformat(obj["timestamp"]),
        )


@dataclass
class DelegateResponse:
    """Response from a delegated task."""
    request_id: str
    instance_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "type": "DELEGATE_RESPONSE",
            "request_id": self.request_id,
            "instance_id": self.instance_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        })
    
    @classmethod
    def from_json(cls, data: str) -> "DelegateResponse":
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            request_id=obj["request_id"],
            instance_id=obj["instance_id"],
            success=obj["success"],
            output=obj.get("output"),
            error=obj.get("error"),
            duration_ms=obj.get("duration_ms", 0),
            metadata=obj.get("metadata", {}),
            timestamp=datetime.fromisoformat(obj["timestamp"]),
        )


@dataclass
class CoordinationMessage:
    """Message for coordinating between instances."""
    message_id: str
    message_type: MessageType
    source_instance: str
    target_instances: List[str]
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "message_id": self.message_id,
            "message_type": self.message_type.name,
            "source_instance": self.source_instance,
            "target_instances": self.target_instances,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        })


class InterInstanceProtocol:
    """Protocol handler for inter-instance communication.
    
    Handles:
    - Message serialization/deserialization
    - Request/response correlation
    - Timeout handling
    - Retry logic
    """
    
    def __init__(self):
        self._pending_requests: Dict[str, DelegateRequest] = {}
        self._message_handlers: Dict[MessageType, callable] = {}
    
    def register_handler(
        self,
        message_type: MessageType,
        handler: callable
    ) -> None:
        """Register a handler for a message type."""
        self._message_handlers[message_type] = handler
    
    async def send_delegation(
        self,
        request: DelegateRequest
    ) -> Optional[DelegateResponse]:
        """Send a delegation request to another instance.
        
        In production, this would make an HTTP/gRPC call.
        """
        self._pending_requests[request.request_id] = request
        
        # Simulate: in production, make actual network call
        logger.info(
            f"Sending delegation {request.request_id} "
            f"to {request.target_instance}"
        )
        
        # Return simulated response
        return DelegateResponse(
            request_id=request.request_id,
            instance_id=request.target_instance,
            success=True,
            output=f"Processed by {request.target_instance}",
            duration_ms=100,
        )
    
    async def receive_response(
        self,
        response: DelegateResponse
    ) -> None:
        """Handle a received delegation response."""
        if response.request_id in self._pending_requests:
            del self._pending_requests[response.request_id]
        
        logger.info(
            f"Received response for {response.request_id} "
            f"from {response.instance_id}"
        )
    
    async def broadcast_coordination(
        self,
        message: CoordinationMessage
    ) -> None:
        """Broadcast coordination message to multiple instances."""
        for target in message.target_instances:
            logger.debug(
                f"Broadcasting {message.message_type.name} "
                f"to {target}"
            )
            # In production, send to each target
    
    def get_pending_requests(self) -> List[DelegateRequest]:
        """Get list of pending requests (for monitoring)."""
        return list(self._pending_requests.values())

