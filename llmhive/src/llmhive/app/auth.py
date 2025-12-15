"""Authentication utilities for LLMHive API.

This module provides authentication dependencies for FastAPI endpoints.
Supports API key authentication via header.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)

# Security: Accept multiple header names for the same API key
API_KEY_HEADER_NAMES = ["x-api-key", "api-key", "api_key", "API_KEY", "X-API-KEY"]


def _extract_api_key(request: Request) -> Optional[str]:
    """Extract API key from common header variants."""
    for name in API_KEY_HEADER_NAMES:
        if name.lower() in request.headers:
            return request.headers.get(name)
    return None


def verify_api_key(request: Request) -> str:
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
    
    provided_key = _extract_api_key(request)
    
    # API_KEY is configured, so authentication is required
    if not provided_key:
        logger.warning("API key required but header not provided")
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
def optional_api_key(request: Request) -> str:
    """Optional API key verification (doesn't fail if key is missing).
    
    Useful for endpoints that work with or without authentication.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        "authenticated" if valid key provided, "anonymous" otherwise
    """
    try:
        provided_key = _extract_api_key(request)
        return verify_api_key(request) if provided_key else "anonymous"
    except HTTPException:
        # If auth fails but it's optional, return anonymous
        return "anonymous"
