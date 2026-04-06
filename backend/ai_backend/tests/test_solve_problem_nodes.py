"""
Unit tests for solve_problem LangGraph nodes (mocked LLM).
"""

import asyncio
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from ai_backend.services.solve_problem.graph import ProblemSolvingState
from ai_backend.services.solve_problem.models import (
    SolveProblemIntentDetection,
    SolveProblemProgressIntent,
)
from ai_backend.services.solve_problem.nodes import (
    make_detect_intent_node,
    make_detect_progress_intent_node,
    make_evaluate_progress_node,
    make_explain_error_node,
    make_provide_hint_node,
    make_provide_solution_node,
)


def _base_state(**kwargs: Any) -> ProblemSolvingState:
    defaults: dict[str, Any] = {
        "messages": [],
        "problem_text": "x = 1",
        "intent": "",
        "student_work": "",
        "hint_level": 0,
        "full_solution_requested": False,
    }
    defaults.update(kwargs)
    return cast(ProblemSolvingState, defaults)


@pytest.mark.asyncio
class TestDetectIntentNode:
    """Tests for make_detect_intent_node."""

    async def test_initial_short_message_sets_initial_question(self, prompt_composer) -> None:
        llm = MagicMock()
        node = make_detect_intent_node(llm, prompt_composer)
        state = _base_state(
            messages=[HumanMessage(content="hi")],
            problem_text="2+2",
        )
        out = await node(state)
        assert out["intent"] == "initial_question"
        assert "2+2" in (out["messages"][-1].content or "")
        llm.ainvoke.assert_not_called()

    async def test_json_intent_from_llm(self, prompt_composer) -> None:
        llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(
            return_value={
                "raw": MagicMock(content=""),
                "parsed": SolveProblemIntentDetection(intent="progress"),
                "parsing_error": None,
            }
        )
        llm.with_structured_output = MagicMock(return_value=structured)
        node = make_detect_intent_node(llm, prompt_composer)
        state = _base_state(
            messages=[HumanMessage(content="x" * 55)],
        )
        out = await node(state)
        assert out["intent"] == "progress"

    async def test_keyword_fallback_solve(self, prompt_composer) -> None:
        llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(
            return_value={
                "raw": MagicMock(content="I will show soluție completă"),
                "parsed": None,
                "parsing_error": Exception("parse failed"),
            }
        )
        llm.with_structured_output = MagicMock(return_value=structured)
        node = make_detect_intent_node(llm, prompt_composer)
        state = _base_state(
            messages=[HumanMessage(content="y" * 55)],
        )
        out = await node(state)
        assert out["intent"] == "solve"


@pytest.mark.asyncio
class TestProvideHintNode:
    """Tests for make_provide_hint_node."""

    async def test_initial_question_streams_existing_then_none(self, prompt_composer) -> None:
        llm = MagicMock()
        node = make_provide_hint_node(llm, prompt_composer)
        q: asyncio.Queue = asyncio.Queue()
        cfg = {"configurable": {"stream_queue": q}}
        ai = AIMessage(content="Hello student")
        state = _base_state(intent="initial_question", messages=[ai])
        out = await node(state, config=cfg)
        assert out["messages"][-1].content == "Hello student"
        assert q.get_nowait() == "Hello student"
        assert q.get_nowait() is None

    async def test_no_stream_ainvoke(self, prompt_composer) -> None:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content="hint"))
        node = make_provide_hint_node(llm, prompt_composer)
        state = _base_state(
            intent="new_hint",
            messages=[HumanMessage(content="help")],
            hint_level=1,
        )
        out = await node(state, config=None)
        assert out["hint_level"] == 2
        assert out["messages"][-1].content == "hint"


@pytest.mark.asyncio
class TestOtherNodes:
    """evaluate_progress, detect_progress_intent, explain_error, provide_solution."""

    async def test_evaluate_progress_with_human_last(self, prompt_composer) -> None:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content="ok"))
        node = make_evaluate_progress_node(llm, prompt_composer)
        state = _base_state(messages=[HumanMessage(content="my work")])
        out = await node(state)
        assert out["student_work"] == "my work"

    async def test_detect_progress_intent_json(self, prompt_composer) -> None:
        llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(
            return_value={
                "raw": MagicMock(content=""),
                "parsed": SolveProblemProgressIntent(progress_intent="bad"),
                "parsing_error": None,
            }
        )
        llm.with_structured_output = MagicMock(return_value=structured)
        node = make_detect_progress_intent_node(llm, prompt_composer)
        state = _base_state(messages=[AIMessage(content="eval")])
        out = await node(state)
        assert out["intent"] == "bad"

    async def test_detect_progress_intent_keyword_good(self, prompt_composer) -> None:
        llm = MagicMock()
        structured = MagicMock()
        structured.ainvoke = AsyncMock(
            return_value={
                "raw": MagicMock(content="totul e bine"),
                "parsed": None,
                "parsing_error": Exception("parse failed"),
            }
        )
        llm.with_structured_output = MagicMock(return_value=structured)
        node = make_detect_progress_intent_node(llm, prompt_composer)
        state = _base_state(messages=[])
        out = await node(state)
        assert out["intent"] == "good"

    async def test_explain_error_ainvoke(self, prompt_composer) -> None:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content="err"))
        node = make_explain_error_node(llm, prompt_composer)
        out = await node(_base_state(), config=None)
        assert out["messages"][-1].content == "err"

    async def test_provide_solution_stream(self, prompt_composer) -> None:
        llm = MagicMock()

        async def _chunks():
            yield MagicMock(content="a")
            yield MagicMock(content="b")

        llm.astream = MagicMock(return_value=_chunks())
        node = make_provide_solution_node(llm, prompt_composer)
        q: asyncio.Queue = asyncio.Queue()
        out = await node(_base_state(), config={"configurable": {"stream_queue": q}})
        assert out["full_solution_requested"] is True
        assert q.get_nowait() == "[THINKING]"
        assert q.get_nowait() == "a"
        assert q.get_nowait() == "b"
        assert q.get_nowait() is None
