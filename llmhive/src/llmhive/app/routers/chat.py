"""Chat API router for LLMHive.

Enhancement-6: Safe Mode validation and orchestrator metrics integration.

Safe Mode Features:
- Empty prompt rejection with structured error
- Abusive/disallowed content detection and blocking
- Input sanitization for mild issues
- Output filtering and content moderation
- Sanitization flag in response
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import verify_api_key
from ..models.orchestration import ChatRequest, ChatResponse
from ..services.orchestrator_adapter import run_orchestration

logger = logging.getLogger(__name__)

# Define router with /v1 prefix
router = APIRouter(prefix="/v1", tags=["chat"])

# Try to import guardrails for Safe Mode
try:
    from ..guardrails import (
        check_output_policy,
        enforce_output_policy,
        assess_query_risk,
        redact_sensitive_info,
        get_safety_validator,
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    GUARDRAILS_AVAILABLE = False
    logger.info("Guardrails not available, Safe Mode disabled")


# ==============================================================================
# Structured Error Response
# ==============================================================================

class ErrorDetail(BaseModel):
    """Structured error detail for API responses."""
    code: str
    message: str
    recoverable: bool = True
    details: Optional[Dict[str, Any]] = None


def create_error_response(code: str, message: str, recoverable: bool = True, details: Optional[Dict] = None) -> Dict:
    """Create a structured error response."""
    return {
        "error": {
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "details": details or {}
        }
    }


# ==============================================================================
# Safe Mode Input Validation
# ==============================================================================

def validate_and_sanitize_input(prompt: str, safe_mode: bool) -> tuple[str, bool, Optional[str]]:
    """
    Validate and sanitize input prompt for Safe Mode.
    
    Args:
        prompt: The user prompt to validate
        safe_mode: Whether safe mode is enabled
        
    Returns:
        Tuple of (sanitized_prompt, is_allowed, rejection_reason)
    """
    if not GUARDRAILS_AVAILABLE or not safe_mode:
        return prompt, True, None
    
    # Step 1: Check for empty or whitespace-only prompts
    if not prompt or not prompt.strip():
        return "", False, "Prompt cannot be empty"
    
    # Step 2: Assess query risk for harmful content
    risk = assess_query_risk(prompt)
    if risk.blocked:
        return "", False, "Sorry, your prompt violates our usage policies and cannot be processed."
    
    # Step 3: Sanitize sensitive information (PII)
    redaction = redact_sensitive_info(prompt)
    sanitized_prompt = redaction.redacted_text
    
    # Log if sanitization occurred
    if redaction.redaction_count > 0:
        logger.info(
            "Input sanitized: %d items redacted (types: %s)",
            redaction.redaction_count,
            [r[2].value for r in redaction.redactions]
        )
    
    return sanitized_prompt, True, None


def filter_and_sanitize_output(message: str, safe_mode: bool) -> tuple[str, bool, list]:
    """
    Filter and sanitize model output for Safe Mode.
    
    Args:
        message: The model output to filter
        safe_mode: Whether safe mode is enabled
        
    Returns:
        Tuple of (filtered_message, was_filtered, issues)
    """
    if not GUARDRAILS_AVAILABLE or not safe_mode:
        return message, False, []
    
    # Use safety validator for comprehensive output validation
    validator = get_safety_validator()
    sanitized_output, is_safe = validator.validate_output(message)
    
    issues = []
    was_filtered = sanitized_output != message
    
    if was_filtered:
        # Get specific policy violations for logging
        policy_check = check_output_policy(message)
        if policy_check.violations:
            issues = [f"{v.violation_type}" for v in policy_check.violations]
    
    # If output is critically unsafe, return refusal message
    if not is_safe:
        return (
            "I apologize, but I cannot provide this response as it may "
            "contain content that violates our safety policies.",
            True,
            ["critical_violation"]
        )
    
    return sanitized_output, was_filtered, issues


# ==============================================================================
# Main Chat Endpoint
# ==============================================================================

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_endpoint(
    payload: ChatRequest,
    user: str = Depends(verify_api_key),
) -> ChatResponse:
    """
    Chat orchestration endpoint.
    
    Accepts a ChatRequest with prompt, reasoning mode, domain pack, agent mode,
    tuning options, metadata, and conversation history.
    
    Enhancement-5: Stricter input validation via Pydantic models.
    Enhancement-6: Safe Mode filtering and error metrics tracking.
    
    Safe Mode (when enabled):
    - Rejects empty prompts with structured error
    - Blocks harmful/abusive content
    - Sanitizes sensitive information (PII)
    - Filters policy-violating output
    - Includes safe_mode_filtered flag when content is modified
    
    Returns a ChatResponse with the final answer and orchestration artifacts.
    """
    safe_mode = payload.orchestration.safe_mode_validator
    dev_mode = payload.orchestration.dev_mode
    
    try:
        logger.info(
            "Chat request received: prompt_length=%d, reasoning_mode=%s, domain=%s, agent_mode=%s, safe_mode=%s, dev_mode=%s",
            len(payload.prompt),
            payload.reasoning_mode.value,
            payload.domain_pack.value,
            payload.agent_mode.value,
            safe_mode,
            dev_mode,
        )
        
        # Dev mode trace logging
        if dev_mode:
            try:
                from ..orchestration.dev_mode import log_orchestration_step
                session_id = payload.metadata.chat_id or "default"
                log_orchestration_step(session_id, "request_received", f"Processing prompt ({len(payload.prompt)} chars)")
            except Exception:
                pass
        
        # Enhancement-5: Input validation and sanitization (Safe Mode)
        sanitized_prompt, is_allowed, rejection_reason = validate_and_sanitize_input(
            payload.prompt, safe_mode
        )
        
        if not is_allowed:
            logger.warning("Query rejected by Safe Mode: %s", rejection_reason)
            # Record error metric
            try:
                from ..api.orchestrator_metrics import record_orchestrator_error
                record_orchestrator_error("input_blocked")
            except Exception:
                pass
            
            # Return structured error response
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_response(
                    code="InvalidRequest",
                    message=rejection_reason or "Request blocked by safety policy",
                    recoverable=False,
                )
            )
        
        # Update payload with sanitized prompt if modified
        if sanitized_prompt != payload.prompt:
            payload = payload.model_copy(update={"prompt": sanitized_prompt})
        
        # Run orchestration
        response = await run_orchestration(payload)
        
        # Enhancement-6: Apply Safe Mode output filtering
        filtered_message, was_filtered, filter_issues = filter_and_sanitize_output(
            response.message, safe_mode
        )
        
        if was_filtered:
            logger.info("Output filtered by Safe Mode: %s", filter_issues)
            # Update response with filtered content and flag
            response = ChatResponse(
                message=filtered_message,
                models_used=response.models_used,
                reasoning_mode=response.reasoning_mode,
                reasoning_method=response.reasoning_method,
                domain_pack=response.domain_pack,
                agent_mode=response.agent_mode,
                used_tuning=response.used_tuning,
                metadata=response.metadata,
                tokens_used=response.tokens_used,
                latency_ms=response.latency_ms,
                agent_traces=response.agent_traces,
                extra={
                    **response.extra,
                    "safe_mode_filtered": True,
                    "filter_issues": filter_issues,
                },
            )
        
        logger.info(
            "Chat response generated: message_length=%d, latency=%dms, filtered=%s",
            len(response.message),
            response.latency_ms or 0,
            was_filtered,
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        # Log orchestrator error metric
        try:
            from ..api.orchestrator_metrics import record_orchestrator_error
            record_orchestrator_error("internal")
        except Exception:
            pass
        
        # Return user-friendly error message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                code="InternalError",
                message="Oops, something went wrong. Please try again.",
                recoverable=True,
            )
        ) from exc

