"""
Backward-compatible re-exports for router modules.

Prefer ``from ai_backend.common import ...`` in new code.
"""

from ai_backend.common import (
    LOG_AUTH,
    LOG_SUPABASE,
    PROMPTS,
    Message,
    QueryRequest,
    ensure_jwks_prefetch,
    extract_json_from_text,
    format_exam_timestamp_for_db,
    get_current_user_id,
    get_llm,
    get_solve_quota_count,
    get_supabase_client,
    get_user_id_from_request,
    is_solve_quota_exceeded,
    load_conversation_history_for_user,
    LangGraphChatModel,
    resolve_effective_history,
)

__all__ = [
    "LOG_AUTH",
    "LOG_SUPABASE",
    "PROMPTS",
    "Message",
    "QueryRequest",
    "ensure_jwks_prefetch",
    "extract_json_from_text",
    "format_exam_timestamp_for_db",
    "get_current_user_id",
    "get_llm",
    "LangGraphChatModel",
    "get_solve_quota_count",
    "get_supabase_client",
    "get_user_id_from_request",
    "is_solve_quota_exceeded",
    "load_conversation_history_for_user",
    "resolve_effective_history",
]
