"""
Shared helpers for the AI backend: auth, Supabase, LLM, prompts, models, JSON parsing.

Routers may import from ``ai_backend.common`` or use ``ai_backend.routers.common`` (re-exports).
"""

from ai_backend.common.auth import (
    LOG_AUTH,
    ensure_jwks_prefetch,
    get_current_user_id,
    get_user_id_from_request,
)
from ai_backend.common.conversation_history import resolve_effective_history
from ai_backend.common.exam_timestamps import format_exam_timestamp_for_db
from ai_backend.common.json_extract import extract_json_from_text
from ai_backend.common.llm import get_llm
from ai_backend.common.models import Message, QueryRequest
from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.common.prompts import PROMPTS
from ai_backend.common.supabase_helpers import (
    LOG_SUPABASE,
    get_solve_quota_count,
    get_supabase_client,
    is_solve_quota_exceeded,
    load_conversation_history_for_user,
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
