"""
Extra coverage for structured problem JSON normalization and JSON edge cases.
"""

from __future__ import annotations

import pytest

from exam_parser.parsers.json_response_utils import parse_json_from_llm_response
from exam_parser.parsers.structured_normalize import validate_and_normalize_problems


def test_validate_and_normalize_empty_keys_raises() -> None:
    """Missing s1/s2/s3 arrays raises ValueError."""
    with pytest.raises(ValueError, match="at least one"):
        validate_and_normalize_problems({"other": []}, None)


def test_validate_and_normalize_keeps_all_when_no_expected() -> None:
    """Multiple keys without expected_key keeps all subject arrays."""
    data = {"s1": [1], "s2": [2]}
    out = validate_and_normalize_problems(data, None)
    assert out == {"s1": [1], "s2": [2]}


def test_parse_json_from_response_plain_object() -> None:
    """JSON without fence parses directly."""
    assert parse_json_from_llm_response('{"s3": []}') == {"s3": []}
