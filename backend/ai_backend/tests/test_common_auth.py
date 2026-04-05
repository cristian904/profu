"""
Unit tests for JWT auth helpers (HS256 paths and error handling).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, status
from starlette.requests import Request

from ai_backend.common import auth as auth_module
from ai_backend.common.auth import (
    ensure_jwks_prefetch,
    get_current_user_id,
    get_user_id_from_request,
)
from ai_backend.config import settings

# PyJWT warns if HMAC secrets are shorter than the hash block size (32 for SHA256, 48 for SHA384).
_TEST_HS256_SECRET = "x" * 32
_SIGNING_SECRET_OTHER = "y" * 32
_TEST_HS384_SIGNING_SECRET = "z" * 48


def _request_with_auth(value: str | None) -> Request:
    """Build a minimal ASGI Request with optional Authorization header."""
    headers: list[tuple[bytes, bytes]] = []
    if value is not None:
        headers.append((b"authorization", value.encode("utf-8")))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
        }
    )


@pytest.fixture(autouse=True)
def _reset_jwks_client() -> None:
    """Avoid cross-test pollution of the global JWKS client."""
    auth_module._jwks_client = None
    yield
    auth_module._jwks_client = None


class TestGetUserIdFromRequest:
    """Tests for get_user_id_from_request."""

    def test_missing_authorization_header(self) -> None:
        """Missing header yields 401."""
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(None))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_bearer_prefix(self) -> None:
        """Non-Bearer scheme yields 401."""
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth("Basic xxx"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_bearer_token(self) -> None:
        """Bearer with empty token yields 401."""
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth("Bearer "))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(settings, "supabase_jwt_secret", "")
    def test_no_jwt_secret_configured(self) -> None:
        """503 when server has no JWT secret."""
        req = _request_with_auth("Bearer sometoken")
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(req)
        assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_hs256_success(self) -> None:
        """Valid HS256 token returns UUID from sub."""
        uid = uuid.uuid4()
        token = jwt.encode(
            {"sub": str(uid), "exp": datetime.now(UTC) + timedelta(hours=1)},
            _TEST_HS256_SECRET,
            algorithm="HS256",
        )
        req = _request_with_auth(f"Bearer {token}")
        assert get_user_id_from_request(req) == uid

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_hs256_expired(self) -> None:
        """Expired token yields 401."""
        uid = uuid.uuid4()
        token = jwt.encode(
            {"sub": str(uid), "exp": datetime.now(UTC) - timedelta(hours=1)},
            _TEST_HS256_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(f"Bearer {token}"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_hs256_wrong_secret(self) -> None:
        """Wrong signing secret yields 401."""
        uid = uuid.uuid4()
        token = jwt.encode(
            {"sub": str(uid), "exp": datetime.now(UTC) + timedelta(hours=1)},
            _SIGNING_SECRET_OTHER,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(f"Bearer {token}"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_missing_sub_claim(self) -> None:
        """Token without sub yields 401."""
        token = jwt.encode(
            {"exp": datetime.now(UTC) + timedelta(hours=1)},
            _TEST_HS256_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(f"Bearer {token}"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_sub_not_uuid(self) -> None:
        """Non-UUID sub yields 401."""
        token = jwt.encode(
            {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(hours=1)},
            _TEST_HS256_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(f"Bearer {token}"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_unsupported_algorithm(self) -> None:
        """Algorithms other than HS256/RS256/ES256 yield 401."""
        uid = uuid.uuid4()
        token = jwt.encode(
            {"sub": str(uid), "exp": datetime.now(UTC) + timedelta(hours=1)},
            _TEST_HS384_SIGNING_SECRET,
            algorithm="HS384",
        )
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(f"Bearer {token}"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUserId:
    """get_current_user_id should mirror get_user_id_from_request."""

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    def test_delegates_to_get_user_id(self) -> None:
        uid = uuid.uuid4()
        token = jwt.encode(
            {"sub": str(uid), "exp": datetime.now(UTC) + timedelta(hours=1)},
            _TEST_HS256_SECRET,
            algorithm="HS256",
        )
        req = _request_with_auth(f"Bearer {token}")
        assert get_current_user_id(req) == uid


class TestGetUserIdFromRequestRs256AndEdgeCases:
    """RS256 path and header/decode edge cases."""

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    @patch.object(settings, "supabase_url", "https://example.supabase.co")
    @patch("jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "kid1"})
    @patch("jwt.decode")
    def test_rs256_verifies_with_jwks_signing_key(
        self,
        mock_decode: MagicMock,
        _hdr: MagicMock,
    ) -> None:
        """Asymmetric tokens should use the global JWKS client and jwt.decode."""
        uid = uuid.uuid4()
        mock_decode.return_value = {"sub": str(uid)}
        signing = MagicMock()
        signing.key = b"pem"
        jwks = MagicMock()
        jwks.get_signing_key_from_jwt.return_value = signing
        auth_module._jwks_client = jwks
        token = "header.payload.sig"
        req = _request_with_auth(f"Bearer {token}")
        assert get_user_id_from_request(req) == uid
        mock_decode.assert_called_once()
        call_kw = mock_decode.call_args.kwargs
        assert call_kw.get("algorithms") == ["RS256"]

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    @patch("jwt.get_unverified_header", side_effect=jwt.DecodeError("bad header"))
    def test_header_decode_failure_falls_back_to_unsupported_alg(self, _hdr: MagicMock) -> None:
        """If the JWT header cannot be read, alg is treated as unsupported."""
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth("Bearer not-a-jwt"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @patch.object(settings, "supabase_jwt_secret", _TEST_HS256_SECRET)
    @patch("jwt.get_unverified_header", return_value={"alg": "HS256"})
    @patch("jwt.decode", side_effect=jwt.InvalidTokenError())
    def test_invalid_token_error_maps_to_401(self, _dec: MagicMock, _hdr: MagicMock) -> None:
        """Generic PyJWT errors should surface as invalid token."""
        token = jwt.encode(
            {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(hours=1)},
            _TEST_HS256_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            get_user_id_from_request(_request_with_auth(f"Bearer {token}"))
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestEnsureJwksPrefetch:
    """Smoke tests for JWKS prefetch (network mocked)."""

    def test_no_op_when_jwks_client_already_initialized(self) -> None:
        """Second prefetch call should not recreate the PyJWKClient."""
        auth_module._jwks_client = MagicMock()
        try:
            with patch.object(auth_module, "PyJWKClient") as mock_cls:
                ensure_jwks_prefetch()
            mock_cls.assert_not_called()
        finally:
            auth_module._jwks_client = None

    def test_no_op_without_url_or_secret(self) -> None:
        with patch.object(settings, "supabase_jwt_secret", ""), patch.object(settings, "supabase_url", ""):
            ensure_jwks_prefetch()
        assert auth_module._jwks_client is None

    @patch.object(settings, "supabase_jwt_secret", "s")
    @patch.object(settings, "supabase_url", "https://example.supabase.co")
    @patch.object(auth_module, "PyJWKClient")
    def test_prefetch_sets_client_on_success(self, mock_jwks_cls: MagicMock) -> None:
        instance = MagicMock()
        instance.get_signing_keys = MagicMock()
        mock_jwks_cls.return_value = instance
        ensure_jwks_prefetch()
        mock_jwks_cls.assert_called_once()
        assert auth_module._jwks_client is instance

    @patch.object(settings, "supabase_jwt_secret", "s")
    @patch.object(settings, "supabase_url", "http://127.0.0.1:54321")
    @patch.object(auth_module, "PyJWKClient")
    def test_prefetch_failure_retries_construct(self, mock_jwks_cls: MagicMock) -> None:
        """First construct or prefetch fails; except block retries when client is still None."""
        good = MagicMock()
        mock_jwks_cls.side_effect = [RuntimeError("network"), good]
        auth_module._jwks_client = None
        ensure_jwks_prefetch()
        assert auth_module._jwks_client is good
