"""Code execution endpoint for MCP 2 sandbox."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..mcp2.sandbox import CodeSandbox, SandboxConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["execute"])


class ExecuteRequest(BaseModel):
    """Request model for code execution."""
    
    code: str = Field(..., description="Code to execute")
    language: str = Field(default="python", description="Programming language")
    session_token: str = Field(..., description="Session token for sandbox isolation")


class ExecuteResponse(BaseModel):
    """Response model for code execution."""
    
    success: bool
    output: str = Field(default="", description="Execution output")
    error: str | None = Field(default=None, description="Error message if execution failed")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


@router.post("/execute/python", response_model=ExecuteResponse, status_code=status.HTTP_200_OK,
             dependencies=[Depends(verify_api_key)])
async def execute_python(
    payload: ExecuteRequest,
) -> ExecuteResponse:
    """
    Execute Python code in MCP 2 sandbox.
    
    This endpoint provides secure Python code execution with:
    - Process isolation
    - Resource limits (timeout, memory, CPU)
    - Security validation
    - Restricted imports
    """
    try:
        if payload.language != "python":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language {payload.language} not supported. Only 'python' is supported.",
            )
        
        logger.info(
            "Executing Python code: session=%s, code_length=%d",
            payload.session_token[:8],
            len(payload.code),
        )
        
        # Initialize sandbox
        config = SandboxConfig(
            timeout_seconds=5.0,
            memory_limit_mb=512,
            cpu_limit_percent=50.0,
            allow_network=False,
        )
        sandbox = CodeSandbox(config, payload.session_token)
        
        # Validate and execute code
        validation_result = sandbox._validate_code_ast(payload.code)
        if not validation_result.get("safe", True):
            return ExecuteResponse(
                success=False,
                error=f"Code validation failed: {validation_result.get('reason', 'Unsafe code detected')}",
                metadata={"validation_result": validation_result},
            )
        
        # Execute code
        result = await sandbox.execute_async(payload.code)
        
        if result.get("success", False):
            return ExecuteResponse(
                success=True,
                output=result.get("output", ""),
                metadata={
                    "execution_time_ms": result.get("execution_time_ms", 0),
                    "tokens_used": result.get("tokens_used", 0),
                },
            )
        else:
            return ExecuteResponse(
                success=False,
                error=result.get("error", "Execution failed"),
                metadata={"execution_result": result},
            )
            
    except Exception as exc:
        logger.exception("Python execution error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(exc)}",
        ) from exc

