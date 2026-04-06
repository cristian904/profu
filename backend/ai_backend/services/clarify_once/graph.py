"""
Clarify-once LangGraph: guardrails then streamed direct answer.
"""

from typing import TYPE_CHECKING, Any

from ai_backend.common.protocols import LangGraphChatModel
from langgraph.graph import END, StateGraph

from ai_backend.services.clarify_guardrails.nodes import (
    make_clarify_guardrails_node,
    make_emit_guardrail_block_node,
    route_after_clarify_guardrails,
)
from ai_backend.services.clarify_once.nodes import make_stream_clarify_answer_node
from ai_backend.services.clarify_once.state import ClarifyOnceGraphState

if TYPE_CHECKING:
    from ai_backend.langfuse.prompts import PromptComposer

__all__ = ["ClarifyOnceGraphState", "build_clarify_once_graph", "get_compiled_clarify_once_graph"]

# Compiled graphs keyed by (id(llm), id(composer)) — stable for process-lifetime singletons.
_compiled_clarify_once_graphs: dict[tuple[int, int], Any] = {}


def build_clarify_once_graph(llm: LangGraphChatModel, composer: "PromptComposer") -> Any:
    """
    Build clarify-once graph: guardrails → (blocked message | streamed answer).

    Args:
        llm: Chat model for guardrails structured output and answer streaming.
        composer: Prompt composer instance.

    Returns:
        Compiled LangGraph runnable.
    """
    workflow = StateGraph(ClarifyOnceGraphState)

    workflow.add_node(
        "clarify_guardrails",
        make_clarify_guardrails_node(llm, composer, query_state_key="request_query"),
    )
    workflow.add_node("guardrails_blocked", make_emit_guardrail_block_node())
    workflow.add_node("clarify_answer", make_stream_clarify_answer_node(llm))

    workflow.set_entry_point("clarify_guardrails")
    workflow.add_conditional_edges(
        "clarify_guardrails",
        route_after_clarify_guardrails,
        {
            "continue": "clarify_answer",
            "blocked": "guardrails_blocked",
        },
    )
    workflow.add_edge("guardrails_blocked", END)
    workflow.add_edge("clarify_answer", END)

    return workflow.compile()


def get_compiled_clarify_once_graph(llm: LangGraphChatModel, composer: "PromptComposer") -> Any:
    """
    Return a cached compiled clarify-once graph for the given LLM and PromptComposer instances.

    Args:
        llm: Chat model instance (identity used as cache key).
        composer: Prompt composer instance (identity used as cache key).

    Returns:
        Compiled LangGraph runnable (shared per distinct llm/composer pair).
    """
    key = (id(llm), id(composer))
    compiled = _compiled_clarify_once_graphs.get(key)
    if compiled is None:
        compiled = build_clarify_once_graph(llm, composer)
        _compiled_clarify_once_graphs[key] = compiled
    return compiled
