"""
Clarify-once service: direct answer mode.

Contains message assembly and SSE streaming logic used by the router.
"""

import asyncio
import time
from typing import Any, Optional

from ai_backend.common.protocols import LangGraphChatModel
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ai_backend.common.conversation_history import resolve_effective_history
from ai_backend.common.models import Message
from ai_backend.langfuse.context import langfuse_trace_context, resolve_session_id
from ai_backend.langfuse.prompts import PromptComposer
from profu_logging.feature_logger import get_feature_logger
from ai_backend.common.streaming.sse import (
    SSE_GENERIC_USER_ERROR,
    emit_done,
    emit_meta_ttft,
    escape_sse_data,
    sse_data_line,
)
from ai_backend.services.clarify_guardrails.context import format_messages_for_guardrails_context
from ai_backend.services.clarify_once.graph import get_compiled_clarify_once_graph

LOG = get_feature_logger(source="clarify_once")


async def stream_clarify_once(
    *,
    request_query: str,
    request_history: list[Message],
    conversation_id: int | None,
    user_id: UUID,
    llm: LangGraphChatModel,
    composer: PromptComposer,
    supabase_client: Optional[Any] = None,
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """
    Async generator that streams clarify-once SSE messages.

    Args:
        request_query: Current user query.
        request_history: Client-provided history (fallback).
        conversation_id: Optional conversation id to load history from Supabase.
        user_id: Authenticated user id.
        llm: LangChain chat model that supports `astream`.
        composer: PromptComposer for loading system prompts.
        supabase_client: Supabase client (optional).
        trace_id: Optional Langfuse trace id (32-char hex).
        session_id: Optional Langfuse session id for grouping traces.

    Yields:
        SSE-formatted strings (`data: ...\\n\\n`).

    Flow:
        LangGraph runs a guardrails structured check, then either streams the clarify reply
        or a short blocked message (Romanian). Uses one extra LLM call when allowed.
    """
    try:
        LOG.info("Stream started", user_id=user_id)
        if not request_query or not request_query.strip():
            LOG.warning("Empty query rejected", user_id=user_id)
            yield sse_data_line("Eroare: Întrebarea nu poate fi goală.")
            yield emit_done()
            return

        system_prompt = composer.get("clarify_chat")
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

        guardrails_context = format_messages_for_guardrails_context(history)

        start_time = time.time()
        first_content_chunk = True

        async with langfuse_trace_context(
            trace_id=trace_id,
            session_id=resolve_session_id(session_id, conversation_id),
            user_id=str(user_id),
            name="clarify_once",
            tags=["clarify"],
        ) as langfuse_config:
            graph = get_compiled_clarify_once_graph(llm, composer)
            stream_queue: asyncio.Queue = asyncio.Queue()
            config = {
                "configurable": {"stream_queue": stream_queue, "user_id": str(user_id)},
                **langfuse_config,
            }
            initial_state = {
                "messages": messages,
                "request_query": request_query,
                "guardrails_context": guardrails_context,
                "guardrails_allowed": False,
                "guardrails_block_message_ro": "",
            }
            invoke_task = asyncio.create_task(graph.ainvoke(initial_state, config=config))

            stream_timeout = 1.0
            while True:
                try:
                    item = await asyncio.wait_for(stream_queue.get(), timeout=stream_timeout)
                except asyncio.TimeoutError:
                    if invoke_task.done():
                        if invoke_task.exception() is not None:
                            raise invoke_task.exception()
                        break
                    continue

                if item is None:
                    break
                if first_content_chunk:
                    yield emit_meta_ttft(start_time)
                    first_content_chunk = False
                yield sse_data_line(escape_sse_data(str(item)))
                await asyncio.sleep(0.01)

            await invoke_task

        yield emit_done()
    except Exception as e:
        import traceback as tb

        LOG.error(str(e), user_id=user_id, traceback=tb.format_exc())
        yield sse_data_line(escape_sse_data(SSE_GENERIC_USER_ERROR))
        yield emit_done()

