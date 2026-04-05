"""Tests for scoring_scale_to_structured JSON helpers (no Gemini calls)."""

from __future__ import annotations

import json

import pytest

from exam_parser.parsers.scoring_scale_to_structured import (
    _normalize_output,
    _parse_json_from_response,
)


def test_parse_json_from_response_strips_fence() -> None:
    """Markdown fences should be removed before parsing."""
    raw = "```json\n" + json.dumps({"s1": []}) + "\n```"
    data = _parse_json_from_response(raw)
    assert data == {"s1": []}


def test_parse_json_from_response_escapes_latex_backslashes() -> None:
    """Single backslashes in JSON strings should survive via escape pass."""
    # Valid JSON with a LaTeX-like fragment that needs the regex escape pass
    raw = json.dumps({"s1": [{"number": "1", "solution_steps": r"\frac{a}{b}"}]})
    data = _parse_json_from_response(raw)
    assert data["s1"][0]["solution_steps"] == r"\frac{a}{b}"


def test_normalize_output_filters_keys() -> None:
    """Only list-valued s1/s2/s3 keys should be kept."""
    out = _normalize_output(
        {
            "s1": [{"n": 1}],
            "s2": "not-a-list",
            "s3": [],
            "extra": [1, 2],
        }
    )
    assert "s1" in out and "s3" in out
    assert "s2" not in out
    assert "extra" not in out


def test_scoring_scale_md_to_structured_empty_raises() -> None:
    """Empty markdown should raise before any API call."""
    from exam_parser.parsers.scoring_scale_to_structured import scoring_scale_md_to_structured

    with pytest.raises(ValueError, match="empty"):
        scoring_scale_md_to_structured("  \n  ")


def test_scoring_scale_md_to_structured_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing GOOGLE_API_KEY should fail fast."""
    from exam_parser.parsers.scoring_scale_to_structured import scoring_scale_md_to_structured

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        scoring_scale_md_to_structured("# barem")
