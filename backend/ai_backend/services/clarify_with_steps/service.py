"""
Clarify-with-steps service: guided learning (step-by-step) mode.

Contains the streaming generator used by the router.
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
    emit_thinking,
    escape_sse_data,
    sse_data_line,
)

from .graph import StepByStepLearningState, build_step_by_step_learning_graph

LOG = get_feature_logger(source="clarify_step_by_step")


async def stream_clarify_step_by_step(
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
    Async generator that streams step-by-step SSE messages.

    Keeps the existing wire format: [META]TTFT, optional [THINKING], escaped newlines, [DONE].

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
    """
    try:
        LOG.info("Stream started", user_id=user_id)
        start_time = time.time()
        first_token_received = False

        history = resolve_effective_history(
            user_id=user_id,
            request_history=request_history,
            conversation_id=conversation_id,
            supabase_client=supabase_client,
        )

        is_initial_query = len(history) == 0

        async with langfuse_trace_context(
            trace_id=trace_id,
            session_id=resolve_session_id(session_id, conversation_id),
            user_id=str(user_id),
            name="clarify_with_steps",
            tags=["clarify", "step_by_step"],
        ) as langfuse_config:
            if is_initial_query:
                graph = build_step_by_step_learning_graph(llm, composer)
                initial_state: StepByStepLearningState = {
                    "messages": [],
                    "original_query": request_query,
                    "prerequisites": [],
                    "current_prerequisite_index": 0,
                    "prerequisites_completed": False,
                    "progress_preview_sent": False,
                }
                stream_queue: asyncio.Queue = asyncio.Queue()
                # Merge langfuse callbacks into the LangGraph config
                config = {
                    "configurable": {"stream_queue": stream_queue},
                    **langfuse_config,
                }
                invoke_task = asyncio.create_task(graph.ainvoke(initial_state, config=config))

                first_content_chunk = True
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
                    if item == "[THINKING]":
                        yield emit_thinking()
                        continue

                    if first_content_chunk:
                        yield emit_meta_ttft(start_time)
                        first_content_chunk = False
                    yield sse_data_line(escape_sse_data(str(item)))

                await invoke_task
            else:
                system_prompt = composer.get("guided_learning.question_asker")
                messages: list[Any] = [SystemMessage(content=system_prompt)]

                for msg in history:
                    if msg.role == "user":
                        messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        messages.append(AIMessage(content=msg.content))

                messages.append(HumanMessage(content=request_query))

                async for chunk in llm.astream(messages, config=langfuse_config):
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
        yield sse_data_line(escape_sse_data(SSE_GENERIC_USER_ERROR))
        yield emit_done()

