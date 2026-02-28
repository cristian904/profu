"""
Common utilities and models shared between clarify and solve routers.
"""
import json
import logging
from pathlib import Path
from uuid import UUID

import yaml
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException, status
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ai_backend.config import settings

logger = logging.getLogger(__name__)

# JWKS client for asymmetric Supabase tokens (RS256 / ES256)
_jwks_client: PyJWKClient | None = None


# Load prompts from YAML file
prompts_path = Path(__file__).parent.parent / "prompts.yaml"
with open(prompts_path, 'r', encoding='utf-8') as f:
    PROMPTS = yaml.safe_load(f)


def get_llm():
    """Initialize and return Gemini LLM instance (model from config)."""
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
    # #region agent log
    _log_path = Path(__file__).resolve().parent.parent.parent / "debug-ffbdb6.log"
    auth = request.headers.get("Authorization")
    _has = auth is not None and len(auth) > 0
    _bearer = auth.startswith("Bearer ") if auth else False
    _len = len(auth) if auth else 0
    try:
        with open(_log_path, "a", encoding="utf-8") as _f:
            _f.write(
                json.dumps(
                    {
                        "sessionId": "ffbdb6",
                        "location": "common.py:get_user_id_from_request",
                        "message": "Auth header check",
                        "data": {
                            "path": str(getattr(request, "scope", {}).get("path", "")),
                            "has_authorization": _has,
                            "starts_with_bearer": _bearer,
                            "auth_value_len": _len,
                        },
                        "timestamp": __import__("time").time() * 1000,
                        "hypothesisId": "A",
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    if not auth or not auth.startswith("Bearer "):
        logger.info("[AUTH] 401: Missing or invalid Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (expected Bearer token)",
        )
    token = auth[7:].strip()
    if not token:
        logger.info("[AUTH] 401: Bearer token is empty")
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
        logger.info("[AUTH] JWT alg=%s", alg)
    except Exception as e:
        logger.warning("[AUTH] JWT header decode failed: %s", e)
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
            logger.warning("[AUTH] 401: Unsupported JWT alg=%s", alg)
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
        logger.warning("[AUTH] 401: Invalid signature (wrong JWT secret?). alg=HS256")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid token signature. Use the JWT Secret from Supabase "
                "(Project Settings → API → JWT Secret), not the anon or service_role key. "
                "Local: run 'npx supabase status' and use the JWT secret shown there."
            ),
        ) from e
    except jwt.InvalidTokenError as e:
        logger.warning("[AUTH] 401: Invalid token: %s", type(e).__name__)
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
        return UUID(sub)
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


def get_solve_quota_count(user_id: UUID) -> int:
    """
    Return the number of solve (problem_solving) conversations for the user in the current month
    (month defined from account creation). Uses Supabase RPC get_solve_conversations_count_current_month.
    """
    if not settings.supabase_url or not settings.supabase_key:
        return 0
    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_key)
        r = client.rpc(
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


def load_conversation_history_for_user(user_id: UUID, conversation_id: int) -> list[Message]:
    """
    Load full conversation history for a given user and conversation_id from Supabase.
    Ensures the conversation belongs to the user before returning any messages.
    """
    if not settings.supabase_url or not settings.supabase_key:
        return []

    try:
        from supabase import create_client

        client = create_client(settings.supabase_url, settings.supabase_key)

        # Verify that the conversation belongs to this user (UUID as string)
        conv_resp = (
            client.table("conversations")
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
            client.table("conversation_messages")
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
        logger.warning("Failed to load conversation history from Supabase: %s", e)
        return []
