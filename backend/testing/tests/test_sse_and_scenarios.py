"""Unit tests for SSE parsing and scenario loading (no HTTP)."""

from pathlib import Path

import pytest

from profu_testing.sse import parse_clarify_sse_to_assistant_text, unescape_sse_payload
from profu_testing.synthetic_data import load_clarify_scenarios


def test_unescape_sse_payload() -> None:
    """Literal \\\\n becomes newline."""
    assert unescape_sse_payload("a\\nb") == "a\nb"
    assert unescape_sse_payload("") == ""


def test_parse_clarify_sse_skips_control_lines() -> None:
    """META, THINKING, DONE are ignored; content is concatenated."""
    body = (
        "data: [META]{\"ttft\": 0.1}\n\n"
        "data: [THINKING]\n\n"
        "data: Hello\\n\n\n"
        "data: world\n\n"
        "data: [DONE]\n\n"
    )
    assert parse_clarify_sse_to_assistant_text(body) == "Hello\nworld"


def test_load_clarify_scenarios_count() -> None:
    """Packaged scenarios: expect five clarify step-by-step files."""
    scenarios = load_clarify_scenarios()
    assert len(scenarios) == 5
    ids = {s.id for s in scenarios}
    assert ids == {
        "derivatives_prerequisites",
        "geometric_progression",
        "vector_scalar_product",
        "logarithm_properties",
        "classical_probability",
    }


def test_load_clarify_scenarios_custom_dir(tmp_path: Path) -> None:
    """Loading from an empty directory raises FileNotFoundError."""
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        load_clarify_scenarios(directory=empty)
