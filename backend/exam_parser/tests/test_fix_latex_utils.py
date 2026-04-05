"""Unit tests for fix_latex_utils (pure helpers and IO, no live Gemini)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from exam_parser.pipeline.steps import fix_latex_utils as flu


def test_is_retriable_error_patterns() -> None:
    """Retriable detection should match status substrings and codes."""
    assert flu._is_retriable_error(RuntimeError("HTTP 429")) is True
    assert flu._is_retriable_error(RuntimeError("resource exhausted")) is True
    assert flu._is_retriable_error(RuntimeError("timeout")) is True

    e = MagicMock()
    e.status_code = 503
    assert flu._is_retriable_error(e) is True

    assert flu._is_retriable_error(RuntimeError("permanent bad request")) is False


def test_parse_json_from_model_text_fence_and_backslash() -> None:
    """Model JSON cleanup should match pipeline behavior."""
    raw = "```\n[{\"id\":\"x\",\"issues\":[\"a\"]}]\n```"
    parsed = flu._parse_json_from_model_text(raw)
    assert parsed[0]["id"] == "x"


def test_with_retries_succeeds_first_try() -> None:
    """Happy path should not sleep."""
    calls: list[int] = []

    def op() -> str:
        calls.append(1)
        return "ok"

    with patch.object(flu.time, "sleep") as mock_sleep:
        assert flu._with_retries(op, max_attempts=3) == "ok"
    mock_sleep.assert_not_called()
    assert calls == [1]


def test_with_retries_non_retriable_raises_fast() -> None:
    """Non-retriable errors should not retry."""
    def op() -> None:
        raise RuntimeError("validation failed")

    with patch.object(flu.time, "sleep") as mock_sleep:
        with pytest.raises(RuntimeError, match="validation"):
            flu._with_retries(op, max_attempts=5)
    mock_sleep.assert_not_called()


def test_collect_latex_fields_s1_and_s2_shapes() -> None:
    """collect_latex_fields should walk statements, choices, items, solutions."""
    data = {
        "s1": [
            {
                "statement": "S",
                "choices": ["C1"],
                "items": ["I1"],
                "solution_steps": [
                    {"step": "step a"},
                ],
            }
        ],
        "s2": [
            {
                "statement": "S2",
                "item_solutions": [
                    {"solution_steps": "plain text sol"},
                    {
                        "solution_steps": [
                            {"step": "nested"},
                        ],
                    },
                ],
            }
        ],
    }
    rows = flu.collect_latex_fields(data)
    ids = {r[0] for r in rows}
    assert "s1/0/statement" in ids
    assert "s1/0/choices/0" in ids
    assert "s1/0/solution_steps/0/step" in ids
    assert "s2/0/item_solutions/0/solution_steps" in ids
    assert "s2/0/item_solutions/1/solution_steps/0/step" in ids


def test_get_at_set_at_roundtrip() -> None:
    """get_at / set_at should navigate mixed dict/list paths."""
    root: dict = {"s1": [{"statement": "old"}]}
    path = ["s1", 0, "statement"]
    assert flu.get_at(root, path) == "old"
    flu.set_at(root, path, "new")
    assert root["s1"][0]["statement"] == "new"


def test_normalize_issues_list() -> None:
    """Issue normalizer should coerce strings and skip junk."""
    assert flu._normalize_issues_list(None) == []
    assert flu._normalize_issues_list(" one ") == ["one"]
    assert flu._normalize_issues_list(["a", "", 3, "b"]) == ["a", "b"]


def test_build_eval_payload() -> None:
    """Payload lines should be JSON objects with id + text."""
    batch = [("id-1", "hello")]
    payload = flu._build_eval_payload(batch)
    row = json.loads(payload.splitlines()[0])
    assert row == {"id": "id-1", "text": "hello"}


def test_format_issues_block() -> None:
    """Issues block should enumerate or show (none)."""
    assert flu._format_issues_block([]) == "(none)"
    assert "1." in flu._format_issues_block(["x"])


def test_strip_markdown_fence() -> None:
    """Outer code fence should be removed once."""
    text = "```\nhello\n```"
    assert flu._strip_markdown_fence(text) == "hello"


def test_append_fix_log(tmp_path: Path) -> None:
    """append_fix_log should append JSON lines."""
    log = tmp_path / "d" / "fix.log"
    flu.append_fix_log(log, {"k": 1})
    flu.append_fix_log(log, {"k": 2})
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0]) == {"k": 1}


def test_truncate_for_log() -> None:
    """Long strings should truncate with metadata suffix."""
    short = "a" * 10
    assert flu._truncate_for_log(short) == short
    long = "b" * (flu.LOG_TRUNCATE + 50)
    out = flu._truncate_for_log(long)
    assert "truncated" in out
    assert len(out) < len(long)


def test_evaluate_batch_pro_empty() -> None:
    """Empty batch should short-circuit without calling the client."""
    client = MagicMock()
    assert flu.evaluate_batch_pro(client, []) == {}
    client.models.generate_content.assert_not_called()


def test_evaluate_batch_pro_parses_and_fills_missing_ids() -> None:
    """Parser should map ids; missing batch ids get a placeholder issue."""
    client = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps([{"id": "a", "issues": ["bad $"]}])
    client.models.generate_content.return_value = resp

    with patch.object(flu, "_with_retries", side_effect=lambda fn: fn()):
        out = flu.evaluate_batch_pro(client, [("a", "t1"), ("b", "t2")])

    assert out["a"] == ["bad $"]
    assert out["b"] == ["Missing from evaluator response"]


def test_evaluate_batch_pro_legacy_reason_field() -> None:
    """Evaluator objects may use reason instead of issues."""
    client = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps([{"id": "z", "reason": "legacy"}])
    client.models.generate_content.return_value = resp
    with patch.object(flu, "_with_retries", side_effect=lambda fn: fn()):
        out = flu.evaluate_batch_pro(client, [("z", "txt")])
    assert out["z"] == ["legacy"]


def test_repair_with_flash_returns_fixed() -> None:
    """When Flash returns different text, repair should return it."""
    client = MagicMock()
    resp = MagicMock()
    resp.text = "fixed body"
    client.models.generate_content.return_value = resp
    with patch.object(flu, "_with_retries", side_effect=lambda fn: fn()):
        out = flu.repair_with_flash(client, "orig", ["issue"])
    assert out == "fixed body"


def test_repair_with_flash_gives_up_returns_none() -> None:
    """Identical output twice should yield None."""
    client = MagicMock()
    resp = MagicMock()
    resp.text = "same"
    client.models.generate_content.return_value = resp
    with patch.object(flu, "_with_retries", side_effect=lambda fn: fn()):
        out = flu.repair_with_flash(client, "same", ["issue"])
    assert out is None
