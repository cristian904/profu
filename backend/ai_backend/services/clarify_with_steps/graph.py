"""
Clarify-with-steps LangGraph: state, routing, compiled graph.

Node implementations live in ``nodes.py`` (imported after state is defined to avoid cycles).
"""

from typing import TYPE_CHECKING, Annotated, Any, Sequence, TypedDict

from ai_backend.common.protocols import LangGraphChatModel

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

if TYPE_CHECKING:
    from ai_backend.langfuse.prompts import PromptComposer

__all__ = [
    "StepByStepLearningState",
    "build_step_by_step_learning_graph",
    "get_compiled_step_by_step_learning_graph",
    "should_continue_prerequisites",
]

_compiled_step_by_step_graphs: dict[tuple[int, int], Any] = {}


class StepByStepLearningState(TypedDict):
    """State for the step-by-step learning graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    original_query: str
    prerequisites: list[str]
    current_prerequisite_index: int
    prerequisites_completed: bool
    progress_preview_sent: bool
    guardrails_context: str
    guardrails_allowed: bool
    guardrails_block_message_ro: str


def should_continue_prerequisites(state: StepByStepLearningState) -> str:
    """Route: continue prerequisite loop or move to final explanation."""
    if state.get("prerequisites_completed", False):
        return "final_explanation"
    return "ask_question"


# Import after state so ``nodes`` can import ``StepByStepLearningState`` from this module without cycles.
from ai_backend.services.clarify_guardrails.nodes import (  # noqa: E402
    make_clarify_guardrails_node,
    make_emit_guardrail_block_node,
    route_after_clarify_guardrails,
)
from ai_backend.services.clarify_with_steps.nodes import (  # noqa: E402
    make_ask_prerequisite_question_node,
    make_generate_prerequisites_node,
    make_provide_final_explanation_node,
)


def build_step_by_step_learning_graph(llm: LangGraphChatModel, composer: "PromptComposer") -> Any:
    """
    Build the step-by-step learning state graph with injected LLM and PromptComposer.
    """
    workflow = StateGraph(StepByStepLearningState)

    workflow.add_node(
        "clarify_guardrails",
        make_clarify_guardrails_node(llm, composer, query_state_key="original_query"),
    )
    workflow.add_node("guardrails_blocked", make_emit_guardrail_block_node())
    workflow.add_node("generate_prerequisites", make_generate_prerequisites_node(llm, composer))
    workflow.add_node("ask_question", make_ask_prerequisite_question_node(llm, composer))
    workflow.add_node("final_explanation", make_provide_final_explanation_node(llm, composer))

    workflow.set_entry_point("clarify_guardrails")
    workflow.add_conditional_edges(
        "clarify_guardrails",
        route_after_clarify_guardrails,
        {
            "continue": "generate_prerequisites",
            "blocked": "guardrails_blocked",
        },
    )
    workflow.add_edge("guardrails_blocked", END)
    workflow.add_edge("generate_prerequisites", "ask_question")
    workflow.add_conditional_edges(
        "ask_question",
        should_continue_prerequisites,
        {
            "ask_question": "ask_question",
            "final_explanation": "final_explanation",
        },
    )
    workflow.add_edge("final_explanation", END)

    return workflow.compile()


def get_compiled_step_by_step_learning_graph(llm: LangGraphChatModel, composer: "PromptComposer") -> Any:
    """
    Return a cached compiled step-by-step graph for the given LLM and PromptComposer instances.

    Args:
        llm: Chat model instance (identity used as cache key).
        composer: Prompt composer instance (identity used as cache key).

    Returns:
        Compiled LangGraph runnable (shared per distinct llm/composer pair).
    """
    key = (id(llm), id(composer))
    compiled = _compiled_step_by_step_graphs.get(key)
    if compiled is None:
        compiled = build_step_by_step_learning_graph(llm, composer)
        _compiled_step_by_step_graphs[key] = compiled
    return compiled
