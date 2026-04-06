"""
Clarify-with-steps LangGraph: state, routing, compiled graph.

Node implementations live in ``nodes.py`` (imported after state is defined to avoid cycles).
"""

from typing import Annotated, Sequence, TypedDict

from ai_backend.common.protocols import LangGraphChatModel

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

__all__ = ["StepByStepLearningState", "build_step_by_step_learning_graph", "should_continue_prerequisites"]


class StepByStepLearningState(TypedDict):
    """State for the step-by-step learning graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    original_query: str
    prerequisites: list[str]
    current_prerequisite_index: int
    prerequisites_completed: bool
    progress_preview_sent: bool


def should_continue_prerequisites(state: StepByStepLearningState) -> str:
    """Route: continue prerequisite loop or move to final explanation."""
    if state.get("prerequisites_completed", False):
        return "final_explanation"
    return "ask_question"


# Import after state so ``nodes`` can import ``StepByStepLearningState`` from this module without cycles.
from ai_backend.services.clarify_with_steps.nodes import (  # noqa: E402
    make_ask_prerequisite_question_node,
    make_generate_prerequisites_node,
    make_provide_final_explanation_node,
)


def build_step_by_step_learning_graph(llm: LangGraphChatModel, composer: "PromptComposer"):  # noqa: F821
    """
    Build the step-by-step learning state graph with injected LLM and PromptComposer.
    """
    workflow = StateGraph(StepByStepLearningState)

    workflow.add_node("generate_prerequisites", make_generate_prerequisites_node(llm, composer))
    workflow.add_node("ask_question", make_ask_prerequisite_question_node(llm, composer))
    workflow.add_node("final_explanation", make_provide_final_explanation_node(llm, composer))

    workflow.set_entry_point("generate_prerequisites")

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
