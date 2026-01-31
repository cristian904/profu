"""
Clarify Once Router - Direct answer mode for "N-am înțeles la clasă" feature.
Provides streaming chat interface where AI answers questions directly with full knowledge.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
import time
import json

from .common import get_llm, QueryRequest, PROMPTS


router = APIRouter(prefix="/clarify", tags=["clarify_once"])


@router.post("/once-stream")
async def clarify_once_stream(request: QueryRequest):
    """
    Streaming endpoint for direct answers to student questions.
    Uses Gemini 2.0 Flash with LangChain for token streaming.
    
    Args:
        request: QueryRequest containing the user's query and conversation history
        
    Returns:
        StreamingResponse with Server-Sent Events (SSE) containing AI response tokens
    """
    async def generate():
        try:
            # Validate query is not empty
            if not request.query or not request.query.strip():
                yield f"data: Eroare: Întrebarea nu poate fi goală.\n\n"
                yield "data: [DONE]\n\n"
                return
            
            llm = get_llm()
            
            # Get system prompt from YAML configuration
            system_prompt = PROMPTS['clarify_chat']['system_prompt']

            # Build message history for conversation context
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history (filter out empty messages)
            for msg in request.history:
                if msg.content and msg.content.strip():  # Only add non-empty messages
                    if msg.role == "user":
                        messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        messages.append(AIMessage(content=msg.content))
            
            # Add current user query
            messages.append(HumanMessage(content=request.query))
            
            # Track time to first token
            start_time = time.time()
            first_token_received = False
            
            # Stream the response
            async for chunk in llm.astream(messages):
                if chunk.content:
                    # Send time to first token metadata on first chunk
                    if not first_token_received:
                        time_to_first_token = time.time() - start_time
                        metadata = json.dumps({"ttft": round(time_to_first_token, 3)})
                        yield f"data: [META]{metadata}\n\n"
                        first_token_received = True
                    
                    # Escape newlines for SSE format (replace \n with placeholder)
                    content = chunk.content.replace('\n', '\\n')
                    # Send in SSE format
                    yield f"data: {content}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for smoother streaming
            
            # Signal completion
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_message = f"Eroare: {str(e)}"
            yield f"data: {error_message}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        }
    )
