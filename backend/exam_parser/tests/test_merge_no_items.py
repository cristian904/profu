"""Merge behaviour for canonical-problem statement/items + new solutions shape."""

from __future__ import annotations

from exam_parser.pipeline.steps.merge import merge_exam_with_solution


def test_merge_s2_copies_item_solutions_from_solution_record() -> None:
    """s2/s3 merge by number and copies item_solutions payload."""
    exam = {
        "s2": [
            {
                "statement": "full block verbatim",
                "number": 1,
                "choices": [],
                "subject": "mate",
                "topic": "x",
                "difficulty": "low",
            },
        ],
    }
    sol = {
        "s2": [
            {
                "number": "1",
                "subject": "mate",
                "topic": "x",
                "difficulty": "low",
                "statement": "full block verbatim",
                "item_solutions": [
                    {"item": "b", "solution_steps": [{"step": "second", "score": 1}]},
                    {"item": "a", "solution_steps": [{"step": "first", "score": 0.5}]},
                ],
            },
        ],
    }
    out = merge_exam_with_solution(exam, sol)
    assert "items" not in out["s2"][0] or out["s2"][0].get("items") == []
    pairs = [(x["item"], x["solution_steps"]) for x in out["s2"][0]["item_solutions"]]
    assert pairs[0][0] == "b"
    assert pairs[1][0] == "a"


def test_merge_s1_keeps_problem_fields_and_string_solution() -> None:
    """S1 keeps canonical problem fields and injects string solution_steps."""
    exam = {
        "s1": [
            {
                "statement": "q1",
                "number": 1,
                "choices": [],
                "items": ["should", "vanish"],
                "subject": "mate",
                "topic": "t",
                "difficulty": "low",
            },
        ],
    }
    sol = {
        "s1": [
            {
                "number": "1",
                "subject": "mate",
                "topic": "t",
                "difficulty": "low",
                "statement": "q1",
                "solution_steps": "rezolvare",
            }
        ]
    }
    out = merge_exam_with_solution(exam, sol)
    assert out["s1"][0]["items"] == ["should", "vanish"]
    assert out["s1"][0]["solution_steps"] == "rezolvare"
