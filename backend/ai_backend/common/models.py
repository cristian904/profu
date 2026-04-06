"""
Shared Pydantic models used across routers and services (chat history, clarify requests).
"""

from typing import Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message model for conversation history."""

    role: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    """Request model for chat queries (clarify-once and clarify-with-steps)."""

    query: str
    history: list[Message] = []  # Optional; BE may load from DB instead
    conversation_id: int | None = None  # Optional Supabase conversation id (preferred for history loading)
    # Langfuse tracing (optional; generated server-side when absent)
    trace_id: Optional[str] = Field(default=None, description="32-char lowercase hex Langfuse trace id")
    session_id: Optional[str] = Field(default=None, description="Logical session id for grouping traces")
