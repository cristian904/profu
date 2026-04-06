"""
LangGraph node implementations for solve-problem (intent, hints, progress, solution).

Each ``make_*`` factory returns an async node callable for the injected ``llm``.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from profu_logging.feature_logger import get_feature_logger
from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.langfuse.context import llm_config
from ai_backend.langfuse.prompts import PromptComposer
from ai_backend.common.structured_output import coerce_structured_output
from ai_backend.services.solve_problem.graph import ProblemSolvingState, user_id_from_state
from ai_backend.services.solve_problem.models import (
    SolveProblemIntentDetection,
    SolveProblemProgressIntent,
)

LOG = get_feature_logger(source="solve_problem_langgraph")


def make_detect_intent_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 1 — detect user intent."""
    intent_llm = llm.with_structured_output(SolveProblemIntentDetection, include_raw=True)

    async def detect_intent(
        state: ProblemSolvingState, config: RunnableConfig | None = None
    ) -> ProblemSolvingState:
        config = config or {}
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

        system_prompt = composer.get("problem_solving.intent_detector")
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                messages.append(HumanMessage(content=f"Mesajul elevului: {last_message.content}"))

        structured_result = await intent_llm.ainvoke(messages, config=llm_config(config))
        parsed, raw_text = coerce_structured_output(structured_result, SolveProblemIntentDetection)
        if parsed is not None:
            intent = (parsed.intent or "new_hint").strip() or "new_hint"
            response = AIMessage(content=parsed.model_dump_json())
        else:
            content_lower = raw_text.lower()
            if any(word in content_lower for word in ["solve", "soluție", "completă", "arătă"]):
                intent = "solve"
            elif any(word in content_lower for word in ["progres", "rezolvat", "făcut"]):
                intent = "progress"
            else:
                intent = "new_hint"
            response = AIMessage(content=raw_text or f'{{"intent": "{intent}"}}')

        return {**state, "intent": intent, "messages": [response] if state.get("messages") else []}

    return detect_intent


def make_provide_hint_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 2 — provide hint."""

    async def provide_hint(state: ProblemSolvingState, config: RunnableConfig | None = None) -> ProblemSolvingState:
        config = config or {}
        stream_queue = (config.get("configurable") or {}).get("stream_queue")
        LOG.info("Node 2: provide_hint", user_id=user_id_from_state(state))

        if state.get("intent") == "initial_question" and state.get("messages"):
            if stream_queue is not None:
                existing_content = state["messages"][-1].content
                stream_queue.put_nowait(existing_content)
                stream_queue.put_nowait(None)
            return state

        system_prompt = composer.get("problem_solving.hint_provider")
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
            async for chunk in llm.astream(messages, config=llm_config(config)):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
        else:
            response = await llm.ainvoke(messages, config=llm_config(config))

        return {**state, "messages": [response], "hint_level": hint_level}

    return provide_hint


def make_evaluate_progress_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 3 — evaluate student progress."""

    async def evaluate_progress(
        state: ProblemSolvingState, config: RunnableConfig | None = None
    ) -> ProblemSolvingState:
        config = config or {}
        system_prompt = composer.get("problem_solving.progress_evaluator")
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

        response = await llm.ainvoke(messages, config=llm_config(config))

        return {
            **state,
            "messages": [response],
            "student_work": state.get("messages", [])[-1].content if state.get("messages") else "",
        }

    return evaluate_progress


def make_detect_progress_intent_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 4 — classify progress as good vs bad."""
    progress_llm = llm.with_structured_output(SolveProblemProgressIntent, include_raw=True)

    async def detect_progress_intent(
        state: ProblemSolvingState, config: RunnableConfig | None = None
    ) -> ProblemSolvingState:
        config = config or {}
        system_prompt = composer.get("problem_solving.progress_intent_detector")
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        structured_result = await progress_llm.ainvoke(messages, config=llm_config(config))
        parsed, raw_text = coerce_structured_output(structured_result, SolveProblemProgressIntent)
        if parsed is not None:
            progress_intent = (parsed.progress_intent or "good").strip() or "good"
            response = AIMessage(content=parsed.model_dump_json())
        else:
            content_lower = raw_text.lower()
            if any(word in content_lower for word in ["greșit", "incorect", "eroare", "nu e bine"]):
                progress_intent = "bad"
            else:
                progress_intent = "good"
            response = AIMessage(content=raw_text or f'{{"progress_intent": "{progress_intent}"}}')

        return {**state, "intent": progress_intent, "messages": [response]}

    return detect_progress_intent


def make_explain_error_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 5 — explain errors without giving hints."""

    async def explain_error(state: ProblemSolvingState, config: RunnableConfig | None = None) -> ProblemSolvingState:
        config = config or {}
        stream_queue = (config.get("configurable") or {}).get("stream_queue")
        system_prompt = composer.get("problem_solving.error_explainer")
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
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

    return explain_error


def make_provide_solution_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 6 — full solution."""

    async def provide_solution(state: ProblemSolvingState, config: RunnableConfig | None = None) -> ProblemSolvingState:
        config = config or {}
        stream_queue = (config.get("configurable") or {}).get("stream_queue")
        system_prompt = composer.get("problem_solving.solution_provider")
        messages: list[Any] = [SystemMessage(content=system_prompt)]

        if state.get("problem_text"):
            messages.append(SystemMessage(content=f"Textul problemei: {state['problem_text']}"))

        if state.get("messages"):
            messages.extend(state["messages"][-10:])

        if stream_queue is not None:
            stream_queue.put_nowait("[THINKING]")
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

        return {**state, "messages": [response], "full_solution_requested": True}

    return provide_solution
