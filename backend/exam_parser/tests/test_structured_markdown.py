"""Tests for structured markdown parse/serialize and typed schema."""

from __future__ import annotations

import pytest

from exam_parser.parsers.structured_markdown import (
    FORMAT_MERGED,
    FORMAT_PROBLEMS,
    FORMAT_SOLUTIONS,
    merged_document_to_rows_dict,
    normalize_llm_markdown_response,
    parse_merged_markdown,
    parse_problems_markdown,
    parse_solutions_markdown,
    serialize_merged_document,
    serialize_problems_document,
    serialize_problems_from_normalized_dict,
    serialize_solutions_document,
    serialize_solutions_from_normalized_dict,
)
from exam_parser.parsers.structured_models import (
    ItemSolutionBlock,
    MergedDocument,
    MergedS1Record,
    MergedS23Record,
    ProblemRecord,
    ProblemsDocument,
    SolutionS1Record,
    SolutionS23Record,
    SolutionsDocument,
    SolutionStep,
)
from exam_parser.pipeline.steps.merge import merge_exam_with_solution


def _minimal_problems_md(statement: str = r"Text \mathbb{R} and \frac{1}{2}") -> str:
    """Minimal valid problems markdown for s1."""
    return f"""# Exam parser — structured problems v1

---
format: {FORMAT_PROBLEMS}
subject: s1
---

## Subject s1

## Problem

```yaml
number: 1
difficulty: low
subject: mate
topic: test
choices: []
statement: |
  {statement}
```
"""


def test_normalize_llm_markdown_response_strips_outer_fence() -> None:
    """Outer markdown fence should be removed."""
    wrapped = "```markdown\n" + _minimal_problems_md() + "\n```"
    assert "format:" in normalize_llm_markdown_response(wrapped)


def test_parse_problems_supports_multiple_subjects() -> None:
    """Problems document may contain any subset of s1/s2/s3."""
    text = f"""---
format: {FORMAT_PROBLEMS}
---

## Subject s1
## Problem
```yaml
number: 1
subject: mate
topic: "t1"
difficulty: low
statement: |
  s1 text
choices: []
```

## Subject s2
## Problem
```yaml
number: 1
subject: mate
topic: "t2"
difficulty: medium
statement: |
  s2 text
choices: []
items:
  - |
    a) aa
  - |
    b) bb
```
"""
    doc = parse_problems_markdown(text)
    assert len(doc.s1 or []) == 1
    assert len(doc.s2 or []) == 1
    assert len(doc.s2[0].items) == 2


def test_parse_problems_no_headings_uses_inferred_subject() -> None:
    """Without section headings we can bucket by inferred subject."""
    md = """```yaml
number: 1
subject: mate
topic: t
difficulty: low
statement: |
  x
choices: []
```"""
    doc = parse_problems_markdown(md, inferred_subject="s1")
    assert doc.s1[0].statement.strip() == "x"


def test_parse_problems_preserves_backslashes() -> None:
    """Literal blocks preserve latex text."""
    doc = parse_problems_markdown(_minimal_problems_md())
    assert r"\mathbb" in doc.s1[0].statement
    assert r"\frac" in doc.s1[0].statement


def test_unclosed_yaml_fence_empty_body_raises() -> None:
    """EOF right after opener remains a hard error."""
    text = f"""---
format: {FORMAT_PROBLEMS}
subject: s1
---
## Subject s1
## Problem
```yaml
"""
    with pytest.raises(ValueError, match="empty body before end of input"):
        parse_problems_markdown(text)


def test_parse_solutions_shape_s1_vs_s2() -> None:
    """S1 uses string solution_steps; S2/S3 use item_solutions list."""
    text = f"""---
format: {FORMAT_SOLUTIONS}
---

## Subject s1
## Solution
```yaml
number: 1
subject: mate
topic: t
difficulty: low
statement: |
  e1
solution_steps: |
  rezolvare s1
```

## Subject s2
## Solution
```yaml
number: 1
subject: mate
topic: t2
difficulty: medium
statement: |
  e2
item_solutions:
  - item: a
    solution_steps:
      - step: |
          pas a
        score: 0.5
```
"""
    doc = parse_solutions_markdown(text)
    data = doc.to_solution_dict()
    assert isinstance(data["s1"][0]["solution_steps"], str)
    assert isinstance(data["s2"][0]["item_solutions"], list)


def test_solution_step_defaults_score_and_skips_empty_step() -> None:
    """Step rows without score default to 0; empty steps are dropped."""
    block = ItemSolutionBlock.model_validate(
        {
            "item": "a",
            "solution_steps": [
                {"step": "pas 1"},
                {"step": ""},
                {"step": "pas 2", "score": 0.5},
            ],
        }
    )
    assert len(block.solution_steps) == 2
    assert block.solution_steps[0].score == 0.0
    assert block.solution_steps[1].score == 0.5


def test_parse_solutions_repairs_latex_column_zero() -> None:
    """Loose latex lines at column 0 are repaired in YAML blocks."""
    text = f"""---
format: {FORMAT_SOLUTIONS}
subject: s1
---

```yaml
number: 1
subject: mate
topic: t
difficulty: low
statement: |
  enunt
solution_steps: |
  Rezolvare:
\\(f(x)=x^2\\)
```
"""
    doc = parse_solutions_markdown(text)
    assert "\\(" in doc.s1[0].solution_steps


def test_parse_solutions_no_headings_uses_inferred_subject() -> None:
    """No headings + inferred subject still parses."""
    text = """```yaml
number: 1
subject: mate
topic: t
difficulty: low
statement: |
  enunt
solution_steps: |
  text
```"""
    doc = parse_solutions_markdown(text, inferred_subject="s1")
    assert doc.s1 is not None and len(doc.s1) == 1


def test_parse_solutions_plain_fence_unclosed_eof_still_parses() -> None:
    """Unclosed plain ``` fence at EOF still yields one block."""
    text = f"""---
format: {FORMAT_SOLUTIONS}
subject: s1
---

```
number: 1
subject: mate
topic: t
difficulty: low
statement: |
  enunt
solution_steps: |
  text
"""
    doc = parse_solutions_markdown(text)
    assert doc.s1 is not None and len(doc.s1) == 1


def test_round_trip_problems_and_solutions() -> None:
    """serialize -> parse keeps payloads for current schema."""
    problems = ProblemsDocument(
        s1=[
            ProblemRecord(
                number=1,
                subject="mate",
                topic="t",
                difficulty="low",
                statement="e1",
                choices=[],
                items=[],
            )
        ],
        s2=[
            ProblemRecord(
                number=1,
                subject="mate",
                topic="t2",
                difficulty="medium",
                statement="e2",
                choices=[],
                items=["a) x", "b) y"],
            )
        ],
    )
    solutions = SolutionsDocument(
        s1=[
            SolutionS1Record(
                number=1,
                subject="mate",
                topic="t",
                difficulty="low",
                statement="e1",
                solution_steps="rezolvare",
            )
        ],
        s2=[
            SolutionS23Record(
                number=1,
                subject="mate",
                topic="t2",
                difficulty="medium",
                statement="e2",
                item_solutions=[ItemSolutionBlock(item="a", solution_steps=[SolutionStep(step="x", score=1)])],
            )
        ],
    )
    parsed_p = parse_problems_markdown(serialize_problems_document(problems))
    parsed_s = parse_solutions_markdown(serialize_solutions_document(solutions))
    assert parsed_p.s2[0].items[0].startswith("a)")
    assert parsed_s.s1[0].solution_steps == "rezolvare"


def test_merge_new_shape_round_trip() -> None:
    """Merge keeps problems canonical and uses new solution shapes."""
    exam = {
        "s1": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t",
                "difficulty": "low",
                "statement": "e1",
                "choices": [],
                "items": [],
            }
        ],
        "s2": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t2",
                "difficulty": "medium",
                "statement": "e2",
                "choices": [],
                "items": ["a) x", "b) y"],
            }
        ],
    }
    sol = {
        "s1": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t",
                "difficulty": "low",
                "statement": "e1",
                "solution_steps": "rez",
            }
        ],
        "s2": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t2",
                "difficulty": "medium",
                "statement": "e2",
                "item_solutions": [
                    {"item": "a", "solution_steps": [{"step": "x", "score": 0.5}]},
                    {"item": "b", "solution_steps": [{"step": "y", "score": 1}]},
                ],
            }
        ],
    }
    merged = merge_exam_with_solution(exam, sol)
    md = serialize_merged_document(MergedDocument.from_merge_dict(merged))
    parsed = parse_merged_markdown(md)
    out = merged_document_to_rows_dict(parsed)
    assert out["s1"][0]["solution_steps"] == "rez"
    assert out["s2"][0]["items"] == ["a) x", "b) y"]
    assert out["s2"][0]["item_solutions"][1]["item"] == "b"


def test_serializer_helpers_from_dicts() -> None:
    """High-level serialize helpers accept normalized dicts."""
    problems_dict = {
        "s1": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t",
                "difficulty": "low",
                "statement": "e",
                "choices": [],
                "items": [],
            }
        ],
        "s3": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t3",
                "difficulty": "high",
                "statement": "e3",
                "choices": [],
                "items": ["a) z"],
            }
        ],
    }
    solutions_dict = {
        "s1": [
            {
                "number": 1,
                "subject": "mate",
                "topic": "t",
                "difficulty": "low",
                "statement": "e",
                "solution_steps": "sol",
            }
        ]
    }
    pdoc = parse_problems_markdown(serialize_problems_from_normalized_dict(problems_dict))
    sdoc = parse_solutions_markdown(serialize_solutions_from_normalized_dict(solutions_dict))
    assert "s3" in pdoc.to_exam_dict()
    assert "s1" in sdoc.to_solution_dict()


def test_merged_document_models() -> None:
    """Direct model construction stays serializable."""
    m1 = MergedS1Record(
        number=1,
        subject="mate",
        topic="t",
        difficulty="low",
        statement="e1",
        choices=[],
        items=[],
        solution_steps="rez",
    )
    m2 = MergedS23Record(
        number=1,
        subject="mate",
        topic="t2",
        difficulty="medium",
        statement="e2",
        choices=[],
        items=["a) x"],
        item_solutions=[ItemSolutionBlock(item="a", solution_steps=[SolutionStep(step="x", score=1)])],
    )
    doc = MergedDocument(s1=[m1], s2=[m2])
    out = doc.to_merge_dict()
    assert out["s1"][0]["solution_steps"] == "rez"
    assert out["s2"][0]["item_solutions"][0]["item"] == "a"

