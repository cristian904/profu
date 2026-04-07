"""
Pydantic models for RAG similar-problem suggestions.
"""

from pydantic import BaseModel


class SuggestProblemRequest(BaseModel):
    """Request model for similar problem suggestions."""

    problem_text: str


class SuggestedProblemItem(BaseModel):
    """One suggested problem (statement only for FE buttons)."""

    statement: str


class SuggestProblemResponse(BaseModel):
    """Response for suggest-problem: message + list of problems for FE buttons."""

    message: str
    problems: list[SuggestedProblemItem]
