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


def _s1_problem_yaml_block(number: int, statement: str) -> str:
    """One fenced YAML block for a Subject I problem (BAC: six per subject)."""
    return f"""## Problem

```yaml
number: {number}
statement: |
  {statement}
items: []
```"""


def _minimal_problems_md(statement: str = r"Text \mathbb{R} and \frac{1}{2}") -> str:
    """Minimal valid problems markdown for s1 (six exercises)."""
    parts: list[str] = []
    for i in range(1, 7):
        st = statement if i == 1 else f"Problem {i} body."
        parts.append(_s1_problem_yaml_block(i, st))
    blocks = "\n\n".join(parts)
    return f"""# Exam parser — structured problems v1

---
format: {FORMAT_PROBLEMS}
subject: s1
---

## Subject s1

{blocks}
"""


def test_normalize_llm_markdown_response_strips_outer_fence() -> None:
    """Outer markdown fence should be removed."""
    wrapped = "```markdown\n" + _minimal_problems_md() + "\n```"
    assert "format:" in normalize_llm_markdown_response(wrapped)


def test_parse_problems_supports_multiple_subjects() -> None:
    """Problems document may contain any subset of s1/s2/s3 (BAC counts: 6 / 2 / 2)."""
    s1_blocks = "\n\n".join(
        f"""## Problem
```yaml
number: {n}
statement: |
  s1 text {n}
items: []
```"""
        for n in range(1, 7)
    )
    text = f"""---
format: {FORMAT_PROBLEMS}
---

## Subject s1
{s1_blocks}

## Subject s2
## Problem
```yaml
number: 1
statement: |
  s2 text one
items:
  - |
    a) aa
  - |
    b) bb
  - |
    c) cc
```

## Problem
```yaml
number: 2
statement: |
  s2 text two
items:
  - |
    a) aa2
  - |
    b) bb2
  - |
    c) cc2
```
"""
    doc = parse_problems_markdown(text)
    assert len(doc.s1 or []) == 6
    assert len(doc.s2 or []) == 2
    assert len(doc.s2[0].items) == 3


def test_parse_problems_no_headings_uses_inferred_subject() -> None:
    """Without section headings we can bucket by inferred subject (s1 needs six exercises)."""
    blocks = []
    for n in range(1, 7):
        body = "x" if n == 1 else f"x{n}"
        blocks.append(
            f"""```yaml
number: {n}
statement: |
  {body}
items: []
```"""
        )
    md = "\n\n".join(blocks)
    doc = parse_problems_markdown(md, inferred_subject="s1")
    assert doc.s1[0].statement.strip() == "x"


def test_parse_problems_unfenced_yaml_under_problem_heading() -> None:
    """Subject sections with unfenced YAML under ## Problem should still parse."""
    text = f"""---
format: {FORMAT_PROBLEMS}
---

## Subject s2
## Problem
number: 1
statement: |
  s2 text one
items:
  - |
    a) aa
  - |
    b) bb
  - |
    c) cc

## Problem
number: 2
statement: |
  s2 text two
items:
  - |
    a) aa2
  - |
    b) bb2
  - |
    c) cc2
"""
    doc = parse_problems_markdown(text)
    assert doc.s2 is not None and len(doc.s2) == 2
    assert doc.s2[0].number == 1


def test_parse_problems_heading_based_sections_without_yaml() -> None:
    """Fallback parser should accept heading-only problem blocks."""
    text = f"""---
format: {FORMAT_PROBLEMS}
---

## Subject s2

## Problem 1
### Topic: Matrice
### Difficulty: Medium
### Statement:
Enunt problema 1.
### Items:
- a) primul item
- b) al doilea item
- c) al treilea item

## Problem 2
### Topic: Aritmetica modulara
### Difficulty: High
### Statement:
Enunt problema 2.
### Items:
- a) item 2a
- b) item 2b
- c) item 2c
"""
    doc = parse_problems_markdown(text)
    assert doc.s2 is not None and len(doc.s2) == 2
    assert doc.s2[0].number == 1
    assert len(doc.s2[0].items) == 3
    assert doc.s2[1].number == 2


def test_parse_problems_heading_based_sections_with_problems_container() -> None:
    """Fallback parser should accept ## Problems + ### Problem N + #### Statement format."""
    text = f"""---
format: {FORMAT_PROBLEMS}
---

## Subject s2
## Problems

### Problem 1
#### Statement
Enunt problema 1.

#### Items:
- a) unu
- b) doi
- c) trei

### Problem 2
#### Statement
Enunt problema 2.

#### Items:
- a) patru
- b) cinci
- c) sase
"""
    doc = parse_problems_markdown(text)
    assert doc.s2 is not None and len(doc.s2) == 2
    assert doc.s2[0].number == 1
    assert doc.s2[1].number == 2
    assert len(doc.s2[0].items) == 3
    assert len(doc.s2[1].items) == 3


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
    s1_sol = "\n\n".join(
        f"""## Solution
```yaml
number: {n}
solution_steps: |
  rezolvare s1 ex {n}
```"""
        for n in range(1, 7)
    )
    s2_one = """## Solution
```yaml
number: 1
item_solutions:
  - item: a
    solution_steps:
      - step: pas a
        score: 0.5
  - item: b
    solution_steps:
      - step: pas b
        score: 0.5
  - item: c
    solution_steps:
      - step: pas c
        score: 0.5
```
"""
    s2_two = """## Solution
```yaml
number: 2
item_solutions:
  - item: a
    solution_steps:
      - step: pas a2
        score: 1
  - item: b
    solution_steps:
      - step: pas b2
        score: 0
  - item: c
    solution_steps:
      - step: pas c2
        score: 0
```
"""
    text = f"""---
format: {FORMAT_SOLUTIONS}
---

## Subject s1
{s1_sol}

## Subject s2
{s2_one}

{s2_two}
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
    tail = "\n\n".join(
        f"""```yaml
number: {n}
solution_steps: |
  ok {n}
```"""
        for n in range(2, 7)
    )
    text = f"""---
format: {FORMAT_SOLUTIONS}
subject: s1
---

```yaml
number: 1
solution_steps: |
  Rezolvare:
\\(f(x)=x^2\\)
```

{tail}
"""
    doc = parse_solutions_markdown(text)
    assert "\\(" in doc.s1[0].solution_steps


def test_parse_solutions_no_headings_uses_inferred_subject() -> None:
    """No headings + inferred subject still parses (six Subject I solutions)."""
    parts = []
    for n in range(1, 7):
        parts.append(
            f"""```yaml
number: {n}
solution_steps: |
  text {n}
```"""
        )
    text = "\n\n".join(parts)
    doc = parse_solutions_markdown(text, inferred_subject="s1")
    assert doc.s1 is not None and len(doc.s1) == 6


def test_parse_solutions_plain_fence_unclosed_eof_still_parses() -> None:
    """Unclosed ```yaml fence at EOF still yields a final block (with five closed blocks before)."""
    closed = "\n\n".join(
        f"""```yaml
number: {n}
solution_steps: |
  text {n}
```"""
        for n in range(1, 6)
    )
    text = f"""---
format: {FORMAT_SOLUTIONS}
subject: s1
---

{closed}

```yaml
number: 6
solution_steps: |
  text six
"""
    doc = parse_solutions_markdown(text)
    assert doc.s1 is not None and len(doc.s1) == 6


def test_round_trip_problems_and_solutions() -> None:
    """serialize -> parse keeps payloads for current schema."""
    s1_probs = [
        ProblemRecord(number=n, statement=f"e{n}", items=[]) for n in range(1, 7)
    ]
    s2_probs = [
        ProblemRecord(
            number=1,
            statement="e2-1",
            items=["a) x", "b) y", "c) z"],
        ),
        ProblemRecord(
            number=2,
            statement="e2-2",
            items=["a) x2", "b) y2", "c) z2"],
        ),
    ]
    problems = ProblemsDocument(s1=s1_probs, s2=s2_probs)
    s1_sols = [SolutionS1Record(number=n, solution_steps="rezolvare") for n in range(1, 7)]
    s2_sols = [
        SolutionS23Record(
            number=1,
            item_solutions=[
                ItemSolutionBlock(item="a", solution_steps=[SolutionStep(step="x", score=1)]),
                ItemSolutionBlock(item="b", solution_steps=[SolutionStep(step="y", score=0)]),
                ItemSolutionBlock(item="c", solution_steps=[SolutionStep(step="z", score=0)]),
            ],
        ),
        SolutionS23Record(
            number=2,
            item_solutions=[
                ItemSolutionBlock(item="a", solution_steps=[SolutionStep(step="x2", score=1)]),
                ItemSolutionBlock(item="b", solution_steps=[SolutionStep(step="y2", score=0)]),
                ItemSolutionBlock(item="c", solution_steps=[SolutionStep(step="z2", score=0)]),
            ],
        ),
    ]
    solutions = SolutionsDocument(s1=s1_sols, s2=s2_sols)
    parsed_p = parse_problems_markdown(serialize_problems_document(problems))
    parsed_s = parse_solutions_markdown(serialize_solutions_document(solutions))
    assert parsed_p.s2[0].items[0].startswith("a)")
    assert parsed_s.s1[0].solution_steps == "rezolvare"


def test_merge_new_shape_round_trip() -> None:
    """Merge keeps problems canonical and uses new solution shapes."""
    exam = {
        "s1": [
            {"number": n, "statement": f"e{n}", "items": []} for n in range(1, 7)
        ],
        "s2": [
            {
                "number": 1,
                "statement": "e2-1",
                "items": ["a) x", "b) y", "c) z"],
            },
            {
                "number": 2,
                "statement": "e2-2",
                "items": ["a) x2", "b) y2", "c) z2"],
            },
        ],
    }
    sol = {
        "s1": [{"number": n, "solution_steps": "rez"} for n in range(1, 7)],
        "s2": [
            {
                "number": 1,
                "item_solutions": [
                    {"item": "a", "solution_steps": [{"step": "x", "score": 0.5}]},
                    {"item": "b", "solution_steps": [{"step": "y", "score": 0.5}]},
                    {"item": "c", "solution_steps": [{"step": "z", "score": 0}]},
                ],
            },
            {
                "number": 2,
                "item_solutions": [
                    {"item": "a", "solution_steps": [{"step": "x2", "score": 1}]},
                    {"item": "b", "solution_steps": [{"step": "y2", "score": 0}]},
                    {"item": "c", "solution_steps": [{"step": "z2", "score": 0}]},
                ],
            },
        ],
    }
    merged = merge_exam_with_solution(exam, sol)
    md = serialize_merged_document(MergedDocument.from_merge_dict(merged))
    parsed = parse_merged_markdown(md)
    out = merged_document_to_rows_dict(parsed)
    assert out["s1"][0]["solution_steps"] == "rez"
    assert out["s2"][0]["items"] == ["a) x", "b) y", "c) z"]
    assert out["s2"][0]["item_solutions"][1]["item"] == "b"


def test_serializer_helpers_from_dicts() -> None:
    """High-level serialize helpers accept normalized dicts."""
    problems_dict = {
        "s1": [{"number": n, "statement": f"e{n}", "items": []} for n in range(1, 7)],
        "s3": [
            {
                "number": 1,
                "statement": "e3-1",
                "items": ["a) z", "b) y", "c) x"],
            },
            {
                "number": 2,
                "statement": "e3-2",
                "items": ["a) z2", "b) y2", "c) x2"],
            },
        ],
    }
    solutions_dict = {
        "s1": [{"number": n, "solution_steps": "sol"} for n in range(1, 7)],
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

