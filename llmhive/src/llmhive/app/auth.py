"""Authentication utilities for LLMHive API.

This module provides authentication dependencies for FastAPI endpoints.
Supports API key authentication via header.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# Security: API key header name
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(provided_key: str = Depends(API_KEY_HEADER)) -> str:
    """
    Verify API key from request header.
    
    Security behavior:
    - If API_KEY environment variable is not set → allows all requests (dev mode)
    - If API_KEY is set → requires X-API-Key header to match, raises 401 on mismatch
    
    Args:
        provided_key: API key from X-API-Key header (may be None if header not sent)
        
    Returns:
        "unauthenticated-allowed" if no API_KEY configured (dev mode)
        "authenticated" if key is valid
        
    Raises:
        HTTPException(401): If API_KEY is configured but header is missing or invalid
    """
    # Read API_KEY from environment (set in Cloud Run)
    expected = os.environ.get("API_KEY")
    
    # If no API_KEY is configured, allow all requests (dev mode)
    if not expected:
        logger.debug("No API_KEY configured, allowing request (dev mode)")
        return "unauthenticated-allowed"
    
    # API_KEY is configured, so authentication is required
    if not provided_key:
        logger.warning("API key required but X-API-Key header not provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    # Verify the API key matches
    if provided_key != expected:
        logger.warning("Invalid API key provided (mismatch)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    logger.debug("API key authentication successful")
    return "authenticated"


# Optional authentication dependency (doesn't fail if key missing)
def optional_api_key(provided_key: Optional[str] = Depends(API_KEY_HEADER)) -> str:
    """Optional API key verification (doesn't fail if key is missing).
    
    Useful for endpoints that work with or without authentication.
    
    Args:
        provided_key: API key from X-API-Key header (optional)
        
    Returns:
        "authenticated" if valid key provided, "anonymous" otherwise
    """
    try:
        return verify_api_key(provided_key) if provided_key else "anonymous"
    except HTTPException:
        # If auth fails but it's optional, return anonymous
        return "anonymous"
