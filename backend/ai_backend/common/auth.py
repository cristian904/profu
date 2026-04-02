"""
Supabase JWT verification (HS256 + JWKS for RS256/ES256) and FastAPI auth dependencies.
"""

from typing import Optional
from uuid import UUID

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from ai_backend.config import settings
from profu_logging.feature_logger import get_feature_logger

LOG_AUTH = get_feature_logger(source="auth")

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
        if hasattr(_jwks_client, "get_signing_keys"):
            _jwks_client.get_signing_keys(refresh=True)
        LOG_AUTH.info(f"JWKS prefetched from {jwks_url}", user_id=None)
    except Exception as e:
        LOG_AUTH.warning(
            f"JWKS prefetch failed (first request will fetch): {e!s} (url={jwks_url})",
            user_id=None,
        )
        if "127.0.0.1" in jwks_url or "localhost" in jwks_url:
            LOG_AUTH.info(
                "If using local Supabase, ensure it is running (e.g. npx supabase start).",
                user_id=None,
            )
        if _jwks_client is None:
            try:
                _jwks_client = PyJWKClient(jwks_url)
            except Exception:
                pass


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
    try:
        unverified = jwt.get_unverified_header(token)
        alg = unverified.get("alg")
        LOG_AUTH.info(f"JWT alg={alg}", user_id=None)
    except Exception as e:
        LOG_AUTH.warning(f"JWT header decode failed: {e!s}", user_id=None)
        alg = None

    try:
        verify_key: Optional[str | bytes] = None
        verify_algorithms: list[str] = []
        if alg == "HS256":
            verify_key = settings.supabase_jwt_secret
            verify_algorithms = ["HS256"]
        elif alg in ("RS256", "ES256"):
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
