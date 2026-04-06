"""
Pydantic models for clarify guardrails (structured LLM output).
"""

from pydantic import BaseModel, Field


class ClarifyGuardrailsOutput(BaseModel):
    """
    Structured decision from the guardrails model: allow tutoring or block with a Romanian message.
    """

    allow: bool = Field(
        description="True if the student message is appropriate for school tutoring and names a real or coherent curricular concept.",
    )
    reason_code: str = Field(
        default="allowed",
        description="Machine-readable reason: allowed | off_topic | unknown_concept | unsafe_or_abuse | parse_error.",
    )
    student_facing_message_ro: str = Field(
        default="",
        description="When allow is false, a short polite message in Romanian for the student. Empty when allow is true.",
    )
