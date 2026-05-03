"""Unit tests for runner checkpoint skip guard behavior."""

from __future__ import annotations

from pathlib import Path

from exam_parser.pipeline.config import Checkpoint, PipelineConfig
from exam_parser.pipeline.runner import _step_has_checkpoint_coverage_gaps


def test_skip_guard_detects_missing_file_for_parse_problems(tmp_path: Path) -> None:
    """Guard should report gaps when expected parse input files are not checkpointed."""
    problems_dir = tmp_path / "problems"
    solutions_dir = tmp_path / "solutions"
    problems_dir.mkdir(parents=True, exist_ok=True)
    solutions_dir.mkdir(parents=True, exist_ok=True)
    (problems_dir / "a.pdf").write_bytes(b"%PDF-1.4\n")
    (problems_dir / "b.pdf").write_bytes(b"%PDF-1.4\n")

    cfg = PipelineConfig(
        run_name="r",
        problems_dir=problems_dir,
        solutions_dir=solutions_dir,
    )
    cp = Checkpoint(tmp_path / "checkpoint.json", run_name="r")
    cp.mark_file_done("parse_problems", "a.pdf")
    cp.mark_step_done("parse_problems")

    assert _step_has_checkpoint_coverage_gaps("parse_problems", cfg, cp) is True


def test_skip_guard_accepts_complete_coverage_for_parse_problems(tmp_path: Path) -> None:
    """Guard should allow skip when all parse input files are checkpointed."""
    problems_dir = tmp_path / "problems"
    solutions_dir = tmp_path / "solutions"
    problems_dir.mkdir(parents=True, exist_ok=True)
    solutions_dir.mkdir(parents=True, exist_ok=True)
    (problems_dir / "a.pdf").write_bytes(b"%PDF-1.4\n")

    cfg = PipelineConfig(
        run_name="r",
        problems_dir=problems_dir,
        solutions_dir=solutions_dir,
    )
    cp = Checkpoint(tmp_path / "checkpoint.json", run_name="r")
    cp.mark_file_done("parse_problems", "a.pdf")
    cp.mark_step_done("parse_problems")

    assert _step_has_checkpoint_coverage_gaps("parse_problems", cfg, cp) is False
