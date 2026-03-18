"""
Clarify Step by Step Router - Step-by-step interactive learning mode.
Uses LangGraph to guide students through prerequisites before explaining the main concept.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from ai_backend.features.clarify_steps.service import stream_clarify_step_by_step

from .common import (
    get_llm,
    get_supabase_client,
    QueryRequest,
    get_current_user_id,
)


router = APIRouter(prefix="/clarify", tags=["clarify_step_by_step"])
from ai_backend.features.clarify_steps.service import stream_clarify_step_by_step


@router.post("/step-by-step-stream")
async def clarify_step_by_step_stream(
    request: QueryRequest,
    user_id: UUID = Depends(get_current_user_id),
    llm=Depends(get_llm),
    supabase=Depends(get_supabase_client),
):
    """
    Streaming endpoint for step-by-step guided learning.
    Uses LangGraph to guide students through prerequisites before explaining the main concept.
    
    Args:
        request: QueryRequest containing the user's query and conversation history
        
    Returns:
        StreamingResponse with Server-Sent Events (SSE) containing AI response tokens
    """
    return StreamingResponse(
        stream_clarify_step_by_step(
            request_query=request.query,
            request_history=request.history,
            conversation_id=request.conversation_id,
            user_id=user_id,
            llm=llm,
            supabase_client=supabase,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )