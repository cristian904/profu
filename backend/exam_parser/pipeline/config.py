"""Pipeline configuration, directory layout, and checkpoint management."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent.parent  # backend/exam_parser
_RUNS_DIR = _SCRIPT_DIR / "runs"

# Ordered list of pipeline step names
STEP_NAMES: list[str] = [
    "parse_problems",
    "parse_solutions",
    "merge",
    "fix_latex",
    "load_to_db",
    "index_to_vector_db",
]


@dataclass
class PipelineConfig:
    """Immutable configuration for a single pipeline run."""

    run_name: str
    problems_dir: Path
    solutions_dir: Path
    source: str = "var"
    start_from: str | None = None
    dry_run: bool = False
    overwrite: bool = False


@dataclass
class RunDirs:
    """Computed directory paths for a pipeline run."""

    root: Path
    problems_vision: Path
    problems_structured: Path
    solutions_vision: Path
    solutions_structured: Path
    merged: Path
    fixed: Path

    @classmethod
    def from_config(cls, config: PipelineConfig) -> RunDirs:
        root = _RUNS_DIR / config.run_name
        return cls(
            root=root,
            problems_vision=root / "01_problems_parsed" / "vision",
            problems_structured=root / "01_problems_parsed" / "structured",
            solutions_vision=root / "02_solutions_parsed" / "vision",
            solutions_structured=root / "02_solutions_parsed" / "structured",
            merged=root / "03_merged",
            fixed=root / "04_fixed",
        )

    def create_all(self) -> None:
        """Create all output directories."""
        for d in (
            self.problems_vision,
            self.problems_structured,
            self.solutions_vision,
            self.solutions_structured,
            self.merged,
            self.fixed,
        ):
            d.mkdir(parents=True, exist_ok=True)


class Checkpoint:
    """File-level checkpoint tracker persisted as JSON.

    Thread-safe: multiple async tasks can call ``mark_done`` concurrently
    (they all go through ``asyncio.to_thread`` which releases the GIL).
    """

    def __init__(self, path: Path, run_name: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                self._data: dict[str, Any] = json.load(f)
        else:
            self._data = {"run_name": run_name, "steps": {}}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_file_done(self, step: str, filename: str) -> bool:
        """Return True if *filename* was already completed in *step*."""
        step_info = self._data["steps"].get(step, {})
        return filename in step_info.get("completed_files", [])

    def is_step_done(self, step: str) -> bool:
        step_info = self._data["steps"].get(step, {})
        return step_info.get("status") == "done"

    # ------------------------------------------------------------------
    # Mutations (thread-safe, auto-flush)
    # ------------------------------------------------------------------

    def mark_file_done(self, step: str, filename: str) -> None:
        with self._lock:
            step_info = self._data["steps"].setdefault(step, {"completed_files": [], "status": "in_progress"})
            if filename not in step_info["completed_files"]:
                step_info["completed_files"].append(filename)
            self._flush()

    def mark_step_done(self, step: str) -> None:
        with self._lock:
            step_info = self._data["steps"].setdefault(step, {"completed_files": [], "status": "done"})
            step_info["status"] = "done"
            self._flush()

    def reset_step(self, step: str) -> None:
        """Clear checkpoint for *step* (used with ``--start-from``)."""
        with self._lock:
            self._data["steps"].pop(step, None)
            self._flush()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        tmp.replace(self._path)
