"""
Clarify step-by-step graph builder and node factories.

The router uses this module to build/run the LangGraph workflow.
"""

import asyncio
from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from ai_backend.parsing.json_extract import extract_json_from_text
from ai_backend.routers.common import PROMPTS


class StepByStepLearningState(TypedDict):
    """
    State for the step-by-step learning graph.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    original_query: str
    prerequisites: list[str]
    current_prerequisite_index: int
    prerequisites_completed: bool
    progress_preview_sent: bool


def _make_generate_prerequisites(llm: Any):
    """
    Factory: Node 1 - Generate list of prerequisite concepts (uses injected llm).
    """

    async def generate_prerequisites(
        state: StepByStepLearningState, config: dict | None = None
    ) -> StepByStepLearningState:
        config = config or {}
        stream_queue: asyncio.Queue | None = config.get("configurable", {}).get("stream_queue")

        system_prompt = PROMPTS["guided_learning"]["prerequisite_generator"]["system_prompt"]

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Elevul întreabă: {state['original_query']}"),
        ]

        response = await llm.ainvoke(messages)

        try:
            result = extract_json_from_text(response.content)
            prerequisites = result.get("prerequisites", [])

            if prerequisites:
                preview_items = "\n".join(
                    [f"{i + 1}. {concept} 🎯" for i, concept in enumerate(prerequisites)]
                )
                preview_message = (
                    f"Minunat! Pentru a înțelege **{state['original_query']}**, vom parcurge următoarele concepte:\n\n"
                    f"{preview_items}\n\n"
                    "Să începem cu primul! 🚀"
                )
            else:
                preview_message = "Să începem! 🚀"

            if stream_queue is not None:
                for char in preview_message:
                    stream_queue.put_nowait(char)
                stream_queue.put_nowait(None)

            preview_ai_message = AIMessage(content=preview_message)

            return {
                **state,
                "prerequisites": prerequisites,
                "current_prerequisite_index": 0,
                "prerequisites_completed": False,
                "progress_preview_sent": True,
                "messages": [preview_ai_message],
            }
        except Exception:
            if stream_queue is not None:
                fallback_message = "Să începem! 🚀"
                for char in fallback_message:
                    stream_queue.put_nowait(char)
                stream_queue.put_nowait(None)
            return {
                **state,
                "prerequisites": [],
                "current_prerequisite_index": 0,
                "prerequisites_completed": True,
                "progress_preview_sent": True,
            }

    return generate_prerequisites


def _make_ask_prerequisite_question(llm: Any):
    """
    Factory: Node 2 - Ask about current prerequisite concept (uses injected llm).
    """

    async def ask_prerequisite_question(
        state: StepByStepLearningState, config: dict | None = None
    ) -> StepByStepLearningState:
        config = config or {}
        stream_queue: asyncio.Queue | None = config.get("configurable", {}).get("stream_queue")

        current_index = state["current_prerequisite_index"]
        prerequisites = state["prerequisites"]

        if current_index >= len(prerequisites):
            return {**state, "prerequisites_completed": True}

        current_concept = prerequisites[current_index]
        total_prerequisites = len(prerequisites)
        system_prompt = PROMPTS["guided_learning"]["question_asker"]["system_prompt"]

        progress_info = f"""
    Progres: Conceptul {current_index + 1} din {total_prerequisites}

    IMPORTANT: La începutul răspunsului tău, include un indicator de progres:
    "**[Concept {current_index + 1}/{total_prerequisites}]** [emoji relevant]"

    Exemple de emoji:
    - 📖 pentru concepte teoretice
    - 🔢 pentru matematică/numere
    - 📐 pentru geometrie
    - 🎯 pentru obiective
    """

        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=f"Conceptul curent de verificat: {current_concept}"),
            SystemMessage(content=progress_info),
        ]

        conversation_messages = list(state.get("messages", []))[-6:]
        messages.extend(conversation_messages)

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

        completion_indicators = [
            "putem trece",
            "următorul pas",
            "ai înțeles",
            "foarte bine",
            "corect",
            "exact",
        ]

        response_lower = (response.content or "").lower()
        should_advance = any(indicator in response_lower for indicator in completion_indicators)
        new_index = current_index + 1 if should_advance else current_index

        return {
            **state,
            "messages": [response],
            "current_prerequisite_index": new_index,
            "prerequisites_completed": new_index >= len(prerequisites),
        }

    return ask_prerequisite_question


def _make_provide_final_explanation(llm: Any):
    """
    Factory: Node 3 - Provide complete explanation (uses injected llm).
    """

    async def provide_final_explanation(
        state: StepByStepLearningState, config: dict | None = None
    ) -> StepByStepLearningState:
        config = config or {}
        stream_queue: asyncio.Queue | None = config.get("configurable", {}).get("stream_queue")

        system_prompt = PROMPTS["guided_learning"]["final_explainer"]["system_prompt"]

        prerequisites_list = state["prerequisites"]
        prerequisites_summary = "\n".join([f"{i + 1}. {p}" for i, p in enumerate(prerequisites_list)])

        recap_instruction = f"""
    IMPORTANT: Începe răspunsul cu această structură EXACTĂ:

    📚 **Recapitulare:** Până acum am învățat despre:
    {chr(10).join([f"{i+1}. ✓ {concept}" for i, concept in enumerate(prerequisites_list)])}

    Acum putem înțelege pe deplin **{state['original_query']}**! 🎯

    [apoi continuă cu explicația completă]
    """

        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=recap_instruction),
            SystemMessage(content=f"Întrebarea inițială a elevului: {state['original_query']}"),
            SystemMessage(content=f"Concepte prerequisite acoperite:\n{prerequisites_summary}"),
            HumanMessage(content=f"Acum explică-mi complet: {state['original_query']}"),
        ]

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

    return provide_final_explanation


def should_continue_prerequisites(state: StepByStepLearningState) -> str:
    """
    Routing function: decide if we continue with prerequisites or move to final explanation.
    """
    if state.get("prerequisites_completed", False):
        return "final_explanation"
    return "ask_question"


def build_step_by_step_learning_graph(llm: Any):
    """
    Build the step-by-step learning state graph with injected LLM.
    """
    workflow = StateGraph(StepByStepLearningState)

    workflow.add_node("generate_prerequisites", _make_generate_prerequisites(llm))
    workflow.add_node("ask_question", _make_ask_prerequisite_question(llm))
    workflow.add_node("final_explanation", _make_provide_final_explanation(llm))

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

