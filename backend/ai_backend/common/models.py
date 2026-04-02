"""
Shared Pydantic models used across routers and services (chat history, clarify requests).
"""

from pydantic import BaseModel


class Message(BaseModel):
    """Message model for conversation history."""

    role: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    """Request model for chat queries (clarify-once and clarify-with-steps)."""

    query: str
    history: list[Message] = []  # Optional; BE may load from DB instead
    conversation_id: int | None = None  # Optional Supabase conversation id (preferred for history loading)
