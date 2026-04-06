"""
Behaviour tests for clarify streaming services (guardrails block, errors, empty query).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_backend.common.models import Message
from ai_backend.services.clarify_once.service import stream_clarify_once
from ai_backend.services.clarify_with_steps.service import stream_clarify_step_by_step


@pytest.mark.asyncio
async def test_stream_clarify_once_empty_query_yields_error_and_done(prompt_composer) -> None:
    """Blank query short-circuits before LangGraph."""
    llm = MagicMock()
    chunks: list[str] = []
    async for line in stream_clarify_once(
        request_query="   ",
        request_history=[],
        conversation_id=None,
        user_id=uuid.uuid4(),
        llm=llm,
        composer=prompt_composer,
    ):
        chunks.append(line)
    text = "".join(chunks)
    assert "goală" in text or "goală".encode() in text.encode()
    assert "[DONE]" in text
    llm.astream.assert_not_called()


@pytest.mark.asyncio
async def test_stream_clarify_once_graph_failure_yields_generic_error(prompt_composer) -> None:
    """Exception from graph.ainvoke surfaces as SSE generic error."""
    llm = MagicMock()
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph failed"))

    with patch(
        "ai_backend.services.clarify_once.service.get_compiled_clarify_once_graph",
        return_value=mock_graph,
    ):
        chunks: list[str] = []
        async for line in stream_clarify_once(
            request_query="Ce este limita?",
            request_history=[],
            conversation_id=None,
            user_id=uuid.uuid4(),
            llm=llm,
            composer=prompt_composer,
        ):
            chunks.append(line)
    joined = "".join(chunks)
    assert "Eroare internă" in joined
    assert "[DONE]" in joined


@pytest.mark.asyncio
async def test_stream_clarify_step_by_step_followup_guardrails_block(prompt_composer) -> None:
    """Follow-up path yields block text when guardrails denies."""
    llm = MagicMock()
    deny = MagicMock()
    deny.allow = False
    deny.student_facing_message_ro = "Nu pot continua test."

    with patch(
        "ai_backend.services.clarify_with_steps.service.evaluate_clarify_guardrails",
        new_callable=AsyncMock,
        return_value=deny,
    ):
        chunks: list[str] = []
        async for line in stream_clarify_step_by_step(
            request_query="bad",
            request_history=[Message(role="user", content="prior")],
            conversation_id=None,
            user_id=uuid.uuid4(),
            llm=llm,
            composer=prompt_composer,
        ):
            chunks.append(line)
    joined = "".join(chunks)
    assert "Nu pot continua test." in joined
    assert "[DONE]" in joined
    llm.astream.assert_not_called()


@pytest.mark.asyncio
async def test_stream_clarify_step_by_step_invoke_exception(prompt_composer) -> None:
    """Initial graph invoke failure yields generic SSE error."""
    llm = MagicMock()
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(side_effect=ValueError("invoke failed"))

    with patch(
        "ai_backend.services.clarify_with_steps.service.get_compiled_step_by_step_learning_graph",
        return_value=mock_graph,
    ):
        chunks: list[str] = []
        async for line in stream_clarify_step_by_step(
            request_query="Întrebare inițială",
            request_history=[],
            conversation_id=None,
            user_id=uuid.uuid4(),
            llm=llm,
            composer=prompt_composer,
        ):
            chunks.append(line)
    body = "".join(chunks)
    assert "Eroare internă" in body
    assert "[DONE]" in body
