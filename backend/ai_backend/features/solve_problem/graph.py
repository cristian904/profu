"""
Solve-problem LangGraph workflow.

Contains state, node factories, routing functions, and the graph builder.
"""

from typing import Annotated, Any, Optional, Sequence, TypedDict, NotRequired
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from ai_backend.logging.feature_logger import get_feature_logger
from ai_backend.parsing.json_extract import extract_json_from_text
from ai_backend.routers.common import PROMPTS

LOG = get_feature_logger(source="solve_problem_langgraph")


class ProblemSolvingState(TypedDict):
    """
    State for the problem solving graph.
    """

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


def _make_detect_intent(llm: Any):
    """
    Factory: Node 1 - Detect user intent (uses injected llm).
    """

    async def detect_intent(state: ProblemSolvingState) -> ProblemSolvingState:
        LOG.info(
            f"Node 1: detect_intent. Messages in state: {len(state.get('messages', []))}",
            user_id=user_id_from_state(state),
        )
        messages_list = state.get("messages", [])

        if len(messages_list) == 1 and isinstance(messages_list[0], HumanMessage):
            user_message = (messages_list[0].content or "").lower()
            if "încărcat" in user_message or "problem" in user_message or len(user_message) < 50:
                LOG.info(
                    "Initial message detected - returning initial question",
                    user_id=user_id_from_state(state),
                )
                problem_text = state.get("problem_text", "")
                if problem_text:
                    initial_message = AIMessage(
                        content=(
                            "Pare o problemă interesantă!\n\n"
                            f"**Problema:**\n{problem_text}\n\n"
                            "Ai vrea o rezolvare completă sau un hint?"
                        )
                    )
                else:
                    initial_message = AIMessage(
                        content="Pare o problemă interesantă! Ai vrea o rezolvare completă sau un hint?"
                    )
                new_state = {**state, "intent": "initial_question"}
                new_state["messages"] = [initial_message]
                return new_state

        system_prompt = PROMPTS["problem_solving"]["intent_detector"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                messages.append(HumanMessage(content=f"Mesajul elevului: {last_message.content}"))

        response = await llm.ainvoke(messages)

        try:
            result = extract_json_from_text(response.content)
            intent = result.get("intent", "new_hint")
        except Exception:
            content_lower = (response.content or "").lower()
            if any(word in content_lower for word in ["solve", "soluție", "completă", "arătă"]):
                intent = "solve"
            elif any(word in content_lower for word in ["progres", "rezolvat", "făcut"]):
                intent = "progress"
            else:
                intent = "new_hint"

        return {**state, "intent": intent, "messages": [response] if state.get("messages") else []}

    return detect_intent


def _make_provide_hint(llm: Any):
    """
    Factory: Node 2 - Provide hint (uses injected llm).
    """

    async def provide_hint(state: ProblemSolvingState, config: dict | None = None) -> ProblemSolvingState:
        config = config or {}
        stream_queue = config.get("configurable", {}).get("stream_queue")
        LOG.info("Node 2: provide_hint", user_id=user_id_from_state(state))

        if state.get("intent") == "initial_question" and state.get("messages"):
            if stream_queue is not None:
                existing_content = state["messages"][-1].content
                stream_queue.put_nowait(existing_content)
                stream_queue.put_nowait(None)
            return state

        system_prompt = PROMPTS["problem_solving"]["hint_provider"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        hint_level = state.get("hint_level", 0) + 1
        messages.append(SystemMessage(content=f"Nivelul hint-ului curent: {hint_level}"))

        if state.get("student_work"):
            messages.append(SystemMessage(content=f"Progresul elevului până acum: {state['student_work']}"))

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
            accumulated: list[str] = []
            async for chunk in llm.astream(messages):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
        else:
            response = await llm.ainvoke(messages)

        return {**state, "messages": [response], "hint_level": hint_level}

    return provide_hint


def _make_evaluate_progress(llm: Any):
    """
    Factory: Node 3 - Evaluate progress (uses injected llm).
    """

    async def evaluate_progress(state: ProblemSolvingState) -> ProblemSolvingState:
        system_prompt = PROMPTS["problem_solving"]["progress_evaluator"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                student_work = last_message.content
                messages.append(SystemMessage(content=f"Progresul elevului: {student_work}"))

        response = await llm.ainvoke(messages)

        return {
            **state,
            "messages": [response],
            "student_work": state.get("messages", [])[-1].content if state.get("messages") else "",
        }

    return evaluate_progress


def _make_detect_progress_intent(llm: Any):
    """
    Factory: Node 4 - Detect progress intent (uses injected llm).
    """

    async def detect_progress_intent(state: ProblemSolvingState) -> ProblemSolvingState:
        system_prompt = PROMPTS["problem_solving"]["progress_intent_detector"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        response = await llm.ainvoke(messages)

        try:
            result = extract_json_from_text(response.content)
            progress_intent = result.get("progress_intent", "good")
        except Exception:
            content_lower = (response.content or "").lower()
            if any(word in content_lower for word in ["greșit", "incorect", "eroare", "nu e bine"]):
                progress_intent = "bad"
            else:
                progress_intent = "good"

        return {**state, "intent": progress_intent, "messages": [response]}

    return detect_progress_intent


def _make_explain_error(llm: Any):
    """
    Factory: Node 5 - Explain errors (uses injected llm).
    """

    async def explain_error(state: ProblemSolvingState, config: dict | None = None) -> ProblemSolvingState:
        config = config or {}
        stream_queue = config.get("configurable", {}).get("stream_queue")
        system_prompt = PROMPTS["problem_solving"]["error_explainer"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
            accumulated: list[str] = []
            async for chunk in llm.astream(messages):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
        else:
            response = await llm.ainvoke(messages)

        return {**state, "messages": [response]}

    return explain_error


def _make_provide_solution(llm: Any):
    """
    Factory: Node 6 - Provide full solution (uses injected llm).
    """

    async def provide_solution(state: ProblemSolvingState, config: dict | None = None) -> ProblemSolvingState:
        config = config or {}
        stream_queue = config.get("configurable", {}).get("stream_queue")
        system_prompt = PROMPTS["problem_solving"]["solution_provider"]["system_prompt"]
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
            accumulated: list[str] = []
            async for chunk in llm.astream(messages):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
        else:
            response = await llm.ainvoke(messages)

        return {**state, "messages": [response], "full_solution_requested": True}

    return provide_solution


def route_after_intent(state: ProblemSolvingState) -> str:
    """
    Route after initial intent detection.
    """
    intent = state.get("intent", "new_hint")
    if intent == "initial_question":
        return "provide_hint"
    if intent == "solve":
        return "provide_solution"
    if intent == "progress":
        return "evaluate_progress"
    return "provide_hint"


def route_after_progress_eval(state: ProblemSolvingState) -> str:
    """
    Route after progress evaluation.
    """
    return "detect_progress_intent"


def route_after_progress_intent(state: ProblemSolvingState) -> str:
    """
    Route after progress intent detection.
    """
    intent = state.get("intent", "good")
    if intent == "bad":
        return "explain_error"
    return "provide_hint"


def build_problem_solving_graph(llm: Any):
    """
    Build the problem solving state graph with injected LLM.
    """
    workflow = StateGraph(ProblemSolvingState)

    workflow.add_node("detect_intent", _make_detect_intent(llm))
    workflow.add_node("provide_hint", _make_provide_hint(llm))
    workflow.add_node("evaluate_progress", _make_evaluate_progress(llm))
    workflow.add_node("detect_progress_intent", _make_detect_progress_intent(llm))
    workflow.add_node("explain_error", _make_explain_error(llm))
    workflow.add_node("provide_solution", _make_provide_solution(llm))

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

