"""
Pydantic models for exam structured data (problems, solutions, merged).
"""
from __future__ import annotations

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
        return int(float(s))
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


class BaseExamRecord(BaseModel):
    """Shared fields across problems/solutions."""

    number: int
    subject: str = "mate"
    topic: str | None = None
    difficulty: str
    statement: str

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


class ProblemRecord(BaseExamRecord):
    """Problems parse output record."""

    choices: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)


class SolutionS1Record(BaseExamRecord):
    """S1 solution: one string payload (no intermediate rows)."""

    solution_steps: str


class SolutionS23Record(BaseExamRecord):
    """S2/S3 solution: item_solutions list."""

    item_solutions: list[ItemSolutionBlock] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_item_solutions(self) -> SolutionS23Record:
        """Require at least one item solution in S2/S3 output."""
        if not self.item_solutions:
            raise ValueError("item_solutions must contain at least one item for s2/s3 records")
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
