"""
Unit tests for structured normalization and Ollama markdown parsing (no network).
"""

from __future__ import annotations

import pytest

from exam_parser.parsers.json_response_utils import parse_json_from_llm_response
from exam_parser.parsers.ollama_structured import extract_structured_problems_from_markdown
from exam_parser.parsers.structured_normalize import (
    detect_subject,
    infer_subject_from_stem,
    validate_and_normalize_problems,
)


def test_detect_subject_variants() -> None:
    """Subject headers map to s1/s2/s3 keys."""
    assert detect_subject("Intro\nSubiectul I (something)") == "s1"
    assert detect_subject("SUBIECTUL II (foo)") == "s2"
    assert detect_subject("subiectul iii (bar)") == "s3"
    assert detect_subject("Barem\nSubiectul I") == "s1"
    assert detect_subject("subiect ii — punctaj") == "s2"
    assert detect_subject("no header here") is None


def test_detect_subject_roman_order() -> None:
    """Longer Roman numerals must win over prefixes."""
    assert detect_subject("Subiectul III din teza") == "s3"
    assert detect_subject("Subiectul II") == "s2"


def test_infer_subject_from_stem_suffix() -> None:
    """Filename stems ending with _sN hint merge subject."""
    assert infer_subject_from_stem("2009_M1_v1_s1") == "s1"
    assert infer_subject_from_stem("2009_M1_v1_S3") == "s3"
    assert infer_subject_from_stem("exam_no_suffix") is None


def test_parse_json_from_response_strips_fence() -> None:
    """Markdown code fence is removed before JSON parse."""
    raw = '```json\n{"s1": []}\n```'
    data = parse_json_from_llm_response(raw)
    assert data == {"s1": []}


def test_validate_and_normalize_single_key() -> None:
    """Single s-key dict passes through structure."""
    data = {"s1": [{"statement": "a", "choices": []}]}
    out = validate_and_normalize_problems(data, "s1")
    assert list(out.keys()) == ["s1"]


def test_validate_and_normalize_prefers_expected_when_multiple() -> None:
    """When both s1 and s2 present, expected_key selects one list."""
    data = {"s1": [], "s2": []}
    out = validate_and_normalize_problems(data, "s2")
    assert out == {"s2": []}


def test_extract_structured_problems_from_markdown_empty_raises() -> None:
    """Whitespace-only markdown raises before Ollama."""
    with pytest.raises(ValueError, match="empty"):
        extract_structured_problems_from_markdown(
            "  \n  ",
            base_url="http://127.0.0.1:11434",
            model="m",
        )


def test_extract_structured_problems_from_markdown_no_subject_raises() -> None:
    """Missing SUBIECTUL header raises before Ollama."""
    with pytest.raises(ValueError, match="Subiect I/II/III"):
        extract_structured_problems_from_markdown(
            "# Only a title\n",
            base_url="http://127.0.0.1:11434",
            model="m",
        )
