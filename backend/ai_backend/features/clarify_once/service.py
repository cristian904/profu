"""
Clarify-once service: direct answer mode.

Contains message assembly and SSE streaming logic used by the router.
"""

import asyncio
import time
from typing import Any, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ai_backend.conversations.history import resolve_effective_history
from ai_backend.logging.feature_logger import get_feature_logger
from ai_backend.routers.common import Message, PROMPTS
from ai_backend.streaming.sse import emit_done, emit_meta_ttft, escape_sse_data, sse_data_line

LOG = get_feature_logger(source="clarify_once")


async def stream_clarify_once(
    *,
    request_query: str,
    request_history: list[Message],
    conversation_id: int | None,
    user_id: UUID,
    llm: Any,
    supabase_client: Optional[Any] = None,
):
    """
    Async generator that streams clarify-once SSE messages.

    Args:
        request_query: Current user query.
        request_history: Client-provided history (fallback).
        conversation_id: Optional conversation id to load history from Supabase.
        user_id: Authenticated user id.
        llm: LangChain chat model that supports `astream`.
        supabase_client: Supabase client (optional).

    Yields:
        SSE-formatted strings (`data: ...\\n\\n`).
    """
    try:
        LOG.info("Stream started", user_id=user_id)
        if not request_query or not request_query.strip():
            LOG.warning("Empty query rejected", user_id=user_id)
            yield sse_data_line("Eroare: Întrebarea nu poate fi goală.")
            yield emit_done()
            return

        system_prompt = PROMPTS["clarify_chat"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        history = resolve_effective_history(
            user_id=user_id,
            request_history=request_history,
            conversation_id=conversation_id,
            supabase_client=supabase_client,
        )

        for msg in history:
            if msg.content and msg.content.strip():
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))

        messages.append(HumanMessage(content=request_query))

        start_time = time.time()
        first_token_received = False

        async for chunk in llm.astream(messages):
            if not getattr(chunk, "content", None):
                continue
            if not first_token_received:
                yield emit_meta_ttft(start_time)
                first_token_received = True
            yield sse_data_line(escape_sse_data(chunk.content))
            await asyncio.sleep(0.01)

        yield emit_done()
    except Exception as e:
        import traceback as tb

        LOG.error(str(e), user_id=user_id, traceback=tb.format_exc())
        yield sse_data_line(f"Eroare: {str(e)}")
        yield emit_done()

