"""Tests for difficulty_rules (reclassify + classify edge cases, mocked Gemini)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from exam_parser.parsers import difficulty_rules as dr


def test_classify_problem_difficulty_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without GOOGLE_API_KEY, classify should raise."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        dr.classify_problem_difficulty({"statement": "x"})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("low", "low"),
        ("HIGH", "high"),
        ("probably medium difficulty", "medium"),
        ("unknown fluff high", "high"),
        ("something low and more", "low"),
    ],
)
def test_classify_problem_difficulty_parses_response(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
    expected: str,
) -> None:
    """Model text should map to low/medium/high including fallbacks."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    mock_resp = MagicMock()
    mock_resp.text = raw
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("google.genai.Client", return_value=mock_client):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
            out = dr.classify_problem_difficulty(
                {"statement": "demo", "items": ["a"], "topic": "algebra"},
            )
    assert out == expected
    mock_client.models.generate_content.assert_called_once()


@patch("exam_parser.parsers.difficulty_rules.classify_problem_difficulty", return_value="high")
def test_reclassify_structured_data_updates_problems(mock_classify: MagicMock) -> None:
    """reclassify_structured_data should set difficulty on each problem dict."""
    data = {
        "s1": [{"statement": "p1"}],
        "s2": [{"statement": "p2", "items": []}],
        "s3": "skip",
    }
    dr.reclassify_structured_data(data)
    assert data["s1"][0]["difficulty"] == "high"
    assert data["s2"][0]["difficulty"] == "high"
    assert mock_classify.call_count == 2
