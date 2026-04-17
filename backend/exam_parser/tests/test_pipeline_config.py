"""Unit tests for pipeline RunDirs and Checkpoint (exam_parser.pipeline.config)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs, STEP_NAMES


def test_step_names_order() -> None:
    """Pipeline step list should stay stable for CLI and checkpoints."""
    assert STEP_NAMES[0] == "extract_problems"
    assert STEP_NAMES[1] == "parse_problems"
    assert "merge" in STEP_NAMES
    assert "index_to_vector_db" in STEP_NAMES
    assert "fix_latex" not in STEP_NAMES


def test_run_dirs_from_config_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RunDirs should mirror the run folder layout under runs/<run_name>."""
    monkeypatch.setattr(
        "exam_parser.pipeline.config._RUNS_DIR",
        tmp_path / "runs",
    )
    cfg = PipelineConfig(
        run_name="unit_test_run",
        problems_dir=Path("/tmp/p"),
        solutions_dir=Path("/tmp/s"),
    )
    dirs = RunDirs.from_config(cfg)
    assert dirs.root == tmp_path / "runs" / "unit_test_run"
    assert dirs.merged == dirs.root / "03_merged"
    assert dirs.problems_vision == dirs.root / "01_problems_parsed" / "vision"


def test_run_dirs_create_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """create_all should mkdir every stage directory."""
    monkeypatch.setattr("exam_parser.pipeline.config._RUNS_DIR", tmp_path)
    cfg = PipelineConfig(run_name="r", problems_dir=Path("p"), solutions_dir=Path("s"))
    dirs = RunDirs.from_config(cfg)
    dirs.create_all()
    assert dirs.problems_vision.is_dir()
    assert dirs.merged.is_dir()


def test_checkpoint_new_file_roundtrip(tmp_path: Path) -> None:
    """Checkpoint should persist completed files and step status."""
    path = tmp_path / "cp.json"
    cp = Checkpoint(path, run_name="r1")
    assert cp.is_file_done("extract_problems", "a.pdf") is False
    cp.mark_file_done("extract_problems", "a.pdf")
    assert cp.is_file_done("extract_problems", "a.pdf") is True
    cp.mark_step_done("extract_problems")
    assert cp.is_step_done("extract_problems") is True

    cp2 = Checkpoint(path, run_name="r1")
    assert cp2.is_file_done("extract_problems", "a.pdf") is True


def test_checkpoint_reset_step(tmp_path: Path) -> None:
    """reset_step should drop the step entry."""
    path = tmp_path / "cp.json"
    cp = Checkpoint(path, run_name="r1")
    cp.mark_file_done("merge", "x.md")
    cp.reset_step("merge")
    assert cp.is_file_done("merge", "x.md") is False


def test_checkpoint_load_existing(tmp_path: Path) -> None:
    """Loading an existing JSON file should hydrate internal state."""
    path = tmp_path / "existing.json"
    payload = {
        "run_name": "old",
        "steps": {
            "merge": {"completed_files": ["1.md"], "status": "in_progress"},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    cp = Checkpoint(path, run_name="ignored_on_load")
    assert cp.is_file_done("merge", "1.md") is True
