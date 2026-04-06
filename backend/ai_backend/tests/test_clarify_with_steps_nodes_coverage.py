"""Branch coverage for clarify_with_steps nodes (streaming fallbacks and no-queue paths)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from ai_backend.services.clarify_with_steps.graph import StepByStepLearningState
from ai_backend.services.clarify_with_steps.models import GuidedLearningPrerequisitesOutput
from ai_backend.services.clarify_with_steps.nodes import (
    make_ask_prerequisite_question_node,
    make_generate_prerequisites_node,
    make_provide_final_explanation_node,
)


def _base_state(**overrides: object) -> StepByStepLearningState:
    state: StepByStepLearningState = {
        "messages": [],
        "original_query": "Ce este derivata?",
        "prerequisites": [],
        "current_prerequisite_index": 0,
        "prerequisites_completed": False,
        "progress_preview_sent": False,
    }
    for key, val in overrides.items():
        state[key] = val  # type: ignore[literal-required]
    return state


def _drain_queue_text(q: asyncio.Queue) -> str:
    parts: list[str] = []
    while True:
        try:
            item = q.get_nowait()
        except asyncio.QueueEmpty:
            break
        if item is None:
            break
        if isinstance(item, str):
            parts.append(item)
    return "".join(parts)


@pytest.mark.asyncio
async def test_generate_prerequisites_parsed_none_streams_fallback(prompt_composer) -> None:
    """When structured output is missing, stream chars then empty prerequisites."""
    mock_llm = MagicMock()
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value={"raw": None, "parsed": None, "parsing_error": "x"})
    mock_llm.with_structured_output.return_value = chain

    node = make_generate_prerequisites_node(mock_llm, prompt_composer)
    q: asyncio.Queue = asyncio.Queue()
    out = await node(
        _base_state(),
        config={"configurable": {"stream_queue": q}},
    )

    preview = _drain_queue_text(q)
    assert "Să începem" in preview
    assert out["prerequisites"] == []
    assert out["prerequisites_completed"] is True


@pytest.mark.asyncio
async def test_generate_prerequisites_empty_list_preview(prompt_composer) -> None:
    """Empty prerequisite list should still emit the short start message."""
    mock_llm = MagicMock()
    chain = MagicMock()
    parsed = GuidedLearningPrerequisitesOutput(prerequisites=[])
    chain.ainvoke = AsyncMock(
        return_value={"raw": MagicMock(), "parsed": parsed, "parsing_error": None},
    )
    mock_llm.with_structured_output.return_value = chain

    node = make_generate_prerequisites_node(mock_llm, prompt_composer)
    q: asyncio.Queue = asyncio.Queue()
    out = await node(_base_state(), config={"configurable": {"stream_queue": q}})

    text = _drain_queue_text(q)
    assert "Să începem" in text
    assert out["prerequisites"] == []


@pytest.mark.asyncio
async def test_ask_prerequisite_question_short_circuits_when_index_past_end(prompt_composer) -> None:
    """If index is past prerequisites, mark completed without calling the LLM."""
    mock_llm = MagicMock()
    node = make_ask_prerequisite_question_node(mock_llm, prompt_composer)
    state = _base_state(prerequisites=[], current_prerequisite_index=1)
    out = await node(state, config={})
    assert out["prerequisites_completed"] is True
    mock_llm.astream.assert_not_called()
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_ask_prerequisite_question_no_stream_queue_uses_ainvoke(prompt_composer) -> None:
    """Without stream_queue, node should use plain ainvoke."""
    mock_llm = MagicMock()
    mock_llm.astream = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="răspuns fără indicator"))
    node = make_ask_prerequisite_question_node(mock_llm, prompt_composer)
    state = _base_state(prerequisites=["Limite"], current_prerequisite_index=0)
    out = await node(state, config={})
    assert isinstance(out["messages"][-1], AIMessage)
    mock_llm.ainvoke.assert_awaited_once()
    mock_llm.astream.assert_not_called()


@pytest.mark.asyncio
async def test_provide_final_explanation_no_stream_queue(prompt_composer) -> None:
    """Final node without queue should call ainvoke once."""
    mock_llm = MagicMock()
    mock_llm.astream = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="final"))
    node = make_provide_final_explanation_node(mock_llm, prompt_composer)
    state = _base_state(prerequisites=["A", "B"])
    out = await node(state, config={})
    assert out["messages"][-1].content == "final"
    mock_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_ask_prerequisite_question_advances_on_completion_keyword(prompt_composer) -> None:
    """Heuristic should bump index when assistant signals understanding."""
    mock_llm = MagicMock()

    async def fake_astream(*_a: object, **_k: object):
        chunk = MagicMock()
        chunk.content = "Foarte bine, putem trece mai departe."
        yield chunk

    mock_llm.astream = fake_astream
    node = make_ask_prerequisite_question_node(mock_llm, prompt_composer)
    state = _base_state(prerequisites=["A", "B"], current_prerequisite_index=0)
    q: asyncio.Queue = asyncio.Queue()
    out = await node(state, config={"configurable": {"stream_queue": q}})
    assert out["current_prerequisite_index"] == 1
    assert out["prerequisites_completed"] is False
