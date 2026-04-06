"""
LangGraph node factories for clarify guardrails (evaluate + emit blocked message).
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig

from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.langfuse.prompts import PromptComposer
from ai_backend.services.clarify_guardrails.constants import CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO
from ai_backend.services.clarify_guardrails.evaluator import evaluate_clarify_guardrails


def make_clarify_guardrails_node(
    llm: LangGraphChatModel,
    composer: PromptComposer,
    *,
    query_state_key: str,
    context_state_key: str = "guardrails_context",
):
    """
    Factory: first graph node — structured guardrails check.

    Args:
        llm: Injected chat model.
        composer: Prompt composer.
        query_state_key: State key for the current user message (e.g. ``request_query`` or ``original_query``).
        context_state_key: State key for optional transcript string.

    Returns:
        Async node callable updating ``guardrails_allowed`` and ``guardrails_block_message_ro``.
    """

    async def clarify_guardrails(state: dict[str, Any], config: RunnableConfig | None = None) -> dict[str, Any]:
        """
        Run guardrails and merge results into graph state.

        Args:
            state: LangGraph state mapping.
            config: Runnable config (Langfuse callbacks, optional stream queue).

        Returns:
            Partial state update with guardrails fields.
        """
        config = config or {}
        user_query = str(state.get(query_state_key) or "")
        context_text = str(state.get(context_state_key) or "")
        raw_uid = (config.get("configurable") or {}).get("user_id")
        user_id: str | UUID | None
        if raw_uid is None:
            user_id = None
        elif isinstance(raw_uid, UUID):
            user_id = raw_uid
        else:
            user_id = str(raw_uid)
        result = await evaluate_clarify_guardrails(
            llm=llm,
            composer=composer,
            user_query=user_query,
            conversation_context=context_text,
            config=config,
            user_id=user_id,
        )
        return {
            "guardrails_allowed": bool(result.allow),
            "guardrails_block_message_ro": (result.student_facing_message_ro or "").strip(),
        }

    return clarify_guardrails


def make_emit_guardrail_block_node() -> Callable[
    [dict[str, Any], RunnableConfig | None], Awaitable[dict[str, Any]]
]:
    """
    Factory: emit the blocked Romanian message through ``stream_queue`` (char-by-char, then None).

    Returns:
        Async node callable that streams ``guardrails_block_message_ro`` and returns state unchanged
        aside from optional passthrough.
    """

    async def emit_guardrail_block(state: dict[str, Any], config: RunnableConfig | None = None) -> dict[str, Any]:
        """
        Push the block message to the clarify SSE queue when guardrails fail.

        Args:
            state: Graph state containing ``guardrails_block_message_ro``.
            config: Runnable config with ``configurable.stream_queue``.

        Returns:
            Unchanged state (streaming is side-effect only).
        """
        config = config or {}
        stream_queue: asyncio.Queue | None = (config.get("configurable") or {}).get("stream_queue")
        text = (state.get("guardrails_block_message_ro") or "").strip()
        if not text:
            text = CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO
        if stream_queue is not None:
            for char in text:
                stream_queue.put_nowait(char)
            stream_queue.put_nowait(None)
        return state

    return emit_guardrail_block


def route_after_clarify_guardrails(state: dict[str, Any]) -> str:
    """
    Conditional edge: continue tutoring or show block message.

    Args:
        state: Graph state after the guardrails node.

    Returns:
        ``continue`` when allowed, otherwise ``blocked``.
    """
    return "continue" if state.get("guardrails_allowed", False) else "blocked"
