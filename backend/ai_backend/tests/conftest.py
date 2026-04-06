"""
Shared pytest fixtures for ai_backend tests.

- Default auth override: Depends(get_current_user_id) returns a stable fake UUID.
- Default LLM override: Depends(get_llm) returns an AsyncMock so tests do not require
  GOOGLE_API_KEY (patching router modules does not affect FastAPI Depends() bindings).
- PromptComposer: initialised once (session-scoped) in YAML-only mode so service code
  can call ``get_prompt_composer()`` without Langfuse keys.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_backend.main import app
from ai_backend.common.auth import get_current_user_id
from ai_backend.common.llm import get_llm
from ai_backend.common.prompts import PROMPTS
from ai_backend.langfuse.prompts import PromptComposer, create_prompt_composer, get_prompt_composer
from ai_backend.services.clarify_with_steps.models import GuidedLearningPrerequisitesOutput
from ai_backend.services.solve_problem.models import (
    SolveProblemIntentDetection,
    SolveProblemProgressIntent,
)

_FAKE_AUTH_USER = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _default_mock_llm() -> MagicMock:
    """
    Build an LLM mock suitable for clarify-once (astream) and clarify step-by-step / solve-problem
    (``with_structured_output`` + astream).
    """
    mock_llm = MagicMock()

    # Include a prerequisite-completion phrase so clarify step-by-step does not loop forever:
    # nodes.ask_prerequisite_question advances only when content matches completion_indicators.
    _MOCK_LLM_REPLY = "Test response — foarte bine, ai înțeles; putem trece mai departe."

    async def _astream_impl(*args: object, **kwargs: object):
        chunk = MagicMock()
        chunk.content = _MOCK_LLM_REPLY
        yield chunk

    mock_llm.astream = MagicMock(side_effect=_astream_impl)

    async def _plain_ainvoke_impl(*args: object, **kwargs: object) -> MagicMock:
        response = MagicMock()
        response.content = _MOCK_LLM_REPLY
        return response

    mock_llm.ainvoke = AsyncMock(side_effect=_plain_ainvoke_impl)

    def _with_structured_output(schema: Any, **kwargs: Any) -> MagicMock:
        name = getattr(schema, "__name__", type(schema).__name__)
        chain = MagicMock()
        if name == "GuidedLearningPrerequisitesOutput":
            chain.ainvoke = AsyncMock(
                return_value={
                    "raw": MagicMock(content=""),
                    "parsed": GuidedLearningPrerequisitesOutput(prerequisites=["Concept A"]),
                    "parsing_error": None,
                }
            )
        elif name == "SolveProblemIntentDetection":
            chain.ainvoke = AsyncMock(
                return_value={
                    "raw": MagicMock(content=""),
                    "parsed": SolveProblemIntentDetection(intent="new_hint"),
                    "parsing_error": None,
                }
            )
        elif name == "SolveProblemProgressIntent":
            chain.ainvoke = AsyncMock(
                return_value={
                    "raw": MagicMock(content=""),
                    "parsed": SolveProblemProgressIntent(progress_intent="good"),
                    "parsing_error": None,
                }
            )
        else:
            chain.ainvoke = AsyncMock(return_value={"raw": MagicMock(content=""), "parsed": None, "parsing_error": None})
        return chain

    mock_llm.with_structured_output = MagicMock(side_effect=_with_structured_output)
    return mock_llm


@pytest.fixture(autouse=True, scope="session")
def _init_prompt_composer() -> None:
    """Initialise PromptComposer in YAML-only mode for the test session."""
    try:
        get_prompt_composer()
    except RuntimeError:
        create_prompt_composer(langfuse_client=None, yaml_prompts=PROMPTS)


@pytest.fixture
def prompt_composer() -> PromptComposer:
    """Provide PromptComposer to tests."""
    return get_prompt_composer()


@pytest.fixture(autouse=True)
def _default_dependency_overrides(request: pytest.FixtureRequest) -> None:
    """
    Apply auth and get_llm overrides unless the test opts out via markers.
    """
    no_auth = request.node.get_closest_marker("no_auth_dependency_override")
    no_llm = request.node.get_closest_marker("no_llm_dependency_override")

    if not no_auth:
        app.dependency_overrides[get_current_user_id] = lambda: _FAKE_AUTH_USER
    if not no_llm:
        app.dependency_overrides[get_llm] = _default_mock_llm

    yield

    if not no_auth:
        app.dependency_overrides.pop(get_current_user_id, None)
    if not no_llm:
        app.dependency_overrides.pop(get_llm, None)
