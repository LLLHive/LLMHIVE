"""Clarification API router for LLMHive.

This router handles the clarifying questions flow:
1. POST /v1/clarify - Analyze a query and get clarification questions
2. POST /v1/clarify/respond - Submit clarification responses
3. POST /v1/chat/clarified - Chat with clarification responses included

The clarification flow improves answer quality by:
- Asking up to 3 focused questions about ambiguous queries
- Asking 3 questions about preferred answer format (detail, format, tone)
- Refining the query based on user responses
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..models.orchestration import (
    ChatRequest,
    ChatResponse,
    ClarificationRequest,
    ClarificationResponse,
    ClarificationStatus as APIClarificationStatus,
    ChatRequestWithClarification,
    ChatResponseWithClarification,
    AnswerPreferences,
)

# Import internal status enum
try:
    from ..orchestration.clarification_manager import ClarificationStatus as InternalStatus
except ImportError:
    InternalStatus = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["clarification"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class ClarifyQueryRequest(BaseModel):
    """Request to analyze a query for clarification needs."""
    prompt: str = Field(..., description="The user's query to analyze")
    skip_preferences: bool = Field(
        default=False,
        description="Skip preference questions (useful for follow-up queries)"
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional conversation context"
    )


class ClarifyQueryResponse(BaseModel):
    """Response with clarification questions or confirmation that none are needed."""
    needs_clarification: bool = Field(..., description="Whether clarification is needed")
    clarification_request: Optional[ClarificationRequest] = Field(
        default=None,
        description="Clarification questions if needed"
    )
    message: str = Field(..., description="Status message")


class ProcessClarificationRequest(BaseModel):
    """Request to process clarification responses and get refined query."""
    original_query: str = Field(..., description="Original query")
    clarification_response: ClarificationResponse = Field(
        ...,
        description="User's responses to clarification questions"
    )


class ProcessClarificationResponse(BaseModel):
    """Response with refined query and preferences."""
    refined_query: str = Field(..., description="The refined, clarified query")
    answer_preferences: AnswerPreferences = Field(..., description="Parsed answer preferences")
    clarification_context: str = Field(
        default="",
        description="Summary of clarifications for context"
    )
    was_clarified: bool = Field(..., description="Whether the query was modified")


# ==============================================================================
# Helper Functions
# ==============================================================================

def _get_clarification_manager():
    """Get or create ClarificationManager instance."""
    try:
        from ..orchestration.clarification_manager import ClarificationManager
        from ..orchestrator import Orchestrator
        
        # Get providers from orchestrator
        orch = Orchestrator()
        
        return ClarificationManager(
            providers=orch.providers,
            ambiguity_threshold=0.4,
            max_query_questions=3,
            always_ask_preferences=True,
        )
    except ImportError as e:
        logger.error("Failed to import ClarificationManager: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clarification feature not available"
        )


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post(
    "/clarify",
    response_model=ClarifyQueryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def analyze_for_clarification(
    request: ClarifyQueryRequest,
) -> ClarifyQueryResponse:
    """
    Analyze a query and generate clarification questions if needed.
    
    This endpoint:
    1. Analyzes the query for ambiguity
    2. Generates up to 3 clarifying questions about the query
    3. Includes 3 preference questions (detail, format, tone)
    
    Use this before sending a chat request to improve response quality.
    """
    logger.info(
        "Clarification analysis requested: prompt_length=%d",
        len(request.prompt),
    )
    
    manager = _get_clarification_manager()
    
    try:
        clarification_request = await manager.analyze_and_generate_questions(
            request.prompt,
            context=request.context,
            skip_preferences=request.skip_preferences,
        )
        
        # Compare status using value string
        needs_clarification = clarification_request.status.value != "not_needed"
        
        if needs_clarification:
            message = (
                f"We have {len(clarification_request.query_questions)} clarifying questions "
                f"and {len(clarification_request.preference_questions)} preference questions."
            )
        else:
            message = "No clarification needed. You can proceed with the query."
        
        logger.info(
            "Clarification analysis complete: needs_clarification=%s, query_questions=%d",
            needs_clarification,
            len(clarification_request.query_questions),
        )
        
        # Convert internal format to API format
        return ClarifyQueryResponse(
            needs_clarification=needs_clarification,
            clarification_request=ClarificationRequest(
                status=APIClarificationStatus(clarification_request.status.value),
                original_query=clarification_request.original_query,
                ambiguity_summary=clarification_request.ambiguity_summary,
                query_questions=[
                    {
                        "id": q.id,
                        "question": q.question,
                        "category": q.category,
                        "options": q.options,
                        "default_answer": q.default_answer,
                        "required": q.required,
                    }
                    for q in clarification_request.query_questions
                ],
                preference_questions=[
                    {
                        "id": q.id,
                        "question": q.question,
                        "category": q.category,
                        "options": q.options,
                        "default_answer": q.default_answer,
                        "required": q.required,
                    }
                    for q in clarification_request.preference_questions
                ],
            ) if needs_clarification else None,
            message=message,
        )
        
    except Exception as exc:
        logger.exception("Clarification analysis error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze query: {str(exc)}",
        )


@router.post(
    "/clarify/respond",
    response_model=ProcessClarificationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def process_clarification_responses(
    request: ProcessClarificationRequest,
) -> ProcessClarificationResponse:
    """
    Process user's clarification responses and return refined query.
    
    This endpoint:
    1. Takes the user's answers to clarification questions
    2. Refines the original query with the clarified information
    3. Parses preference answers into usable settings
    
    The refined query can then be used in a /v1/chat request.
    """
    logger.info(
        "Processing clarification responses: query_answers=%d, preference_answers=%d",
        len(request.clarification_response.query_answers),
        len(request.clarification_response.preference_answers),
    )
    
    manager = _get_clarification_manager()
    
    try:
        # Create a minimal request object
        from ..orchestration.clarification_manager import (
            ClarificationRequest as InternalRequest,
            ClarificationResponse as InternalResponse,
            ClarificationQuestion,
        )
        
        # Build internal request (we need the original questions for context)
        internal_request = InternalRequest(
            original_query=request.original_query,
            query_questions=[
                ClarificationQuestion(
                    id=qid,
                    question="",  # Not needed for processing
                    category="query",
                )
                for qid in request.clarification_response.query_answers.keys()
            ],
        )
        
        # Build internal response
        internal_response = InternalResponse(
            query_answers=request.clarification_response.query_answers,
            preference_answers=request.clarification_response.preference_answers,
            skipped=request.clarification_response.skipped,
        )
        
        # Process
        result = await manager.process_responses(internal_request, internal_response)
        
        logger.info(
            "Clarification processed: was_clarified=%s",
            result.was_clarified,
        )
        
        # Convert preferences to API model
        from ..orchestration.clarification_manager import (
            DetailLevel as InternalDetailLevel,
            AnswerFormat as InternalFormat,
            AnswerTone as InternalTone,
        )
        from ..models.orchestration import DetailLevel, AnswerFormat, AnswerTone
        
        api_preferences = AnswerPreferences(
            detail_level=DetailLevel(result.answer_preferences.detail_level.value),
            format=AnswerFormat(result.answer_preferences.format.value),
            tone=AnswerTone(result.answer_preferences.tone.value),
            max_length=result.answer_preferences.max_length,
            include_examples=result.answer_preferences.include_examples,
            include_citations=result.answer_preferences.include_citations,
            custom_instructions=result.answer_preferences.custom_instructions,
        )
        
        return ProcessClarificationResponse(
            refined_query=result.refined_query,
            answer_preferences=api_preferences,
            clarification_context=result.clarification_context,
            was_clarified=result.was_clarified,
        )
        
    except Exception as exc:
        logger.exception("Clarification processing error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process clarifications: {str(exc)}",
        )


@router.post(
    "/chat/clarified",
    response_model=ChatResponseWithClarification,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def chat_with_clarification(
    request: ChatRequestWithClarification,
) -> ChatResponseWithClarification:
    """
    Chat endpoint with integrated clarification flow.
    
    This endpoint combines clarification and chat:
    1. If clarification_response is provided, processes it and answers
    2. If skip_clarification is True, skips directly to answering
    3. Otherwise, checks if clarification is needed and returns questions
    
    This is the recommended endpoint for a seamless clarification experience.
    """
    logger.info(
        "Clarified chat request: prompt_length=%d, has_clarification=%s, skip=%s",
        len(request.prompt),
        request.clarification_response is not None,
        request.skip_clarification,
    )
    
    manager = _get_clarification_manager()
    
    try:
        # Case 1: Clarification responses provided - process and answer
        if request.clarification_response is not None:
            from ..orchestration.clarification_manager import (
                ClarificationRequest as InternalRequest,
                ClarificationResponse as InternalResponse,
                ClarificationQuestion,
            )
            
            # Process clarification
            internal_request = InternalRequest(
                original_query=request.prompt,
                query_questions=[
                    ClarificationQuestion(id=qid, question="", category="query")
                    for qid in request.clarification_response.query_answers.keys()
                ],
            )
            
            internal_response = InternalResponse(
                query_answers=request.clarification_response.query_answers,
                preference_answers=request.clarification_response.preference_answers,
                skipped=request.clarification_response.skipped,
            )
            
            result = await manager.process_responses(internal_request, internal_response)
            
            # Run orchestration with refined query and preferences
            from ..services.orchestrator_adapter import run_orchestration
            
            # Update request with refined query
            refined_request = ChatRequest(
                prompt=result.refined_query,
                models=request.models,
                reasoning_mode=request.reasoning_mode,
                reasoning_method=request.reasoning_method,
                domain_pack=request.domain_pack,
                agent_mode=request.agent_mode,
                tuning=request.tuning,
                orchestration=request.orchestration,
                metadata=request.metadata,
                history=request.history,
            )
            
            # Add preferences to orchestration settings
            if refined_request.orchestration:
                style_guidelines = result.answer_preferences.to_style_guidelines()
                # Store in extra for downstream use
                if not hasattr(refined_request, '_answer_preferences'):
                    refined_request._answer_preferences = result.answer_preferences
            
            response = await run_orchestration(refined_request)
            
            # Apply preference-based refinement to the response
            from ..refiner import AnswerRefiner
            refiner = AnswerRefiner()
            refined_message = await refiner.refine_with_preferences(
                response.message,
                result.answer_preferences,
            )
            response.message = refined_message
            
            return ChatResponseWithClarification(
                needs_clarification=False,
                clarification_request=None,
                response=response,
            )
        
        # Case 2: Skip clarification - go straight to answering
        if request.skip_clarification:
            from ..services.orchestrator_adapter import run_orchestration
            
            response = await run_orchestration(request)
            
            return ChatResponseWithClarification(
                needs_clarification=False,
                clarification_request=None,
                response=response,
            )
        
        # Case 3: Check if clarification is needed
        clarification_request = await manager.analyze_and_generate_questions(
            request.prompt,
            history=[
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in (request.history or [])
            ],
        )
        
        needs_clarification = clarification_request.status.value != "not_needed"
        
        if needs_clarification:
            # Return clarification questions
            return ChatResponseWithClarification(
                needs_clarification=True,
                clarification_request=ClarificationRequest(
                    status=APIClarificationStatus(clarification_request.status.value),
                    original_query=clarification_request.original_query,
                    ambiguity_summary=clarification_request.ambiguity_summary,
                    query_questions=[
                        {
                            "id": q.id,
                            "question": q.question,
                            "category": q.category,
                            "options": q.options,
                            "default_answer": q.default_answer,
                            "required": q.required,
                        }
                        for q in clarification_request.query_questions
                    ],
                    preference_questions=[
                        {
                            "id": q.id,
                            "question": q.question,
                            "category": q.category,
                            "options": q.options,
                            "default_answer": q.default_answer,
                            "required": q.required,
                        }
                        for q in clarification_request.preference_questions
                    ],
                ),
                response=None,
            )
        else:
            # No clarification needed - proceed with chat
            from ..services.orchestrator_adapter import run_orchestration
            
            response = await run_orchestration(request)
            
            return ChatResponseWithClarification(
                needs_clarification=False,
                clarification_request=None,
                response=response,
            )
        
    except Exception as exc:
        logger.exception("Clarified chat error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(exc)}",
        )

