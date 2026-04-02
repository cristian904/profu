"""
Pydantic request/response models for the solve-problem feature.
"""

from pydantic import BaseModel, Field

from ai_backend.common.models import Message


class SolveProblemIntentDetection(BaseModel):
    """Structured LLM output for intent detection (LangGraph node 1)."""

    intent: str = Field(
        default="new_hint",
        description=(
            'User intent: "solve" (full solution), "progress" (showing work), '
            'or "new_hint" (another hint).'
        ),
    )


class SolveProblemProgressIntent(BaseModel):
    """Structured LLM output for progress quality (LangGraph node 4)."""

    progress_intent: str = Field(
        default="good",
        description='Whether student work is on track: "good" or "bad".',
    )


class ProblemSolveRequest(BaseModel):
    """Request model for problem solving conversation."""

    query: str
    problem_text: str
    history: list[Message] = []  # Optional; BE may load from DB instead
    conversation_id: int | None = None  # Optional Supabase conversation id (preferred for history loading)


class SuggestProblemRequest(BaseModel):
    """Request model for similar problem suggestions."""

    problem_text: str


class SuggestedProblemItem(BaseModel):
    """One suggested problem (statement only for FE buttons)."""

    statement: str


class SuggestProblemResponse(BaseModel):
    """Response for /suggest-problem: message + list of problems for FE buttons."""

    message: str
    problems: list[SuggestedProblemItem]
