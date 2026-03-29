"""Step 1 — Parse problem PDFs: vision (PDF → md) then structured extraction (md → JSON)."""
from __future__ import annotations

import asyncio
import json
import traceback
from pathlib import Path

from profu_logging.feature_logger import FeatureLogger

from exam_parser.parsers.gemini_vision_parser import parse_with_gemini_vision
from exam_parser.parsers.vision_to_structured import extract_structured_problems
from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.settings import settings

STEP_NAME = "parse_problems"


async def _process_one(
    pdf: Path,
    vision_dir: Path,
    structured_dir: Path,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Parse a single problem PDF (vision + structured) and checkpoint."""
    stem = pdf.stem
    vision_out = vision_dir / f"{stem}.md"
    structured_out = structured_dir / f"{stem}.json"

    try:
        # Vision: PDF → markdown
        md_text: str = await asyncio.to_thread(parse_with_gemini_vision, pdf, settings.model_vision)
        vision_out.write_text(md_text, encoding="utf-8")
        logger.info(f"Vision done: {pdf.name}")

        # Structured: markdown → JSON (needs a temp .md file on disk)
        data: dict = await asyncio.to_thread(extract_structured_problems, vision_out, settings.model_structured)
        structured_out.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Structured done: {pdf.name}")

        checkpoint.mark_file_done(STEP_NAME, pdf.name)
    except Exception as exc:
        logger.error(exc, traceback=traceback.format_exc())


async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Discover problem PDFs, skip completed ones, fire all remaining concurrently."""
    pdfs = sorted(config.problems_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"No PDFs found in {config.problems_dir}")
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
        _process_one(pdf, dirs.problems_vision, dirs.problems_structured, checkpoint, logger)
        for pdf in pending
    ]
    await asyncio.gather(*tasks)
    checkpoint.mark_step_done(STEP_NAME)
    logger.info(f"[{STEP_NAME}] Step complete")
