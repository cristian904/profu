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
    data = {"s1": [{"statement": "a"}]}
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


def test_extract_structured_problems_from_markdown_no_subject_uses_llm_output() -> None:
    """Missing source header should rely on LLM output, not deterministic pre-check."""
    from exam_parser.parsers import ollama_structured
    def _fake_ollama_chat_text(
        base_url: str,
        model: str,
        user_content: str,
        *,
        timeout_sec: float = 900.0,
        request_json_format: bool = False,
    ) -> str:
        assert request_json_format is True
        return """{
  "s1": [
    {"number": 1, "statement": "x + 1 = 2", "items": []},
    {"number": 2, "statement": "p2", "items": []},
    {"number": 3, "statement": "p3", "items": []},
    {"number": 4, "statement": "p4", "items": []},
    {"number": 5, "statement": "p5", "items": []},
    {"number": 6, "statement": "p6", "items": []}
  ]
}"""

    original = ollama_structured.ollama_chat_text
    ollama_structured.ollama_chat_text = _fake_ollama_chat_text
    try:
        out = extract_structured_problems_from_markdown(
            "# Only a title\n",
            base_url="http://127.0.0.1:11434",
            model="m",
        )
    finally:
        ollama_structured.ollama_chat_text = original

    assert "s1" in out
    assert len(out["s1"]) == 6


def test_extract_structured_problems_from_markdown_includes_source_stem_subject_hint() -> None:
    """When source stem has _sN suffix, prompt should include a subject hint."""
    from exam_parser.parsers import ollama_structured

    captured_prompt: dict[str, str] = {"value": ""}

    def _fake_ollama_chat_text(
        base_url: str,
        model: str,
        user_content: str,
        *,
        timeout_sec: float = 900.0,
        request_json_format: bool = False,
    ) -> str:
        captured_prompt["value"] = user_content
        assert request_json_format is True
        return """{
  "s2": [
    {
      "number": 1,
      "statement": "x + 1 = 2",
      "items": ["a) i", "b) j", "c) k"]
    },
    {
      "number": 2,
      "statement": "y",
      "items": ["a) i2", "b) j2", "c) k2"]
    }
  ]
}"""

    original = ollama_structured.ollama_chat_text
    ollama_structured.ollama_chat_text = _fake_ollama_chat_text
    try:
        out = extract_structured_problems_from_markdown(
            "# Exercitii\n",
            base_url="http://127.0.0.1:11434",
            model="m",
            source_stem="2009_M1_v1_s2",
        )
    finally:
        ollama_structured.ollama_chat_text = original

    assert "SOURCE SUBJECT CONSTRAINT (from filename): s2" in captured_prompt["value"]
    assert "You MUST use this exact subject key in output." in captured_prompt["value"]
    assert "s2" in out
