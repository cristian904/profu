"""
Pydantic models for clarify-with-steps (guided learning) service.
"""

from pydantic import BaseModel, Field


class GuidedLearningPrerequisitesOutput(BaseModel):
    """Structured LLM output for prerequisite list generation (first graph node)."""

    prerequisites: list[str] = Field(
        default_factory=list,
        description="Ordered list of prerequisite concept names to cover before the main question.",
    )
