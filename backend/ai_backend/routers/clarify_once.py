"""
Clarify Once Router - Direct answer mode for "N-am înțeles la clasă" feature.
Provides streaming chat interface where AI answers questions directly with full knowledge.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ai_backend.services.clarify_once.service import stream_clarify_once

from .common import (
    LangGraphChatModel,
    QueryRequest,
    get_current_user_id,
    get_llm,
    get_supabase_client,
)


router = APIRouter(prefix="/clarify", tags=["clarify_once"])


@router.post("/once-stream")
async def clarify_once_stream(
    request: QueryRequest,
    user_id: UUID = Depends(get_current_user_id),
    llm: LangGraphChatModel = Depends(get_llm),
    supabase=Depends(get_supabase_client),
):
    """
    Streaming endpoint for direct answers to student questions.
    Uses Gemini 2.0 Flash with LangChain for token streaming.
    
    Args:
        request: QueryRequest containing the user's query and conversation history
        
    Returns:
        StreamingResponse with Server-Sent Events (SSE) containing AI response tokens
    """
    return StreamingResponse(
        stream_clarify_once(
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
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        }
    )
