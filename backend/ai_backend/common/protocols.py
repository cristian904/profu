"""
Structural types (``typing.Protocol``) for dependency boundaries.

Keeps typing explicit without extra wrapper classes: real LangChain models satisfy these protocols.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class LangGraphChatModel(Protocol):
    """
    Minimal chat model surface used by LangGraph node factories and SSE streamers.

    Satisfied by ``ChatGoogleGenerativeAI`` and test doubles that implement the same methods.
    """

    def with_structured_output(
        self,
        schema: Any,
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Bind a schema (e.g. Pydantic model) for parsed structured responses."""
        ...

    async def ainvoke(self, input: Any, config: Any | None = None) -> Any:
        """Single-shot invocation (messages in, message or structured result out)."""
        ...

    async def astream(self, input: Any, config: Any | None = None) -> AsyncIterator[Any]:
        """Token/chunk stream for SSE-style endpoints."""
        ...
