"""
Langfuse trace context manager and helpers for wrapping AI service calls.

LangGraph tracing architecture
--------------------------------
The ``CallbackHandler`` (from ``langfuse.langchain``) automatically creates
Langfuse observations for every LangGraph node via ``on_chain_start`` /
``on_chain_end`` callbacks.  LLM generation observations are nested under the
correct node observation because ``llm_config()`` preserves the
``AsyncCallbackManagerForChainRun`` (which carries ``parent_run_id=node_run_id``).

Do **not** use ``node_span()`` inside LangGraph node functions: LangGraph's
``set_config_context`` resets the OTel ``contextvars`` inside each node task,
so any span created with ``start_as_current_observation`` would become a
detached root span with a new, unrelated trace id.

Usage::

    async with langfuse_trace_context(
        trace_id=request.trace_id,
        session_id=request.session_id,
        user_id=str(user_id),
        name="clarify_once",
    ) as langfuse_config:
        # For direct LLM calls:
        async for chunk in llm.astream(messages, config=langfuse_config):
            ...

        # For LangGraph — merge with existing config, pass llm_config() to LLM calls:
        config = {"configurable": {"stream_queue": q}, **langfuse_config}
        await graph.ainvoke(state, config=config)
        # Inside each node: await llm.ainvoke(messages, config=llm_config(config))
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager, nullcontext
from typing import Any, Optional

from langfuse import propagate_attributes
from langfuse.langchain import CallbackHandler
from langchain_core.runnables import RunnableConfig
from profu_logging.feature_logger import get_feature_logger

from ai_backend.langfuse.client import get_langfuse_client


class _InlineCallbackHandler(CallbackHandler):
    """
    Langfuse CallbackHandler with ``run_inline = True``.

    By default, LangChain runs sync callbacks in a thread-pool executor
    (``run_in_executor``) with a copy of the calling context.  Inside a
    LangGraph node task (which itself runs in an ``asyncio.create_task`` with
    its own copied context), this means:

    * ``_attach_observation`` modifies the thread's copy of the OTel context,
      not the asyncio task's context.
    * Subsequent ``copy_context()`` calls (e.g., by LangGraph's
      ``set_config_context``) capture the *unmodified* asyncio context, so the
      OTel parent-span chain is broken and all node observations appear as
      orphan root spans.

    Setting ``run_inline = True`` makes every sync callback fire *directly*
    inside the asyncio event-loop thread where LangGraph is running.  This
    keeps OTel context propagation correct (``_attach_observation`` modifies the
    right contextvar) and ensures ``_runs`` is populated before LangGraph
    creates child tasks for nested nodes.

    Trade-off: callbacks briefly block the event loop, but span creation is
    purely in-memory and completes in microseconds.
    """

    run_inline: bool = True


LOG = get_feature_logger(source="langfuse")


def resolve_session_id(
    session_id: Optional[str],
    conversation_id: int | None,
) -> Optional[str]:
    """
    Return the effective Langfuse session id for a request.

    Priority:
      1. Explicit ``session_id`` from the client (already a string).
      2. ``str(conversation_id)`` — groups all traces for the same Supabase
         conversation into one Langfuse session automatically.
      3. ``None`` — traces are ungrouped.

    Args:
        session_id:      Client-supplied session id (may be None).
        conversation_id: Supabase conversation id (may be None).

    Returns:
        Session id string, or None when neither source is available.
    """
    return session_id or (str(conversation_id) if conversation_id is not None else None)


def node_span(name: str, input: Optional[Any] = None):
    """
    Return a sync context manager that creates a Langfuse span and sets it as
    the current OTel span for the duration of the block.

    **Important**: This works correctly when there is an active OTel span in the
    current context (e.g., inside ``langfuse_trace_context`` or another
    ``start_as_current_observation`` block).  It does **not** work inside
    LangGraph node functions, because LangGraph's ``set_config_context``
    resets the OTel context inside every node task — so any span created here
    would become a detached root span with a wrong trace id.  For LangGraph
    nodes, rely on the ``CallbackHandler``'s automatic per-node observations
    (created via ``on_chain_start`` / ``on_chain_end``) instead.

    Gracefully degrades to a no-op when the Langfuse client is not initialised.

    Args:
        name:  Span name shown in the Langfuse UI.
        input: Optional input payload for the span.
    """
    try:
        client = get_langfuse_client()
        return client.start_as_current_observation(name=name, as_type="span", input=input)
    except RuntimeError:
        # Langfuse client not yet initialised — return a safe no-op.
        return nullcontext(None)


def llm_config(node_config: RunnableConfig) -> dict:
    """
    Build a LangChain config dict suitable for passing to ``llm.astream`` /
    ``llm.ainvoke`` inside a LangGraph node.

    Keeps only ``callbacks`` and ``metadata`` from the node config:

    * ``callbacks``: the child ``AsyncCallbackManagerForChainRun`` created by
      LangGraph for this node (it already carries ``parent_run_id = node_run_id``).
      The ``CallbackHandler`` uses that ``parent_run_id`` in ``on_chat_model_start``
      to look up the node observation and nest the LLM generation under it.
    * ``metadata``: Langfuse trace attributes (user_id, session_id, etc.).

    Stripping ``configurable`` removes ``stream_queue`` and other non-LLM keys
    that would cause warnings.  Stripping ``run_id`` is critical: passing the
    node's ``run_id`` to the LLM would cause the LLM run to overwrite the node's
    entry in the ``CallbackHandler._runs`` dict, breaking the parent-child tree.

    Args:
        node_config: The ``RunnableConfig`` received by a LangGraph node.

    Returns:
        A dict with ``callbacks`` and ``metadata`` only.
    """
    return {
        "callbacks": node_config.get("callbacks", []),
        "metadata": node_config.get("metadata", {}),
    }


def _schedule_flush(*, user_id: Optional[str] = None) -> None:
    """
    Fire-and-forget flush of pending Langfuse spans.

    Runs the blocking ``Langfuse.flush()`` call in a thread-pool executor so
    it does not block the asyncio event loop.  Any exception is swallowed —
    spans will be auto-flushed by the background batch exporter if this fails.

    Args:
        user_id: Used only for error logging.
    """
    async def _do_flush() -> None:
        try:
            client = get_langfuse_client()
            await asyncio.to_thread(client.flush)
        except Exception as exc:
            LOG.error(f"Background Langfuse flush failed: {exc}", user_id=user_id)

    try:
        asyncio.create_task(_do_flush())
    except RuntimeError:
        # No running event loop (e.g., in a test teardown) — skip.
        pass


@asynccontextmanager
async def langfuse_trace_context(
    *,
    trace_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    name: str = "profu",
    tags: Optional[list[str]] = None,
) -> Any:
    """
    Async context manager that establishes a Langfuse v4 OTel trace context.

    Creates a ``CallbackHandler`` bound to a specific trace and yields a
    LangChain-compatible config dict (``callbacks`` + ``metadata``) that
    callers merge into their own ``RunnableConfig``.

    Args:
        trace_id:   32-char lowercase hex trace id.  Auto-generated when absent.
        session_id: Logical session (e.g. conversation_id) for grouping traces.
        user_id:    Authenticated user id.
        name:       Human-readable trace name shown in the Langfuse UI.
        tags:       Optional categorisation tags.

    Yields:
        ``dict`` with ``callbacks`` and ``metadata`` keys ready to spread
        into a LangChain / LangGraph invocation config.
    """
    # Ensure a valid 32-char lowercase hex trace id
    trace_id = trace_id or uuid.uuid4().hex

    trace_context: dict[str, str] = {"trace_id": trace_id}

    # Create the LangChain callback handler bound to this trace.
    # _InlineCallbackHandler runs callbacks synchronously in the asyncio event-loop
    # thread (run_inline=True) so OTel context propagation works correctly inside
    # LangGraph node tasks (which reset contextvars via asyncio.create_task).
    handler = _InlineCallbackHandler(trace_context=trace_context)

    # Metadata keys recognised by the CallbackHandler for attribute propagation
    langfuse_metadata: dict[str, Any] = {}
    if user_id:
        langfuse_metadata["langfuse_user_id"] = str(user_id)
    if session_id:
        langfuse_metadata["langfuse_session_id"] = session_id
    if tags:
        langfuse_metadata["langfuse_tags"] = tags

    config: dict[str, Any] = {
        "callbacks": [handler],
        "metadata": langfuse_metadata,
    }

    LOG.info(
        f"Trace context opened: name={name}, trace_id={trace_id}",
        user_id=user_id,
    )

    # propagate_attributes sets OTel context so trace_name, user_id, session_id
    # are attached to every span created inside this block.
    with propagate_attributes(
        user_id=str(user_id) if user_id else None,
        session_id=session_id,
        trace_name=name,
        tags=tags,
    ):
        try:
            yield config
        finally:
            LOG.info(
                f"Trace context closed: name={name}, trace_id={trace_id}",
                user_id=user_id,
            )
            # Schedule a non-blocking flush so spans appear in Langfuse immediately
            # rather than waiting for the next batch export interval (~1 s).
            _schedule_flush(user_id=user_id)
