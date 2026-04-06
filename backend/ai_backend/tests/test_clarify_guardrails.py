"""
Unit tests for clarify guardrails helpers, evaluator, and compiled graph caching.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_backend.common.models import Message
from ai_backend.services.clarify_guardrails.constants import CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO
from ai_backend.services.clarify_guardrails.context import format_messages_for_guardrails_context
from ai_backend.services.clarify_guardrails.evaluator import evaluate_clarify_guardrails
from ai_backend.services.clarify_guardrails.models import ClarifyGuardrailsOutput
from ai_backend.services.clarify_guardrails.nodes import route_after_clarify_guardrails
from ai_backend.services.clarify_once.graph import get_compiled_clarify_once_graph
from ai_backend.services.clarify_with_steps.graph import get_compiled_step_by_step_learning_graph


def test_format_messages_for_guardrails_context_empty() -> None:
    """Empty history yields an empty context string."""
    assert format_messages_for_guardrails_context([]) == ""


def test_format_messages_for_guardrails_context_skips_blank() -> None:
    """Blank message bodies are omitted from the transcript."""
    history = [
        Message(role="user", content="   "),
        Message(role="user", content="Hello"),
    ]
    assert format_messages_for_guardrails_context(history) == "user: Hello"


def test_format_messages_for_guardrails_context_tail_limit() -> None:
    """Only the last ``max_messages`` entries are included."""
    history = [
        Message(role="user", content="a"),
        Message(role="assistant", content="b"),
        Message(role="user", content="c"),
    ]
    out = format_messages_for_guardrails_context(history, max_messages=2)
    assert "user: a" not in out
    assert "assistant: b" in out
    assert "user: c" in out


def test_route_after_clarify_guardrails_continue() -> None:
    """Allowed state routes to the continue branch."""
    assert route_after_clarify_guardrails({"guardrails_allowed": True}) == "continue"


def test_route_after_clarify_guardrails_blocked() -> None:
    """Denied state routes to the blocked branch."""
    assert route_after_clarify_guardrails({"guardrails_allowed": False}) == "blocked"


def test_route_after_clarify_guardrails_missing_defaults_blocked() -> None:
    """Missing flag is treated as blocked (fail-closed routing)."""
    assert route_after_clarify_guardrails({}) == "blocked"


@pytest.mark.asyncio
async def test_evaluate_clarify_guardrails_empty_query_short_circuits(prompt_composer) -> None:
    """Whitespace-only query never calls the structured LLM."""
    llm = MagicMock()
    result = await evaluate_clarify_guardrails(
        llm=llm,
        composer=prompt_composer,
        user_query="   ",
        conversation_context="",
        user_id="test-user",
    )
    assert result.allow is False
    assert result.reason_code == "off_topic"
    assert result.student_facing_message_ro == CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO
    llm.with_structured_output.assert_not_called()


@pytest.mark.asyncio
async def test_evaluate_clarify_guardrails_allow_from_structured(prompt_composer) -> None:
    """Structured allow=true is normalized with reason_code allowed."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock(
        return_value={
            "raw": MagicMock(content=""),
            "parsed": ClarifyGuardrailsOutput(
                allow=True,
                reason_code="off_topic",
                student_facing_message_ro="should clear",
            ),
            "parsing_error": None,
        }
    )
    llm = MagicMock()
    with patch(
        "ai_backend.services.clarify_guardrails.evaluator.get_guardrails_structured_llm",
        return_value=chain,
    ):
        result = await evaluate_clarify_guardrails(
            llm=llm,
            composer=prompt_composer,
            user_query="Explică derivata",
            conversation_context="",
            user_id=None,
        )
    assert result.allow is True
    assert result.reason_code == "allowed"
    assert result.student_facing_message_ro == ""


@pytest.mark.asyncio
async def test_evaluate_clarify_guardrails_block_fills_default_message(prompt_composer) -> None:
    """When allow=false and empty student message, use shared default Romanian string."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock(
        return_value={
            "raw": MagicMock(content=""),
            "parsed": ClarifyGuardrailsOutput(
                allow=False,
                reason_code="off_topic",
                student_facing_message_ro="",
            ),
            "parsing_error": None,
        }
    )
    llm = MagicMock()
    with patch(
        "ai_backend.services.clarify_guardrails.evaluator.get_guardrails_structured_llm",
        return_value=chain,
    ):
        result = await evaluate_clarify_guardrails(
            llm=llm,
            composer=prompt_composer,
            user_query="spam",
            conversation_context="",
            user_id=None,
        )
    assert result.allow is False
    assert result.student_facing_message_ro == CLARIFY_GUARDRAILS_DEFAULT_BLOCK_MESSAGE_RO


@pytest.mark.no_llm_dependency_override
def test_get_compiled_clarify_once_graph_cache(prompt_composer) -> None:
    """Same (llm, composer) pair returns the identical compiled graph object."""
    llm_a = MagicMock()
    g1 = get_compiled_clarify_once_graph(llm_a, prompt_composer)
    g2 = get_compiled_clarify_once_graph(llm_a, prompt_composer)
    assert g1 is g2

    llm_b = MagicMock()
    g3 = get_compiled_clarify_once_graph(llm_b, prompt_composer)
    assert g3 is not g1


class _DummyLlmForCache:
    """Minimal LLM stand-in that supports weakref-based structured-output cache."""

    def __init__(self) -> None:
        self.bind_count = 0

    def with_structured_output(self, schema: object, **kwargs: object) -> MagicMock:
        self.bind_count += 1
        chain = MagicMock()
        chain.ainvoke = AsyncMock(
            return_value={
                "raw": MagicMock(content=""),
                "parsed": ClarifyGuardrailsOutput(allow=True, reason_code="allowed", student_facing_message_ro=""),
                "parsing_error": None,
            }
        )
        return chain


class _UnhashableLlmStub:
    """
    Stand-in for chat models that cannot be used as ``WeakKeyDictionary`` keys.

    ``weakref.WeakKeyDictionary.get`` raises ``TypeError: unhashable type`` for
    instances (same failure mode as ``ChatGoogleGenerativeAI`` in production).
    """

    __hash__ = None  # type: ignore[assignment]

    def __init__(self) -> None:
        self.bind_count = 0

    def __eq__(self, other: object) -> bool:
        return False

    def with_structured_output(self, schema: object, **kwargs: object) -> MagicMock:
        self.bind_count += 1
        chain = MagicMock()
        chain.ainvoke = AsyncMock(return_value={})
        return chain


def test_weak_key_dict_rejects_unhashable_llm_like_stub() -> None:
    """Sanity check: unhashable instances hit the same WeakKeyDictionary TypeError as Google chat models."""
    import weakref

    llm = _UnhashableLlmStub()
    cache: weakref.WeakKeyDictionary[object, object] = weakref.WeakKeyDictionary()
    with pytest.raises(TypeError, match="unhashable"):
        cache.get(llm)


def test_get_guardrails_structured_llm_unhashable_llm_no_typeerror_skips_cache() -> None:
    """
    Guardrails structured runnable must not crash when the base LLM is unhashable.

    Regression: ``WeakKeyDictionary.get(llm)`` raised before a try/except that only
    wrapped assignment, causing ``TypeError: unhashable type: 'ChatGoogleGenerativeAI'``.
    """
    from ai_backend.services.clarify_guardrails.structured_llm import get_guardrails_structured_llm

    llm = _UnhashableLlmStub()
    first = get_guardrails_structured_llm(llm)
    second = get_guardrails_structured_llm(llm)
    assert first is not second
    assert llm.bind_count == 2


@pytest.mark.no_llm_dependency_override
def test_get_guardrails_structured_llm_chat_google_generative_ai_no_weak_key_crash() -> None:
    """
    Real ``ChatGoogleGenerativeAI`` cannot be keyed in ``WeakKeyDictionary``; helper must still work.

    Uses a dummy API key (no network): only ``with_structured_output`` is exercised.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    from ai_backend.services.clarify_guardrails.structured_llm import get_guardrails_structured_llm

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key="unit-test-key-unused")
    first = get_guardrails_structured_llm(llm)
    second = get_guardrails_structured_llm(llm)
    assert first is not second


def test_get_guardrails_structured_llm_returns_cached_instance() -> None:
    """Second call with the same LLM returns the same structured runnable (weak-key cache)."""
    from ai_backend.services.clarify_guardrails.structured_llm import get_guardrails_structured_llm

    llm = _DummyLlmForCache()
    first = get_guardrails_structured_llm(llm)
    second = get_guardrails_structured_llm(llm)
    assert first is second
    assert llm.bind_count == 1


@pytest.mark.asyncio
async def test_evaluate_clarify_guardrails_keyerror_on_missing_prompt(prompt_composer) -> None:
    """Missing YAML path returns fail-closed output."""
    from ai_backend.services.clarify_guardrails.evaluator import evaluate_clarify_guardrails

    composer = MagicMock()
    composer.get = MagicMock(side_effect=KeyError("clarify_guardrails"))
    llm = MagicMock()
    result = await evaluate_clarify_guardrails(
        llm=llm,
        composer=composer,
        user_query="text",
        conversation_context="",
        user_id="u1",
    )
    assert result.allow is False
    assert result.reason_code == "parse_error"


@pytest.mark.no_llm_dependency_override
def test_get_compiled_step_by_step_graph_cache(prompt_composer) -> None:
    """Step-by-step graph is cached per (llm, composer) identity."""
    llm_a = MagicMock()
    g1 = get_compiled_step_by_step_learning_graph(llm_a, prompt_composer)
    g2 = get_compiled_step_by_step_learning_graph(llm_a, prompt_composer)
    assert g1 is g2
