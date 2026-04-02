"""
Integration tests for the streaming functionality.
Tests both Clarify Once and Clarify Step-by-Step streaming endpoints.
"""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from ai_backend.main import app
from ai_backend.common.llm import get_llm

client = TestClient(app)


class TestStreamingIntegration:
    """Integration tests for SSE streaming (Clarify Once mode)."""

    def test_stream_response_format(self) -> None:
        """Test that streaming response follows SSE format."""
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"

    def test_stream_includes_done_signal(self) -> None:
        """Test that streaming includes [DONE] signal."""
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"},
        )

        content = response.text
        assert "data: [DONE]" in content

    async def _fake_astream(self, chunks: list) -> None:
        """Helper async generator for mocking llm.astream."""
        for c in chunks:
            yield c

    def test_stream_handles_empty_chunks(self) -> None:
        """Test that streaming handles empty chunks gracefully."""
        mock_chunk_empty = MagicMock()
        mock_chunk_empty.content = ""
        mock_chunk_valid = MagicMock()
        mock_chunk_valid.content = "Valid"

        mock_llm = AsyncMock()
        mock_llm.astream = MagicMock(return_value=self._fake_astream([mock_chunk_empty, mock_chunk_valid]))
        app.dependency_overrides[get_llm] = lambda: mock_llm

        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"},
        )

        assert response.status_code == 200

    def test_stream_includes_meta_ttft(self) -> None:
        """Test that streaming includes [META]{ttft} before first token."""
        response = client.post("/clarify/once-stream", json={"query": "Test"})
        assert response.status_code == 200
        assert "data: [META]" in response.text


class TestStepByStepIntegration:
    """Integration tests for SSE streaming (Clarify Step-by-Step mode)."""

    async def _fake_astream(self, chunks: list) -> None:
        for c in chunks:
            yield c

    def test_step_by_step_followup_includes_meta_and_done(self) -> None:
        """Test follow-up path emits [META] and [DONE]."""
        mock_chunk = MagicMock()
        mock_chunk.content = "Răspuns\ncu newline"

        mock_llm = AsyncMock()
        mock_llm.astream = MagicMock(return_value=self._fake_astream([mock_chunk]))
        app.dependency_overrides[get_llm] = lambda: mock_llm

        response = client.post(
            "/clarify/step-by-step-stream",
            json={
                "query": "Follow-up",
                "history": [{"role": "user", "content": "Start"}],
            },
        )
        assert response.status_code == 200
        body = response.text
        assert "data: [META]" in body
        assert "data: [DONE]" in body
        assert "\\n" in body


class TestErrorHandling:
    """Test error handling in streaming."""

    def test_stream_handles_llm_errors(self) -> None:
        """Test that streaming handles LLM errors gracefully."""

        async def _astream_raises(*args: object, **kwargs: object):
            raise RuntimeError("LLM Error")
            if False:
                yield None  # makes this an async generator for `async for`

        mock_llm = AsyncMock()
        mock_llm.astream = _astream_raises
        app.dependency_overrides[get_llm] = lambda: mock_llm

        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"},
        )

        assert response.status_code == 200
        content = response.text
        assert "Eroare" in content or "data: [DONE]" in content
