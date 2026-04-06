"""
LangGraph nodes for clarify-once (streamed answer after guardrails).
"""

import asyncio

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.langfuse.context import llm_config
from ai_backend.services.clarify_once.state import ClarifyOnceGraphState


def make_stream_clarify_answer_node(llm: LangGraphChatModel):
    """
    Factory: stream the main clarify reply to ``configurable.stream_queue`` using state messages.

    Args:
        llm: Chat model supporting ``astream``.

    Returns:
        Async node that appends the assistant message to state and streams tokens.
    """

    async def stream_clarify_answer(
        state: ClarifyOnceGraphState, config: RunnableConfig | None = None
    ) -> ClarifyOnceGraphState:
        """
        Run the tutor LLM over ``state['messages']`` and push chunks to the SSE queue.

        Args:
            state: Graph state with assembled LangChain messages.
            config: Runnable config (stream_queue, Langfuse callbacks).

        Returns:
            State update with the final ``AIMessage`` in ``messages``.
        """
        config = config or {}
        stream_queue: asyncio.Queue | None = (config.get("configurable") or {}).get("stream_queue")
        messages = list(state.get("messages") or [])

        if stream_queue is not None:
            accumulated: list[str] = []
            async for chunk in llm.astream(messages, config=llm_config(config)):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
        else:
            response = await llm.ainvoke(messages, config=llm_config(config))

        return {**state, "messages": [response]}

    return stream_clarify_answer
