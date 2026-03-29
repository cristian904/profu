"""CLI entry point for the exam ingestion pipeline.

Usage (from repo root):
    uv run python -m exam_parser.pipeline.cli \\
        --run-name bac_2024 \\
        --problems-dir path/to/problems \\
        --solutions-dir path/to/solutions \\
        [--source var] [--start-from fix_latex] [--dry-run] [--overwrite]
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from exam_parser.pipeline.config import STEP_NAMES, PipelineConfig
from exam_parser.pipeline.runner import run_pipeline


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="End-to-end exam ingestion pipeline: PDF → parse → merge → fix → DB → vector index.",
    )
    p.add_argument(
        "--run-name",
        required=True,
        help="Unique name for this pipeline run (used as directory name under runs/)",
    )
    p.add_argument(
        "--problems-dir",
        type=Path,
        required=True,
        help="Directory containing problem PDFs",
    )
    p.add_argument(
        "--solutions-dir",
        type=Path,
        required=True,
        help="Directory containing solution PDFs (same filenames as problems)",
    )
    p.add_argument(
        "--source",
        choices=("var", "exam", "test"),
        default="var",
        help="exam_problems.source value (default: var)",
    )
    p.add_argument(
        "--start-from",
        choices=STEP_NAMES,
        default=None,
        metavar="STEP",
        help=f"Resume from this step (resets it + all subsequent). Steps: {', '.join(STEP_NAMES)}",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making API calls or DB writes",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-process files even if checkpoint says done",
    )
    return p


def main() -> None:
    # Set up console logging for profu_logging
    import logging
    import sys
    from profu_logging.log_utils import ColoredJsonFormatter

    root_logger = logging.getLogger("ai_backend.json")
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredJsonFormatter("%(message)s"))
        root_logger.addHandler(handler)

    parser = _build_parser()
    args = parser.parse_args()

    config = PipelineConfig(
        run_name=args.run_name,
        problems_dir=args.problems_dir.resolve(),
        solutions_dir=args.solutions_dir.resolve(),
        source=args.source,
        start_from=args.start_from,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )

    asyncio.run(run_pipeline(config))


if __name__ == "__main__":
    main()
