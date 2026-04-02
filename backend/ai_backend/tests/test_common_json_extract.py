"""
Unit tests for common.json_extract (fenced JSON, raw_decode, errors).
"""

import pytest

from ai_backend.common.json_extract import extract_json_from_text


class TestExtractJsonFromText:
    """Coverage for extract_json_from_text branches."""

    def test_fenced_json_block(self) -> None:
        text = 'Some text\n```json\n{"intent": "solve"}\n```\n'
        assert extract_json_from_text(text) == {"intent": "solve"}

    def test_raw_object_in_text(self) -> None:
        assert extract_json_from_text('prefix {"a": 1} suffix') == {"a": 1}

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="No JSON"):
            extract_json_from_text("")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="No JSON"):
            extract_json_from_text(None)  # type: ignore[arg-type]

    def test_no_brace_raises(self) -> None:
        with pytest.raises(ValueError, match="No JSON"):
            extract_json_from_text("no json here")

    def test_fence_without_brace_falls_back(self) -> None:
        """Fence match but no `{` after fence uses first `{` in text."""
        text = '```json\nstill no brace\n{"x": true}'
        assert extract_json_from_text(text) == {"x": True}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Failed to parse"):
            extract_json_from_text("{not valid json")

    def test_array_top_level_raises(self) -> None:
        """No ``{`` in text -> same error path as missing JSON."""
        with pytest.raises(ValueError, match="No JSON"):
            extract_json_from_text("[1, 2, 3]")
