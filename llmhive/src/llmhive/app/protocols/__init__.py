"""Protocol framework for diverse orchestration strategies."""
from __future__ import annotations

from .base import BaseProtocol, ProtocolResult
from .simple import SimpleProtocol
from .critique_and_improve import CritiqueAndImproveProtocol

__all__ = [
    "BaseProtocol",
    "ProtocolResult",
    "SimpleProtocol",
    "CritiqueAndImproveProtocol",
]

# Protocol registry: maps protocol names to classes
PROTOCOL_REGISTRY: dict[str, type[BaseProtocol]] = {
    "simple": SimpleProtocol,
    "critique-and-improve": CritiqueAndImproveProtocol,
    "critique_and_improve": CritiqueAndImproveProtocol,  # Alias with underscore
}


def get_protocol(protocol_name: str | None) -> type[BaseProtocol] | None:
    """
    Get protocol class by name.
    
    Args:
        protocol_name: Name of the protocol (e.g., "simple", "critique-and-improve")
        
    Returns:
        Protocol class or None if not found
    """
    if not protocol_name:
        return None
    return PROTOCOL_REGISTRY.get(protocol_name.lower())


def list_protocols() -> list[str]:
    """List all available protocol names."""
    return list(PROTOCOL_REGISTRY.keys())

