"""CLI entry point for the exam ingestion pipeline.

Usage (from repo root):
    uv run python -m exam_parser.pipeline.cli \\
        --run-name bac_2024 \\
        --problems-dir path/to/problems \\
        --solutions-dir path/to/solutions \\
        [--source var] [--start-from merge] [--dry-run] [--overwrite]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from exam_parser.pipeline.config import STEP_NAMES, PipelineConfig
from exam_parser.pipeline.model_options import ollama_ids_for_argparse


def _build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for the ingestion pipeline."""
    p = argparse.ArgumentParser(
        description=(
            "End-to-end exam ingestion: PDF → Nougat → markdown → Ollama JSON → merge → DB → vector index."
        ),
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
        help="Show what would be processed without calling Ollama or writing to DB",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-process files even if checkpoint says done",
    )
    oids = ollama_ids_for_argparse()
    p.add_argument(
        "--ollama-model",
        choices=oids,
        default=None,
        metavar="MODEL",
        help="Ollama model for markdown → JSON (parse problems & solutions).",
    )
    return p


def _register_nougat_gpu_cleanup_on_signals() -> None:
    """
    Register SIGTERM/SIGINT handlers that release Nougat GPU resources before process exit.

    The handler reinstates the default behavior and re-sends the signal to preserve
    normal termination semantics. ``kill -9`` cannot be intercepted.
    """
    from exam_parser.parsers.nougat_local_gpu import release_nougat_gpu_resources

    log = logging.getLogger(__name__)

    def _handler(signum: int, frame: object | None) -> None:
        try:
            release_nougat_gpu_resources(log=log.info)
        except Exception:
            log.exception("Nougat GPU release after signal failed")
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _handler)
        except ValueError:
            log.debug("Skipping signal %s registration (not main thread or unsupported)", sig)


def _log_torch_runtime_diagnostics(log: logging.Logger) -> None:
    """Log runtime diagnostics for PyTorch/CUDA visibility in this CLI process."""
    try:
        import torch

        log.info(
            "Runtime diagnostics: python=%s, torch=%s, torch_cuda=%s, cuda_available=%s, cuda_device_count=%s, CUDA_VISIBLE_DEVICES=%s",
            sys.executable,
            torch.__version__,
            torch.version.cuda,
            torch.cuda.is_available(),
            torch.cuda.device_count() if torch.cuda.is_available() else 0,
            os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"),
        )
        if torch.cuda.is_available():
            log.info("Runtime diagnostics: cuda_device_0=%s", torch.cuda.get_device_name(0))
    except Exception:
        log.exception("Failed to collect torch/CUDA runtime diagnostics")


def main() -> None:
    """Parse CLI args, build pipeline config, and run the async pipeline entrypoint."""
    # Set up console logging for profu_logging
    from profu_logging.log_utils import ColoredJsonFormatter

    root_logger = logging.getLogger("ai_backend.json")
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredJsonFormatter("%(message)s"))
        root_logger.addHandler(handler)
    log = root_logger

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
        ollama_model=args.ollama_model,
    )

    _register_nougat_gpu_cleanup_on_signals()

    try:
        # Import lazily so startup/import errors (e.g. settings validation)
        # are logged through the JSON logger and surfaced in the Streamlit UI.
        from exam_parser.pipeline.runner import run_pipeline

        _log_torch_runtime_diagnostics(log)
        log.info("Starting exam parser pipeline run")
        asyncio.run(run_pipeline(config))
    except KeyboardInterrupt:
        log.warning("Pipeline interrupted by user")
        raise
    except Exception:
        # Always log through the JSON logger consumed by the Streamlit UI.
        log.exception("Pipeline stopped after an error in a step")
        sys.exit(1)


if __name__ == "__main__":
    main()
