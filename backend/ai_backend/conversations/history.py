"""
Conversation history resolution helpers.

Centralizes the logic that prefers Supabase conversation history when a conversation_id is provided.
"""

from typing import Any, Optional
from uuid import UUID

from profu_logging.feature_logger import get_feature_logger
from ai_backend.routers.common import Message, load_conversation_history_for_user

LOG_SUPABASE = get_feature_logger(source="supabase")


def resolve_effective_history(
    user_id: UUID,
    request_history: list[Message],
    conversation_id: int | None,
    supabase_client: Optional[Any] = None,
) -> list[Message]:
    """
    Resolve the effective conversation history for an incoming request.

    Preference order:
    - If conversation_id is provided, attempt to load history from Supabase (and only if it belongs to user).
      If load returns non-empty, use it.
    - Otherwise (or on failure/empty), fall back to request_history.

    Args:
        user_id: Authenticated user UUID.
        request_history: History provided by the client request body.
        conversation_id: Optional Supabase conversation id.
        supabase_client: Supabase client (or None if not configured).

    Returns:
        A list of Message objects to use as history.
    """
    try:
        if conversation_id is None:
            return request_history

        loaded = load_conversation_history_for_user(user_id, conversation_id, supabase_client)
        if loaded:
            return loaded

        return request_history
    except Exception as e:
        LOG_SUPABASE.warning(f"Failed to resolve effective history: {e!s}", user_id=user_id)
        return request_history

