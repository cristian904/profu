"""
Common utilities and models shared between clarify and solve routers.
"""
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import yaml
from supabase import create_client
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, status
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ai_backend.config import settings
from ai_backend.logging.feature_logger import get_feature_logger

# Feature-scoped loggers (preserve `source` values)
LOG_AUTH = get_feature_logger(source="auth")
LOG_SUPABASE = get_feature_logger(source="supabase")

# JWKS client for asymmetric Supabase tokens (RS256 / ES256)
_jwks_client: PyJWKClient | None = None


def ensure_jwks_prefetch() -> None:
    """
    Create the global JWKS client and prefetch keys at startup so the first
    RS256/ES256 request does not pay the JWKS fetch latency.
    No-op if Supabase URL is not set or auth is not configured.
    """
    global _jwks_client
    if _jwks_client is not None:
        return
    if not settings.supabase_jwt_secret or not settings.supabase_url:
        return
    jwks_url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    try:
        _jwks_client = PyJWKClient(jwks_url)
        # Prefetch and cache the key set so first user request doesn't fetch
        if hasattr(_jwks_client, "get_signing_keys"):
            _jwks_client.get_signing_keys(refresh=True)
        LOG_AUTH.info(f"JWKS prefetched from {jwks_url}", user_id=None)
    except Exception as e:
        LOG_AUTH.warning(
            f"JWKS prefetch failed (first request will fetch): {e!s} (url={jwks_url})",
            user_id=None,
        )
        # Hint when Supabase is likely local and not running
        if "127.0.0.1" in jwks_url or "localhost" in jwks_url:
            LOG_AUTH.info(
                "If using local Supabase, ensure it is running (e.g. npx supabase start).",
                user_id=None,
            )
        if _jwks_client is None:
            try:
                _jwks_client = PyJWKClient(jwks_url)
            except Exception:
                pass  # first request will create and fetch


# Load prompts from YAML file
prompts_path = Path(__file__).parent.parent / "prompts.yaml"
with open(prompts_path, 'r', encoding='utf-8') as f:
    PROMPTS = yaml.safe_load(f)


def get_llm() -> ChatGoogleGenerativeAI:
    """Initialize and return Gemini LLM instance (model from config). Use with FastAPI Depends(get_llm) for dependency injection."""
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.0,
        google_api_key=settings.google_api_key,
    )


class Message(BaseModel):
    """Message model for conversation history"""
    role: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    """Request model for chat queries"""
    query: str
    history: list[Message] = []  # Conversation history (optional; BE may load from DB instead)
    conversation_id: int | None = None  # Optional Supabase conversation id (preferred for history loading)


def get_user_id_from_request(request: Request) -> UUID:
    """
    Extract and verify Supabase JWT from Authorization header; return user UUID (sub).
    Raises HTTPException 401 if missing or invalid.
    """
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        LOG_AUTH.info("401: Missing or invalid Authorization header", user_id=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (expected Bearer token)",
        )
    token = auth[7:].strip()
    if not token:
        LOG_AUTH.info("401: Bearer token is empty", user_id=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (expected Bearer token)",
        )
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server auth not configured (SUPABASE_JWT_SECRET)",
        )
    # Log token algorithm for diagnostics (header only, no payload)
    try:
        unverified = jwt.get_unverified_header(token)
        alg = unverified.get("alg")
        LOG_AUTH.info(f"JWT alg={alg}", user_id=None)
    except Exception as e:
        LOG_AUTH.warning(f"JWT header decode failed: {e!s}", user_id=None)
        alg = None

    # Choose verification strategy based on alg
    try:
        verify_key = None
        verify_algorithms: list[str] = []
        if alg == "HS256":
            # Symmetric: use shared secret (legacy jwt_secret)
            verify_key = settings.supabase_jwt_secret
            verify_algorithms = ["HS256"]
        elif alg in ("RS256", "ES256"):
            # Asymmetric: use JWKS from Supabase
            if not settings.supabase_url:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Supabase URL not configured for JWKS verification",
                )
            global _jwks_client
            if _jwks_client is None:
                jwks_url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
                _jwks_client = PyJWKClient(jwks_url)
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            verify_key = signing_key.key
            verify_algorithms = [alg]
        else:
            LOG_AUTH.warning(f"401: Unsupported JWT alg={alg}", user_id=None)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unsupported token algorithm: {alg}",
            )

        payload = jwt.decode(
            token,
            verify_key,
            algorithms=verify_algorithms,
            options={"verify_aud": False, "verify_iss": False},
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please sign in again.",
        ) from e
    except jwt.InvalidSignatureError as e:
        LOG_AUTH.warning("401: Invalid signature (wrong JWT secret?). alg=HS256", user_id=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid token signature. Use the JWT Secret from Supabase "
                "(Project Settings → API → JWT Secret), not the anon or service_role key. "
                "Local: run 'npx supabase status' and use the JWT secret shown there."
            ),
        ) from e
    except jwt.InvalidTokenError as e:
        LOG_AUTH.warning(f"401: Invalid token: {type(e).__name__}", user_id=None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject (sub)",
        )
    try:
        resolved_user_id = UUID(sub)
        LOG_AUTH.info("Auth successful", user_id=resolved_user_id)
        return resolved_user_id
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        ) from e


def get_current_user_id(request: Request) -> UUID:
    """
    FastAPI dependency wrapper around get_user_id_from_request.
    Use this with Depends() in route signatures.
    """
    return get_user_id_from_request(request)


def get_supabase_client() -> Optional[Any]:
    """
    FastAPI dependency: returns Supabase client, or None if URL/key not configured.
    Use with Depends(get_supabase_client) in route signatures.
    """
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


def get_solve_quota_count(user_id: UUID, supabase_client: Optional[Any] = None) -> int:
    """
    Return the number of solve (problem_solving) conversations for the user in the current month
    (month defined from account creation). Uses Supabase RPC get_solve_conversations_count_current_month.
    Pass the result of Depends(get_supabase_client) as supabase_client.
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


def load_conversation_history_for_user(
    user_id: UUID, conversation_id: int, supabase_client: Optional[Any] = None
) -> list[Message]:
    """
    Load full conversation history for a given user and conversation_id from Supabase.
    Ensures the conversation belongs to the user before returning any messages.
    Pass the result of Depends(get_supabase_client) as supabase_client.
    """
    if supabase_client is None:
        return []

    try:
        # Verify that the conversation belongs to this user (UUID as string)
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
            # Do not leak existence of other users' conversations
            return []

        # Fetch all messages ordered by created_at ascending
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
