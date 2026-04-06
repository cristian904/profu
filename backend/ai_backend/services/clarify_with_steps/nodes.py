"""
LangGraph node implementations for clarify-with-steps (prerequisites, questions, final explanation).

Each ``make_*`` factory returns an async node callable for the injected ``llm``.
"""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.langfuse.context import llm_config
from ai_backend.langfuse.prompts import PromptComposer
from ai_backend.common.structured_output import coerce_structured_output
from ai_backend.services.clarify_with_steps.graph import StepByStepLearningState
from ai_backend.services.clarify_with_steps.models import GuidedLearningPrerequisitesOutput


def make_generate_prerequisites_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 1 — generate prerequisite concepts and preview message."""
    prerequisites_llm = llm.with_structured_output(GuidedLearningPrerequisitesOutput, include_raw=True)

    async def generate_prerequisites(
        state: StepByStepLearningState, config: RunnableConfig | None = None
    ) -> StepByStepLearningState:
        config = config or {}
        stream_queue: asyncio.Queue | None = (config.get("configurable") or {}).get("stream_queue")

        system_prompt = composer.get("guided_learning.prerequisite_generator")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Elevul întreabă: {state['original_query']}"),
        ]

        structured_result = await prerequisites_llm.ainvoke(messages, config=llm_config(config))
        parsed, _raw = coerce_structured_output(structured_result, GuidedLearningPrerequisitesOutput)

        if parsed is None:
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

        prerequisites = list(parsed.prerequisites or [])

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

    return generate_prerequisites


def make_ask_prerequisite_question_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 2 — ask about the current prerequisite."""

    async def ask_prerequisite_question(
        state: StepByStepLearningState, config: RunnableConfig | None = None
    ) -> StepByStepLearningState:
        config = config or {}
        stream_queue: asyncio.Queue | None = (config.get("configurable") or {}).get("stream_queue")

        current_index = state["current_prerequisite_index"]
        prerequisites = state["prerequisites"]

        if current_index >= len(prerequisites):
            return {**state, "prerequisites_completed": True}

        current_concept = prerequisites[current_index]
        total_prerequisites = len(prerequisites)
        system_prompt = composer.get("guided_learning.question_asker")

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
            async for chunk in llm.astream(messages, config=llm_config(config)):
                if getattr(chunk, "content", None):
                    accumulated.append(chunk.content)
                    stream_queue.put_nowait(chunk.content)
            full_content = "".join(accumulated)
            response = AIMessage(content=full_content)
            stream_queue.put_nowait(None)
        else:
            response = await llm.ainvoke(messages, config=llm_config(config))

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


def make_provide_final_explanation_node(llm: LangGraphChatModel, composer: PromptComposer):
    """Factory: Node 3 — final explanation after prerequisites."""

    async def provide_final_explanation(
        state: StepByStepLearningState, config: RunnableConfig | None = None
    ) -> StepByStepLearningState:
        config = config or {}
        stream_queue: asyncio.Queue | None = (config.get("configurable") or {}).get("stream_queue")

        system_prompt = composer.get("guided_learning.final_explainer")
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

    return provide_final_explanation
