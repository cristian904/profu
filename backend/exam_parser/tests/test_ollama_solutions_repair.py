"""Tests for solutions JSON repair retry and stem-hint validation in ollama_structured."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from exam_parser.parsers.ollama_structured import (
    StructuredJsonParseError,
    _parse_solutions_ollama_raw_to_dict,
    scoring_scale_md_to_structured_ollama,
)


def test_parse_solutions_rejects_non_array_when_stem_hint_s3() -> None:
    """Filename subject s3 requires top-level s3 to be an array, not a nested object."""
    bad = '{"s3": {"c": {"x": 1}}}'
    with pytest.raises(StructuredJsonParseError, match="JSON array"):
        _parse_solutions_ollama_raw_to_dict(bad, "s3")


def test_scoring_scale_repair_second_call_succeeds() -> None:
    """After invalid JSON shape, a second Ollama response can validate."""
    s1_parts = [f'{{"number": {n}, "solution_steps": "rezolvare completă"}}' for n in range(1, 7)]
    valid = '{"s1": [' + ",".join(s1_parts) + "]}"
    invalid = '{"s1": "not an array"}'

    def fake_chat(
        _base_url: str,
        _model: str,
        user_content: str,
        *,
        timeout_sec: float = 900.0,
        request_json_format: bool = False,
    ) -> str:
        if "Your previous JSON was rejected" in user_content:
            return valid
        return invalid

    with patch("exam_parser.parsers.ollama_structured.ollama_chat_text", side_effect=fake_chat):
        out = scoring_scale_md_to_structured_ollama(
            "# barem\n",
            base_url="http://127.0.0.1:11434",
            model="m",
            source_stem=None,
            solution_repair_attempts=1,
        )

    assert out["s1"][0]["solution_steps"] == "rezolvare completă"


def test_scoring_scale_no_repair_when_attempts_zero() -> None:
    """With solution_repair_attempts=0, only one Ollama call is made."""
    calls: list[str] = []

    def fake_chat(
        _base_url: str,
        _model: str,
        user_content: str,
        *,
        timeout_sec: float = 900.0,
        request_json_format: bool = False,
    ) -> str:
        calls.append(user_content)
        return '{"s1": "bad"}'

    with patch("exam_parser.parsers.ollama_structured.ollama_chat_text", side_effect=fake_chat):
        with pytest.raises(StructuredJsonParseError):
            scoring_scale_md_to_structured_ollama(
                "md",
                base_url="http://127.0.0.1:11434",
                model="m",
                solution_repair_attempts=0,
            )

    assert len(calls) == 1
