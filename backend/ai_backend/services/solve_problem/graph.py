"""
Solve-problem LangGraph: state, routing, compiled graph.

Node implementations live in ``nodes.py`` (imported after state is defined to avoid cycles).
"""

from typing import Annotated, NotRequired, Optional, Sequence, TypedDict
from uuid import UUID

from ai_backend.common.protocols import LangGraphChatModel

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

__all__ = ["ProblemSolvingState", "build_problem_solving_graph", "user_id_from_state"]


class ProblemSolvingState(TypedDict):
    """State for the problem solving graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    problem_text: str
    intent: str
    student_work: str
    hint_level: int
    full_solution_requested: bool
    user_id: NotRequired[Optional[str]]


def user_id_from_state(state: ProblemSolvingState) -> Optional[UUID]:
    """
    Extract user_id from graph state for logging (stream endpoint sets it).
    """
    uid = state.get("user_id")
    if not uid:
        return None
    if isinstance(uid, UUID):
        return uid
    try:
        return UUID(uid) if isinstance(uid, str) else None
    except (ValueError, TypeError):
        return None


def route_after_intent(state: ProblemSolvingState) -> str:
    """Route after initial intent detection."""
    intent = state.get("intent", "new_hint")
    if intent == "initial_question":
        return "provide_hint"
    if intent == "solve":
        return "provide_solution"
    if intent == "progress":
        return "evaluate_progress"
    return "provide_hint"


def route_after_progress_eval(state: ProblemSolvingState) -> str:
    """Route after progress evaluation."""
    return "detect_progress_intent"


def route_after_progress_intent(state: ProblemSolvingState) -> str:
    """Route after progress intent detection."""
    intent = state.get("intent", "good")
    if intent == "bad":
        return "explain_error"
    return "provide_hint"


# Import after state so ``nodes`` can import ``ProblemSolvingState`` from this module without cycles.
from ai_backend.services.solve_problem.nodes import (  # noqa: E402
    make_detect_intent_node,
    make_detect_progress_intent_node,
    make_evaluate_progress_node,
    make_explain_error_node,
    make_provide_hint_node,
    make_provide_solution_node,
)


def build_problem_solving_graph(llm: LangGraphChatModel, composer: "PromptComposer"):  # noqa: F821
    """
    Build the problem solving state graph with injected LLM and PromptComposer.
    """
    workflow = StateGraph(ProblemSolvingState)

    workflow.add_node("detect_intent", make_detect_intent_node(llm, composer))
    workflow.add_node("provide_hint", make_provide_hint_node(llm, composer))
    workflow.add_node("evaluate_progress", make_evaluate_progress_node(llm, composer))
    workflow.add_node("detect_progress_intent", make_detect_progress_intent_node(llm, composer))
    workflow.add_node("explain_error", make_explain_error_node(llm, composer))
    workflow.add_node("provide_solution", make_provide_solution_node(llm, composer))

    workflow.set_entry_point("detect_intent")

    workflow.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "provide_solution": "provide_solution",
            "provide_hint": "provide_hint",
            "evaluate_progress": "evaluate_progress",
        },
    )

    workflow.add_conditional_edges(
        "evaluate_progress",
        route_after_progress_eval,
        {"detect_progress_intent": "detect_progress_intent"},
    )

    workflow.add_conditional_edges(
        "detect_progress_intent",
        route_after_progress_intent,
        {"explain_error": "explain_error", "provide_hint": "provide_hint"},
    )

    workflow.add_edge("provide_solution", END)
    workflow.add_edge("provide_hint", END)
    workflow.add_edge("explain_error", END)

    return workflow.compile()
