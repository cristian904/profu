"""Additional solve-problem stream coverage (history replay + graph failures)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from ai_backend.common.models import Message
from ai_backend.main import app

client = TestClient(app)


@patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
@patch("ai_backend.routers.solve_problem.resolve_effective_history")
@patch("ai_backend.routers.solve_problem.build_problem_solving_graph")
def test_stream_replays_resolved_history(
    mock_build: MagicMock,
    mock_history: MagicMock,
    _mock_quota: MagicMock,
) -> None:
    """History from resolve_effective_history should populate LangChain messages."""
    mock_history.return_value = [
        Message(role="user", content="prev q"),
        Message(role="assistant", content="prev a"),
    ]

    async def fake_ainvoke(state: dict, config: dict) -> dict:
        msgs = state.get("messages") or []
        assert any(isinstance(m, HumanMessage) for m in msgs)
        assert any(isinstance(m, AIMessage) for m in msgs)
        q = config["configurable"]["stream_queue"]
        await q.put("[THINKING]")
        await q.put("out")
        await q.put(None)
        return {"intent": "new_hint"}

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(side_effect=fake_ainvoke)
    mock_build.return_value = mock_graph

    response = client.post(
        "/solve-problem/stream",
        json={
            "query": "next",
            "problem_text": "p",
            "history": [],
        },
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "[DONE]" in response.text


@patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
@patch("ai_backend.routers.solve_problem.resolve_effective_history", return_value=[])
@patch("ai_backend.routers.solve_problem.build_problem_solving_graph")
@patch(
    "ai_backend.routers.solve_problem.asyncio.wait_for",
    side_effect=lambda coro, timeout=None: asyncio.wait_for(coro, timeout=0.05),
)
def test_stream_graph_failure_yields_generic_sse_error(
    _mock_wait: MagicMock,
    mock_build: MagicMock,
    _mock_hist: MagicMock,
    _mock_quota: MagicMock,
) -> None:
    """When the graph task fails, client should see the generic SSE error and [DONE]."""
    mock_graph = MagicMock()

    async def boom(_state: dict, _config: dict) -> dict:
        raise RuntimeError("graph exploded")

    mock_graph.ainvoke = boom
    mock_build.return_value = mock_graph

    response = client.post(
        "/solve-problem/stream",
        json={"query": "q", "problem_text": "p", "history": []},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    text = response.text
    assert "[DONE]" in text
    assert "Eroare internă" in text
