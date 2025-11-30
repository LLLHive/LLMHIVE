"""Security and Compliance for LLMHive.

This module provides:
- Data retention policies
- GDPR compliance (data deletion, export)
- Security hardening utilities
- Audit logging
- Role-based access control
"""
from __future__ import annotations

# Data retention
try:
    from .data_retention import (
        DataRetentionManager,
        RetentionPolicy,
        DataCategory,
        get_retention_manager,
    )
    DATA_RETENTION_AVAILABLE = True
except ImportError:
    DATA_RETENTION_AVAILABLE = False

# GDPR compliance
try:
    from .gdpr import (
        GDPRManager,
        DataSubjectRequest,
        RequestType,
        export_user_data,
        delete_user_data,
    )
    GDPR_AVAILABLE = True
except ImportError:
    GDPR_AVAILABLE = False

# Security hardening
try:
    from .hardening import (
        SecurityManager,
        sanitize_input,
        validate_request,
        apply_security_headers,
    )
    HARDENING_AVAILABLE = True
except ImportError:
    HARDENING_AVAILABLE = False

__all__ = [
    "DATA_RETENTION_AVAILABLE",
    "GDPR_AVAILABLE",
    "HARDENING_AVAILABLE",
]

if DATA_RETENTION_AVAILABLE:
    __all__.extend([
        "DataRetentionManager",
        "RetentionPolicy",
        "DataCategory",
        "get_retention_manager",
    ])

if GDPR_AVAILABLE:
    __all__.extend([
        "GDPRManager",
        "DataSubjectRequest",
        "RequestType",
        "export_user_data",
        "delete_user_data",
    ])

if HARDENING_AVAILABLE:
    __all__.extend([
        "SecurityManager",
        "sanitize_input",
        "validate_request",
        "apply_security_headers",
    ])

