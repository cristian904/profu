"""Parse problem markdown files to structured markdown (fenced YAML) using Ollama."""
from __future__ import annotations

import asyncio
import traceback
from pathlib import Path

from profu_logging.feature_logger import FeatureLogger

from exam_parser.parsers.ollama_structured import extract_structured_problems_from_markdown
from exam_parser.parsers.structured_markdown import serialize_problems_from_normalized_dict
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
    """Read ``{stem}.md``, call Ollama, write ``{stem}.md`` structured artifact."""
    stem = pdf.stem
    vision_path = vision_dir / f"{stem}.md"
    structured_out = structured_dir / f"{stem}.md"

    if not vision_path.is_file():
        raise FileNotFoundError(
            f"Missing markdown for {pdf.name}; run extract_problems first. Expected: {vision_path}"
        )

    try:
        md_text = vision_path.read_text(encoding="utf-8")
        data: dict = await asyncio.to_thread(
            extract_structured_problems_from_markdown,
            md_text,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        md_body = serialize_problems_from_normalized_dict(data)
        structured_out.write_text(md_body, encoding="utf-8")
        logger.info(f"[{STEP_NAME}] Structured markdown written: {structured_out.name}")
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
    """Parse each problem PDF's markdown concurrently (Ollama local)."""
    pdfs = sorted(config.problems_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"[{STEP_NAME}] No PDFs found in {config.problems_dir}")
        return

    pending = [p for p in pdfs if not checkpoint.is_file_done(STEP_NAME, p.name)]
    logger.info(
        f"[{STEP_NAME}] {len(pdfs)} PDFs total, {len(pdfs) - len(pending)} already parsed, "
        f"{len(pending)} to process"
    )

    if not pending:
        return

    if config.dry_run:
        for p in pending:
            logger.info(f"[{STEP_NAME}] [DRY RUN] Would parse via Ollama: {p.name}")
        return

    tasks = [
        _process_one(pdf, dirs.problems_vision, dirs.problems_structured, checkpoint, logger)
        for pdf in pending
        if (dirs.problems_vision / f"{pdf.stem}.md").is_file()
    ]
    missing_md = [
        p.name
        for p in pending
        if not (dirs.problems_vision / f"{p.stem}.md").is_file()
    ]
    if missing_md:
        preview = ", ".join(missing_md[:5])
        extra = f" (+{len(missing_md) - 5} more)" if len(missing_md) > 5 else ""
        logger.warning(
            f"[{STEP_NAME}] Skipping {len(missing_md)} file(s) without markdown: {preview}{extra}"
        )

    if not tasks:
        logger.warning(f"[{STEP_NAME}] No markdown files to parse")
        return

    await asyncio.gather(*tasks)
    checkpoint.mark_step_done(STEP_NAME)
    logger.info(f"[{STEP_NAME}] Step complete")
