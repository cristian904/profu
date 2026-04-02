"""
Conversation history resolution: prefer Supabase when conversation_id is provided.
"""

from typing import Any, Optional
from uuid import UUID

from ai_backend.common.models import Message
from ai_backend.common.supabase_helpers import load_conversation_history_for_user
from profu_logging.feature_logger import get_feature_logger

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
    - If conversation_id is provided, load from Supabase when the row belongs to the user;
      if non-empty, use it.
    - Otherwise fall back to request_history.
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
