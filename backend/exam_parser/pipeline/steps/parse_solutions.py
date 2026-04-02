"""Step 2 — Parse solution PDFs: vision (PDF → md) then structured extraction (md → JSON)."""
from __future__ import annotations

import asyncio
import json
import traceback
from pathlib import Path

from profu_logging.feature_logger import FeatureLogger

from exam_parser.parsers.scoring_scale_vision import parse_scoring_scale_pdf
from exam_parser.parsers.scoring_scale_to_structured import scoring_scale_md_to_structured
from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.settings import settings

STEP_NAME = "parse_solutions"


async def _process_one(
    pdf: Path,
    vision_dir: Path,
    structured_dir: Path,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Parse a single solution PDF (vision + structured) and checkpoint."""
    stem = pdf.stem
    vision_out = vision_dir / f"{stem}.md"
    structured_out = structured_dir / f"{stem}.json"

    try:
        # Vision: PDF → markdown
        md_text: str = await asyncio.to_thread(parse_scoring_scale_pdf, pdf, settings.model_vision)
        vision_out.write_text(md_text, encoding="utf-8")
        logger.info(f"Vision done: {pdf.name}")

        # Structured: markdown → JSON
        data: dict = await asyncio.to_thread(scoring_scale_md_to_structured, md_text, settings.model_structured)
        structured_out.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Structured done: {pdf.name}")

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
    """Discover solution PDFs, skip completed ones, fire all remaining concurrently."""
    pdfs = sorted(config.solutions_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"No PDFs found in {config.solutions_dir}")
        return

    pending = [p for p in pdfs if not checkpoint.is_file_done(STEP_NAME, p.name)]
    logger.info(
        f"[{STEP_NAME}] {len(pdfs)} PDFs total, {len(pdfs) - len(pending)} already done, "
        f"{len(pending)} to process"
    )

    if not pending:
        return

    if config.dry_run:
        for p in pending:
            logger.info(f"[DRY RUN] Would process: {p.name}")
        return

    tasks = [
        _process_one(pdf, dirs.solutions_vision, dirs.solutions_structured, checkpoint, logger)
        for pdf in pending
    ]
    await asyncio.gather(*tasks)
    checkpoint.mark_step_done(STEP_NAME)
    logger.info(f"[{STEP_NAME}] Step complete")
