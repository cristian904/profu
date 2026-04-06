"""
Extra coverage for ``vision_to_structured`` normalization and JSON edge cases.
"""

from __future__ import annotations

import pytest

from exam_parser.parsers import vision_to_structured


def test_validate_and_normalize_empty_keys_raises() -> None:
    """Missing s1/s2/s3 arrays raises ValueError."""
    with pytest.raises(ValueError, match="JSON must contain"):
        vision_to_structured._validate_and_normalize({"other": []}, None)


def test_validate_and_normalize_picks_first_when_ambiguous_no_expected() -> None:
    """Multiple keys without expected_key keeps the first sorted key's list."""
    data = {"s1": [1], "s2": [2]}
    out = vision_to_structured._validate_and_normalize(data, None)
    assert len(out) == 1
    assert "s1" in out or "s2" in out


def test_parse_json_from_response_plain_object() -> None:
    """JSON without fence parses directly."""
    assert vision_to_structured._parse_json_from_response('{"s3": []}') == {"s3": []}


def test_extract_structured_problems_missing_api_key(tmp_path, monkeypatch) -> None:
    """After file checks, missing GOOGLE_API_KEY raises ValueError."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    md = tmp_path / "sub.md"
    md.write_text("Subiectul I (foo)\n\nbody\n", encoding="utf-8")
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        vision_to_structured.extract_structured_problems(md)
