"""Tests for common.structured_output helpers."""

from unittest.mock import MagicMock

from pydantic import BaseModel, Field

from ai_backend.common.structured_output import coerce_structured_output


class _Sample(BaseModel):
    x: str = Field(default="a")


def test_coerce_plain_model() -> None:
    m = _Sample(x="b")
    parsed, raw = coerce_structured_output(m, _Sample)
    assert parsed is m
    assert raw == ""


def test_coerce_include_raw_dict_success() -> None:
    raw = MagicMock(content="hello")
    out = {"raw": raw, "parsed": _Sample(x="c"), "parsing_error": None}
    parsed, raw_text = coerce_structured_output(out, _Sample)
    assert parsed is not None and parsed.x == "c"
    assert raw_text == "hello"


def test_coerce_include_raw_dict_parse_failed() -> None:
    raw = MagicMock(content="fallback text")
    out = {"raw": raw, "parsed": None, "parsing_error": ValueError("bad")}
    parsed, raw_text = coerce_structured_output(out, _Sample)
    assert parsed is None
    assert raw_text == "fallback text"
