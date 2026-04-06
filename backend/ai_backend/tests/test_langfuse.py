"""
Tests for ``ai_backend.langfuse`` — client singleton and trace context helpers.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai_backend.langfuse import (
    create_langfuse_client,
    get_langfuse_client,
    langfuse_trace_context,
)
from langfuse.langchain import CallbackHandler


@pytest.fixture(autouse=True)
def reset_langfuse_singleton() -> None:
    """Ensure ``_client`` is cleared so tests do not leak global state."""
    import ai_backend.langfuse.client as client_mod

    previous = client_mod._client
    client_mod._client = None
    yield
    client_mod._client = previous


def test_package_exports() -> None:
    """Public re-exports from ``ai_backend.langfuse`` are importable."""
    from ai_backend import langfuse as pkg

    assert set(pkg.__all__) == {
        "create_langfuse_client",
        "get_langfuse_client",
        "langfuse_trace_context",
        "llm_config",
        "node_span",
        "resolve_session_id",
        "PromptComposer",
        "create_prompt_composer",
        "get_prompt_composer",
    }


def test_get_langfuse_client_raises_before_initialisation() -> None:
    """``get_langfuse_client`` fails fast when startup did not run."""
    with pytest.raises(RuntimeError, match="Langfuse client not initialised"):
        get_langfuse_client()


def test_create_langfuse_client_disabled_without_keys() -> None:
    """Missing keys produce a disabled client and register the singleton."""
    settings = SimpleNamespace(
        langfuse_public_key="",
        langfuse_secret_key="",
        langfuse_host="https://cloud.langfuse.com",
    )
    client = create_langfuse_client(settings)
    assert client is not None
    assert getattr(client, "_tracing_enabled", None) is False
    assert get_langfuse_client() is client


@patch("ai_backend.langfuse.client.Langfuse")
def test_create_langfuse_client_with_keys_calls_langfuse(
    mock_langfuse: MagicMock,
) -> None:
    """When keys are set, ``Langfuse`` is constructed with host and keys."""
    mock_instance = MagicMock()
    mock_langfuse.return_value = mock_instance
    settings = SimpleNamespace(
        langfuse_public_key="pk-lf-test",
        langfuse_secret_key="sk-lf-test",
        langfuse_host="https://custom.langfuse.example",
    )
    out = create_langfuse_client(settings)
    mock_langfuse.assert_called_once_with(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        host="https://custom.langfuse.example",
        flush_interval=1.0,
    )
    assert out is mock_instance
    assert get_langfuse_client() is mock_instance


@pytest.mark.asyncio
async def test_langfuse_trace_context_yields_callback_and_metadata() -> None:
    """Context yields LangChain config with ``CallbackHandler`` and Langfuse metadata keys."""
    trace_id = "a" * 32
    async with langfuse_trace_context(
        trace_id=trace_id,
        session_id="session-abc",
        user_id="user-123",
        name="unit_test_trace",
        tags=["unit", "langfuse"],
    ) as cfg:
        assert "callbacks" in cfg
        assert "metadata" in cfg
        assert len(cfg["callbacks"]) == 1
        handler = cfg["callbacks"][0]
        assert isinstance(handler, CallbackHandler)
        assert handler._trace_context is not None
        assert handler._trace_context["trace_id"] == trace_id
        meta = cfg["metadata"]
        assert meta["langfuse_user_id"] == "user-123"
        assert meta["langfuse_session_id"] == "session-abc"
        assert meta["langfuse_tags"] == ["unit", "langfuse"]


@pytest.mark.asyncio
async def test_langfuse_trace_context_generates_trace_id_when_omitted() -> None:
    """Omitted ``trace_id`` is replaced with a 32-char lowercase hex string."""
    async with langfuse_trace_context(user_id=None) as cfg:
        handler = cfg["callbacks"][0]
        tid = handler._trace_context["trace_id"]
        assert len(tid) == 32
        uuid.UUID(hex=tid)  # raises if invalid hex


@pytest.mark.asyncio
async def test_langfuse_trace_context_minimal_metadata() -> None:
    """Optional fields omit corresponding metadata keys."""
    async with langfuse_trace_context() as cfg:
        assert cfg["metadata"] == {}
