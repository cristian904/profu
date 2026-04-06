"""
Cache ``with_structured_output`` guardrails runnables per LLM instance (weak keys to avoid leaks).
"""

from __future__ import annotations

import weakref
from typing import Any

from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.services.clarify_guardrails.models import ClarifyGuardrailsOutput

# WeakKeyDict: when an LLM object is GC'd, its cached structured runnable is dropped.
_guardrails_structured_cache: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()


def get_guardrails_structured_llm(llm: LangGraphChatModel) -> Any:
    """
    Return a cached structured-output runnable for guardrails (one binding per LLM identity).

    Args:
        llm: Base chat model (same instance should be reused across requests in production).

    Returns:
        Runnable that returns structured ``ClarifyGuardrailsOutput`` (with ``include_raw=True``).
    """
    try:
        cached = _guardrails_structured_cache.get(llm)
    except TypeError:
        # WeakKeyDictionary key lookup can fail for some chat models (e.g. ChatGoogleGenerativeAI:
        # ``unhashable type``). Skip cache and return a fresh structured-output runnable.
        return llm.with_structured_output(ClarifyGuardrailsOutput, include_raw=True)
    if cached is not None:
        return cached
    bound = llm.with_structured_output(ClarifyGuardrailsOutput, include_raw=True)
    try:
        _guardrails_structured_cache[llm] = bound
    except TypeError:
        # Non-weakref-able mocks or proxies: no cache.
        return bound
    return bound
