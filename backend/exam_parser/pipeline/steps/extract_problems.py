"""Extract problem PDFs to markdown with local Nougat (GPU/CPU)."""
from __future__ import annotations

import asyncio
import traceback
from pathlib import Path

from profu_logging.feature_logger import FeatureLogger

from exam_parser.parsers.nougat_local_gpu import release_nougat_gpu_resources, write_markdown_local_gpu
from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.settings import settings

STEP_NAME = "extract_problems"


async def _extract_one(
    pdf: Path,
    vision_dir: Path,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Run Nougat on one local PDF and write ``{stem}.md``."""
    stem = pdf.stem
    vision_out = vision_dir / f"{stem}.md"

    try:
        await asyncio.to_thread(
            write_markdown_local_gpu,
            pdf,
            vision_out,
            model_id=settings.nougat_model_id,
            device_setting=settings.nougat_device,
            feature_logger=logger,
        )
        logger.info(f"[{STEP_NAME}] Nougat markdown written: {vision_out.name}")
        checkpoint.mark_file_done(STEP_NAME, pdf.name)
    except Exception as exc:
        logger.error(exc, traceback=traceback.format_exc())
        raise


async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Process problem PDFs sequentially (one PDF at a time)."""
    try:
        pdfs = sorted(config.problems_dir.glob("*.pdf"))
        if not pdfs:
            logger.warning(f"[{STEP_NAME}] No PDFs found in {config.problems_dir}")
            return

        pending = [p for p in pdfs if not checkpoint.is_file_done(STEP_NAME, p.name)]
        logger.info(
            f"[{STEP_NAME}] model={settings.nougat_model_id}, device_setting={settings.nougat_device}, "
            f"{len(pdfs)} PDFs total, {len(pdfs) - len(pending)} already extracted, "
            f"{len(pending)} to process"
        )

        if not pending:
            return

        if config.dry_run:
            for p in pending:
                logger.info(f"[{STEP_NAME}] [DRY RUN] Would run local Nougat on: {p.name}")
            return

        for pdf in pending:
            logger.info(f"[{STEP_NAME}] === Extracting {pdf.name} ===")
            await _extract_one(pdf, dirs.problems_vision, checkpoint, logger)

        checkpoint.mark_step_done(STEP_NAME)
        logger.info(f"[{STEP_NAME}] Step complete")
    finally:
        try:
            release_nougat_gpu_resources(log=logger.info)
        except Exception as exc:
            logger.error(exc, traceback=traceback.format_exc())
