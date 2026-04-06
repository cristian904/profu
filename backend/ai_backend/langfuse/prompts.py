"""
PromptComposer: loads prompt text from Langfuse Prompt Management with local YAML fallback.

Uses Langfuse SDK's built-in caching (60 s TTL, background refresh) so network
calls are rare after the first fetch. When Langfuse is disabled or a prompt has
not been seeded yet, falls back to ``prompts.yaml`` automatically.

Can be used as:
1. **FastAPI dependency** (recommended): ``Depends(get_prompt_composer)`` in route handlers.
2. **Singleton** (legacy): ``get_prompt_composer()`` in non-request code (e.g. background tasks).

Lifecycle:
    1. ``create_prompt_composer()`` — called once during the FastAPI lifespan.
    2. **Dependency mode**: Router/service receives ``composer`` via ``Depends(get_prompt_composer)``.
    3. **Singleton mode** (fallback): ``get_prompt_composer()`` returns the stored instance.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from profu_logging.feature_logger import get_feature_logger

LOG = get_feature_logger(source="prompt_composer")

# Prefix used in scripts/seed_langfuse_prompts.py
_LANGFUSE_PREFIX = "profu"

# Module-level singleton — set by create_prompt_composer().
_composer: Optional["PromptComposer"] = None


class PromptComposer:
    """Resolve prompt text from Langfuse with YAML fallback.

    The class wraps ``langfuse.get_prompt()`` and transparently falls
    back to the local ``prompts.yaml`` dict when Langfuse is unavailable
    (keys not set, network error, prompt not seeded, etc.).

    Prompt paths use **dot notation** that mirrors the YAML structure
    *without* the trailing ``system_prompt`` key:

    - ``"clarify_chat"``
    - ``"guided_learning.question_asker"``
    - ``"problem_solving.hint_provider"``

    These are mapped to Langfuse names like ``profu/clarify_chat``,
    ``profu/guided_learning/question_asker``, etc.
    """

    def __init__(self, langfuse_client: Any, yaml_prompts: Dict[str, Any]) -> None:
        """
        Initialise the composer.

        Args:
            langfuse_client: Langfuse SDK instance (may be disabled / None).
            yaml_prompts: Parsed ``prompts.yaml`` dict (local fallback).
        """
        self._client = langfuse_client
        self._yaml = yaml_prompts
        self._langfuse_available = self._check_langfuse_available()

    def _check_langfuse_available(self) -> bool:
        """Return True when the Langfuse client is properly initialised for prompt fetch."""
        if self._client is None:
            return False
        # The SDK sets _resources to None when public/secret keys are missing.
        return getattr(self._client, "_resources", None) is not None

    def get(self, path: str) -> str:
        """
        Return the system prompt text for the given dotted path.

        Tries Langfuse first (with SDK-level caching); falls back to
        ``prompts.yaml`` on any error or when Langfuse is disabled.

        Args:
            path: Dot-separated YAML key path *excluding* the trailing
                  ``system_prompt`` key.  E.g. ``"clarify_chat"``,
                  ``"guided_learning.question_asker"``.

        Returns:
            The prompt text string.

        Raises:
            KeyError: If the path does not exist in the YAML fallback *and*
                      Langfuse also fails to provide the prompt.
        """
        yaml_text = self._yaml_fallback(path)

        if not self._langfuse_available:
            return yaml_text

        langfuse_name = self._langfuse_name(path)
        try:
            prompt_client = self._client.get_prompt(
                langfuse_name,
                type="text",
                label="production",
                fallback=yaml_text,
            )
            return prompt_client.compile()
        except Exception as e:
            LOG.warning(
                f"Langfuse prompt fetch failed for '{langfuse_name}', "
                f"using YAML fallback: {e!s}",
                user_id=None,
            )
            return yaml_text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _langfuse_name(path: str) -> str:
        """Convert dot path to Langfuse prompt name (e.g. ``profu/guided_learning/question_asker``)."""
        return f"{_LANGFUSE_PREFIX}/{path.replace('.', '/')}"

    def _yaml_fallback(self, path: str) -> str:
        """Walk the YAML dict to find ``system_prompt`` at the given dot path."""
        parts = path.split(".")
        node: Any = self._yaml
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"Prompt path '{path}' not found in prompts.yaml")
            node = node[part]
        if isinstance(node, dict) and "system_prompt" in node:
            return node["system_prompt"]
        raise KeyError(f"No 'system_prompt' at path '{path}' in prompts.yaml")


def create_prompt_composer(
    langfuse_client: Any,
    yaml_prompts: Dict[str, Any],
) -> PromptComposer:
    """
    Create and store the global ``PromptComposer`` singleton.

    Call once during FastAPI lifespan, after ``create_langfuse_client()``.

    Args:
        langfuse_client: Initialised ``Langfuse`` instance.
        yaml_prompts: Parsed ``prompts.yaml`` dict.

    Returns:
        The initialised ``PromptComposer``.
    """
    global _composer
    _composer = PromptComposer(langfuse_client, yaml_prompts)
    mode = "Langfuse + YAML fallback" if _composer._langfuse_available else "YAML-only (Langfuse disabled)"
    LOG.info(f"PromptComposer initialised ({mode})", user_id=None)
    return _composer


def get_prompt_composer() -> PromptComposer:
    """
    FastAPI dependency that returns the ``PromptComposer`` singleton.

    Use in route handlers and services via ``Depends(get_prompt_composer)``.

    Also works as a direct function call (e.g. for background tasks or
    non-request code) when the singleton has been initialised.

    Raises:
        RuntimeError: If ``create_prompt_composer()`` has not been called yet.

    Examples:
        **As FastAPI dependency:**
        ```python
        @router.post("/clarify")
        async def clarify(
            req: ClarifyRequest,
            composer: PromptComposer = Depends(get_prompt_composer),
        ) -> StreamingResponse:
            system_prompt = composer.get("clarify_chat")
            ...
        ```

        **As singleton (legacy):**
        ```python
        async def some_background_task():
            composer = get_prompt_composer()
            system_prompt = composer.get("clarify_chat")
            ...
        ```
    """
    if _composer is None:
        raise RuntimeError(
            "PromptComposer not initialised. "
            "Call create_prompt_composer() during app startup."
        )
    return _composer
