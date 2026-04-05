"""Tests for FastAPI exception handlers in main (validation + unhandled errors)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from ai_backend.main import app, unhandled_exception_handler, validation_exception_handler


@pytest.mark.asyncio
async def test_validation_exception_handler_returns_422_detail() -> None:
    """RequestValidationError handler should return structured 422 JSON."""
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/solve-problem/suggest-problem",
            "headers": [],
        }
    )
    exc = RequestValidationError(
        [{"loc": ("body", "problem_text"), "msg": "invalid", "type": "value_error"}]
    )
    response = await validation_exception_handler(request, exc)
    assert response.status_code == 422
    payload = json.loads(response.body.decode())
    assert "detail" in payload
    assert payload.get("message")


@pytest.mark.asyncio
async def test_unhandled_exception_handler_returns_500_with_error_id() -> None:
    """Unhandled errors should log and return opaque error_id."""
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
        }
    )
    response = await unhandled_exception_handler(request, RuntimeError("boom"))
    assert response.status_code == 500
    payload = json.loads(response.body.decode())
    assert payload["detail"] == "Internal server error"
    assert "error_id" in payload


def test_suggest_problem_invalid_body_triggers_validation_handler() -> None:
    """Client should see 422 when JSON types do not match the schema."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post(
        "/solve-problem/suggest-problem",
        json={"problem_text": 123},
    )
    assert response.status_code == 422


def test_unhandled_runtime_error_via_temp_route() -> None:
    """A route that raises should hit the global Exception handler."""
    from fastapi.testclient import TestClient

    router = APIRouter()

    @router.get("/__test_unhandled_runtime__")
    async def _boom() -> str:
        raise RuntimeError("intentional test failure")

    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.get("/__test_unhandled_runtime__")
        assert response.status_code == 500
        data = response.json()
        assert data.get("detail") == "Internal server error"
        assert data.get("error_id")
    finally:
        app.router.routes = [
            r
            for r in app.router.routes
            if getattr(r, "path", None) != "/__test_unhandled_runtime__"
        ]


def test_suppress_uvicorn_filter_drops_duplicate_line() -> None:
    """Uvicorn duplicate exception filter should hide the noisy line."""
    import logging

    from ai_backend import main as main_mod

    filt = main_mod._SuppressUvicornExceptionLog()
    keep = logging.LogRecord("n", logging.ERROR, "", 0, "ok", (), None)
    drop = logging.LogRecord(
        "n",
        logging.ERROR,
        "",
        0,
        "Exception in ASGI application",
        (),
        None,
    )
    assert filt.filter(keep) is True
    assert filt.filter(drop) is False


@patch("ai_backend.main.get_user_id_from_request", side_effect=RuntimeError("auth read failed"))
@pytest.mark.asyncio
async def test_unhandled_handler_swallows_user_id_resolution_errors(
    _mock_uid: MagicMock,
) -> None:
    """If resolving user_id for logging fails, handler should still return 500 JSON."""
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": [],
        }
    )
    response = await unhandled_exception_handler(request, ValueError("inner"))
    assert response.status_code == 500
