"""
Clarify step-by-step service: guided learning mode.

Contains the streaming generator used by the router.
"""

import asyncio
import time
from typing import Any, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ai_backend.conversations.history import resolve_effective_history
from profu_logging.feature_logger import get_feature_logger
from ai_backend.routers.common import Message, PROMPTS
from ai_backend.streaming.sse import emit_done, emit_meta_ttft, emit_thinking, escape_sse_data, sse_data_line

from .graph import StepByStepLearningState, build_step_by_step_learning_graph

LOG = get_feature_logger(source="clarify_step_by_step")


async def stream_clarify_step_by_step(
    *,
    request_query: str,
    request_history: list[Message],
    conversation_id: int | None,
    user_id: UUID,
    llm: Any,
    supabase_client: Optional[Any] = None,
):
    """
    Async generator that streams step-by-step SSE messages.

    Keeps the existing wire format: [META]TTFT, optional [THINKING], escaped newlines, [DONE].
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

        if is_initial_query:
            graph = build_step_by_step_learning_graph(llm)
            initial_state: StepByStepLearningState = {
                "messages": [],
                "original_query": request_query,
                "prerequisites": [],
                "current_prerequisite_index": 0,
                "prerequisites_completed": False,
                "progress_preview_sent": False,
            }
            stream_queue: asyncio.Queue = asyncio.Queue()
            config = {"configurable": {"stream_queue": stream_queue}}
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
            system_prompt = PROMPTS["guided_learning"]["question_asker"]["system_prompt"]
            messages: list[Any] = [SystemMessage(content=system_prompt)]

            for msg in history:
                if msg.role == "user":
                    messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))

            messages.append(HumanMessage(content=request_query))

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

