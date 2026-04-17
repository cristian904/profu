"""Tests for solution JSON helpers (parse_json_from_llm_response, normalize_solutions_output)."""

from __future__ import annotations

import json

import pytest

from exam_parser.parsers.json_response_utils import parse_json_from_llm_response
from exam_parser.parsers.ollama_structured import scoring_scale_md_to_structured_ollama
from exam_parser.parsers.structured_normalize import normalize_solutions_output


def test_parse_json_from_llm_response_strips_fence() -> None:
    """Markdown fences should be removed before parsing."""
    raw = "```json\n" + json.dumps({"s1": []}) + "\n```"
    data = parse_json_from_llm_response(raw)
    assert data == {"s1": []}


def test_parse_json_from_llm_response_escapes_latex_backslashes() -> None:
    """Single backslashes in JSON strings should survive via escape pass."""
    raw = json.dumps({"s1": [{"number": "1", "solution_steps": r"\frac{a}{b}"}]})
    data = parse_json_from_llm_response(raw)
    assert data["s1"][0]["solution_steps"] == r"\frac{a}{b}"


def test_normalize_output_filters_keys() -> None:
    """Only list-valued s1/s2/s3 keys should be kept."""
    out = normalize_solutions_output(
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


def test_scoring_scale_md_to_structured_ollama_empty_raises() -> None:
    """Empty markdown should raise before any HTTP call."""
    with pytest.raises(ValueError, match="empty"):
        scoring_scale_md_to_structured_ollama(
            "  \n  ",
            base_url="http://127.0.0.1:11434",
            model="m",
        )
