"""
Pydantic models for exam structured data (problems, solutions, merged).
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SubjectKey = Literal["s1", "s2", "s3"]


def _coerce_problem_number(v: Any) -> int:
    """Coerce exercise number from int/float/string."""
    if isinstance(v, bool):
        raise TypeError("number must not be boolean")
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            raise ValueError("number string is empty")
        try:
            return int(float(s))
        except ValueError:
            match = re.search(r"\d+", s)
            if match is not None:
                return int(match.group(0))
            raise ValueError(f"number string is not numeric: {s!r}") from None
    raise TypeError(f"number must be int-coercible, got {type(v).__name__}")


def _normalize_step_rows(v: Any) -> list[Any]:
    """Normalize list-of-steps from small-model YAML output."""
    if not isinstance(v, list):
        raise TypeError("solution_steps must be a list of step rows")
    out: list[Any] = []
    for item in v:
        if isinstance(item, dict):
            step_val = item.get("step", "")
            if isinstance(step_val, str) and not step_val.strip():
                continue
            if step_val is None:
                continue
            row = dict(item)
            if row.get("score") is None:
                row["score"] = 0.0
            out.append(row)
            continue
        out.append(item)
    return out


class BaseNumberedRecord(BaseModel):
    """Shared numeric identity for problems/solutions."""

    number: int

    @field_validator("number", mode="before")
    @classmethod
    def coerce_number(cls, v: Any) -> int:
        """Normalize problem number."""
        return _coerce_problem_number(v)


class SolutionStep(BaseModel):
    """One table row in a scored solution list."""

    step: str
    score: float = Field(default=0.0)

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, v: Any) -> float:
        """Accept numeric strings and comma decimals; missing defaults to 0."""
        if v is None:
            return 0.0
        if isinstance(v, bool):
            raise TypeError("score must not be boolean")
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip().replace(",", ".")
            if not s:
                return 0.0
            return float(s)
        raise TypeError(f"score must be numeric, got {type(v).__name__}")


class ItemSolutionBlock(BaseModel):
    """S2/S3 item solution with per-step scoring rows."""

    item: str
    solution_steps: list[SolutionStep]

    @field_validator("item", mode="before")
    @classmethod
    def normalize_item(cls, v: Any) -> str:
        """Normalize item letter."""
        if isinstance(v, str):
            return v.strip().lower()
        return str(v).strip().lower()

    @field_validator("solution_steps", mode="before")
    @classmethod
    def normalize_steps(cls, v: Any) -> list[Any]:
        """Drop empty rows and fill missing score."""
        return _normalize_step_rows(v)


class ProblemRecord(BaseNumberedRecord):
    """Problems parse output record."""

    statement: str
    items: list[str] = Field(default_factory=list)


class SolutionS1Record(BaseNumberedRecord):
    """S1 solution: one string payload (no intermediate rows)."""

    solution_steps: str


class SolutionS23Record(BaseNumberedRecord):
    """S2/S3 solution: item_solutions list."""

    item_solutions: list[ItemSolutionBlock] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_item_solutions(self) -> SolutionS23Record:
        """Require exactly three item blocks ``a``, ``b``, ``c`` (bac-style barem)."""
        n = len(self.item_solutions)
        if n != 3:
            raise ValueError(
                f"item_solutions must contain exactly 3 blocks (a, b, c), got {n}"
            )
        letters = sorted(b.item for b in self.item_solutions)
        if letters != ["a", "b", "c"]:
            raise ValueError(
                "item_solutions must use items a, b, c exactly once each; "
                f"got {[b.item for b in self.item_solutions]}"
            )
        return self


class MergedS1Record(ProblemRecord):
    """Merged s1 record."""

    solution_steps: str = ""


class MergedS23Record(ProblemRecord):
    """Merged s2/s3 record."""

    item_solutions: list[ItemSolutionBlock] = Field(default_factory=list)


class ProblemsDocument(BaseModel):
    """Structured problems document with any subset of subjects."""

    s1: list[ProblemRecord] | None = None
    s2: list[ProblemRecord] | None = None
    s3: list[ProblemRecord] | None = None

    @model_validator(mode="after")
    def at_least_one_subject(self) -> ProblemsDocument:
        """Require at least one non-empty subject list."""
        has_any = any(
            getattr(self, k) is not None and len(getattr(self, k) or []) > 0
            for k in ("s1", "s2", "s3")
        )
        if not has_any:
            raise ValueError("ProblemsDocument must contain at least one non-empty s1/s2/s3 list")
        return self

    @model_validator(mode="after")
    def validate_bac_exercise_counts(self) -> ProblemsDocument:
        """
        Enforce fixed baccalaureate-style counts when a subject list is non-empty.

        Subject I: 6 problems. Subjects II and III: 2 problems each; each S2/S3 problem
        has exactly 3 sub-items (a, b, c).
        """
        if self.s1 is not None and len(self.s1) > 0 and len(self.s1) != 6:
            raise ValueError(f"s1 must contain exactly 6 problems, got {len(self.s1)}")
        for subj in ("s2", "s3"):
            rows = getattr(self, subj)
            if rows is None or len(rows) == 0:
                continue
            if len(rows) != 2:
                raise ValueError(f"{subj} must contain exactly 2 problems, got {len(rows)}")
            for idx, rec in enumerate(rows, start=1):
                if len(rec.items) != 3:
                    raise ValueError(
                        f"{subj} problem {idx}: must have exactly 3 items (a, b, c), "
                        f"got {len(rec.items)}"
                    )
        return self

    def subject_key(self) -> SubjectKey:
        """Return subject key when exactly one is present."""
        non_empty = [k for k in ("s1", "s2", "s3") if getattr(self, k)]
        if len(non_empty) != 1:
            raise ValueError(f"Expected exactly one subject, got {non_empty or 'none'}")
        return non_empty[0]  # type: ignore[return-value]

    def to_exam_dict(self) -> dict[str, Any]:
        """Dump non-empty subject lists as plain dict."""
        out: dict[str, Any] = {}
        for k in ("s1", "s2", "s3"):
            rows = getattr(self, k)
            if rows:
                out[k] = [r.model_dump(mode="python") for r in rows]
        return out


class SolutionsDocument(BaseModel):
    """Structured solutions document with any subset of subjects."""

    s1: list[SolutionS1Record] | None = None
    s2: list[SolutionS23Record] | None = None
    s3: list[SolutionS23Record] | None = None

    @model_validator(mode="after")
    def at_least_one_subject(self) -> SolutionsDocument:
        """Require at least one non-empty subject list."""
        has_any = any(
            getattr(self, k) is not None and len(getattr(self, k) or []) > 0
            for k in ("s1", "s2", "s3")
        )
        if not has_any:
            raise ValueError("SolutionsDocument must contain at least one non-empty s1/s2/s3 list")
        return self

    @model_validator(mode="after")
    def validate_bac_solution_counts(self) -> SolutionsDocument:
        """
        Enforce fixed counts for non-empty subject lists (same as problems: 6 / 2 / 2).

        Per-exercise ``item_solutions`` shape for S2/S3 is validated on ``SolutionS23Record``.
        """
        if self.s1 is not None and len(self.s1) > 0 and len(self.s1) != 6:
            raise ValueError(f"s1 must contain exactly 6 solution records, got {len(self.s1)}")
        for subj in ("s2", "s3"):
            rows = getattr(self, subj)
            if rows is None or len(rows) == 0:
                continue
            if len(rows) != 2:
                raise ValueError(
                    f"{subj} must contain exactly 2 solution records, got {len(rows)}"
                )
        return self

    def to_solution_dict(self) -> dict[str, Any]:
        """Dump solutions as legacy-compatible per-subject arrays."""
        out: dict[str, Any] = {}
        if self.s1:
            out["s1"] = [r.model_dump(mode="python") for r in self.s1]
        if self.s2:
            out["s2"] = [r.model_dump(mode="python") for r in self.s2]
        if self.s3:
            out["s3"] = [r.model_dump(mode="python") for r in self.s3]
        return out


class MergedDocument(BaseModel):
    """Merged output document with any subset of subjects."""

    s1: list[MergedS1Record] | None = None
    s2: list[MergedS23Record] | None = None
    s3: list[MergedS23Record] | None = None

    def to_merge_dict(self) -> dict[str, Any]:
        """Dump merged rows per subject."""
        out: dict[str, Any] = {}
        if self.s1:
            out["s1"] = [r.model_dump(mode="python") for r in self.s1]
        if self.s2:
            out["s2"] = [r.model_dump(mode="python") for r in self.s2]
        if self.s3:
            out["s3"] = [r.model_dump(mode="python") for r in self.s3]
        return out

    @classmethod
    def from_merge_dict(cls, data: dict[str, Any]) -> MergedDocument:
        """Build typed merged document from plain dict."""
        kwargs: dict[str, Any] = {}
        if isinstance(data.get("s1"), list):
            kwargs["s1"] = [MergedS1Record.model_validate(x) for x in data["s1"] if isinstance(x, dict)]
        if isinstance(data.get("s2"), list):
            kwargs["s2"] = [MergedS23Record.model_validate(x) for x in data["s2"] if isinstance(x, dict)]
        if isinstance(data.get("s3"), list):
            kwargs["s3"] = [MergedS23Record.model_validate(x) for x in data["s3"] if isinstance(x, dict)]
        return cls(**kwargs)
