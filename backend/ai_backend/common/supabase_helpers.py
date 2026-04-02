"""
Supabase client dependency, solve-problem quota, and conversation history loading.
"""

from typing import Any, Optional
from uuid import UUID

from supabase import create_client

from ai_backend.common.models import Message
from ai_backend.config import settings
from profu_logging.feature_logger import get_feature_logger

LOG_SUPABASE = get_feature_logger(source="supabase")


def get_supabase_client() -> Optional[Any]:
    """
    FastAPI dependency: returns Supabase client, or None if URL/key not configured.
    """
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def get_solve_quota_count(user_id: UUID, supabase_client: Optional[Any] = None) -> int:
    """
    Return the number of solve (problem_solving) conversations for the user in the current month.
    Uses Supabase RPC get_solve_conversations_count_current_month.
    """
    if supabase_client is None:
        return 0
    try:
        r = supabase_client.rpc(
            "get_solve_conversations_count_current_month",
            {"p_user_id": str(user_id)},
        ).execute()
        data = getattr(r, "data", None)
        if data is not None and isinstance(data, (list, tuple)) and len(data) > 0:
            return int(data[0]) if data[0] is not None else 0
        if data is not None and isinstance(data, (int, float)):
            return int(data)
        return 0
    except Exception:
        return 0


def is_solve_quota_exceeded(
    user_id: UUID,
    supabase_client: Optional[Any],
    threshold: int,
) -> bool:
    """
    Return True when monthly solve quota is enabled and usage is at or above the threshold.
    """
    if threshold <= 0:
        return False
    count = get_solve_quota_count(user_id, supabase_client)
    return count >= threshold


def load_conversation_history_for_user(
    user_id: UUID, conversation_id: int, supabase_client: Optional[Any] = None
) -> list[Message]:
    """
    Load full conversation history for a given user and conversation_id from Supabase.
    Ensures the conversation belongs to the user before returning any messages.
    """
    if supabase_client is None:
        return []

    try:
        conv_resp = (
            supabase_client.table("conversations")
            .select("id,user_id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        conv_rows = getattr(conv_resp, "data", None) or []
        if not conv_rows:
            return []
        conv = conv_rows[0]
        if str(conv.get("user_id")) != str(user_id):
            return []

        msg_resp = (
            supabase_client.table("conversation_messages")
            .select("speaker,content,created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .execute()
        )
        rows = getattr(msg_resp, "data", None) or []

        history: list[Message] = []
        for row in rows:
            speaker = (row.get("speaker") or "").strip() or "assistant"
            role = "user" if speaker == "user" else "assistant"
            content = row.get("content") or ""
            history.append(Message(role=role, content=content))
        return history
    except Exception as e:
        LOG_SUPABASE.warning(f"Failed to load conversation history from Supabase: {e!s}", user_id=user_id)
        return []
