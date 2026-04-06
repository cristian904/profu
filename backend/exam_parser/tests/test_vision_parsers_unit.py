"""
Unit tests for vision-related parsers (mocked Gemini client; no network).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from exam_parser.parsers import gemini_vision_parser
from exam_parser.parsers import scoring_scale_vision
from exam_parser.parsers import vision_to_structured


def test_to_markdown_latex_returns_unchanged_when_blank() -> None:
    """Whitespace-only raw text skips the model call."""
    client = MagicMock()
    assert gemini_vision_parser._to_markdown_latex(client, "   \n", "gemini-2.5-flash") == "   \n"
    client.models.generate_content.assert_not_called()


def test_to_markdown_latex_strips_model_output() -> None:
    """Non-empty raw text triggers generate_content and strips response text."""
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text="  converted  ")
    out = gemini_vision_parser._to_markdown_latex(client, "raw", "m")
    assert out == "converted"
    client.models.generate_content.assert_called_once()


def test_parse_with_gemini_vision_not_pdf_raises(tmp_path: Path) -> None:
    """Non-PDF path raises FileNotFoundError (suffix check)."""
    p = tmp_path / "x.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="PDF file not found"):
        gemini_vision_parser.parse_with_gemini_vision(p)


def test_parse_with_gemini_vision_missing_file_raises(tmp_path: Path) -> None:
    """Missing path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="PDF file not found"):
        gemini_vision_parser.parse_with_gemini_vision(tmp_path / "missing.pdf")


def test_parse_scoring_scale_pdf_not_pdf_raises(tmp_path: Path) -> None:
    """Non-PDF raises before API key check."""
    p = tmp_path / "x.md"
    p.write_text("# x", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="PDF file not found"):
        scoring_scale_vision.parse_scoring_scale_pdf(p)


def test_detect_subject_variants() -> None:
    """Subject headers map to s1/s2/s3 keys."""
    assert vision_to_structured._detect_subject("Intro\nSubiectul I (something)") == "s1"
    assert vision_to_structured._detect_subject("SUBIECTUL II (foo)") == "s2"
    assert vision_to_structured._detect_subject("subiectul iii (bar)") == "s3"
    assert vision_to_structured._detect_subject("no header here") is None


def test_parse_json_from_response_strips_fence() -> None:
    """Markdown code fence is removed before JSON parse."""
    raw = '```json\n{"s1": []}\n```'
    data = vision_to_structured._parse_json_from_response(raw)
    assert data == {"s1": []}


def test_validate_and_normalize_single_key() -> None:
    """Single s-key dict passes through structure."""
    data = {"s1": [{"statement": "a", "choices": []}]}
    out = vision_to_structured._validate_and_normalize(data, "s1")
    assert list(out.keys()) == ["s1"]


def test_validate_and_normalize_prefers_expected_when_multiple() -> None:
    """When both s1 and s2 present, expected_key selects one list."""
    data = {"s1": [], "s2": []}
    out = vision_to_structured._validate_and_normalize(data, "s2")
    assert out == {"s2": []}


def test_extract_structured_problems_file_validation(tmp_path: Path) -> None:
    """Paths and content validated before any Gemini call."""
    with pytest.raises(FileNotFoundError):
        vision_to_structured.extract_structured_problems(tmp_path / "nope.md")

    bad = tmp_path / "x.txt"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected .md"):
        vision_to_structured.extract_structured_problems(bad)

    empty = tmp_path / "e.md"
    empty.write_text("  \n  ", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty file"):
        vision_to_structured.extract_structured_problems(empty)

    no_sub = tmp_path / "n.md"
    no_sub.write_text("# Title only\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SUBIECTUL"):
        vision_to_structured.extract_structured_problems(no_sub)
