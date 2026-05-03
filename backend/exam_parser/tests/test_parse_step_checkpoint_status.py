"""Regression tests for parse step checkpoint status handling."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from exam_parser.parsers.ollama_structured import StructuredJsonParseError
from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.steps import parse_problems, parse_solutions


class _TestLogger:
    """Minimal logger stub used by parse step tests."""

    def info(self, message: str) -> None:
        """Log info messages for test execution."""
        return None

    def warning(self, message: str) -> None:
        """Log warning messages for test execution."""
        return None

    def error(self, message: str) -> None:
        """Log error messages for test execution."""
        return None


def _build_problem_run(tmp_path: Path) -> tuple[PipelineConfig, RunDirs, Checkpoint]:
    """Create config/directories/checkpoint for a problem parse test run."""
    problems_dir = tmp_path / "problems"
    solutions_dir = tmp_path / "solutions"
    problems_dir.mkdir(parents=True, exist_ok=True)
    solutions_dir.mkdir(parents=True, exist_ok=True)

    cfg = PipelineConfig(
        run_name="test_run",
        problems_dir=problems_dir,
        solutions_dir=solutions_dir,
    )
    run_root = tmp_path / "runs" / cfg.run_name
    dirs = RunDirs(
        root=run_root,
        problems_vision=run_root / "01_problems_parsed" / "vision",
        problems_structured=run_root / "01_problems_parsed" / "structured",
        solutions_vision=run_root / "02_solutions_parsed" / "vision",
        solutions_structured=run_root / "02_solutions_parsed" / "structured",
        merged=run_root / "03_merged",
    )
    dirs.create_all()
    checkpoint = Checkpoint(dirs.root / "checkpoint.json", run_name=cfg.run_name)
    return cfg, dirs, checkpoint


def test_parse_problems_does_not_mark_step_done_when_files_fail(tmp_path: Path) -> None:
    """parse_problems should fail the step when unresolved files remain."""
    cfg, dirs, checkpoint = _build_problem_run(tmp_path)
    logger = _TestLogger()

    pdf = cfg.problems_dir / "demo.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    (dirs.problems_vision / "demo.md").write_text("markdown", encoding="utf-8")

    with patch(
        "exam_parser.pipeline.steps.parse_problems.extract_structured_problems_from_markdown",
        side_effect=StructuredJsonParseError("invalid json", "{}"),
    ):
        with pytest.raises(RuntimeError, match="\\[parse_problems\\] Parsing failed"):
            asyncio.run(parse_problems.run(cfg, dirs, checkpoint, logger))

    assert checkpoint.is_file_done("parse_problems", "demo.pdf") is False
    assert checkpoint.is_step_done("parse_problems") is False


def test_parse_solutions_does_not_mark_step_done_when_files_fail(tmp_path: Path) -> None:
    """parse_solutions should fail the step when unresolved files remain."""
    cfg, dirs, checkpoint = _build_problem_run(tmp_path)
    logger = _TestLogger()

    pdf = cfg.solutions_dir / "demo.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    (dirs.solutions_vision / "demo.md").write_text("markdown", encoding="utf-8")

    with patch(
        "exam_parser.pipeline.steps.parse_solutions.scoring_scale_md_to_structured_ollama",
        side_effect=StructuredJsonParseError("invalid json", "{}"),
    ):
        with pytest.raises(RuntimeError, match="\\[parse_solutions\\] Parsing failed"):
            asyncio.run(parse_solutions.run(cfg, dirs, checkpoint, logger))

    assert checkpoint.is_file_done("parse_solutions", "demo.pdf") is False
    assert checkpoint.is_step_done("parse_solutions") is False
